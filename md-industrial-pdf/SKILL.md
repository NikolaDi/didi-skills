---
name: md-industrial-pdf
description: 把 Markdown 技术文档渲染成工业风格 PDF（带设计感封面、可选厂商名/logo、页脚工程图签、灰蓝色系），通过无头 Edge/Chrome 打印并自动质检。适用于需要生成严谨克制风格的技术规格书、协议文档、接口文档 PDF 的场景。不用于已有 PDF 的编辑、合并、拆分、提取（那些用 pdf 技能），也不适合需要复杂交互或大幅自绘版式的场景。
---

# Markdown → 工业风 PDF

把 Markdown 技术文档渲染成带封面和页脚图签的工业风 PDF：单色灰蓝版面、细黑分隔线、黑底白字表头、等宽代码块、封面含主/副标题与文档信息栏、正文每页盖 `文档代号 | 版本 | 日期 + PAGE n / N` 图签。

## 环境要求

- Windows + Microsoft Edge 或 Chrome（缺省自动查找，可用 `--edge` 指定路径）
- Python 依赖：`markdown`、`pymupdf`（缺失时先 `pip install markdown pymupdf`）
- 中文渲染依赖系统字体 Microsoft YaHei / SimSun（Windows 自带）
- 纸张固定 A4 纵向

## 工作流

1. 确认依赖可用（见上）。
2. 在输入 Markdown 所在目录或任意位置执行：

   ```
   python <skill目录>/scripts/build_pdf.py INPUT.md [INPUT2.md ...] [选项]
   ```

3. 脚本默认：输出同名 `.pdf`；封面主标题自动取文档首个 H1；封面语言按标题是否含中文自动判断；厂商标识缺省中性（无厂商信息）。
4. 脚本构建后自动质检（页脚不压线、页码齐全、无乱码、文本不越界），失败会逐条打印问题，按提示修复后重跑。
5. 需要视觉验收时，用 pymupdf 把 PDF 渲染成 PNG 逐页目检（封面配色、表格跨页表头、图片完整性）。
6. 交付 PDF 路径。Markdown 修改后重跑同一命令即可重新生成。

## 常用选项

| 选项 | 说明 |
| --- | --- |
| `--title` / `--subtitle` | 封面主/副标题（主标题默认取首个 H1） |
| `--doc-code` | 页脚与封面的文档代号（默认由文件名推导，如 `MODBUS-PROTOCOL`） |
| `--vendor "名称"` | 封面厂商名；缺省为中性几何标识 |
| `--logo logo.png` | 封面厂商 logo（png/jpg/svg/gif/webp，base64 内嵌） |
| `--rev` / `--date` | 版本号 / 文档日期（日期默认今天） |
| `--meta "键=值"` | 封面信息栏附加行，可重复，如 `--meta "协议 PROTOCOL=Modbus RTU"` |
| `--lang zh\|en` | 封面语言（默认按标题自动判断） |
| `--colors "暗,中,浅"` | 覆盖配色，六位十六进制，默认 `2C3440,8A95A5,E5E7EB` |
| `--no-cover` | 不生成封面（页脚从第 1 页起编号） |
| `--no-strip-meta` | 保留正文开头的 H1 / 元信息表（默认有封面时移除以免与封面重复） |
| `--no-verify` | 跳过构建后质检 |

## 定制

- 配色三类角色的用法：暗色 = 标题/表头/粗线/正文文字，中色 = 细线/次要文字，浅色 = 代码块/引用块/信息栏底色。换配色只需 `--colors` 保持这个角色划分。
- 版式细节（字号、边距、封面色带比例、信息栏行高）：改 `scripts/build_pdf.py` 顶部的 `CSS_TEMPLATE` 与 `COVER_TMPL`。
- 页脚图签格式在 `stamp_footer()`；注意文字基线需在分隔线下方约 9pt，否则线条会穿过文字（上升高度约 6.8pt，这是内置质检的检查项之一）。

## 已知边界

- 表格跨页时由浏览器自动重复表头（thead），行内不拆分；单行内容过长仍可能溢出，需精简单元格文本。
- letter-spacing 会使 PDF 文本提取时字母被拆开（如 `T E C H`），属正常现象，不影响渲染和检索工具的视觉结果。
- 依赖 Windows 系统字体与 Edge/Chrome 打印引擎；Linux 下需自行改字体栈并指定 chromium 路径。
