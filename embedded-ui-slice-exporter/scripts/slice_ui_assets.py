from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


EXPORT_STYLE = """
html.__export-base [data-export-node] {
  visibility: hidden !important;
}

html.__export-transparent,
html.__export-transparent body {
  background: transparent !important;
}

html.__export-transparent [data-ui-root] {
  background: transparent !important;
  border-color: transparent !important;
  box-shadow: none !important;
}

html.__export-transparent [data-ui-root]::before,
html.__export-transparent [data-ui-root]::after {
  opacity: 0 !important;
}

html.__export-node-capture [data-ui-root] * {
  visibility: hidden !important;
}

html.__export-node-capture [data-export-node].__export-target,
html.__export-node-capture [data-export-node].__export-target * {
  visibility: visible !important;
}

html.__export-glyph-capture [data-ui-root] {
  visibility: hidden !important;
}

html.__export-glyph-capture,
html.__export-glyph-capture body {
  background: #000000 !important;
}

#__glyph_export_stage {
  position: fixed;
  left: 20px;
  top: 20px;
  display: grid;
  grid-template-columns: max-content;
  gap: 0;
  z-index: 9999;
  pointer-events: none;
}

.__glyph-cell {
  padding: 8px 1px;
  display: inline-flex;
  align-items: flex-end;
  justify-content: center;
  background: #000000;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Embedded Export Spec v2 UI assets.")
    parser.add_argument("--html", default="index.html")
    parser.add_argument("--output-dir")
    parser.add_argument("--root-selector", default="[data-ui-root]")
    parser.add_argument("--wait-ms", type=int, default=250)
    return parser.parse_args()


def sanitize_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip())
    slug = slug.strip("-").lower()
    return slug or "slice"


def prepare_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_csv(value: str | None, default: list[str] | None = None) -> list[str]:
    if value is None or not value.strip():
        return list(default or [])
    return [part.strip() for part in value.split(",") if part.strip()]


def determine_glyph_chars(text_node: dict[str, Any]) -> set[str]:
    data_format = str(text_node.get("format") or "text").lower()
    text = str(text_node.get("text") or "")
    if data_format == "int":
        return set("0123456789-")
    if data_format.startswith("float"):
        return set("0123456789.-")
    return {char for char in text}


def glyph_char_name(char: str) -> str:
    special_names = {
        " ": "space",
        ".": "dot",
        "-": "minus",
        "+": "plus",
        "/": "slash",
    }
    if char in special_names:
        return special_names[char]
    return sanitize_name(char)


def resolve_output_dir(html_path: Path, output_dir_arg: str | None) -> Path:
    folder_name = f"slices_{sanitize_name(html_path.stem)}"
    parent_dir = Path(output_dir_arg).resolve() if output_dir_arg else Path.cwd().resolve()
    return (parent_dir / folder_name).resolve()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


class LocalServer:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def __enter__(self) -> "LocalServer":
        handler = partial(QuietHandler, directory=str(self.root_dir))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        if self.port is None:
            raise RuntimeError("Local server has not been started.")
        return f"http://127.0.0.1:{self.port}"


def install_export_style(page) -> None:
    page.evaluate(
        """(styleText) => {
            const styleId = "__embedded_export_style__";
            let styleEl = document.getElementById(styleId);
            if (!styleEl) {
              styleEl = document.createElement("style");
              styleEl.id = styleId;
              document.head.appendChild(styleEl);
            }
            styleEl.textContent = styleText;
        }""",
        EXPORT_STYLE,
    )


def set_mode(page, *modes: str) -> None:
    classes = ["__export-base", "__export-transparent", "__export-node-capture", "__export-glyph-capture"]
    page.evaluate(
        """(payload) => {
            const html = document.documentElement;
            html.classList.remove(...payload.allClasses);
            html.classList.add(...payload.activeClasses);
        }""",
        {"allClasses": classes, "activeClasses": list(modes)},
    )


def crop_image(source: Path, bbox: dict[str, int], destination: Path) -> None:
    with Image.open(source) as image:
        left = bbox["x"]
        top = bbox["y"]
        right = left + bbox["width"]
        bottom = top + bbox["height"]
        image.crop((left, top, right, bottom)).save(destination)


def convert_black_bg_to_alpha(source: Path, destination: Path) -> None:
    with Image.open(source).convert("RGBA") as image:
        pixels = image.load()
        width, height = image.size
        converted = Image.new("RGBA", image.size, (255, 255, 255, 0))
        out_pixels = converted.load()
        for y in range(height):
            for x in range(width):
                r, g, b, _ = pixels[x, y]
                alpha = max(r, g, b)
                out_pixels[x, y] = (255, 255, 255, alpha)
        converted.save(destination)


def get_root_metadata(page, root_selector: str) -> dict[str, Any]:
    data = page.evaluate(
        """({ rootSelector }) => {
            const root = document.querySelector(rootSelector);
            if (!root) return null;
            const rect = root.getBoundingClientRect();
            return {
              version: root.getAttribute('data-ui-version') || '',
              screenWidth: root.getAttribute('data-screen-width') || '',
              screenHeight: root.getAttribute('data-screen-height') || '',
              x: Math.round(rect.left),
              y: Math.round(rect.top),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
        }""",
        {"rootSelector": root_selector},
    )
    if not isinstance(data, dict):
        raise RuntimeError(f"Root selector not found: {root_selector}")
    if str(data.get("version") or "") != "2":
        raise RuntimeError("Root node must declare data-ui-version=\"2\".")

    screen_width = int(data["screenWidth"]) if str(data.get("screenWidth") or "").isdigit() else int(data["width"])
    screen_height = int(data["screenHeight"]) if str(data.get("screenHeight") or "").isdigit() else int(data["height"])

    return {
        "x": int(data["x"]),
        "y": int(data["y"]),
        "width": int(data["width"]),
        "height": int(data["height"]),
        "screen_width": screen_width,
        "screen_height": screen_height,
    }


def get_pages(page, root_selector: str) -> list[dict[str, Any]]:
    items = page.evaluate(
        """({ rootSelector }) => {
            const root = document.querySelector(rootSelector);
            if (!root) return [];
            return Array.from(root.querySelectorAll('[data-ui-page]'))
              .map((el, domOrder) => {
                const pageId = el.getAttribute('data-page-id') || '';
                const pageTitle = el.getAttribute('data-page-title');
                const pageIndexRaw = el.getAttribute('data-page-index');
                const pageIndex = pageIndexRaw === null ? Number.NaN : Number(pageIndexRaw);
                return {
                  id: pageId,
                  title: pageTitle,
                  index: pageIndex,
                  domOrder,
                };
              })
              .sort((a, b) => {
                const left = Number.isFinite(a.index) ? a.index : Number.MAX_SAFE_INTEGER;
                const right = Number.isFinite(b.index) ? b.index : Number.MAX_SAFE_INTEGER;
                return left - right || a.domOrder - b.domOrder;
              });
        }""",
        {"rootSelector": root_selector},
    )
    if not isinstance(items, list) or not items:
        raise RuntimeError("No pages found. Each page must declare data-ui-page.")

    page_ids: set[str] = set()
    pages: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        page_id = str(item.get("id") or "").strip()
        page_title = str(item.get("title") or "").strip()
        raw_index = item.get("index")
        if not page_id:
            raise RuntimeError("Each data-ui-page must declare data-page-id.")
        if not page_title:
            raise RuntimeError(f"Page {page_id} must declare data-page-title.")
        if raw_index is None:
            raise RuntimeError(f"Page {page_id} must declare data-page-index.")
        if page_id in page_ids:
            raise RuntimeError(f"Duplicate data-page-id detected: {page_id}")
        page_ids.add(page_id)
        try:
            page_index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Page {page_id} has invalid data-page-index: {raw_index}") from exc
        pages.append(
            {
                "id": page_id,
                "title": page_title,
                "index": page_index,
            }
        )
    return pages


def activate_page(page, root_selector: str, page_id: str) -> None:
    page.evaluate(
        """({ rootSelector, pageId }) => {
            const root = document.querySelector(rootSelector);
            if (!root) {
              throw new Error(`Root selector not found: ${rootSelector}`);
            }

            const pages = Array.from(root.querySelectorAll('[data-ui-page]'));
            const target = pages.find((el) => el.getAttribute('data-page-id') === pageId);
            if (!target) {
              throw new Error(`Page not found: ${pageId}`);
            }

            const api = window.__EMBEDDED_EXPORT__;
            if (api && typeof api.activatePage === 'function') {
              api.activatePage(pageId);
            }

            pages.forEach((el) => {
              const active = el.getAttribute('data-page-id') === pageId;
              el.setAttribute('data-page-active', active ? 'true' : 'false');
              if (active) {
                el.removeAttribute('hidden');
              } else {
                el.setAttribute('hidden', '');
              }
            });
        }""",
        {"rootSelector": root_selector, "pageId": page_id},
    )
    page.wait_for_timeout(80)


def mark_export_default_classes(page) -> None:
    page.evaluate(
        """() => {
            document.querySelectorAll('[data-export-node]').forEach((el) => {
              el.setAttribute('data-export-initial-class', el.className || '');
            });
        }"""
    )


def restore_export_node_defaults(page) -> None:
    page.evaluate(
        """() => {
            document.querySelectorAll('[data-export-node]').forEach((el) => {
              el.className = el.getAttribute('data-export-initial-class') || '';
              el.classList.remove('__export-target');
            });
        }"""
    )


def set_capture_target(page, root_selector: str, page_id: str, export_id: str, state_name: str | None = None) -> None:
    page.evaluate(
        """({ rootSelector, pageId, exportId, stateName }) => {
            const root = document.querySelector(rootSelector);
            if (!root) {
              throw new Error(`Root selector not found: ${rootSelector}`);
            }

            const activePage = Array.from(root.querySelectorAll('[data-ui-page]'))
              .find((el) => el.getAttribute('data-page-id') === pageId);
            if (!activePage) {
              throw new Error(`Page not found: ${pageId}`);
            }

            const node = Array.from(activePage.querySelectorAll('[data-export-node]'))
              .find((el) => el.getAttribute('data-export-id') === exportId);
            if (!node) {
              throw new Error(`Export node not found: ${exportId}`);
            }

            node.classList.add('__export-target');

            const stateAttr = (name) => {
              return `data-state-class-${name}`;
            };

            const states = (node.dataset.states || 'normal')
              .split(',')
              .map((part) => part.trim())
              .filter(Boolean);

            states.forEach((state) => {
              const className = node.getAttribute(stateAttr(state));
              if (className) {
                node.classList.remove(className);
              }
            });

            if (stateName && stateName !== 'normal') {
              const className = node.getAttribute(stateAttr(stateName));
              if (!className) {
                throw new Error(`State class not declared for ${exportId}:${stateName}`);
              }
              node.classList.add(className);
            }
        }""",
        {
            "rootSelector": root_selector,
            "pageId": page_id,
            "exportId": export_id,
            "stateName": state_name or "normal",
        },
    )


def get_export_nodes(page, cdp, root_selector: str, page_id: str) -> list[dict[str, Any]]:
    items = page.evaluate(
        """({ rootSelector, pageId }) => {
            const root = document.querySelector(rootSelector);
            if (!root) return [];
            const activePage = Array.from(root.querySelectorAll('[data-ui-page]'))
              .find((el) => el.getAttribute('data-page-id') === pageId);
            if (!activePage) return [];

            const rootRect = root.getBoundingClientRect();
            const nodes = Array.from(activePage.querySelectorAll('[data-export-node]'));
            
            // 为每个节点添加临时 id 以便 CDP 查找
            nodes.forEach((el, index) => {
              el.setAttribute('data-export-cdp-id', `cdp-${pageId}-${index}`);
            });
            
            return nodes.map((el) => {
              const rect = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              const stateClasses = {};
              el.getAttributeNames().forEach((attrName) => {
                if (!attrName.startsWith('data-state-class-')) {
                  return;
                }
                const stateName = attrName.slice('data-state-class-'.length);
                const className = el.getAttribute(attrName) || '';
                if (!stateName || !className) {
                  return;
                }
                stateClasses[stateName] = className;
              });

              return {
                id: el.getAttribute('data-export-id') || '',
                cdpId: el.getAttribute('data-export-cdp-id') || '',
                type: el.getAttribute('data-export-node') || '',
                bind: el.getAttribute('data-bind') || '',
                x: Math.round(rect.left - rootRect.left),
                y: Math.round(rect.top - rootRect.top),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                text: el.textContent || '',
                fontToken: el.getAttribute('data-font-token') || '',
                glyphSet: el.getAttribute('data-glyph-set') || '',
                format: el.getAttribute('data-format') || '',
                controlType: el.getAttribute('data-control-type') || '',
                action: el.getAttribute('data-action') || '',
                targetPage: el.getAttribute('data-target-page') || '',
                states: (el.getAttribute('data-states') || '').split(',').map((part) => part.trim()).filter(Boolean),
                stateClasses,
                imageType: el.getAttribute('data-image-type') || '',
                indicatorType: el.getAttribute('data-indicator-type') || '',
                containerType: el.getAttribute('data-container-type') || '',
                styleSnapshot: {
                  fontFamily: style.fontFamily,
                  fontSize: style.fontSize,
                  fontWeight: style.fontWeight,
                  fontStyle: style.fontStyle,
                  lineHeight: style.lineHeight,
                  letterSpacing: style.letterSpacing,
                  fontVariantNumeric: style.fontVariantNumeric,
                  textTransform: style.textTransform,
                  fontFeatureSettings: style.fontFeatureSettings,
                },
              };
            }).filter((item) => item.id && item.type && item.width > 0 && item.height > 0);
        }""",
        {"rootSelector": root_selector, "pageId": page_id},
    )
    if not isinstance(items, list):
        raise RuntimeError("Unexpected export node metadata.")

    node_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        export_id = str(item.get("id") or "").strip()
        if not export_id:
            raise RuntimeError("Each export node must declare data-export-id.")
        if export_id in node_ids:
            raise RuntimeError(f"Duplicate data-export-id detected in page {page_id}: {export_id}")
        node_ids.add(export_id)
        node_type = str(item.get("type") or "").strip()
        
        cdp_id = str(item.get("cdpId") or "")
        
        # Get actual rendered fonts via CDP
        rendered_fonts = []
        if cdp_id:
            try:
                # Need to resolve the DOM node ID first
                node_info = cdp.send("DOM.getDocument")
                root_node_id = node_info["root"]["nodeId"]
                query_result = cdp.send("DOM.querySelector", {
                    "nodeId": root_node_id,
                    "selector": f"[data-export-cdp-id='{cdp_id}']"
                })
                target_node_id = query_result.get("nodeId")
                
                if target_node_id:
                    fonts_result = cdp.send("CSS.getPlatformFontsForNode", {
                        "nodeId": target_node_id
                    })
                    if "fonts" in fonts_result:
                        rendered_fonts = [font["familyName"] for font in fonts_result["fonts"]]
            except Exception as e:
                print(f"Warning: Failed to get rendered fonts for {export_id}: {e}")
                
        if "styleSnapshot" in item:
            item["styleSnapshot"]["renderedFonts"] = rendered_fonts

        if node_type == "text":
            missing_attrs = [
                attr_name
                for attr_name, value in (
                    ("data-bind", item.get("bind")),
                    ("data-font-token", item.get("fontToken")),
                    ("data-glyph-set", item.get("glyphSet")),
                    ("data-format", item.get("format")),
                )
                if not str(value or "").strip()
            ]
            if missing_attrs:
                raise RuntimeError(
                    f'Text node "{export_id}" in page {page_id} is missing required attributes: '
                    + ", ".join(missing_attrs)
                )
        nodes.append(item)
    return nodes


def render_single_glyph(page, style_snapshot: dict[str, Any], char: str) -> dict[str, Any]:
    glyph = page.evaluate(
        """({ styleSnapshot, char }) => {
            const oldStage = document.getElementById('__glyph_export_stage');
            if (oldStage) oldStage.remove();

            const stage = document.createElement('div');
            stage.id = '__glyph_export_stage';
            document.body.appendChild(stage);

            const cell = document.createElement('div');
            cell.className = '__glyph-cell';
            cell.id = '__glyph_export_cell';
            cell.dataset.char = char;
            cell.dataset.charCode = String(char.charCodeAt(0));

            const span = document.createElement('span');
            span.textContent = char === ' ' ? '\\u00A0' : char;
            span.style.color = '#ffffff';
            span.style.fontFamily = styleSnapshot.fontFamily || 'Arial, sans-serif';
            span.style.fontSize = styleSnapshot.fontSize || '16px';
            span.style.fontWeight = styleSnapshot.fontWeight || '400';
            span.style.fontStyle = styleSnapshot.fontStyle || 'normal';
            span.style.lineHeight = styleSnapshot.lineHeight || '1';
            span.style.letterSpacing = styleSnapshot.letterSpacing || 'normal';
            span.style.fontVariantNumeric = styleSnapshot.fontVariantNumeric || 'normal';
            span.style.textTransform = styleSnapshot.textTransform || 'none';
            span.style.fontFeatureSettings = styleSnapshot.fontFeatureSettings || 'normal';
            span.style.display = 'inline-block';
            cell.appendChild(span);
            stage.appendChild(cell);

            const rect = cell.getBoundingClientRect();
            return {
              char,
              charCode: char.charCodeAt(0),
              x: Math.round(rect.left),
              y: Math.round(rect.top),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
        }""",
        {"styleSnapshot": style_snapshot, "char": char},
    )
    if not isinstance(glyph, dict):
        raise RuntimeError("Unexpected glyph metadata.")
    return glyph


def remove_glyph_stage(page) -> None:
    page.evaluate(
        """() => {
            const stage = document.getElementById('__glyph_export_stage');
            if (stage) stage.remove();
        }"""
    )


def build_text_manifest(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(node["id"]),
        "type": "text",
        "bind": str(node.get("bind") or ""),
        "font_token": str(node.get("fontToken") or ""),
        "glyph_set": str(node.get("glyphSet") or ""),
        "format": str(node.get("format") or ""),
        "x": int(node["x"]),
        "y": int(node["y"]),
        "width": int(node["width"]),
        "height": int(node["height"]),
    }


def build_region_manifest(node: dict[str, Any], node_type: str) -> dict[str, Any]:
    item = {
        "id": str(node["id"]),
        "type": node_type,
        "bind": str(node.get("bind") or ""),
        "x": int(node["x"]),
        "y": int(node["y"]),
        "width": int(node["width"]),
        "height": int(node["height"]),
    }
    if node_type == "image":
        item["image_type"] = str(node.get("imageType") or "")
    if node_type == "indicator":
        item["indicator_type"] = str(node.get("indicatorType") or "")
        item["states"] = list(node.get("states") or [])
    if node_type == "container":
        item["container_type"] = str(node.get("containerType") or "")
    return item


def capture_node_asset(
    page,
    temp_dir: Path,
    root_selector: str,
    root_box: dict[str, int],
    page_id: str,
    page_folder: str,
    node: dict[str, Any],
    output_path: Path,
    state_name: str | None = None,
) -> str:
    set_mode(page, "__export-transparent", "__export-node-capture")
    restore_export_node_defaults(page)
    set_capture_target(page, root_selector, page_id, str(node["id"]), state_name)
    page.wait_for_timeout(50)
    capture_suffix = sanitize_name(state_name or "current")
    capture_raw = temp_dir / f"{page_folder}-{sanitize_name(str(node['id']))}-{capture_suffix}.png"
    page.screenshot(path=str(capture_raw), omit_background=True)
    crop_image(
        capture_raw,
        {
            "x": root_box["x"] + int(node["x"]),
            "y": root_box["y"] + int(node["y"]),
            "width": int(node["width"]),
            "height": int(node["height"]),
        },
        output_path,
    )
    restore_export_node_defaults(page)
    return str(output_path)


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    html_dir = html_path.parent
    output_dir = prepare_dir(resolve_output_dir(html_path, args.output_dir))
    base_dir = prepare_dir(output_dir / "base")
    preview_dir = prepare_dir(output_dir / "preview")
    controls_dir = prepare_dir(output_dir / "controls")
    static_dir = prepare_dir(output_dir / "static")
    images_dir = prepare_dir(output_dir / "images")
    indicators_dir = prepare_dir(output_dir / "indicators")
    glyphs_dir = prepare_dir(output_dir / "glyphs")

    manifest: dict[str, Any] = {
        "version": 2,
        "source_html": str(html_path),
        "root_selector": args.root_selector,
        "screen": {},
        "pages": [],
        "glyph_sets": {},
    }

    with LocalServer(html_dir) as server:
        page_url = f"{server.base_url}/{html_path.relative_to(html_dir).as_posix()}"

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch()
            except PlaywrightError as exc:
                raise RuntimeError(
                    "Chromium is not available for Playwright. Run: python -m playwright install chromium"
                ) from exc

            context = browser.new_context(viewport={"width": 1100, "height": 760}, device_scale_factor=1)
            page = context.new_page()
            
            # Enable CSS agent for CDP font retrieval later
            cdp = page.context.new_cdp_session(page)
            cdp.send("DOM.enable")
            cdp.send("CSS.enable")
            
            page.goto(page_url, wait_until="networkidle")
            page.wait_for_timeout(args.wait_ms)
            install_export_style(page)
            mark_export_default_classes(page)

            root_meta = get_root_metadata(page, args.root_selector)
            manifest["screen"] = {
                "width": int(root_meta["screen_width"]),
                "height": int(root_meta["screen_height"]),
            }
            root_box = {
                "x": int(root_meta["x"]),
                "y": int(root_meta["y"]),
                "width": int(root_meta["width"]),
                "height": int(root_meta["height"]),
            }

            pages = get_pages(page, args.root_selector)
            glyph_sets: dict[str, dict[str, Any]] = {}

            with TemporaryDirectory() as temp_dir_name:
                temp_dir = Path(temp_dir_name)

                for order, page_info in enumerate(pages, start=1):
                    page_id = str(page_info["id"])
                    page_title = str(page_info["title"])
                    page_index = int(page_info["index"])
                    page_folder = f"page_{order:02d}"

                    activate_page(page, args.root_selector, page_id)
                    restore_export_node_defaults(page)

                    page_base_dir = ensure_dir(base_dir / page_folder)
                    page_preview_dir = ensure_dir(preview_dir / page_folder)
                    page_controls_dir = ensure_dir(controls_dir / page_folder)
                    page_static_dir = ensure_dir(static_dir / page_folder)
                    page_images_dir = ensure_dir(images_dir / page_folder)
                    page_indicators_dir = ensure_dir(indicators_dir / page_folder)

                    set_mode(page)
                    composite_raw = temp_dir / f"{page_folder}-composite.png"
                    page.screenshot(path=str(composite_raw))
                    composite_path = page_preview_dir / "full_composite.png"
                    crop_image(composite_raw, root_box, composite_path)

                    nodes = get_export_nodes(page, cdp, args.root_selector, page_id)

                    set_mode(page, "__export-base")
                    page.wait_for_timeout(80)
                    base_raw = temp_dir / f"{page_folder}-base.png"
                    page.screenshot(path=str(base_raw))
                    base_path = page_base_dir / "static_base.png"
                    crop_image(base_raw, root_box, base_path)

                    page_manifest = {
                        "id": page_id,
                        "title": page_title,
                        "index": page_index,
                        "files": {
                            "base": str(base_path),
                            "preview": str(composite_path),
                        },
                        "nodes": [],
                    }

                    for node in nodes:
                        node_type = str(node["type"])
                        if node_type == "text":
                            node_manifest = build_text_manifest(node)
                            page_manifest["nodes"].append(node_manifest)
                            glyph_set = str(node.get("glyphSet") or "")
                            if glyph_set:
                                if glyph_set not in glyph_sets:
                                    glyph_sets[glyph_set] = {
                                        "chars": set(),
                                        "style_snapshot": dict(node.get("styleSnapshot") or {}),
                                        "font_token": str(node.get("fontToken") or ""),
                                    }
                                glyph_sets[glyph_set]["chars"].update(determine_glyph_chars(node))
                            continue

                        if node_type == "control":
                            states = list(node.get("states") or [])
                            if not states:
                                states = ["normal"]
                            control_dir = ensure_dir(page_controls_dir / sanitize_name(str(node["id"])))
                            state_files: dict[str, str] = {}
                            for state_name in states:
                                state_path = control_dir / f"{sanitize_name(state_name)}.png"
                                state_files[state_name] = capture_node_asset(
                                    page,
                                    temp_dir,
                                    args.root_selector,
                                    root_box,
                                    page_id,
                                    page_folder,
                                    node,
                                    state_path,
                                    state_name,
                                )
                            page_manifest["nodes"].append(
                                {
                                    "id": str(node["id"]),
                                    "type": "control",
                                    "control_type": str(node.get("controlType") or ""),
                                    "action": str(node.get("action") or ""),
                                    "target_page": str(node.get("targetPage") or ""),
                                    "x": int(node["x"]),
                                    "y": int(node["y"]),
                                    "width": int(node["width"]),
                                    "height": int(node["height"]),
                                    "states": state_files,
                                }
                            )
                            continue

                        if node_type == "static":
                            static_path = page_static_dir / f"{sanitize_name(str(node['id']))}.png"
                            page_manifest["nodes"].append(
                                {
                                    "id": str(node["id"]),
                                    "type": "static",
                                    "x": int(node["x"]),
                                    "y": int(node["y"]),
                                    "width": int(node["width"]),
                                    "height": int(node["height"]),
                                    "file": capture_node_asset(
                                        page,
                                        temp_dir,
                                        args.root_selector,
                                        root_box,
                                        page_id,
                                        page_folder,
                                        node,
                                        static_path,
                                    ),
                                }
                            )
                            continue

                        if node_type == "image":
                            image_dir = ensure_dir(page_images_dir / sanitize_name(str(node["id"])))
                            image_path = image_dir / "current.png"
                            page_manifest["nodes"].append(
                                {
                                    "id": str(node["id"]),
                                    "type": "image",
                                    "bind": str(node.get("bind") or ""),
                                    "image_type": str(node.get("imageType") or ""),
                                    "x": int(node["x"]),
                                    "y": int(node["y"]),
                                    "width": int(node["width"]),
                                    "height": int(node["height"]),
                                    "file": capture_node_asset(
                                        page,
                                        temp_dir,
                                        args.root_selector,
                                        root_box,
                                        page_id,
                                        page_folder,
                                        node,
                                        image_path,
                                    ),
                                }
                            )
                            continue

                        if node_type == "indicator":
                            indicator_states = list(node.get("states") or [])
                            if not indicator_states:
                                indicator_states = ["normal"]
                            indicator_dir = ensure_dir(page_indicators_dir / sanitize_name(str(node["id"])))
                            state_files: dict[str, str] = {}
                            for state_name in indicator_states:
                                state_path = indicator_dir / f"{sanitize_name(state_name)}.png"
                                state_files[state_name] = capture_node_asset(
                                    page,
                                    temp_dir,
                                    args.root_selector,
                                    root_box,
                                    page_id,
                                    page_folder,
                                    node,
                                    state_path,
                                    state_name,
                                )
                            page_manifest["nodes"].append(
                                {
                                    "id": str(node["id"]),
                                    "type": "indicator",
                                    "bind": str(node.get("bind") or ""),
                                    "indicator_type": str(node.get("indicatorType") or ""),
                                    "x": int(node["x"]),
                                    "y": int(node["y"]),
                                    "width": int(node["width"]),
                                    "height": int(node["height"]),
                                    "states": state_files,
                                }
                            )
                            continue

                        if node_type == "container":
                            page_manifest["nodes"].append(build_region_manifest(node, node_type))
                            continue

                        raise RuntimeError(f"Unsupported data-export-node type: {node_type}")

                    manifest["pages"].append(page_manifest)

                if glyph_sets:
                    set_mode(page, "__export-transparent", "__export-glyph-capture")
                    page.wait_for_timeout(80)
                    for glyph_set_name, glyph_info in glyph_sets.items():
                        font_dir = prepare_dir(glyphs_dir / sanitize_name(glyph_set_name))
                        chars = sorted(glyph_info["chars"])
                        manifest["glyph_sets"][glyph_set_name] = {
                            "font_token": str(glyph_info.get("font_token") or ""),
                            "font_family": str(glyph_info.get("style_snapshot", {}).get("fontFamily") or ""),
                            "rendered_fonts": glyph_info.get("style_snapshot", {}).get("renderedFonts") or [],
                            "font_size": str(glyph_info.get("style_snapshot", {}).get("fontSize") or ""),
                            "font_weight": str(glyph_info.get("style_snapshot", {}).get("fontWeight") or ""),
                            "chars": [],
                        }
                        for char in chars:
                            glyph = render_single_glyph(page, dict(glyph_info["style_snapshot"]), char)
                            char_code = int(glyph["charCode"])
                            char_name = glyph_char_name(char)
                            glyph_path = font_dir / f"ascii_{char_code:03d}_{char_name}.png"
                            glyph_raw_path = temp_dir / f"{sanitize_name(glyph_set_name)}-{char_code:03d}.png"
                            page.screenshot(
                                path=str(glyph_raw_path),
                                clip={
                                    "x": float(glyph["x"]),
                                    "y": float(glyph["y"]),
                                    "width": float(glyph["width"]),
                                    "height": float(glyph["height"]),
                                },
                            )
                            convert_black_bg_to_alpha(glyph_raw_path, glyph_path)
                            manifest["glyph_sets"][glyph_set_name]["chars"].append(
                                {
                                    "char": char,
                                    "char_code": char_code,
                                    "width": int(glyph["width"]),
                                    "height": int(glyph["height"]),
                                    "file": str(glyph_path),
                                }
                            )
                    remove_glyph_stage(page)

            context.close()
            browser.close()

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Source: {html_path}")
    print(f"Output: {output_dir}")
    print(f"Pages: {len(manifest['pages'])}")
    print(f"Glyph sets: {', '.join(manifest['glyph_sets'].keys())}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
