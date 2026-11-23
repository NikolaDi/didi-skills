# 嘉立创 EDA API 速查

只收录连接、原理图、PCB 修改和交付需要的常用接口。签名从本机已安装的 `easyeda-api` 1.1.36 参考文档提取，属于版本快照；新增调用仍须阅读完整参数、返回值及备注。若当前客户端与快照不一致，以相应版本官方文档及实际只读探测为准，不猜接口。

## 来源与版本

- 上游项目：<https://github.com/easyeda/easyeda-api-skill>；本地集成基线 1.1.36。
- 官方 API 文档：<https://prodocs.easyeda.com/en/api/>；按类名查找 API、枚举和接口。
- API 网关：<https://github.com/easyeda/eext-run-api-gateway>；扩展市场入口：<https://jlc-ext.com/item/oshwhub/run-api-gateway>。
- 桥接代码来源、许可证元数据和本地修改说明见 [第三方来源](../../THIRD_PARTY_NOTICES.md)。本包不包含 EDA 客户端或网关扩展安装文件。

## 调用约定

- `DMT_Project` 对应 `eda.dmt_Project`，`PCB_PrimitiveLine` 对应 `eda.pcb_PrimitiveLine`，`SCH_PrimitiveComponent` 对应 `eda.sch_PrimitiveComponent`；接口对象的方法如 `IPCB_PrimitiveComponent.done()` 调用在读取到的对象上。
- PCB 数值单位 mil；SCH 数值单位 10 mil。毫米转换分别为 `mm / 0.0254`、`mm / 0.254`。
- `get` 的单对象和多对象重载可能返回不同结构，必须查对应重载；创建或修改失败可能返回 `undefined`，不能直接读取属性。
- 图元异步修改使用 `const editable = primitive.toAsync(); editable.setState_X(x); ...; await editable.done();`，或使用该图元类公开的 `modify`。`done()` 也需要 `await`。
- PCB 层号经 `EPCB_LayerId` 确认为 TOP=1、BOTTOM=2、TOP_SILKSCREEN=3、BOTTOM_SILKSCREEN=4、BOARD_OUTLINE=11；其他层另查枚举。`setLayerVisible` 的第二参数含义是“隐藏其他层”，不是目标层可见开关。
- `importChanges(uuid)` 的可选参数为**原理图 UUID**，不是 PCB、图页或板 UUID；不传时使用同一 Board 关联原理图，独立 PCB 须明确提供对应原理图 UUID。
- `check(..., true)` 返回详细数组。按当前版本结构展开分组，只统计实际违规条目，按原始严重度汇总并保留关联对象。同一条违规涉及多个对象仍计一次。顶层数组长度在分组模式下表示类别数。结构或严重度无法识别时，保留原始结果并标明未统计范围及原因。`check(..., false)` 返回整体通过状态，布尔值不能给出违规数量。
- `createNetFlag` 创建电源或地符号；普通网络标签关联导线的网络名，`createNetPort` 创建端口。按已确认的方案选择对应的电气对象。

## 按任务查找

| 操作 | 类/对象 |
| --- | --- |
| 识别工程和文档 | DMT_Project、DMT_SelectControl、DMT_EditorControl |
| 器件搜索、符号、引脚 | LIB_Device、SCH_PrimitiveComponent |
| 原理图导线、标签及检查 | SCH_PrimitiveWire、SCH_PrimitiveComponent、SCH_Document、SCH_Drc |
| 导入、保存及视图 | PCB_Document、PCB_Layer |
| 器件、铜线、过孔及文字 | PCB_PrimitiveComponent、PCB_PrimitiveLine、PCB_PrimitiveVia、PCB_PrimitiveAttribute |
| 实际边界、网络和规则检查 | PCB_Primitive、PCB_Net、PCB_Drc |
| 原生项目、源码和图片导出 | SYS_FileManager、DMT_EditorControl |

## 常用签名

### DMT_SelectControl

`getCurrentDocumentInfo`

```typescript
function getCurrentDocumentInfo(): Promise<IDMT_EditorDocumentItem | undefined>;
```

### DMT_Project

`getCurrentProjectInfo`

```typescript
function getCurrentProjectInfo(): Promise<IDMT_ProjectItem | undefined>;
```

`openProject`

```typescript
function openProject(projectUuid: string): Promise<boolean>;
```

### DMT_EditorControl

`activateDocument`

```typescript
function activateDocument(tabId: string): Promise<boolean>;
```

`openDocument`

```typescript
function openDocument(documentUuid: string, splitScreenId?: string): Promise<string | undefined>;
```

`getCurrentRenderedAreaImage`

```typescript
function getCurrentRenderedAreaImage(tabId?: string): Promise<Blob | undefined>;
```

### LIB_Device

`search`

```typescript
function search(
	key: string,
	libraryUuid?: string,
	classification?: ILIB_ClassificationIndex | Array<string>,
	symbolType?: ELIB_SymbolType,
	itemsOfPage?: number,
	page?: number,
): Promise<Array<ILIB_DeviceSearchItem>>;
```

`get`

```typescript
function get(deviceUuid: string, libraryUuid?: string): Promise<ILIB_DeviceItem | undefined>;
```

### SCH_PrimitiveComponent

`create`

```typescript
function create(
	component:
		| { libraryType?: ELIB_LibraryType.DEVICE; libraryUuid: string; uuid: string }
		| ILIB_DeviceItem
		| ILIB_DeviceSearchItem
		| { libraryType: ELIB_LibraryType.SYMBOL; libraryUuid: string; uuid: string }
		| ILIB_SymbolItem
		| ILIB_SymbolSearchItem,
	x: number,
	y: number,
	subPartName?: string,
	rotation?: number,
	mirror?: boolean,
	addIntoBom?: boolean,
	addIntoPcb?: boolean,
): Promise<ISCH_PrimitiveComponent | undefined>;
```

`createNetFlag`

```typescript
function createNetFlag(
	identification: 'Power' | 'Ground' | 'AnalogGround' | 'ProtectGround',
	net: string,
	x: number,
	y: number,
	rotation?: number,
	mirror?: boolean,
): Promise<ISCH_PrimitiveComponent | undefined>;
```

`getAllPinsByPrimitiveId`

```typescript
function getAllPinsByPrimitiveId(
	primitiveId: string,
): Promise<Array<ISCH_PrimitiveComponentPin> | undefined>;
```

### SCH_PrimitiveWire

`create`

```typescript
function create(
	line: Array<number> | Array<Array<number>>,
	net?: string,
	color?: string | null,
	lineWidth?: number | null,
	lineType?: ESCH_PrimitiveLineType | null,
): Promise<ISCH_PrimitiveWire | undefined>;
```

`getAll`

```typescript
function getAll(net?: string | Array<string>): Promise<Array<ISCH_PrimitiveWire>>;
```

### SCH_Document

`save`

```typescript
function save(): Promise<boolean>;
```

### SCH_ManufactureData

在目标原理图页中读取 Protel2 网表或取得当前单页的 PDF。下例中的 `fileName` 与 `pageSize` 取自当前任务，两个方法均返回 `File | undefined`。

```javascript
const netlist = await eda.sch_ManufactureData.getNetlistFile(fileName, 'Protel2');
const pdf = await eda.sch_ManufactureData.getExportDocumentFile(
    fileName, 'PDF', { size: pageSize }, 'Current Schematic Page'
);
```

### SCH_Drc

`check`

```typescript
function check(
	strict: boolean,
	userInterface: boolean,
	includeVerboseError: false,
): Promise<boolean>;
function check(
	strict: boolean,
	userInterface: boolean,
	includeVerboseError: true,
): Promise<Array<any>>;
```

### PCB_Document

`importChanges`

```typescript
function importChanges(uuid?: string): Promise<boolean>;
```

`save`

```typescript
function save(): Promise<boolean>;
```

`zoomToBoardOutline`

```typescript
function zoomToBoardOutline(): Promise<boolean>;
```

### PCB_PrimitiveComponent

`getAll`

```typescript
function getAll(
	layer?: TPCB_LayersOfComponent,
	primitiveLock?: boolean,
): Promise<Array<IPCB_PrimitiveComponent>>;
```

`getAllPinsByPrimitiveId`

```typescript
function getAllPinsByPrimitiveId(
	primitiveId: string,
): Promise<Array<IPCB_PrimitiveComponentPad> | undefined>;
```

`modify`

```typescript
function modify(
	primitiveId: string | IPCB_PrimitiveComponent,
	property: {
		layer?: TPCB_LayersOfComponent;
		x?: number;
		y?: number;
		rotation?: number;
		primitiveLock?: boolean;
		addIntoBom?: boolean;
		designator?: string | null;
		name?: string | null;
		uniqueId?: string | null;
		manufacturer?: string | null;
		manufacturerId?: string | null;
		supplier?: string | null;
		supplierId?: string | null;
		otherProperty?: { [key: string]: any };
	},
): Promise<IPCB_PrimitiveComponent | undefined>;
```

### PCB_PrimitiveLine

`create`

```typescript
function create(
	net: string,
	layer: TPCB_LayersOfLine,
	startX: number,
	startY: number,
	endX: number,
	endY: number,
	lineWidth?: number,
	primitiveLock?: boolean,
): Promise<IPCB_PrimitiveLine | undefined>;
```

`getAll`

```typescript
function getAll(
	net?: string,
	layer?: TPCB_LayersOfLine,
	primitiveLock?: boolean,
): Promise<Array<IPCB_PrimitiveLine>>;
```

`delete`

```typescript
function delete(primitiveIds: string | IPCB_PrimitiveLine | Array<string> | Array<IPCB_PrimitiveLine>): Promise<boolean>;
```

### PCB_PrimitiveVia

`create`

```typescript
function create(
	net: string,
	x: number,
	y: number,
	holeDiameter: number,
	diameter: number,
	viaType?: EPCB_PrimitiveViaType,
	designRuleBlindViaName?: string | null,
	solderMaskExpansion?: IPCB_PrimitiveSolderMaskAndPasteMaskExpansion | null,
	primitiveLock?: boolean,
): Promise<IPCB_PrimitiveVia | undefined>;
```

`getAll`

```typescript
function getAll(net?: string, primitiveLock?: boolean): Promise<Array<IPCB_PrimitiveVia>>;
```

`delete`

```typescript
function delete(primitiveIds: string | IPCB_PrimitiveVia | Array<string> | Array<IPCB_PrimitiveVia>): Promise<boolean>;
```

### PCB_Primitive

`getPrimitivesBBox`

```typescript
function getPrimitivesBBox(
	primitiveIds: Array<string | IPCB_Primitive>,
): Promise<{ minX: number; minY: number; maxX: number; maxY: number } | undefined>;
```

### PCB_PrimitiveAttribute

`modify`

```typescript
function modify(
	primitiveId: string | IPCB_PrimitiveAttribute,
	property: {
		layer?: TPCB_LayersOfImage;
		x?: number;
		y?: number;
		key?: string;
		value?: string;
		keyVisible?: boolean;
		valueVisible?: boolean;
		fontFamily?: string;
		fontSize?: number;
		lineWidth?: number;
		alignMode?: EPCB_PrimitiveStringAlignMode;
		rotation?: number;
		reverse?: boolean;
		expansion?: number;
		mirror?: boolean;
		primitiveLock?: boolean;
	},
): Promise<IPCB_PrimitiveAttribute | undefined>;
```

### PCB_Layer

`setLayerVisible`

```typescript
function setLayerVisible(
	layer?: TPCB_LayersInTheSelectable | Array<TPCB_LayersInTheSelectable>,
	setOtherLayerInvisible?: boolean,
): Promise<boolean>;
```

`selectLayer`

```typescript
function selectLayer(layer: TPCB_LayersInTheSelectable): Promise<boolean>;
```

### PCB_Net

`getNetlist`

```typescript
function getNetlist(type?: ESYS_NetlistType): Promise<string>;
```

### PCB_Drc

`check`

```typescript
function check(
	strict: boolean,
	userInterface: boolean,
	includeVerboseError: false,
): Promise<boolean>;
function check(
	strict: boolean,
	userInterface: boolean,
	includeVerboseError: true,
): Promise<Array<any>>;
```

### SYS_FileManager

`getDocumentSource`

```typescript
function getDocumentSource(): Promise<string | undefined>;
```

`getProjectFile`

```typescript
function getProjectFile(
	fileName?: string,
	password?: string,
	fileType?: 'epro' | 'epro2',
): Promise<File | undefined>;
```

### IPCB_PrimitiveComponent

`toAsync`

```typescript
function toAsync(): IPCB_PrimitiveComponent;
```

`done`

```typescript
function done(): Promise<IPCB_PrimitiveComponent>;
```
