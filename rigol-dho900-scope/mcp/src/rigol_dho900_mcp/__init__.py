"""RIGOL DHO900 系列示波器 MCP 服务器。

依据：
- 《DHO900 用户手册》第 25 章 远程控制（SCPI / USB / LAN）
- 《DHO800/DHO900 Programming Guide》SCPI 命令参考
"""

__version__ = "0.1.0"

from .driver import DHO900, Waveform, DHO900Error
from .transport import Transport, SocketTransport, open_transport, DEFAULT_SOCKET_PORT

__all__ = [
    "DHO900",
    "Waveform",
    "DHO900Error",
    "Transport",
    "SocketTransport",
    "open_transport",
    "DEFAULT_SOCKET_PORT",
    "__version__",
]
