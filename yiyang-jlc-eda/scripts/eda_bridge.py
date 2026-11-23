"""Discover the local EasyEDA bridge and execute code in a verified document.

Uses only the Python standard library; never retries a code-execution request.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


SERVICE = "easyeda-bridge"
PORTS = range(49620, 49630)
PROBE = """return {
  project: await eda.dmt_Project.getCurrentProjectInfo(),
  document: await eda.dmt_SelectControl.getCurrentDocumentInfo()
};"""


def request(port, endpoint, payload=None, timeout=40):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{endpoint}", data=body,
        headers={"Content-Type": "application/json"},
    )
    # The local service must not be routed through a configured HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def discover(port=None):
    found = []
    for candidate in ([port] if port is not None else PORTS):
        try:
            health = request(candidate, "/health", timeout=.5)
        except (OSError, ValueError, RuntimeError):
            continue
        if isinstance(health, dict) and health.get("service") == SERVICE:
            found.append({"port": candidate, "health": health})
    return found


def resolve_bridge(port):
    found = discover(port)
    if not found:
        raise RuntimeError("No easyeda-bridge service found on local ports 49620-49629.")
    if len(found) != 1:
        raise RuntimeError("Multiple bridges found; use discover and specify --port.")
    return found[0]["port"]


def resolve_window(port, requested):
    inventory = request(port, "/eda-windows")
    windows = [w for w in inventory.get("windows", []) if w.get("connected")]
    if requested:
        if not any(w.get("windowId") == requested for w in windows):
            raise RuntimeError("Requested EDA window is not connected; probe current windows again.")
        return requested
    if len(windows) != 1:
        raise RuntimeError("Expected one connected EDA window; use windows and specify --window-id.")
    return windows[0]["windowId"]


def execute(port, window_id, code):
    result = request(port, "/execute", {"code": code, "windowId": window_id})
    if not isinstance(result, dict) or result.get("success") is not True:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def guarded_code(code, project, document):
    # Embed identifiers as JSON data, not shell or JavaScript expressions.
    expected = json.dumps({"project": project, "document": document})
    return """const __yiyangExpected = %s;
const __yiyangProject = await eda.dmt_Project.getCurrentProjectInfo();
const __yiyangDocument = await eda.dmt_SelectControl.getCurrentDocumentInfo();
if (__yiyangProject?.uuid !== __yiyangExpected.project ||
    __yiyangDocument?.uuid !== __yiyangExpected.document) {
  throw new Error('Target project/document changed; probe again before editing.');
}
return await (async () => {
%s
})();""" % (expected, code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("discover", "windows", "probe", "execute"):
        p = sub.add_parser(name)
        p.add_argument("--port", type=int, choices=PORTS)
        p.add_argument("--output", type=Path)
        if name in ("probe", "execute"):
            p.add_argument("--window-id", required=name == "execute")
        if name == "execute":
            p.add_argument("--project", required=True)
            p.add_argument("--document", required=True)
            p.add_argument("--file", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "discover":
        result = {"bridges": discover(args.port)}
    else:
        port = resolve_bridge(args.port)
        if args.command == "windows":
            result = {"port": port, **request(port, "/eda-windows")}
        else:
            window_id = resolve_window(port, args.window_id)
            code = PROBE if args.command == "probe" else guarded_code(
                args.file.read_text(encoding="utf-8-sig"), args.project, args.document)
            result = {"port": port, **execute(port, window_id, code)}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
