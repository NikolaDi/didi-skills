---
name: embedded-ui-slice-exporter
description: 用于把符合 Embedded Export Spec v2 的 HTML 原型页面切成适合嵌入式使用的资源。适用于需要按页面协议、图层协议和语义化导出节点导出静态底图、控件状态图、字库、动态图像区域和 manifest 坐标清单时。该技能只关注 v2 导出规则、页面标记和切图脚本，不负责界面风格设计。
---

# 嵌入式切片导出 v2

用于将符合新规范的 HTML 原型页面导出为嵌入式可直接使用的切图片段和坐标清单。只处理 v2 页面结构，不兼容旧格式约定。

## 工作流

1. 先阅读 `references/export-contract.md`，确认页面已经满足导出约定。
2. 检查页面是否存在 `data-ui-root`、`data-ui-page`、`data-ui-layer` 和 `data-export-node`。
3. 在任意目录执行 `scripts/slice_ui_assets.py`，并通过 `--html` 指向目标页面。
4. 按页面协议逐页导出底图、节点资源和 manifest。
5. 检查 `manifest.json`、分页目录、节点资源和字库目录是否正确。

## 这个技能只关心什么

- 页面根节点尺寸和定位
- 页面协议和分页激活方式
- 图层协议
- `text`、`control`、`image`、`indicator`、`static`、`container` 节点定义
- 字库输出和 manifest 坐标映射

## 这个技能不关心什么

- 页面整体风格
- 主题明暗
- 字体大小是否美观
- 配色是否高级

只要页面结构满足导出契约，就可以执行切图。

## 内置资源

- `references/export-contract.md`：v2 页面协议、节点类型、输出目录结构和 manifest 说明。
- `scripts/slice_ui_assets.py`：切图导出脚本。

## 执行说明

- 不指定 `--output-dir` 时，输出到当前运行目录下的 `slices_{html文件名}`：
  `python slice_ui_assets.py --html e:/project/sleep_monitor/sleep_monitor/ui/index.html`
- 指定 `--output-dir` 时，输出到该目录下的 `slices_{html文件名}`：
  `python slice_ui_assets.py --html e:/project/sleep_monitor/sleep_monitor/ui/index.html --output-dir e:/project/sleep_monitor/sleep_monitor/ui/exports`
- 若缺少浏览器运行环境，可执行：
  `python -m playwright install chromium`
