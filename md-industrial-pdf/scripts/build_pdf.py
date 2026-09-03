# -*- coding: utf-8 -*-
"""
md-industrial-pdf 通用构建器：Markdown -> 工业风 PDF（封面 + 页脚图签）。

用法：
    python build_pdf.py INPUT.md [INPUT2.md ...] [选项]

默认行为：
    - 输出与输入同名的 .pdf（同目录）
    - 封面主标题自动取文档首个 H1；--title/--subtitle 可覆盖
    - 封面语言按标题是否含中文自动判断（--lang 可强制）
    - 厂商标识缺省为中性几何标识（--vendor/--logo 定制）
    - 配色 #3A506B / #5BC0BE / #CDEDF6（--colors 可覆盖）
    - 第 2 页起盖页脚图签，封面不盖、不计数
    - 构建后自动做程序化质检（--no-verify 跳过）

依赖：pip install markdown pymupdf；本机安装 Microsoft Edge 或 Chrome。
"""

import argparse
import base64
import datetime
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import markdown

MM = 72 / 25.4  # mm -> pt

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# CSS 使用 @DARK@/@MID@/@LIGHT@ 记号替换，避免 % 转义问题
CSS_TEMPLATE = """
@page { size: A4; margin: 16mm 16mm 20mm 16mm; }
@@FIRST_PAGE@@

* { box-sizing: border-box; }

html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }

body {
    font-family: Arial, "Microsoft YaHei", "SimSun", sans-serif;
    font-size: 9pt;
    line-height: 1.6;
    color: @DARK@;
    margin: 0;
}

/* ============================== 封面 ============================== */

.cover {
    height: 296mm;
    padding: 18mm 20mm 16mm;
    display: flex;
    flex-direction: column;
    page-break-after: always;
    overflow: hidden;
}

.cover-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 6mm;
    border-bottom: 0.6pt solid @LIGHT@;
}

.brand { display: flex; align-items: center; gap: 3.5mm; min-height: 12mm; }

.brand img { height: 11mm; max-width: 55mm; object-fit: contain; }

.brand-mark { display: flex; gap: 1.6mm; }
.brand-mark i { width: 4.2mm; height: 4.2mm; display: block; }
.brand-mark i:nth-child(1) { background: @DARK@; }
.brand-mark i:nth-child(2) { background: @MID@; }
.brand-mark i:nth-child(3) { background: @LIGHT@; border: 0.4pt solid @MID@; }

.brand-name {
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 0.6pt;
    color: @DARK@;
}

.cover-doc-code {
    font-size: 8pt;
    letter-spacing: 1.5pt;
    color: @MID@;
    padding-top: 2mm;
}

.cover-main { margin-top: auto; margin-bottom: auto; padding-top: 20mm; }

.cover-tag {
    font-size: 10pt;
    letter-spacing: 3pt;
    color: @MID@;
    margin-bottom: 6mm;
}

.cover-title {
    font-size: 27pt;
    font-weight: 700;
    line-height: 1.25;
    letter-spacing: 0.5pt;
    color: @DARK@;
    margin: 0 0 4mm;
}

.cover-subtitle {
    font-size: 14pt;
    font-weight: 400;
    color: #566073;
    margin-bottom: 9mm;
}

.cover-bar { display: flex; height: 1.6mm; width: 100%; }
.cover-bar i { display: block; height: 100%; }
.cover-bar i:nth-child(1) { width: 58%; background: @DARK@; }
.cover-bar i:nth-child(2) { width: 26%; background: @MID@; }
.cover-bar i:nth-child(3) { width: 16%; background: @LIGHT@; }

.cover-block { margin-top: auto; }

.cover-info {
    width: 100%;
    border-collapse: collapse;
    border: 0.9pt solid @MID@;
    font-size: 9pt;
}

.cover-info td { border: 0.5pt solid @MID@; padding: 3.2mm 5mm; }

.cover-info .k {
    width: 34%;
    background: @LIGHT@;
    color: #566073;
    font-weight: 700;
    letter-spacing: 0.3pt;
}

.cover-info .v { color: @DARK@; }

.cover-note {
    margin-top: 4mm;
    font-size: 7pt;
    color: @MID@;
    letter-spacing: 0.4pt;
}

/* ============================== 正文 ============================== */

main h1 {
    font-size: 15.5pt;
    font-weight: 700;
    letter-spacing: 0.4pt;
    border-top: 3pt solid @DARK@;
    border-bottom: 0.8pt solid @MID@;
    padding: 6pt 0 5pt;
    margin: 0 0 10pt;
}

main h2 {
    font-size: 12pt;
    font-weight: 700;
    border-bottom: 1.2pt solid @DARK@;
    padding-bottom: 2.5pt;
    margin: 16pt 0 7pt;
    break-after: avoid;
}

main h3 {
    font-size: 10.5pt;
    font-weight: 700;
    margin: 12pt 0 5pt;
    break-after: avoid;
}

main p { margin: 4pt 0; }

main ul, main ol { margin: 4pt 0; padding-left: 16pt; }
main li { margin: 2pt 0; }

main table {
    width: 100%;
    border-collapse: collapse;
    margin: 6pt 0 10pt;
    font-size: 8pt;
    line-height: 1.45;
    border: 0.9pt solid @DARK@;
}

main th {
    background: @DARK@;
    color: #ffffff;
    font-weight: 700;
    border: 0.5pt solid @DARK@;
    padding: 3pt 5pt;
    text-align: left;
    vertical-align: top;
}

main td {
    border: 0.5pt solid #A9B2BF;
    padding: 3pt 5pt;
    vertical-align: top;
}

main tr { break-inside: avoid; }

main code {
    font-family: Consolas, "Courier New", monospace;
    font-size: 8pt;
    background: @LIGHT@;
    padding: 0 2pt;
}

main pre {
    background: @LIGHT@;
    border: 0.5pt solid @MID@;
    padding: 5pt 7pt;
    margin: 5pt 0 8pt;
    white-space: pre-wrap;
    break-inside: avoid;
}

main pre code { background: none; padding: 0; font-size: 8pt; }

main blockquote {
    border-left: 2.5pt solid @DARK@;
    background: @LIGHT@;
    margin: 6pt 0;
    padding: 4pt 8pt;
}

main blockquote p { margin: 2pt 0; }

main hr { border: none; border-top: 0.8pt solid @MID@; margin: 12pt 0; }

main img {
    max-width: 62%;
    display: block;
    margin: 4pt 0 8pt;
    border: 0.5pt solid @MID@;
    padding: 3pt;
}

main strong { font-weight: 700; }

main a { color: @DARK@; text-decoration: underline; }
"""

COVER_TMPL = """
<section class="cover">
  <div class="cover-top">
    <div class="brand">{brand}</div>
    <div class="cover-doc-code">{doc_code}</div>
  </div>
  <div class="cover-main">
    <div class="cover-tag">{tag}</div>
    <div class="cover-title">{title}</div>
    <div class="cover-subtitle">{subtitle}</div>
    <div class="cover-bar"><i></i><i></i><i></i></div>
  </div>
  <div class="cover-block">
    <table class="cover-info">
      {info_rows}
    </table>
    <div class="cover-note">{note}</div>
  </div>
</section>
"""

NEUTRAL_MARK = '<span class="brand-mark"><i></i><i></i><i></i></span>'


# --------------------------------------------------------------- 工具 ----

def hex_to_rgb(color: str):
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def find_browser(override: str) -> str:
    if override:
        if Path(override).exists():
            return override
        raise SystemExit("指定的浏览器不存在: %s" % override)
    for p in BROWSER_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("未找到 Edge/Chrome，请用 --edge 指定浏览器路径")


def md_first_h1(text: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    return m.group(1) if m else ""


def detect_lang(*texts: str) -> str:
    return "zh" if any(CJK_RE.search(t) for t in texts if t) else "en"


def strip_leading_meta(html: str) -> str:
    """封面已承载标题与元信息时，移除正文开头重复的 H1 / 元信息表 / 互链说明 / 多余分隔线。"""
    html = re.sub(r"^[\s]*<h1>.*?</h1>", "", html, count=1, flags=re.S)
    html = re.sub(r"^[\s]*<table>.*?</table>", "", html, count=1, flags=re.S)
    m = re.search(r"<blockquote>.*?</blockquote>", html, re.S)
    if m and re.search(r"\.md", m.group(0)):
        html = html[: m.start()] + html[m.end():]
    html = re.sub(r"^[\s]*(<hr\s*/?>)", "", html, count=1)
    return html.lstrip()


# --------------------------------------------------------------- 封面 ----

def logo_data_uri(path: str) -> str:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "svg": "image/svg+xml", "gif": "image/gif", "webp": "image/webp"}.get(ext)
    if mime is None:
        raise SystemExit("不支持的 logo 格式: %s（支持 png/jpg/svg/gif/webp）" % ext)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return "data:%s;base64,%s" % (mime, data)


def build_brand(vendor: str, logo: str) -> str:
    """封面厂商标识：logo > 厂商名 + 几何标识 > 纯中性几何标识。"""
    if logo:
        img = '<img src="%s" alt="logo">' % logo_data_uri(logo)
        return img + ('<span class="brand-name">%s</span>' % vendor if vendor else "")
    if vendor:
        return NEUTRAL_MARK + '<span class="brand-name">%s</span>' % vendor
    return NEUTRAL_MARK


def build_cover(doc_code, lang, title, subtitle, rev, date, brand_html, metas):
    if lang == "zh":
        tag = "TECHNICAL SPECIFICATION&nbsp;&nbsp;·&nbsp;&nbsp;技术规格书"
        rows = [
            ("文档编号&nbsp;&nbsp;DOC NO.", doc_code),
            ("版本&nbsp;&nbsp;REVISION", rev.replace("REV ", "")),
            ("日期&nbsp;&nbsp;DATE", date),
        ]
        for k, v in metas:
            rows.append((k, v))
        note = "本文件内容如有变更，恕不另行通知。 Specifications subject to change without notice."
    else:
        tag = "TECHNICAL SPECIFICATION"
        rows = [
            ("DOC NO.", doc_code),
            ("REVISION", rev.replace("REV ", "")),
            ("DATE", date),
        ]
        for k, v in metas:
            rows.append((k, v))
        note = "Specifications subject to change without notice."
    info_rows = "\n".join(
        '<tr><td class="k">%s</td><td class="v">%s</td></tr>' % (k, v) for k, v in rows
    )
    return COVER_TMPL.format(
        brand=brand_html, doc_code=doc_code, tag=tag, title=title,
        subtitle=subtitle, info_rows=info_rows, note=note,
    )


# ------------------------------------------------------------- 打印盖章 ----

def print_pdf(html_path: Path, pdf_path: Path, browser: str) -> None:
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            "--virtual-time-budget=10000",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)


def stamp_footer(pdf_path: Path, doc_code: str, rev: str, date: str,
                 has_cover: bool, colors) -> None:
    """盖页脚图签：细线 + 左侧文档代号 + 右侧页码；封面（若有）不盖不计页。"""
    dark_rgb = hex_to_rgb(colors[0])
    mid_rgb = hex_to_rgb(colors[1])
    doc = fitz.open(pdf_path)
    n = doc.page_count
    total = n - 1 if has_cover else n
    start = 1 if has_cover else 0
    fs = 6.3
    for i in range(start, n):
        page = doc[i]
        w, h = page.rect.width, page.rect.height
        lm, rm = 16 * MM, 16 * MM
        y = h - 13 * MM
        page.draw_line(fitz.Point(lm, y), fitz.Point(w - rm, y), color=dark_rgb, width=0.7)
        left = "%s  |  %s  |  %s" % (doc_code, rev, date)
        # 基线在线下方 9pt：字面上升约 6.8pt，确保文字整体位于分隔线下且留有间隙
        page.insert_text((lm, y + 9.0), left, fontname="helv", fontsize=fs, color=dark_rgb)
        right = "PAGE %d / %d" % (i - start + 1, total)
        tw = fitz.get_text_length(right, fontname="helv", fontsize=fs)
        page.insert_text((w - rm - tw, y + 9.0), right, fontname="helv", fontsize=fs, color=mid_rgb)
    tmp = pdf_path.with_suffix(".tmp.pdf")
    doc.save(str(tmp), garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf_path)


# --------------------------------------------------------------- 质检 ----

def verify(pdf_path: Path, has_cover: bool) -> list:
    """程序化质检，返回问题列表（空 = 通过）。"""
    problems = []
    doc = fitz.open(pdf_path)
    n = doc.page_count
    total = n - 1 if has_cover else n
    start = 1 if has_cover else 0

    if has_cover:
        cover_text = doc[0].get_text().replace(" ", "")
        if "PAGE" in cover_text:
            problems.append("p1: 封面出现页码图签")

    for i in range(n):
        page = doc[i]
        w, h = page.rect.width, page.rect.height
        text = page.get_text()
        if "\ufffd" in text:
            problems.append("p%d: 存在乱码字符 U+FFFD" % (i + 1))
        for b in page.get_text("blocks"):
            if b[2] > w + 2 or b[0] < -2 or b[3] > h + 2 or b[1] < -2:
                problems.append("p%d: 文本块越出页面 %s" % (i + 1, str(b[:4])))

    for i in range(start, n):
        page = doc[i]
        h = page.rect.height
        t = page.get_text()
        if "PAGE %d / %d" % (i - start + 1, total) not in t:
            problems.append("p%d: 页脚页码缺失或错误" % (i + 1))
        # 页脚文字必须整体位于分隔线下方
        line_y = None
        for d in page.get_drawings():
            r = d["rect"]
            if r.y1 > h - 16 * MM and abs(r.y0 - r.y1) < 0.5:
                line_y = r.y0
                break
        if line_y is None:
            problems.append("p%d: 页脚分隔线缺失" % (i + 1))
            continue
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            if y0 > h - 16 * MM and y0 <= line_y + 0.5:
                problems.append("p%d: 页脚文字 %r 与分隔线重叠" % (i + 1, word))
    doc.close()
    return problems


# --------------------------------------------------------------- 构建 ----

def build_one(args, md_path: Path, browser: str) -> Path:
    md_text = md_path.read_text(encoding="utf-8")

    title = args.title or md_first_h1(md_text) or md_path.stem
    subtitle = args.subtitle or ""
    doc_code = args.doc_code or md_path.stem.replace("_", "-").upper()
    lang = args.lang if args.lang != "auto" else detect_lang(title, subtitle)

    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    if args.cover and args.strip_meta:
        body = strip_leading_meta(body)

    css = (CSS_TEMPLATE
           .replace("@DARK@", args.colors[0])
           .replace("@MID@", args.colors[1])
           .replace("@LIGHT@", args.colors[2])
           .replace("@@FIRST_PAGE@@", "@page :first { margin: 0; }" if args.cover else ""))

    cover_html = ""
    if args.cover:
        brand = build_brand(args.vendor, args.logo)
        cover_html = build_cover(doc_code, lang, title, subtitle,
                                 args.rev, args.date, brand, args.metas)

    html = (
        '<!doctype html>\n<html lang="%s">\n<head><meta charset="utf-8">'
        "<title>%s</title>\n<style>%s</style></head>\n<body>\n%s\n<main>\n%s\n</main>\n</body>\n</html>\n"
        % ("zh-CN" if lang == "zh" else "en", doc_code, css, cover_html, body)
    )
    html_path = md_path.parent / ("_print_%s.html" % doc_code.lower())
    html_path.write_text(html, encoding="utf-8")

    pdf_path = Path(args.out).resolve() if args.out else md_path.with_suffix(".pdf")
    print_pdf(html_path, pdf_path, browser)
    html_path.unlink()
    stamp_footer(pdf_path, doc_code, args.rev, args.date, args.cover, args.colors)

    problems = []
    if args.verify:
        problems = verify(pdf_path, args.cover)
    n = fitz.open(pdf_path).page_count
    tag = "cover + %d content" % (n - 1) if args.cover else "%d pages" % n
    print("%s -> %s (%s)%s" % (md_path.name, pdf_path, tag,
                                "" if not problems else "  [VERIFY FAIL]"))
    for p in problems:
        print("  - " + p)
    return pdf_path


def parse_colors(s: str):
    parts = [p.strip().lstrip("#") for p in s.split(",")]
    if len(parts) != 3 or not all(re.fullmatch(r"[0-9A-Fa-f]{6}", p) for p in parts):
        raise SystemExit('--colors 格式应为 "DARK,MID,LIGHT" 六位十六进制，如 3A506B,5BC0BE,CDEDF6')
    return ["#" + p.upper() for p in parts]


def parse_meta(s: str):
    if "=" not in s:
        raise SystemExit('--meta 格式应为 "键=值"，如 "协议 PROTOCOL=Modbus RTU"')
    k, v = s.split("=", 1)
    return k.strip(), v.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown -> 工业风 PDF（封面 + 页脚图签）")
    ap.add_argument("inputs", nargs="+", metavar="MD", help="输入 Markdown 文件")
    ap.add_argument("-o", "--out", help="输出 PDF 路径（仅单输入时有效）")
    ap.add_argument("--title", default="", help="封面主标题（默认取文档首个 H1）")
    ap.add_argument("--subtitle", default="", help="封面副标题")
    ap.add_argument("--doc-code", default="", help="文档代号（默认由文件名推导，如 MODBUS-PROTOCOL）")
    ap.add_argument("--lang", choices=["auto", "zh", "en"], default="auto", help="封面语言")
    ap.add_argument("--vendor", default="", help="厂商名（缺省为中性封面）")
    ap.add_argument("--logo", default="", help="厂商 logo 图片路径（png/jpg/svg/gif/webp）")
    ap.add_argument("--rev", default="REV 1.0", help="版本号")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="文档日期 YYYY-MM-DD")
    ap.add_argument("--meta", action="append", default=[], metavar="KEY=VALUE",
                    help="封面信息栏附加行，可重复")
    ap.add_argument("--colors", type=parse_colors, default=parse_colors("3A506B,5BC0BE,CDEDF6"),
                    help='配色 "暗,中,浅" 十六进制（不带 #）')
    ap.add_argument("--edge", default="", help="浏览器路径（缺省自动查找 Edge/Chrome）")
    ap.add_argument("--no-cover", dest="cover", action="store_false", help="不生成封面")
    ap.add_argument("--no-strip-meta", dest="strip_meta", action="store_false",
                    help="保留正文开头的 H1/元信息表（默认封面开启时移除）")
    ap.add_argument("--no-verify", dest="verify", action="store_false", help="跳过构建后质检")
    args = ap.parse_args()

    if args.out and len(args.inputs) > 1:
        raise SystemExit("--out 仅在单个输入文件时可用")
    if args.logo and not Path(args.logo).exists():
        raise SystemExit("logo 文件不存在: %s" % args.logo)
    for f in args.inputs:
        if not Path(f).exists():
            raise SystemExit("输入文件不存在: %s" % f)
    args.metas = [parse_meta(m) for m in args.meta]

    browser = find_browser(args.edge)
    rc = 0
    for f in args.inputs:
        try:
            build_one(args, Path(f).resolve(), browser)
        except Exception as e:  # noqa: BLE001
            print("FAILED %s: %s" % (f, e), file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
