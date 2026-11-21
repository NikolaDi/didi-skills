"""宿主没有原生示波器工具时，通过本地 MCP stdio 会话串行调用。"""

import argparse
import asyncio
import json
import os
import re
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def usb_resource():
    try:
        import pyvisa
    except ImportError as exc:
        raise ValueError("请指定 LAN 地址，或用已有 PyVISA 的解释器枚举 USB 设备。") from exc
    with pyvisa.ResourceManager() as manager:
        candidates = [r for r in manager.list_resources("USB?*::INSTR")
                      if re.match(r"^USB\d*::(?:0x0*1AB1|6833)::", r, re.I)]
    if len(candidates) != 1:
        raise ValueError(f"需要唯一的 RIGOL USB 地址，请用 --resource 选择。候选 {candidates}")
    return candidates[0]


async def call(session, name, arguments, timeout):
    result = await asyncio.wait_for(session.call_tool(name, arguments), timeout)
    # 协议字段保持一致；不同 SDK 的 Python 属性名可能是蛇形或驼峰。
    payload = result.model_dump(by_alias=True)
    texts = [block["text"] for block in payload["content"] if block["type"] == "text"]
    if payload.get("isError"):
        raise ValueError(f"{name} 失败：{' '.join(texts)}")
    data = payload.get("structuredContent")
    if data is not None:
        return data
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except ValueError:
            return texts[0]
    # 截图由服务端写入 save_path；只输出路径信息，避免向终端写入大段图像。
    return texts


async def run(options, requests):
    resource = options.resource
    if not options.list and not resource:
        resource = usb_resource()
    # 在 SDK 自带的进程环境之上，传递本机解释器和 VISA 所需的选项。
    keys = ("PYTHONPATH", "PYTHONUTF8", "PYTHONIOENCODING", "PYVISA_LIBRARY", "DHO900_TIMEOUT")
    server = StdioServerParameters(command=sys.executable, args=["-m", "rigol_dho900_mcp"],
                                   env={k: os.environ[k] for k in keys if k in os.environ})
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await asyncio.wait_for(session.initialize(), options.timeout)
            listing = await asyncio.wait_for(session.list_tools(), options.timeout)
            names = {tool.name for tool in listing.tools}
            if options.list:
                print(json.dumps(sorted(names)))
                return
            for request in requests:
                if (not isinstance(request, dict) or request.get("tool") not in names
                        or request["tool"] in ("connect", "disconnect")
                        or not isinstance(request.get("arguments", {}), dict)):
                    raise ValueError("请求须指定已列出的工具与参数对象；连接与释放由调用器处理。")
            identity = await call(session, "connect", {"resource": resource}, options.timeout)
            try:
                idn = identity["idn"].split(",")
                if len(idn) < 2 or "RIGOL" not in idn[0].upper() or not re.fullmatch(
                        r"DHO9(?:14|24)S?", idn[1].strip(), re.I):
                    raise ValueError(f"仪器身份不匹配：{identity['idn']}")
                print(json.dumps(identity, ensure_ascii=False), flush=True)
                for request in requests:
                    name = request["tool"]
                    data = await call(session, name, request.get("arguments", {}), options.timeout)
                    print(json.dumps({"tool": name, "result": data}, ensure_ascii=False), flush=True)
            finally:
                await call(session, "disconnect", {}, options.timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="只发现工具，不连接示波器")
    parser.add_argument("--resource", default=os.getenv("DHO900_RESOURCE"), help="IP 或 VISA 资源")
    parser.add_argument("--timeout", type=int, default=120, help="单次 MCP 响应期限（秒）")
    options = parser.parse_args()
    if options.timeout <= 0:
        parser.error("--timeout 必须大于零")
    requests = [] if options.list else json.load(sys.stdin)
    if not options.list and (not isinstance(requests, list) or not requests):
        parser.error("请在标准输入提供非空的 JSON 请求列表")
    asyncio.run(run(options, requests))


if __name__ == "__main__":
    main()
