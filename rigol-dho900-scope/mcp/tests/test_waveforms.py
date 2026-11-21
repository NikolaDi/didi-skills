"""TMC 块解析、波形解码/换算/抽稀的单元测试。"""

import struct

import pytest

from rigol_dho900_mcp.waveforms import (
    FMT_ASCII,
    FMT_BYTE,
    FMT_WORD,
    Preamble,
    WaveformError,
    decode_codes,
    downsample,
    scale_voltages,
    signal_stats,
    strip_tmc_block,
    time_axis,
)

# 官方手册 PREamble 示例：BYTE、NORMal、1000 点、10 ns/点、起点 -5 µs、YREF=128
OFFICIAL_PREAMBLE = "0,0,1000,1,1.000000E-8,-5.000000E-6,0.000000E-12,4.000000E-03,0,128"


def test_strip_tmc_block_official_example():
    # 手册示例 #9000001000 + 1000 字节数据
    payload = bytes(range(256)) * 3 + bytes(range(232))  # 1000 字节
    assert len(payload) == 1000
    raw = b"#9000001000" + payload + b"\n"
    assert strip_tmc_block(raw) == payload


def test_strip_tmc_block_passthrough_ascii():
    assert strip_tmc_block(b"1.0E-3,2.0E-3,3.0E-3\r\n") == b"1.0E-3,2.0E-3,3.0E-3"


def test_strip_tmc_block_bad_length():
    with pytest.raises(WaveformError):
        strip_tmc_block(b"#9000001000short")


def test_decode_byte():
    assert decode_codes(b"\x00\x80\xff", FMT_BYTE) == [0, 128, 255]


def test_decode_word_little_endian_unsigned():
    payload = struct.pack("<3H", 0, 32768, 65535)
    assert decode_codes(payload, FMT_WORD) == [0, 32768, 65535]


def test_decode_word_odd_length():
    with pytest.raises(WaveformError):
        decode_codes(b"\x01\x02\x03", FMT_WORD)


def test_decode_ascii():
    assert decode_codes(b"1.5E-3,-2.5E-3\n", FMT_ASCII) == pytest.approx([0.0015, -0.0025])


def test_preamble_parse_official():
    pre = Preamble.parse(OFFICIAL_PREAMBLE)
    assert pre.format == FMT_BYTE
    assert pre.type == 0
    assert pre.points == 1000
    assert pre.xincrement == pytest.approx(1e-8)
    assert pre.xorigin == pytest.approx(-5e-6)
    assert pre.xreference == pytest.approx(0.0)
    assert pre.yincrement == pytest.approx(4e-3)
    assert pre.yorigin == 0
    assert pre.yreference == 128
    assert pre.format_name == "BYTE"
    assert pre.mode_name == "NORMal"


def test_preamble_parse_wrong_arity():
    with pytest.raises(WaveformError):
        Preamble.parse("0,0,1000")


def test_scale_formula_official():
    # V = (code - YOR - YREF) × YINC → code 128 → 0 V；code 138 → +40 mV
    pre = Preamble.parse(OFFICIAL_PREAMBLE)
    volts = scale_voltages([128, 138, 118], pre)
    assert volts == pytest.approx([0.0, 0.04, -0.04])


def test_scale_ascii_passthrough():
    pre = Preamble.parse(OFFICIAL_PREAMBLE)
    pre.format = FMT_ASCII
    assert scale_voltages([0.1, -0.2], pre) == pytest.approx([0.1, -0.2])


def test_time_axis_formula():
    pre = Preamble.parse(OFFICIAL_PREAMBLE)
    t = time_axis(3, pre)
    assert t == pytest.approx([-5e-6, -4.99e-6, -4.98e-6])


def test_downsample_keeps_extremes():
    t = [i * 1.0 for i in range(1000)]
    v = [0.0] * 1000
    v[123] = 5.0
    v[789] = -5.0
    ot, ov = downsample(t, v, 100)
    assert len(ov) <= 100
    assert 5.0 in ov and -5.0 in ov


def test_downsample_noop_when_small():
    t, v = [0.0, 1.0], [1.0, 2.0]
    assert downsample(t, v, 100) == (t, v)


def test_signal_stats():
    s = signal_stats([1.0, -1.0, 3.0])
    assert s == {"min": -1.0, "max": 3.0, "pp": 4.0, "mean": 1.0}
    assert signal_stats([])["min"] is None
