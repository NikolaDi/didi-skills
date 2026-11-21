---
name: rigol-dho900-scope
description: 通过 RIGOL DHO900 MCP 操作 DHO914、DHO914S、DHO924、DHO924S。当用户要求用台架示波器查看 CH1～CH4、测纹波或频率、截图、捕获单次瞬态、导出波形或排查采集通信时使用。不用于纯电路理论、离线分析已有波形、控制电源或烧录 MCU。
---

# RIGOL DHO900 示波器

用户说「看一下 CH1 电压」或「用示波器抓卸载波形」时，默认用已安装 skill 的 [stdio 调用器](scripts/scope_mcp.py)启动随包服务。用 `--list` 可先核对工具。若宿主已经通过本份 skill 的 `mcp/serve.py` 建立会话，可直接复用。一次测量只用一个会话；目标仪器已被其他服务占用时先协调释放。Python 环境、资源地址和调用示例见[连接说明](references/connection.md)。

1. **辨认目标。** 在有仪器操作授权的任务中，连接既定资源并检查返回的型号；多台设备时依据资源名或序列号选定。仅解释问题或准备离线方案时无需连接。涉及被测设备的接线、上电和触发条件遵循当前台架约定。
2. **按请求选工具。** 查当前直流均值用 `measure(item="VAVG", source="CH1")`，峰峰值用 `VPP`，频率用 `FREQuency`。面板截图用 `get_screenshot(save_path=绝对路径)`。查看当前屏幕用 `get_waveform(source="CH1", mode="NORMal", data_format="WORD", points=1000)`。读取当前状态时保留现有量程、触发和 RUN/STOP；报告实际通道、单位、有效点数或读数。仪器无效哨兵、截幅或掉探头时，报出可疑读数并核对。
3. **抓单次事件。** 按测量目的设置通道、时基、触发，核对实际采样率、深度、预触发窗口。用 `acquire(action="single")` 布防。真实边沿触发时等事件到来；明确要强制触发时等预触发填满、确认 WAIT，再发一次 `force_trigger`。有界等待自然 STOP，再用 `export_waveform_csv` 或 `get_waveform` 的 RAW 模式导出。RAW 读取会发 STOP，提前读取可能截断事件。关键瞬态至少核对时间覆盖、幅值范围和完整点数；要证明冻结一致性时，双读同一帧，期间保持 STOP。
4. **解释异常。** 遇到长时基 STOP/AUTO、`*OPC?` 返回 0、直流近零、屏幕与 RAW 不一致或霍尔钳偏差时，按[采集判据与实测经验](references/capture.md)定位。仪器故障单独处理。开关节点和高侧 Vgs 要确认合适的差分测量方式；普通地夹只接确认与保护地等电位的点。
