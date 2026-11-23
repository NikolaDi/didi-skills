# 工程操作

从已核对目标的会话开始。[连接与执行](connection.md)说明怎样取得工程、文档和窗口标识；[接口速查](api-usage.md)列出以下调用的参数与重载。

## 准备编辑

1. 从当前工程树确认目标图页、所属原理图及关联的板。通过 `dmt_EditorControl.openDocument` 或 `activateDocument` 打开或激活文档后重新探测。切换工程前先处理当前未保存内容。
2. 修改前用 `sys_FileManager.getDocumentSource()` 读取当前文档，保存可恢复的基线。原理图坐标每单位 0.254 mm，PCB 每单位 0.0254 mm。按目标文档换算单位，并单独处理原点、旋转及底面镜像。
3. 图元使用对应类型公开的 `modify`，或 `toAsync()`、属性设置、`await done()`。每批操作检查实际返回值，再读回对象；导线自动拆分或合并后重新获取图元 ID。

## 原理图

1. 用 `lib_Device.search` 搜索已确认的器件，再用 `get` 读取具体库条目。将检索对象或完整的库 UUID 与器件 UUID 传给 `sch_PrimitiveComponent.create`，记录返回的实例 ID。
2. 用 `getAllPinsByPrimitiveId` 取得放置或旋转后的引脚坐标，按确认的连接用 `sch_PrimitiveWire.create` 绘线。需要普通网络标签时设置导线的网络名及标签显示；电源或地用 `createNetFlag` 设置网络及方向。修改标签时分别核对电气锚点和显示文字。模块框线使用图形对象。
3. 读回导线、引脚、网络及装配属性。保存目标图页，运行原理图检查；需要单页图纸时选择当前原理图页，核对导出页数、纸张和边界。

## 读取 BOM 源数据

1. 只读导出前，通过[连接流程](connection.md)定位用户指定的工程和图页。若用户指的是编辑器里刚改的图，读取该窗口的活动设计。多页工程覆盖该板关联的所有原理图页，记录采用的装配变体。
2. 用 `sch_PrimitiveComponent.getAll` 枚举目标范围的实例，读取 `getState_Designator()`、`getState_Footprint()` 和 `getState_AddIntoBom()`。最后一个字段只表示是否加入 BOM。另从所选装配变体或图面取得实装依据。只有项目明确约定该标志与贴装状态等价时，才按其值映射实装与 DNP；导出表中缺少某行也不足以判为 DNP。页源缺少实例覆盖字段时读回有效值。排除图框等非物料对象，多单元符号按物理位号合并。
3. 逐位号检查图页实例的可见属性，包括自定义参数标注。对 `={Value}` 等表达式读取当前实例的显示结果。遇到属性继承、标注归属不清或原生 BOM 导出值与图面有差异，用同版图页导出的 PDF 按位号核对，再按[BOM 与成本估算](../bom-and-costing.md)处理差异和归并物料。

## 导入 PCB 与编辑板图

1. 从工程树区分图页 UUID、原理图 UUID 和 PCB UUID。先保存源图并核实封装，再激活目标 PCB。调用 `eda.pcb_Document.importChanges()` 导入同一 Board 关联的原理图；独立目标板显式传入对应的**原理图 UUID**。也可在目标 PCB 中使用「从原理图导入变更」。
2. 检查导入返回值。用 `pcb_PrimitiveComponent.getAll`、`getAllPinsByPrimitiveId` 及 `pcb_Net.getNetlist` 读回实际器件、焊盘与网络，按位号和焊盘编号对照源图。出现差异时定位缺件、封装映射或连接，避免重复执行全板导入。
3. 读取实际板框、锁定器件、层和封装边界。用 `pcb_PrimitiveComponent.modify` 摆件，在 `BOARD_OUTLINE` 层按已定外形编辑板框。脚本将逐网手工确定的线段和过孔分别写入 `pcb_PrimitiveLine` 与 `pcb_PrimitiveVia`，读回网络、起止坐标、层和尺寸。通过对应属性图元调整丝印及位号显示。
4. 完成影响铜皮的编辑后，执行当前版本公开的重建铺铜操作，或调用客户端菜单中的重建命令。检查实际填充结果，再启动本轮 DRC。

## 检查与导出

- **原生检查。** 在原理图页执行 `await eda.sch_Drc.check(true, false, true)`，在 PCB 执行 `await eda.pcb_Drc.check(true, false, true)`。按[检查结果的调用约定](api-usage.md#调用约定)统计实际违规，记录严重度与关联对象。PCB 另查原生未连接结果。比较网络时，可从原理图导出 Protel2 网表，并从目标板读取对应格式的网表。
- **工程文件。** 保存操作按文档类型调用 `sch_Document.save()` 或 `pcb_Document.save()` 并检查返回值。用 `sys_FileManager.getProjectFile(fileName, undefined, 'epro')` 取得原生包。仅受托只读导出时保持当前工程状态，并标明所导出版次。
- **图纸与预览。** 原理图整页 PDF 用 `sch_ManufactureData.getExportDocumentFile`，明确选择图页范围和图幅。当前视区截图用 `dmt_EditorControl.getCurrentRenderedAreaImage`；PCB 预览先适配板框、选择相应图层并取消选择高亮。
- **文件回传。** 对返回的 `File` 或 `Blob` 读取 `arrayBuffer()`。走 JSON 桥接时分块编码，由外部客户端解码并保存；文件过大时可用客户端原生导出。重新打开交付包核对板、图页与库绑定，检查 PDF 页数和图面，并报告实际取得的检查结果。
