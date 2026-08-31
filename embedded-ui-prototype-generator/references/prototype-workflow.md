# 原型生成流程 v2

## 目标

在不额外约束视觉风格的前提下，生成一个符合 Embedded Export Spec v2、后续可以稳定切片导出的前端原型页面。

## 先补齐的信息

优先确认以下内容：

- 页面宽度和高度
- 页数，是单页还是多页
- 多页时的导航方式，是左右箭头、页签还是程序切页
- 是否需要导出导航控件
- 页面核心功能
- 哪些内容是静态展示
- 哪些内容属于 `text`、`control`、`image`、`indicator`
- 每个动态节点绑定什么字段
- 哪些控件需要哪些状态，例如 `normal`、`pressed`、`active`、`disabled`

如果用户没有明确页面大小，必须先问。页面大小会直接影响根容器尺寸、导出坐标和切图片段。

## 生成原则

- 原型首先满足用户业务表达。
- 只对后续切图会用到的结构做约束。
- 不主动限制风格、配色、字体、明暗主题、阴影和图标语言。
- 语义声明优先于视觉类名。

## 与切图有关的结构要求

1. 页面根节点使用 `data-ui-root`，并声明版本和尺寸。
2. 每一页使用 `data-ui-page`，并声明 `data-page-id`、`data-page-title`、`data-page-index`。
3. 页面内用 `data-ui-layer` 明确区分 `background`、`content`、`overlay`、`chrome`。
   - **防重叠规范**：跨层（Layer）布局时，必须确保处于相同物理区域的元素不会发生视觉重叠。例如：如果在 `chrome` 层左侧放置了返回按钮，则在 `background` 层的标题应调整对齐方式（如居中或右对齐，或增加相应的 padding），只要确保其不与交互层的控件发生重叠即可。
4. 所有需要导出的节点使用 `data-export-node` 明确声明类型。
5. 动态节点使用稳定的 `data-export-id`；业务绑定字段使用 `data-bind`。
6. 多页界面推荐提供 `window.__EMBEDDED_EXPORT__.getPages()` 和 `window.__EMBEDDED_EXPORT__.activatePage(pageId)`。
7. 同类信息块尽量保持统一结构，方便批量切图和规则复用。
8. 页面不依赖滚动来展示额外内容，放不下就拆页。

## 页面完成前检查

- 根节点已声明 `data-ui-root`、`data-ui-version="2"`、尺寸属性。
- 每一页都已声明 `data-ui-page` 和唯一 `data-page-id`。
- 每个导出节点都已声明 `data-export-node` 和 `data-export-id`。
- `text`、`control`、`image`、`indicator` 节点都已补齐必要语义属性。
- 如果是多页界面，页面切换协议已经明确，不依赖样式类名约定。
- 数值区、控件区、图像区、状态区没有混杂在不可拆分的复杂节点里。
