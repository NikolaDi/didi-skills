"""DHO900 驱动的单元测试（FakeTransport 模拟仪器响应）。"""

import struct

import pytest

from rigol_dho900_mcp.driver import DHO900, DHO900Error
from rigol_dho900_mcp.transport import Transport


def tmc(payload: bytes) -> bytes:
    digits = str(len(payload)).encode()
    return b"#" + str(len(digits)).encode() + digits + payload + b"\n"


class FakeTransport(Transport):
    """按命令路由响应，并记录全部下行命令。"""

    def __init__(self, responder):
        self.commands: list[str] = []
        self.responder = responder

    def write(self, command: str) -> None:
        self.commands.append(command.strip())

    def _read_response(self) -> bytes:
        return self.responder(self.commands[-1])

    def close(self) -> None:
        pass


def make_scope(responder, chunk_size=250_000) -> DHO900:
    scope = DHO900("fake", chunk_size=chunk_size)
    scope._transport = FakeTransport(responder)
    return scope


WORD_PREAMBLE = "1,0,3,1,1.000000E-8,-5.000000E-6,0.000000E-00,1.000000E-04,0,32768"


def test_read_waveform_normal_word():
    codes = [32768, 32778, 32758]

    def responder(cmd: str) -> bytes:
        if cmd == ":WAVeform:DATA?":
            return tmc(struct.pack(f"<{len(codes)}H", *codes))
        if cmd.startswith(":WAVeform:PREamble"):
            return WORD_PREAMBLE.encode() + b"\n"
        return b"\n"

    scope = make_scope(responder)
    wf = scope.read_waveform(source="CH1", mode="NORMal", data_format="WORD", points=3)

    assert wf.points == 3
    assert wf.v == pytest.approx([0.0, 0.001, -0.001])  # (code-32768)×1e-4
    assert wf.t[0] == pytest.approx(-5e-6)
    assert wf.format == "WORD" and wf.mode == "NORMal"
    assert ":WAVeform:POINts 3" in scope._transport.commands
    assert scope._transport.commands[0] == ":WAVeform:SOURce CHANnel1"


def test_read_waveform_raw_chunked():
    # 三块分别 400/400/200 点，模拟仪器按 STARt/STOP 范围返回
    payloads = [bytes([100]) * 400, bytes([101]) * 400, bytes([102]) * 200]

    def responder(cmd: str) -> bytes:
        if cmd == ":WAVeform:DATA?":
            return tmc(payloads.pop(0))
        if cmd in (":WAVeform:STARt?", ":WAVeform:STOP?"):
            prefix = cmd[:-1] + " "
            value = next(c[len(prefix):] for c in reversed(scope._transport.commands) if c.startswith(prefix))
            return value.encode() + b"\n"
        if cmd.startswith(":WAVeform:PREamble"):
            return b"0,2,1000,1,8.0E-10,-4.0E-7,0.0,1.0E-3,0,128\n"
        return b"\n"

    scope = make_scope(responder, chunk_size=400)
    wf = scope.read_waveform(source="CH2", mode="RAW", data_format="BYTE", points=1000)

    cmds = scope._transport.commands
    assert ":STOP" in cmds  # RAW 前自动停止采集
    assert cmds.index(":WAVeform:STARt 1") < cmds.index(":WAVeform:STARt 401")
    assert ":WAVeform:STOP 400" in cmds
    assert ":WAVeform:STOP 800" in cmds
    assert ":WAVeform:STOP 1000" in cmds
    assert payloads == []  # 恰好读了 3 块

    assert wf.points == 1000
    assert wf.mode == "RAW"
    # 每块 400 点，码值 100/101/102 → (code-128)×1e-3
    assert wf.v[0] == pytest.approx((100 - 128) * 1e-3)
    assert wf.v[400] == pytest.approx((101 - 128) * 1e-3)
    assert wf.v[800] == pytest.approx((102 - 128) * 1e-3)


@pytest.mark.parametrize("returned", [0, 3, 5])
def test_raw_rejects_wrong_chunk_length(returned):
    def responder(cmd):
        if cmd == ":WAVeform:STARt?":
            return b"1\n"
        if cmd == ":WAVeform:STOP?":
            return b"4\n"
        if cmd == ":WAVeform:DATA?":
            return tmc(bytes([100]) * returned)
        return b"\n"

    scope = make_scope(responder, chunk_size=4)
    with pytest.raises(DHO900Error, match="点数不一致"):
        scope.read_waveform(mode="RAW", data_format="BYTE", points=8)
    assert scope._transport.commands.count(":WAVeform:DATA?") == 1
    assert ":WAVeform:STARt 5" not in scope._transport.commands


def test_raw_rejects_clamped_range_before_reading():
    scope = make_scope(lambda c: b"1\n" if c.endswith("STARt?") else b"3\n")
    with pytest.raises(DHO900Error, match="范围不一致"):
        scope.read_waveform(mode="RAW", data_format="WORD", points=4)
    assert ":WAVeform:DATA?" not in scope._transport.commands


@pytest.mark.parametrize("points,start", [(0, 1), (-1, 1), (4, 0)])
def test_raw_rejects_invalid_range(points, start):
    scope = make_scope(lambda c: b"\n")
    with pytest.raises(DHO900Error):
        scope.read_waveform(mode="RAW", points=points, start=start)
    assert ":WAVeform:DATA?" not in scope._transport.commands


def test_read_waveform_rejects_bad_args():
    scope = make_scope(lambda cmd: b"\n")
    with pytest.raises(DHO900Error):
        scope.read_waveform(mode="BOGUS")
    with pytest.raises(DHO900Error):
        scope.read_waveform(data_format="HEX")
    with pytest.raises(DHO900Error):
        scope.read_waveform(mode="NORMal", points=5000)  # NORMal ≤ 1000


def test_measure():
    def responder(cmd: str) -> bytes:
        if cmd.startswith(":MEASure:ITEM?"):
            return b"1.023000E+00\n"
        return b"\n"

    scope = make_scope(responder)
    assert scope.measure("vpp", "CH1") == pytest.approx(1.023)
    assert scope._transport.commands[-1] == ":MEASure:ITEM? VPP,CHANnel1"
    with pytest.raises(DHO900Error):
        scope.measure("NOT_AN_ITEM")


def test_screenshot_png(tmp_path):
    payload = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"

    def responder(cmd: str) -> bytes:
        if cmd.startswith(":DISPlay:DATA?"):
            return tmc(payload)
        return b"\n"

    scope = make_scope(responder)
    target = tmp_path / "screen.png"
    data, path = scope.screenshot(str(target), "PNG")
    assert data == payload
    assert path == str(target)
    assert target.read_bytes() == payload
    assert scope._transport.commands[-1] == ":DISPlay:DATA? PNG"


def test_screenshot_bad_magic(tmp_path):
    def responder(cmd: str) -> bytes:
        return tmc(b"NOT-AN-IMAGE")

    scope = make_scope(responder)
    with pytest.raises(DHO900Error):
        scope.screenshot(str(tmp_path / "x.png"), "PNG")


def test_error_queue_drain():
    replies = iter([
        b'-113,"Undefined header; command cannot be found"\n',
        b'-222,"Data out of range"\n',
        b'0,"No error"\n',
    ])

    def responder(cmd: str) -> bytes:
        return next(replies)

    scope = make_scope(responder)
    assert scope.errors() == [
        '-113,"Undefined header; command cannot be found"',
        '-222,"Data out of range"',
    ]


def test_settings_commands():
    scope = make_scope(lambda cmd: b"\n")
    scope.set_channel("CH1", display=True, scale=0.5, offset=0.1,
                      coupling="ac", bwlimit=True, probe=10)
    scope.set_timebase(scale=1e-3, mode="MAIN")
    scope.set_trigger_edge(source="CH2", level=0.1, slope="POS", sweep="SING")

    assert scope._transport.commands == [
        ":CHANnel1:DISPlay ON",
        ":CHANnel1:SCALe 0.5",
        ":CHANnel1:OFFSet 0.1",
        ":CHANnel1:COUPling AC",
        ":CHANnel1:BWLimit 20M",
        ":CHANnel1:PROBe 10.0",
        ":TIMebase:MODE MAIN",
        ":TIMebase:SCALe 0.001",
        ":TRIGger:MODE EDGE",
        ":TRIGger:EDGE:SOURce CHANnel2",
        ":TRIGger:EDGE:SLOPe POSitive",
        ":TRIGger:EDGE:LEVel 0.1",
        ":TRIGger:SWEep SINGle",
    ]


def test_acquire_commands():
    scope = make_scope(lambda cmd: b"TD\n" if cmd.endswith("STATus?") else b"\n")
    scope.run()
    scope.stop()
    scope.single()
    scope.force_trigger()
    scope.clear_sweep()
    assert scope._transport.commands == [":RUN", ":STOP", ":SINGle", ":TFORce", ":CLEar"]
    assert scope.trigger_status() == "TD"
