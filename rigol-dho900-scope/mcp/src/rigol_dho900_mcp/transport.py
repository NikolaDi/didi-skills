"""仪器通信层：LAN 原生 SCPI socket 与可选 PyVISA（USBTMC/VXI-11）。

DHO800/DHO900 后面板 LAN 口默认开放原生 SCPI socket（实测端口 5555，
可通过 :LAN:VISA? SOCKet 从仪器读回确认）。USBTMC 与 VXI-11(INSTR)
资源由 PyVISA 处理。
"""

from __future__ import annotations

import re
import socket
from abc import ABC, abstractmethod

from .waveforms import strip_tmc_block

# DHO800/DHO900 原生 SCPI socket 端口（社区实测值，非手册明示）
DEFAULT_SOCKET_PORT = 5555


class TransportError(RuntimeError):
    """通信层错误。"""


class Transport(ABC):
    """一次完整写入/查询的传输抽象。"""

    @abstractmethod
    def write(self, command: str) -> None: ...

    @abstractmethod
    def _read_response(self) -> bytes:
        """读取一次完整响应（ASCII 以行为尾，二进制以 TMC 块为单位）。"""

    @abstractmethod
    def close(self) -> None: ...

    def query(self, command: str) -> str:
        self.write(command)
        return self._read_response().decode("utf-8", errors="replace").strip("\r\n")

    def query_binary(self, command: str) -> bytes:
        self.write(command)
        return strip_tmc_block(self._read_response())


class SocketTransport(Transport):
    """TCP 原生 SCPI socket（命令以 \\n 结尾）。"""

    def __init__(self, host: str, port: int = DEFAULT_SOCKET_PORT, timeout: float = 10.0):
        try:
            self._sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as exc:
            raise TransportError(f"无法连接 {host}:{port} —— {exc}") from exc
        self._sock.settimeout(timeout)
        self._timeout = timeout

    def write(self, command: str) -> None:
        try:
            self._sock.sendall(command.strip().encode("ascii", errors="replace") + b"\n")
        except OSError as exc:
            raise TransportError(f"发送失败: {exc}") from exc

    def _recv_exact(self, n: int) -> bytes:
        chunks: list[bytes] = []
        remaining = n
        while remaining > 0:
            try:
                chunk = self._sock.recv(min(remaining, 65536))
            except socket.timeout as exc:
                raise TransportError(f"读取超时（还需 {remaining} 字节）") from exc
            if not chunk:
                raise TransportError("连接已关闭")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_response(self) -> bytes:
        first = self._recv_exact(1)
        if first == b"#":
            n_digits = int(self._recv_exact(1))
            if n_digits == 0:
                raise TransportError("不支持不定长 TMC 块（#0）")
            digits = self._recv_exact(n_digits)
            size = int(digits)
            payload = self._recv_exact(size)
            self._eat_terminator()
            return b"#" + str(n_digits).encode("ascii") + digits + payload

        buf = bytearray(first)
        while True:
            try:
                byte = self._sock.recv(1)
            except socket.timeout as exc:
                raise TransportError("读取响应超时") from exc
            if not byte or byte == b"\n":
                break
            buf += byte
        return bytes(buf)

    def _eat_terminator(self) -> None:
        self._sock.settimeout(0.2)
        try:
            self._sock.recv(1)
        except OSError:
            pass
        finally:
            self._sock.settimeout(self._timeout)

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class VisaTransport(Transport):
    """PyVISA 传输，用于 USBTMC / VXI-11 / GPIB 等 VISA 资源。"""

    def __init__(self, resource: str, timeout: float = 10.0):
        try:
            import pyvisa
        except ImportError as exc:
            raise TransportError(
                "该资源需要 PyVISA：请先 `pip install pyvisa pyvisa-py`，"
                "或改用 LAN 原生 socket（直接传 IP 地址）"
            ) from exc
        self._rm = pyvisa.ResourceManager()
        try:
            self._inst = self._rm.open_resource(resource)
        except Exception as exc:  # pyvisa 抛出后端特定异常
            raise TransportError(f"打开资源 {resource} 失败: {exc}") from exc
        self._inst.timeout = int(timeout * 1000)

    def write(self, command: str) -> None:
        self._inst.write(command.strip())

    def _read_response(self) -> bytes:
        return bytes(self._inst.read_raw())

    def close(self) -> None:
        try:
            self._inst.close()
            self._rm.close()
        except Exception:
            pass


_SOCKET_RE = re.compile(r"^TCPIP\d*::(?P<host>[^:]+)::(?P<port>\d+)::SOCK$", re.IGNORECASE)
_VISA_RE = re.compile(r"^(USB|TCPIP|ASRL|GPIB)", re.IGNORECASE)


def open_transport(resource: str, timeout: float = 10.0, port: int = DEFAULT_SOCKET_PORT) -> Transport:
    """按资源字符串形态选择传输方式。

    - ``TCPIP::host::5555::SOCK`` → 原生 socket
    - ``USB...`` / ``TCPIP...::INSTR`` / ``ASRL...`` 等 VISA 资源 → PyVISA
    - 裸 IP / 主机名 / ``host:port`` → 原生 socket（默认端口 5555）
    """
    res = resource.strip()
    if not res:
        raise TransportError("资源字符串为空")

    m = _SOCKET_RE.match(res)
    if m:
        return SocketTransport(m.group("host"), int(m.group("port")), timeout)

    if _VISA_RE.match(res):
        return VisaTransport(res, timeout)

    host, _, maybe_port = res.rpartition(":")
    if host and maybe_port.isdigit():
        return SocketTransport(host, int(maybe_port), timeout)
    return SocketTransport(res, port, timeout)
