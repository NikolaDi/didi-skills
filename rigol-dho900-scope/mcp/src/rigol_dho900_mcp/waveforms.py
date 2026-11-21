"""TMC 二进制块解析、波形解码与换算。

换算公式来自《DHO800/DHO900 Programming Guide》:WAVeform 章节：
    电压 V = (code - YORigin - YREFerence) × YINCrement
    时间 t[i] = XORigin + (i - XREFerence) × XINCrement   （XREFerence 恒为 0）

WORD 按无符号 16 位小端解析（官方手册未明示符号性与字节序，
经多个开源 DHO800/900 驱动交叉验证一致）；BYTE 为无符号 8 位。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

FMT_BYTE = 0
FMT_WORD = 1
FMT_ASCII = 2

_FORMAT_NAMES = {FMT_BYTE: "BYTE", FMT_WORD: "WORD", FMT_ASCII: "ASCii"}
_MODE_TYPES = {0: "NORMal", 1: "MAXimum", 2: "RAW"}


class WaveformError(RuntimeError):
    """波形数据解析/换算错误。"""


def strip_tmc_block(raw: bytes) -> bytes:
    """剥离 ``#N`` 头与末尾终止符，返回负载；非块数据仅去除行尾。"""
    if not raw.startswith(b"#"):
        return raw.rstrip(b"\r\n")
    if len(raw) < 2:
        raise WaveformError("TMC 块头不完整")
    n_digits = raw[1] - 0x30
    if not 1 <= n_digits <= 9:
        raise WaveformError(f"TMC 块长度位数非法: {raw[:2]!r}")
    if len(raw) < 2 + n_digits:
        raise WaveformError("TMC 块长度字段不完整")
    size = int(raw[2 : 2 + n_digits])
    payload = raw[2 + n_digits : 2 + n_digits + size]
    if len(payload) != size:
        raise WaveformError(f"TMC 块数据长度不足：期望 {size}，实际 {len(payload)}")
    return payload


@dataclass
class Preamble:
    """:WAVeform:PREamble? 返回的 10 个参数。"""

    format: int  # 0=BYTE 1=WORD 2=ASCii
    type: int  # 0=NORMal 1=MAXimum 2=RAW
    points: int
    count: int
    xincrement: float
    xorigin: float
    xreference: float
    yincrement: float
    yorigin: float
    yreference: float

    @classmethod
    def parse(cls, text: str) -> "Preamble":
        parts = [p.strip() for p in text.strip().strip(",").split(",")]
        if len(parts) != 10:
            raise WaveformError(f"PREamble 应含 10 项，实际 {len(parts)}: {text!r}")
        ints = [int(float(parts[k])) for k in range(4)]
        floats = [float(parts[k]) for k in range(4, 10)]
        return cls(*ints, *floats)

    @property
    def format_name(self) -> str:
        return _FORMAT_NAMES.get(self.format, f"UNKNOWN({self.format})")

    @property
    def mode_name(self) -> str:
        return _MODE_TYPES.get(self.type, f"UNKNOWN({self.type})")

    def as_dict(self) -> dict:
        return {
            "format": self.format_name,
            "mode": self.mode_name,
            "points": self.points,
            "count": self.count,
            "xincrement": self.xincrement,
            "xorigin": self.xorigin,
            "xreference": self.xreference,
            "yincrement": self.yincrement,
            "yorigin": self.yorigin,
            "yreference": self.yreference,
        }


def decode_codes(payload: bytes, data_format: int) -> list[float]:
    """把 DATA? 负载解码为原始码值（ASCii 格式直接得到电压值）。"""
    if data_format == FMT_BYTE:
        return list(payload)
    if data_format == FMT_WORD:
        if len(payload) % 2:
            raise WaveformError("WORD 数据长度不是偶数")
        count = len(payload) // 2
        return list(struct.unpack(f"<{count}H", payload))
    if data_format == FMT_ASCII:
        text = payload.decode("ascii", errors="replace").replace("\n", "").replace("\r", "")
        return [float(x) for x in text.strip().strip(",").split(",") if x.strip()]
    raise WaveformError(f"未知波形格式: {data_format}")


def scale_voltages(codes: list[float], pre: Preamble) -> list[float]:
    """按官方公式换算电压：V = (code - YOR - YREF) × YINC。"""
    if pre.format == FMT_ASCII:
        return list(codes)
    base = pre.yorigin + pre.yreference
    inc = pre.yincrement
    return [(code - base) * inc for code in codes]


def time_axis(n: int, pre: Preamble) -> list[float]:
    """按公式换算时间：t[i] = XOR + (i - XREF) × XINC。"""
    return [pre.xorigin + (i - pre.xreference) * pre.xincrement for i in range(n)]


def downsample(t: list[float], v: list[float], max_points: int) -> tuple[list[float], list[float]]:
    """分桶 min/max 抽稀，保留极值与时间顺序，供 LLM 上下文友好地查看波形。"""
    n = len(v)
    if max_points <= 0 or n <= max_points:
        return list(t), list(v)
    buckets = max(1, max_points // 2)
    step = -(-n // buckets)
    out_t: list[float] = []
    out_v: list[float] = []
    for start in range(0, n, step):
        seg = v[start : start + step]
        ts = t[start : start + step]
        lo = min(range(len(seg)), key=seg.__getitem__)
        hi = max(range(len(seg)), key=seg.__getitem__)
        first, second = (lo, hi) if lo <= hi else (hi, lo)
        out_t.append(ts[first])
        out_v.append(seg[first])
        if second != first:
            out_t.append(ts[second])
            out_v.append(seg[second])
    return out_t, out_v


def signal_stats(v: list[float]) -> dict:
    if not v:
        return {"min": None, "max": None, "pp": None, "mean": None}
    lo = min(v)
    hi = max(v)
    return {"min": lo, "max": hi, "pp": hi - lo, "mean": sum(v) / len(v)}


def write_csv(path: str, columns: dict[str, list[float]]) -> str:
    """按列导出 CSV（列顺序即字典顺序）。"""
    import csv
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    names = list(columns)
    length = max((len(columns[name]) for name in names), default=0)
    with p.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(names)
        for i in range(length):
            writer.writerow([columns[name][i] if i < len(columns[name]) else "" for name in names])
    return str(p)
