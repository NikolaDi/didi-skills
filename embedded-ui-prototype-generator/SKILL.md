---
name: embedded-ui-prototype-generator
description: 用于生成符合 Embedded Export Spec v2 的嵌入式 HTML 原型页面。适用于需要新建或修改单页或多页导航界面，并要求后续稳定切片导出时。先确认页面尺寸、页数、导航协议、动态节点类型和绑定字段，再生成使用 data-ui-root、data-ui-page、data-ui-layer、data-export-node 语义标记的页面结构。
---

# 嵌入式原型生成 v2

用于创建符合新导出规范的嵌入式前端原型页面。只生成 v2 结构，不保留旧格式写法。

## 工作流

1. 如果用户没有明确提供页面尺寸，先询问页面宽高。
2. 如果用户没有明确提供页数、导航方式、动态节点类型或必要功能，继续询问最少必要信息。
3. 阅读 `references/prototype-workflow.md`，按问询清单补全信息。
4. 阅读 `references/export-hooks.md`，确保页面结构兼容后续切片导出。
5. 新页面优先从 `assets/prototype-template-single.html` 或 `assets/prototype-template-multipage.html` 开始改；`assets/prototype-template.html` 仅作为模板入口页。
6. 若是多页界面，优先生成稳定分页骨架和页面协议，不要依赖滚动容纳全部内容。
7. 页面视觉风格、字体大小、颜色、阴影、图标表现等，除非用户要求，否则不要额外施加限制。

## 先问什么

- 页面宽度和高度是多少。
- 是单页原型还是多页原型。
- 多页时通过什么导航切换，以及是否需要导出导航控件。
- 页面要展示哪些模块或数据。
- 哪些内容属于动态文本、控制控件、动态图像、状态指示器。
- 每个动态节点绑定什么字段，例如 `oxygen.target`、`wifi.qrcode`。
- 后续是否需要做切片导出。

如果这些信息里已有一部分很明确，只补问缺失项，不要机械重复提问。

## 结构约束

- 页面根节点使用 `data-ui-root`，并声明 `data-ui-version="2"`、`data-screen-width`、`data-screen-height`。
- 每一页使用 `data-ui-page`，并声明 `data-page-id`、`data-page-title`、`data-page-index`。
- 页面内按语义拆层，使用 `data-ui-layer="background|content|overlay|chrome"`。注意跨层布局时，防止同区域元素发生视觉重叠（通过调整对齐方式或增加 padding 来避让）。
- 所有需要导出的节点都使用 `data-export-node` 显式声明类型，不再使用旧的 `data-export-role`。
- 动态节点必须声明稳定的 `data-export-id`；需要绑定业务字段时，声明 `data-bind`。
- 控件节点必须声明 `data-control-type`、`data-action` 和可导出的状态集合。
- 多页界面推荐提供 `window.__EMBEDDED_EXPORT__.getPages()` 和 `window.__EMBEDDED_EXPORT__.activatePage(pageId)`。
- 不要依赖滚动区域来放额外内容；放不下就拆页。
- 同一类型节点尽量复用统一结构，避免后续导出规则分叉。

## 不额外约束的内容

- 不强制界面风格。
- 不强制深色或浅色主题。
- 不强制字体大小和字重。
- 不强制布局方式，只要结构清晰并满足用户需求即可。

## 内置资源

- `references/prototype-workflow.md`：问询顺序和页面生成流程。
- `references/export-hooks.md`：Embedded Export Spec v2 的 DOM 标记约定。
- `assets/prototype-template.html`：模板入口页，用于选择单页或多页模板。
- `assets/prototype-template-single.html`：单页 v2 原型模板。
- `assets/prototype-template-multipage.html`：多页导航 v2 原型模板。
