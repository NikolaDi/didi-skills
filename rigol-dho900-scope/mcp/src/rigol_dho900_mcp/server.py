"""RIGOL DHO900 系列示波器 MCP 服务器（stdio）。

面向 LLM agent 暴露连接管理、SCPI 透传、波形读取、截图、自动测量、
采集控制与通道/时基/触发设置工具。
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import threading
from typing import Any, Literal

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.server.fastmcp.utilities.types import Image
except ModuleNotFoundError:  # mcp 2.x：FastMCP 更名为 MCPServer
    from mcp.server.mcpserver import Image, MCPServer as _Server

from .driver import DHO900, DHO900Error, MEASURE_ITEMS
from .waveforms import write_csv

logger = logging.getLogger("rigol_dho900_mcp")

mcp = _Server(
    "rigol-dho900",
    instructions=(
        "RIGOL DHO900 系列数字示波器（DHO914/DHO914S/DHO924/DHO924S）控制服务器。"
        "典型流程：connect() → setup_channel/setup_timebase/setup_trigger_edge → "
        "acquire('run'|'single') → get_waveform()/measure()/get_screenshot()。"
        "波形默认 NORMal 模式（屏幕 1000 点）；需要完整内存波形用 mode='RAW'（会自动停止采集）。"
        "任意 SCPI 命令可用 scpi_write/scpi_query 透传。"
    ),
)

_scope: DHO900 | None = None
_scope_lock = threading.Lock()


def _get_scope(resource: str = "", timeout: float | None = None) -> DHO900:
    global _scope
    with _scope_lock:
        if _scope is not None and _scope.connected:
            return _scope
        res = resource or os.environ.get("DHO900_RESOURCE", "")
        if not res:
            raise DHO900Error(
                "尚未连接仪器。请调用 connect(resource=...) 并传入仪器地址"
                "（如 192.168.1.100 或 USB0::0x1AB1::0x044C::INSTR），"
                "或设置环境变量 DHO900_RESOURCE"
            )
        to = timeout if timeout is not None else float(os.environ.get("DHO900_TIMEOUT", "10"))
        _scope = DHO900(res, timeout=to)
        _scope.connect()
        logger.info("connected: %s", res)
        return _scope


def _disconnect_scope() -> None:
    global _scope
    with _scope_lock:
        if _scope is not None:
            _scope.close()
            _scope = None


@mcp.tool()
def connect(resource: str = "", timeout: float = 10.0) -> dict[str, Any]:
    """连接示波器并返回仪器身份信息。

    resource 支持：LAN 原生 socket（`192.168.1.100`、`192.168.1.100:5555`、
    `TCPIP::192.168.1.100::5555::SOCK`）、VXI-11（`TCPIP0::192.168.1.100::inst0::INSTR`，
    需要 pyvisa）、USBTMC（`USB0::0x1AB1::0x044C::000000::INSTR`，需要 pyvisa）。
    留空则使用环境变量 DHO900_RESOURCE。
    """
    scope = _get_scope(resource, timeout)
    return {"resource": scope.resource, "idn": scope.idn(), "connected": True}


@mcp.tool()
def disconnect() -> str:
    """断开与示波器的连接。"""
    _disconnect_scope()
    return "已断开连接"


@mcp.tool()
def get_identity() -> dict[str, Any]:
    """查询仪器身份（*IDN?）、运行状态与存储深度。"""
    scope = _get_scope()
    info: dict[str, Any] = {"idn": scope.idn()}
    try:
        info["trigger_status"] = scope.trigger_status()
    except DHO900Error:
        pass
    try:
        info["memory_depth"] = scope.memory_depth()
    except DHO900Error:
        pass
    return info


@mcp.tool()
def scpi_write(command: str) -> str:
    """发送任意 SCPI 写命令（透传，无返回值）。

    例如：`:CHANnel1:SCALe 0.5`、`:TRIGger:EDGE:LEVel 0.2`、`:STOP`。
    """
    _get_scope().write(command)
    return f"已发送: {command}"


@mcp.tool()
def scpi_query(command: str) -> str:
    """发送任意 SCPI 查询命令并返回响应文本。

    例如：`:WAVeform:PREamble?`、`:MEASure:ITEM? VPP,CHANnel1`、`:SYSTem:ERRor?`。
    本机DHO924S 00.01.02在200ms/div、Auto ROLL=0时MODE?会超时并报-232；
    普通捕获改为独立核对TIMebase:XY:ENABle?=0、TIMebase:ROLL?=0及实际时基。
    不将查询失败伪装为MAIN；具体实测限制见README。
    """
    return _get_scope().query(command)


@mcp.tool()
def get_waveform(
    source: str = "CHANnel1",
    mode: Literal["NORMal", "MAXimum", "RAW"] = "NORMal",
    data_format: Literal["WORD", "BYTE", "ASCii"] = "WORD",
    points: int | None = None,
    start: int = 1,
    max_points: int = 512,
    include_arrays: bool = True,
    csv_path: str = "",
) -> dict[str, Any]:
    """读取波形数据并换算为时间(s)/电压(V)。

    source: CHANnel1~4、MATH1~4、D0~D15（数字通道仅 DHO900）。
    mode: NORMal=屏幕数据（≤1000 点，随时可读）；RAW=完整内存数据（仅停止态，
    本工具会自动 :STOP 后分块读取，points=None 时读整个存储深度）；
    MAXimum=RUN 读屏幕/STOP 读内存。
    返回统计量（min/max/pp/mean）与抽稀后的 t/v 数组（min/max 包络，最多 max_points 点）；
    csv_path 非空时把完整数据写入 CSV 并在结果中给出路径。
    """
    scope = _get_scope()
    wf = scope.read_waveform(source=source, mode=mode, data_format=data_format,
                             points=points, start=start)
    result: dict[str, Any] = {
        "source": wf.source,
        "mode": wf.mode,
        "format": wf.format,
        "points": wf.points,
        "stats": wf.stats,
        "preamble": wf.preamble,
    }
    if csv_path:
        result["csv_path"] = wf.to_csv(csv_path)
    if include_arrays:
        t, v = wf.downsampled(max_points)
        result["t_s"] = t
        result["v_v"] = v
        result["returned_points"] = len(v)
    return result


@mcp.tool()
# 混合Image/文本必须走MCP内容块；list[Any]会让SDK 2.x错误生成JSON输出模型。
def get_screenshot(save_path: str = "", image_format: Literal["PNG", "BMP", "JPG"] = "PNG"):
    """截取示波器当前屏幕并返回图像，同时保存到本地文件。

    save_path 留空则保存到当前目录（自动命名）。返回内容包含图像本体与文件路径。
    """
    data, path = _get_scope().screenshot(save_path, image_format)
    blocks: list[Any] = []
    try:
        blocks.append(Image(data=data, format=image_format.lower()))
    except Exception:
        blocks.append({
            "image_base64": base64.b64encode(data).decode("ascii"),
            "format": image_format.lower(),
        })
    blocks.append(f"截图已保存到: {path}")
    return blocks


@mcp.tool()
def measure(item: str, source: str = "CHANnel1", source2: str = "") -> dict[str, Any]:
    """执行单项自动测量并返回数值。

    item 可选：VPP（峰峰值）、VMAX、VMIN、VAVG、VRMS、FREQuency、PERiod、
    RTIMe（上升时间）、FTIMe（下降时间）、PWIDth、NWIDth、PDUTy、NDUTy、
    OVERshoot、PREShoot、PSLewrate、NSLewrate、VUPPer、VMID、VLOWer、
    VARiance、PPULses、NPULses、PEDGes、NEDGes、ACRMs 等。
    双源测量（相位/延迟类，如 RRPHase、RRDelay）通过 source2 传第二个信源。
    """
    value = _get_scope().measure(item, source, source2 or None)
    return {"item": item.upper(), "source": source, "value": value}


@mcp.tool()
def acquire(action: Literal["run", "stop", "single", "force_trigger", "autoset", "clear"]) -> dict[str, Any]:
    """采集控制：run=运行，stop=停止，single=单次触发，force_trigger=强制触发，
    autoset=自动设置（:AUToset），clear=清除已显示波形。返回当前触发状态。
    single/force_trigger返回时可能仍为WAIT/TD/RUN，须限时轮询到STOP再读取冻结波形。
    """
    scope = _get_scope()
    actions = {
        "run": scope.run,
        "stop": scope.stop,
        "single": scope.single,
        "force_trigger": scope.force_trigger,
        "autoset": scope.autoset,
        "clear": scope.clear_sweep,
    }
    actions[action]()
    status = ""
    try:
        status = scope.trigger_status()
    except DHO900Error:
        pass
    return {"action": action, "trigger_status": status}


@mcp.tool()
def get_errors() -> list[str]:
    """排空并返回仪器错误队列（:SYSTem:ERRor?），用于排查之前命令的失败原因。"""
    return _get_scope().errors()


@mcp.tool()
def setup_channel(
    channel: str,
    display: bool | None = None,
    scale: float | None = None,
    offset: float | None = None,
    coupling: Literal["AC", "DC", "GND"] | None = None,
    bwlimit: str | bool | None = None,
    probe: float | None = None,
) -> dict[str, Any]:
    """设置模拟通道参数。channel: CHANnel1~4 或 CH1~CH4。

    display=通道开关；scale=垂直档位 V/div；offset=垂直偏移 V；
    coupling=AC/DC/GND；bwlimit=True 表示 20 MHz 带宽限制（也可传 "20M"/"OFF"）；
    probe=探头倍率（如 1、10、100）。仅传需要修改的参数。
    """
    _get_scope().set_channel(channel, display, scale, offset, coupling, bwlimit, probe)
    return {"channel": channel, "applied": True}


@mcp.tool()
def setup_timebase(
    scale: float | None = None,
    offset: float | None = None,
    mode: Literal["MAIN", "XY", "ROLL"] | None = None,
) -> dict[str, Any]:
    """设置水平时基。scale=时基 s/div（如 1e-3 表示 1 ms/div）；offset=水平位移 s；
    mode=MAIN/XY/ROLL。仅传需要修改的参数。"""
    _get_scope().set_timebase(scale, offset, mode)
    return {"scale": scale, "offset": offset, "mode": mode}


@mcp.tool()
def setup_trigger_edge(
    source: str | None = None,
    level: float | None = None,
    slope: Literal["POSitive", "NEGative", "RFALl"] | None = None,
    sweep: Literal["AUTO", "NORMal", "SINGle"] | None = None,
    holdoff: float | None = None,
) -> dict[str, Any]:
    """设置边沿触发（自动切到 EDGE 模式）。

    source=触发信源（CHANnel1~4 等）；level=触发电平 V；
    slope=POSitive/NEGative/RFALl(双沿)；sweep=AUTO/NORMal/SINGle；
    holdoff=触发释抑 s。仅传需要修改的参数。
    """
    _get_scope().set_trigger_edge(source, level, slope, sweep, holdoff)
    return {"mode": "EDGE", "source": source, "level": level, "slope": slope, "sweep": sweep}


@mcp.tool()
def export_waveform_csv(csv_path: str, source: str = "CHANnel1", mode: str = "RAW",
                        data_format: str = "WORD", points: int | None = None) -> dict[str, Any]:
    """把波形完整数据导出为 CSV 文件（time_s, voltage_v 两列），适合离线分析。

    默认 RAW 模式导出完整内存波形。返回保存路径与统计信息。
    """
    wf = _get_scope().read_waveform(source=source, mode=mode, data_format=data_format,
                                    points=points)
    path = wf.to_csv(csv_path)
    return {"csv_path": path, "points": wf.points, "stats": wf.stats}


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    mcp.run()


if __name__ == "__main__":
    main()
