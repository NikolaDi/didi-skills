"""从 skill 的实际入口经 stdio 测量回环 SCPI 设备。"""

import json
import os
import socketserver
import subprocess
import sys
import threading
from pathlib import Path


def test_bundled_scope_measurement(tmp_path):
    launcher = Path(__file__).resolve().parents[2] / "scripts" / "scope_mcp.py"
    # 模拟工作目录和 PYTHONPATH 中遗留同名服务，误用时必须能暴露出来。
    (tmp_path / "rigol_dho900_mcp.py").write_text("raise RuntimeError('wrong MCP')")
    env = dict(os.environ, PYTHONPATH=str(tmp_path), PYTHONUTF8="1")
    commands = []
    responses = {b"*IDN?": b"RIGOL,DHO924S,MOCK,00.01.02",
                 b":MEASURE:ITEM? VAVG,CHANNEL1": b"3.125"}

    class MockScope(socketserver.StreamRequestHandler):
        def handle(self):
            for line in self.rfile:
                command = line.strip().upper()
                commands.append(command)
                self.wfile.write(responses[command] + b"\n")

    with socketserver.TCPServer(("127.0.0.1", 0), MockScope) as scope:
        thread = threading.Thread(target=scope.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(
                [sys.executable, str(launcher), "--resource",
                 f"127.0.0.1:{scope.server_address[1]}"],
                input=json.dumps([{"tool": "measure", "arguments": {
                    "item": "VAVG", "source": "CH1"}}]),
                cwd=tmp_path, env=env, capture_output=True, encoding="utf-8", timeout=30,
            )
        finally:
            scope.shutdown()
            thread.join()
    assert result.returncode == 0, result.stderr
    identity, reading = map(json.loads, result.stdout.splitlines())
    assert identity["idn"] == "RIGOL,DHO924S,MOCK,00.01.02"
    assert reading == {"tool": "measure", "result": {
        "item": "VAVG", "source": "CH1", "value": 3.125}}
    assert commands[-1] == b":MEASURE:ITEM? VAVG,CHANNEL1"
