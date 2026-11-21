"""MCP 服务器 stdio 握手冒烟测试：initialize → tools/list。"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("mcp") is None, reason="mcp SDK 未安装"
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _rpc(proc, msg_id, method, params=None):
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            raise AssertionError("服务器提前退出")
        payload = json.loads(line)
        if payload.get("id") == msg_id:
            return payload


def test_server_lists_tools():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [sys.executable, "-m", "rigol_dho900_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        init = _rpc(proc, 1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke-test", "version": "0.0"},
        })
        assert "result" in init
        proc.stdin.write((json.dumps({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }) + "\n").encode())
        proc.stdin.flush()

        listing = _rpc(proc, 2, "tools/list")
        names = {tool["name"] for tool in listing["result"]["tools"]}
        assert {
            "connect", "disconnect", "get_identity", "scpi_write", "scpi_query",
            "get_waveform", "get_screenshot", "measure", "acquire", "get_errors",
            "setup_channel", "setup_timebase", "setup_trigger_edge",
            "export_waveform_csv",
        } <= names

        # 未连接仪器时，工具应返回 isError 结果而不是让服务器崩溃
        call = _rpc(proc, 3, "tools/call", {"name": "get_identity", "arguments": {}})
        assert call["result"]["isError"] is True
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_screenshot_returns_mcp_image_content(monkeypatch):
    """经过SDK结果转换，复现并防止Image被误当普通JSON序列化。"""
    import asyncio
    import base64
    from rigol_dho900_mcp import server
    payload = b"\x89PNG\r\n\x1a\nmock"

    class Scope:
        def screenshot(self, path, fmt):
            assert fmt == "PNG"
            return payload, "capture.png"

    monkeypatch.setattr(server, "_get_scope", lambda: Scope())
    result = asyncio.run(server.mcp.call_tool("get_screenshot", {}))
    # SDK 2.x返回CallToolResult；1.x返回内容序列或(content, structured)。
    content = getattr(result, "content", result)
    if isinstance(content, tuple):
        content = content[0]
    images = [block for block in content if block.type == "image"]
    assert len(images) == 1
    assert base64.b64decode(images[0].data) == payload
    assert any(block.type == "text" and "capture.png" in block.text for block in content)
