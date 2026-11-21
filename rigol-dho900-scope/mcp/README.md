# RIGOL DHO900 MCP

本目录包含 DHO914/S、DHO924/S 的 Python 服务、SCPI 驱动和离线测试。安装整个 skill 后，在其根目录按[连接说明](../references/connection.md)准备 Python 环境。调用器和原生 MCP 客户端均可通过本目录的 `serve.py` 启动 stdio 服务。

驱动负责串行收发、波形分块和换算。单次触发完成及波形可用性的判断见[采集说明](../references/capture.md)，实测的慢时基查询限制和错误响应见[台架记录](../references/dho924s-bench-notes.md)。

在 skill 根目录用虚拟环境的 Python 运行 `python -m pip install "./mcp[dev]"`，再执行 `python -m pytest mcp/tests -q`。安装目录迁移或启动入口有修改时一并验证 `python scripts/scope_mcp.py --list`。
