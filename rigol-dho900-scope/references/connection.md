# 发现服务与调用

- **宿主已提供工具。** 搜索服务名 `rigol-dho900` 或工具 `get_waveform`。已有会话用 `get_identity`；首次用 `connect(resource=…)` 或由服务端读取 `DHO900_RESOURCE`，核对返回的实际资源和型号。已有会话可能被复用，即使传入新地址也须核对返回值。可用工具以宿主发现结果为准。
- **宿主未提供工具。** 用已能导入 `mcp` 与 `rigol_dho900_mcp` 的 Python 执行 `scripts/scope_mcp.py`。调用器启动同一台机上的 MCP 服务并经 stdio 发起工具调用，一批请求共用同一会话。它不需要改客户端配置。仅在宿主支持执行本地脚本且当前任务允许访问仪器时使用；已注册服务若被明确禁用或拒绝权限，应报告原因。
- **设备地址。** 优先用本轮指定资源或 `DHO900_RESOURCE`。LAN 可用已知 IP 或 IP:端口，USB 使用完整 VISA 资源名。有 PyVISA 和可用的 VISA 后端时，调用器可自动选择唯一的 RIGOL USB 资源；多台时列出候选，不扫描局域网。连接后按 `*IDN?` 核对 DHO900 型号。

以下命令在**安装后的 skill 目录**运行。第一行只握手及列工具，不访问示波器；第二行在已授权测量时读取 CH1。Windows PowerShell 可通过标准输入传 JSON，避免引号被命令行吞掉。

```powershell
python scripts/scope_mcp.py --list
'[{"tool":"measure","arguments":{"item":"VAVG","source":"CH1"}}]' | python scripts/scope_mcp.py
```

可通过 `--resource` 显式选定仪器。每个请求均为实际 MCP 工具名及参数，结果按行输出。截图传入明确的 `save_path`，大波形用 `csv_path` 或 `export_waveform_csv`。需要根据 WAIT/STOP 决定何时继续时，分步读状态并判断；不要把布防和 RAW 读取无条件放进同一个请求列表。

本机维护的服务源码在 `E:\project\00-ai\rigol_dho900_mcp`。若服务器未安装，可用已有含 MCP SDK 的解释器，把服务的 `src` 加入当前进程的 `PYTHONPATH`。USB 还需 PyVISA 和已工作的 VISA 后端。本台架 Python 3.11 已能导入 MCP 服务，已有 PyVISA 位于 `E:\work\12-mppt-60a\code\mppt\build\rigol-mcp-deps`，需要时将该目录加入同一进程的 `PYTHONPATH`。其他电脑按其实际部署选择解释器与地址。缺少服务、依赖或设备时说明缺哪一项；安装 skill 本身不安装驱动或服务器。
