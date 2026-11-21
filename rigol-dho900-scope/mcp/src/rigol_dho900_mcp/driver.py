"""DHO900 高层驱动：采集控制、波形读取、截图、自动测量与设置。

命令语法依据《DHO800/DHO900 Programming Guide》；支持型号
DHO914/DHO914S/DHO924/DHO924S（及同系列 DHO800）。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .transport import DEFAULT_SOCKET_PORT, Transport, TransportError, open_transport
from .waveforms import (
    FMT_ASCII,
    FMT_BYTE,
    FMT_WORD,
    Preamble,
    WaveformError,
    decode_codes,
    downsample,
    scale_voltages,
    signal_stats,
    time_axis,
    write_csv,
)


class DHO900Error(RuntimeError):
    """仪器交互错误。"""


# :MEASure:ITEM 支持的测量项（编程手册 §3.17.2）
MEASURE_ITEMS = [
    "VMAX", "VMIN", "VPP", "VTOP", "VBASe", "VAMP", "VAVG", "VRMS", "OVERshoot",
    "PREShoot", "MARea", "MPARea", "PERiod", "FREQuency", "RTIMe", "FTIMe",
    "PWIDth", "NWIDth", "PDUTy", "NDUTy", "TVMAX", "TVMIN", "PSLewrate",
    "NSLewrate", "VUPPer", "VMID", "VLOWer", "VARiance", "PVRMs", "PPULses",
    "NPULses", "PEDGes", "NEDGes", "RRDelay", "RFDelay", "FRDelay", "FFDelay",
    "RRPHase", "RFPHase", "FRPHase", "FFPHase", "ACRMs",
]

_FORMAT_ALIASES = {
    "BYTE": FMT_BYTE, "B": FMT_BYTE,
    "WORD": FMT_WORD, "W": FMT_WORD,
    "ASCII": FMT_ASCII, "ASC": FMT_ASCII, "ASCii": FMT_ASCII,
}

_MODE_ALIASES = {
    "NORM": "NORMal", "NORMAL": "NORMal", "NORMal": "NORMal", "SCREEN": "NORMal",
    "MAX": "MAXimum", "MAXIMUM": "MAXimum", "MAXimum": "MAXimum",
    "RAW": "RAW", "MEM": "RAW", "MEMORY": "RAW",
}

_SLOPE_ALIASES = {"POS": "POSitive", "POSITIVE": "POSitive", "NEG": "NEGative",
                  "NEGATIVE": "NEGative", "RFAL": "RFALl", "RFALL": "RFALl",
                  "BOTH": "RFALl"}

_COUPLING_ALIASES = {"AC": "AC", "DC": "DC", "GND": "GND", "GROUND": "GND"}

_SWEEP_ALIASES = {
    "AUTO": "AUTO",
    "NORM": "NORMal", "NORMAL": "NORMal", "NORMal": "NORMal",
    "SING": "SINGle", "SINGLE": "SINGle", "SINGle": "SINGle",
}

_SOURCE_ALIASES = {
    "CH1": "CHANnel1", "CH2": "CHANnel2", "CH3": "CHANnel3", "CH4": "CHANnel4",
    "CHANNEL1": "CHANnel1", "CHANNEL2": "CHANnel2",
    "CHANNEL3": "CHANnel3", "CHANNEL4": "CHANnel4", "M1": "MATH1", "M2": "MATH2",
    "M3": "MATH3", "M4": "MATH4", "MATH1": "MATH1", "MATH2": "MATH2",
    "MATH3": "MATH3", "MATH4": "MATH4",
}

_SCREEN_POINTS_MAX = 1000  # NORMal 模式单次最大点数（编程手册 :WAVeform:POINts）


def normalize_source(source: str) -> str:
    s = source.strip().upper()
    if s in _SOURCE_ALIASES:
        return _SOURCE_ALIASES[s]
    if s.startswith("CHAN") or s.startswith("MATH") or s.startswith("D"):
        return source.strip()
    if s.isdigit() and 1 <= int(s) <= 4:
        return f"CHANnel{s}"
    return source.strip()


@dataclass
class Waveform:
    """一次波形读取的结果。"""

    source: str
    mode: str
    format: str
    points: int
    t: list[float] = field(default_factory=list)
    v: list[float] = field(default_factory=list)
    preamble: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def downsampled(self, max_points: int) -> tuple[list[float], list[float]]:
        return downsample(self.t, self.v, max_points)

    def to_csv(self, path: str) -> str:
        return write_csv(path, {"time_s": self.t, "voltage_v": self.v})


class DHO900:
    """线程安全的 DHO900 驱动（内部加锁，命令串行化）。"""

    def __init__(self, resource: str, timeout: float = 10.0, chunk_size: int = 250_000):
        self._resource = resource
        self._timeout = timeout
        self._chunk_size = max(1, int(chunk_size))
        self._transport: Transport | None = None
        self._lock = threading.RLock()

    # ---------- 连接管理 ----------

    def connect(self) -> str:
        with self._lock:
            if self._transport is not None:
                return self.idn()
            self._transport = open_transport(self._resource, self._timeout)
            try:
                return self.idn()
            except Exception:
                self.close()
                raise

    def close(self) -> None:
        with self._lock:
            if self._transport is not None:
                self._transport.close()
                self._transport = None

    @property
    def connected(self) -> bool:
        return self._transport is not None

    @property
    def resource(self) -> str:
        return self._resource

    def _t(self) -> Transport:
        if self._transport is None:
            raise DHO900Error("尚未连接仪器，请先 connect()")
        return self._transport

    # ---------- 原始 SCPI ----------

    def write(self, command: str) -> None:
        with self._lock:
            try:
                self._t().write(command)
            except TransportError as exc:
                raise DHO900Error(str(exc)) from exc

    def query(self, command: str) -> str:
        with self._lock:
            try:
                return self._t().query(command)
            except TransportError as exc:
                raise DHO900Error(str(exc)) from exc

    def query_binary(self, command: str) -> bytes:
        with self._lock:
            try:
                return self._t().query_binary(command)
            except TransportError as exc:
                raise DHO900Error(str(exc)) from exc

    # ---------- 系统 ----------

    def idn(self) -> str:
        return self.query("*IDN?")

    def reset(self) -> None:
        self.write("*RST")
        self.query("*OPC?")  # *RST 为 Overlapped 命令，等待完成

    def errors(self) -> list[str]:
        """排空 :SYSTem:ERRor? 错误队列。"""
        found: list[str] = []
        for _ in range(20):
            raw = self.query(":SYSTem:ERRor?")
            if not raw or "No error" in raw or raw.startswith('0,'):
                break
            found.append(raw)
        return found

    def trigger_status(self) -> str:
        return self.query(":TRIGger:STATus?")

    def memory_depth(self) -> int:
        try:
            return int(float(self.query(":ACQuire:MDEPth?")))
        except ValueError as exc:
            raise DHO900Error("解析存储深度失败") from exc

    # ---------- 采集控制 ----------

    def run(self) -> None:
        self.write(":RUN")

    def stop(self) -> None:
        self.write(":STOP")

    def single(self) -> None:
        self.write(":SINGle")

    def force_trigger(self) -> None:
        self.write(":TFORce")

    def autoset(self) -> None:
        self.write(":AUToset")
        self.query("*OPC?")

    def clear_sweep(self) -> None:
        self.write(":CLEar")

    # ---------- 波形读取 ----------

    def read_waveform(
        self,
        source: str = "CHANnel1",
        mode: str = "NORMal",
        data_format: str = "WORD",
        points: int | None = None,
        start: int = 1,
    ) -> Waveform:
        """读取波形并按官方公式换算为时间/电压。

        - NORMal（屏幕数据）：单次最多 1000 点，运行/停止均可读。
        - MAXimum：RUN 时读屏幕、STOP 时读内存，按 points 单次读取。
        - RAW（内存数据）：仅 STOP 状态可读，会自动先 :STOP 并分块读取。
        """
        mode_u = _MODE_ALIASES.get(mode.strip().upper())
        if mode_u is None:
            raise DHO900Error(f"未知波形模式 {mode!r}，可选 NORMal/MAXimum/RAW")
        fmt = _FORMAT_ALIASES.get(data_format.strip().upper())
        if fmt is None:
            raise DHO900Error(f"未知波形格式 {data_format!r}，可选 BYTE/WORD/ASCii")
        src = normalize_source(source)

        with self._lock:
            self.write(f":WAVeform:SOURce {src}")
            self.write(f":WAVeform:MODE {mode_u}")
            self.write(f":WAVeform:FORMat {_fmt_command(fmt)}")

            if mode_u == "RAW":
                self.write(":STOP")  # RAW 仅 STOP 状态可读
                codes = self._read_chunked(points, start, fmt)
            elif mode_u == "NORMal":
                if points and points > _SCREEN_POINTS_MAX:
                    raise DHO900Error(
                        f"NORMal 模式单次最多 {_SCREEN_POINTS_MAX} 点；"
                        "需要完整内存波形请用 mode='RAW'"
                    )
                n = int(points) if points else _SCREEN_POINTS_MAX
                self.write(f":WAVeform:POINts {n}")
                codes = decode_codes(self.query_binary(":WAVeform:DATA?"), fmt)
            else:  # MAXimum
                if points and points > self._chunk_size:
                    codes = self._read_chunked(points, start, fmt)
                else:
                    if points:
                        self.write(f":WAVeform:POINts {int(points)}")
                    codes = decode_codes(self.query_binary(":WAVeform:DATA?"), fmt)

            pre = Preamble.parse(self.query(":WAVeform:PREamble?"))

        volts = scale_voltages(codes, pre)
        times = time_axis(len(volts), pre)
        return Waveform(
            source=src,
            mode=mode_u,
            format=pre.format_name,
            points=len(volts),
            t=times,
            v=volts,
            preamble=pre.as_dict(),
            stats=signal_stats(volts),
        )

    def _read_chunked(self, points: int | None, start: int, fmt: int) -> list[float]:
        """按 :WAVeform:STARt/STOP 分块读取（每块自带 TMC 头）。"""
        if int(start) < 1:
            raise DHO900Error("波形起点必须大于等于1")
        if points is None:
            points = self.memory_depth() - (start - 1)
        points = int(points)
        if points < 1:
            raise DHO900Error("波形点数必须大于等于1")
        codes: list[float] = []
        pos = int(start)
        end = pos + points - 1
        while pos <= end:
            chunk_end = min(pos + self._chunk_size - 1, end)
            self.write(f":WAVeform:STARt {pos}")
            self.write(f":WAVeform:STOP {chunk_end}")
            actual_start = int(self.query(":WAVeform:STARt?"))
            actual_stop = int(self.query(":WAVeform:STOP?"))
            if (actual_start, actual_stop) != (pos, chunk_end):
                raise DHO900Error(
                    f"波形分块范围不一致：请求 {pos}..{chunk_end}，"
                    f"实际 {actual_start}..{actual_stop}"
                )
            block = decode_codes(self.query_binary(":WAVeform:DATA?"), fmt)
            expected = chunk_end - pos + 1
            if len(block) != expected:
                raise DHO900Error(
                    f"波形分块点数不一致：范围 {pos}..{chunk_end}，"
                    f"期望 {expected}，实际 {len(block)}；停止读取，不拼接缺帧"
                )
            codes.extend(block)
            pos = chunk_end + 1
        return codes

    # ---------- 截图 ----------

    def screenshot(self, save_path: str = "", image_format: str = "PNG") -> tuple[bytes, str]:
        """截取当前屏幕（:DISPlay:DATA?），返回 (图像字节, 保存路径)。"""
        fmt = image_format.strip().upper().lstrip(".")
        if fmt not in ("PNG", "BMP", "JPG"):
            raise DHO900Error(f"截图格式仅支持 PNG/BMP/JPG，收到 {image_format!r}")
        data = self.query_binary(f":DISPlay:DATA? {fmt}")
        magic_ok = (
            (fmt == "PNG" and data.startswith(b"\x89PNG"))
            or (fmt == "BMP" and data.startswith(b"BM"))
            or (fmt == "JPG" and data.startswith(b"\xff\xd8"))
        )
        if not magic_ok:
            raise DHO900Error(f"截图数据头与 {fmt} 不符（前 8 字节 {data[:8]!r}）")

        if save_path:
            p = Path(save_path)
        else:
            p = Path.cwd() / f"dho900_{time.strftime('%Y%m%d_%H%M%S')}.{fmt.lower()}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return data, str(p)

    # ---------- 测量 ----------

    def measure(self, item: str, source: str = "CHANnel1", source2: str | None = None) -> float:
        item_u = item.strip().upper()
        if item_u not in MEASURE_ITEMS:
            raise DHO900Error(f"未知测量项 {item!r}；可用项见 MEASURE_ITEMS/工具说明")
        cmd = f":MEASure:ITEM? {item_u},{normalize_source(source)}"
        if source2:
            cmd += f",{normalize_source(source2)}"
        raw = self.query(cmd)
        try:
            return float(raw)
        except ValueError as exc:
            raise DHO900Error(f"测量返回值无法解析: {raw!r}") from exc

    # ---------- 设置 ----------

    def set_channel(
        self,
        channel: str,
        display: bool | None = None,
        scale: float | None = None,
        offset: float | None = None,
        coupling: str | None = None,
        bwlimit: str | bool | None = None,
        probe: float | None = None,
    ) -> None:
        ch = normalize_source(channel)
        if not ch.startswith("CHANnel"):
            raise DHO900Error(f"通道参数非法: {channel!r}")
        with self._lock:
            if display is not None:
                self.write(f":{ch}:DISPlay {'ON' if display else 'OFF'}")
            if scale is not None:
                self.write(f":{ch}:SCALe {float(scale)}")
            if offset is not None:
                self.write(f":{ch}:OFFSet {float(offset)}")
            if coupling is not None:
                c = _COUPLING_ALIASES.get(coupling.strip().upper())
                if c is None:
                    raise DHO900Error(f"耦合方式非法: {coupling!r}，可选 AC/DC/GND")
                self.write(f":{ch}:COUPling {c}")
            if bwlimit is not None:
                if isinstance(bwlimit, bool):
                    self.write(f":{ch}:BWLimit {'20M' if bwlimit else 'OFF'}")
                else:
                    self.write(f":{ch}:BWLimit {bwlimit.strip().upper()}")
            if probe is not None:
                self.write(f":{ch}:PROBe {float(probe)}")

    def set_timebase(
        self,
        scale: float | None = None,
        offset: float | None = None,
        mode: str | None = None,
    ) -> None:
        with self._lock:
            if mode is not None:
                m = mode.strip().upper()
                if m not in ("MAIN", "XY", "ROLL"):
                    raise DHO900Error(f"时基模式非法: {mode!r}，可选 MAIN/XY/ROLL")
                self.write(f":TIMebase:MODE {m}")
            if scale is not None:
                self.write(f":TIMebase:SCALe {float(scale)}")
            if offset is not None:
                self.write(f":TIMebase:OFFSet {float(offset)}")

    def set_trigger_edge(
        self,
        source: str | None = None,
        level: float | None = None,
        slope: str | None = None,
        sweep: str | None = None,
        holdoff: float | None = None,
    ) -> None:
        with self._lock:
            self.write(":TRIGger:MODE EDGE")
            if source is not None:
                self.write(f":TRIGger:EDGE:SOURce {normalize_source(source)}")
            if slope is not None:
                s = _SLOPE_ALIASES.get(slope.strip().upper())
                if s is None:
                    raise DHO900Error(f"斜率非法: {slope!r}，可选 POSitive/NEGative/RFALl")
                self.write(f":TRIGger:EDGE:SLOPe {s}")
            if level is not None:
                self.write(f":TRIGger:EDGE:LEVel {float(level)}")
            if sweep is not None:
                sw = _SWEEP_ALIASES.get(sweep.strip().upper())
                if sw is None:
                    raise DHO900Error(f"触发方式非法: {sweep!r}，可选 AUTO/NORMal/SINGle")
                self.write(f":TRIGger:SWEep {sw}")
            if holdoff is not None:
                self.write(f":TRIGger:HOLDoff {float(holdoff)}")


def _fmt_command(fmt: int) -> str:
    return {FMT_BYTE: "BYTE", FMT_WORD: "WORD", FMT_ASCII: "ASCii"}[fmt]
