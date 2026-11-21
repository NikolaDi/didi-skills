# 安装与调用

将完整的 `rigol-dho900-scope/` 复制或链接到宿主的 skills 目录，保留同级的 `scripts/`、`mcp/` 和 `references/`。默认调用器按自身路径启动随包源码，可以从任意工作目录执行。

## 首次准备 Python

需要 Python 3.10 或以上及 MCP SDK。以下 PowerShell 示例从**已安装的 skill 根目录**执行，使用独立虚拟环境；当前解释器已具备依赖时可直接运行调用器。

```powershell
$venv = Join-Path $env:LOCALAPPDATA 'didi-skills/venvs/rigol-dho900'
python -m venv $venv
$py = Join-Path $venv 'Scripts/python.exe'
& $py -m pip install ./mcp
& $py scripts/scope_mcp.py --list
```

USB 或 VXI-11 用户将安装项换成 `"./mcp[visa]"`，并使用本机可用的 VISA 后端与设备驱动。LAN 原生 socket 只需基本安装。Linux/macOS 使用虚拟环境的 `bin/python`。首次安装依赖需要软件源或本地 wheel 缓存。升级时更新整个 skill 目录；依赖发生变化时重新执行对应的安装命令，常驻服务需重新启动。

## 调用

`--list` 只进行 stdio 握手和工具发现。读 CH1 直流均值时，用本轮指定地址替换示例地址：

```powershell
'[{"tool":"measure","arguments":{"item":"VAVG","source":"CH1"}}]' | & $py scripts/scope_mcp.py --resource 192.168.1.100
```

调用器优先使用 `--resource`，其次取 `DHO900_RESOURCE`。LAN 支持 IP 或 IP:端口；USB 使用完整 VISA 资源名。两者均未指定时，调用器尝试枚举 RIGOL USB 设备，发现多台时列出候选。连接后核对 `*IDN?` 型号。一批 JSON 请求共用一次会话，逐项串行调用，结束后断开。截图传入 `save_path`，大波形用 `csv_path` 或 `export_waveform_csv`。单次瞬态先等自然 STOP，再读取 RAW。

## 宿主已有原生 MCP 工具

可将宿主的 stdio 命令指向上述虚拟环境的 Python，参数为**安装后** `mcp/serve.py` 的绝对路径。仅在确认服务已指向本份 skill 后复用已有工具和会话。首次调用 `connect(resource=…)` 时核对实际资源和型号，已连接的会话可能继续复用之前的仪器。宿主明确禁用仪器访问时遵循其权限设置。
