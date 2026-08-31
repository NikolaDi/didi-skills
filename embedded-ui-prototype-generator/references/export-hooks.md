# Embedded Export Spec v2 页面标记

## 目标

这些约定不是为了限制视觉设计，而是为了让后续切图脚本能够基于语义协议稳定识别页面结构。

## 根节点

- 页面根节点使用 `data-ui-root`
- 根节点声明 `data-ui-version="2"`
- 根节点声明 `data-screen-width` 和 `data-screen-height`

示例：

```html
<div
  data-ui-root
  data-ui-version="2"
  data-screen-width="800"
  data-screen-height="480"
>
</div>
```

## 页面

- 每个页面节点使用 `data-ui-page`
- 页面必须声明 `data-page-id`
- 建议声明 `data-page-title` 和 `data-page-index`
- 当前页状态由页面协议控制，不再依赖旧的 `.page-view.active`

示例：

```html
<section
  data-ui-page
  data-page-id="oxygen"
  data-page-title="氧浓度"
  data-page-index="1"
>
</section>
```

## 图层

- 使用 `data-ui-layer` 声明图层语义
- 推荐图层值：
  - `background`
  - `content`
  - `overlay`
  - `chrome`
- 注意：跨层布局时，防止同区域元素发生视觉重叠（通过调整对齐方式或增加 padding 来避让，不强制特定的对齐方式，只要不重叠即可）。

示例：

```html
<div data-ui-layer="background"></div>
<div data-ui-layer="content"></div>
<div data-ui-layer="overlay"></div>
<div data-ui-layer="chrome"></div>
```

## 导出节点

- 所有需要导出的节点都使用 `data-export-node`
- 每个导出节点都必须声明 `data-export-id`
- 业务绑定字段使用 `data-bind`

推荐节点类型：

- `static`
- `text`
- `control`
- `image`
- `indicator`
- `container`

## text 节点

```html
<div
  data-export-node="text"
  data-export-id="oxygen-target"
  data-bind="oxygen.target"
  data-font-token="value-large"
  data-glyph-set="digits-large"
  data-format="int"
>
  21
</div>
```

要求：

- `data-export-id` 在全页面唯一
- `data-bind` 指向运行时字段
- `data-font-token` 表示页面中的字体样式 token
- `data-glyph-set` 表示导出的字库集合
- `data-format` 表示数据格式，例如 `int`、`float1`、`text`

## control 节点

```html
<button
  data-export-node="control"
  data-export-id="page-next"
  data-control-type="nav"
  data-action="next-page"
  data-states="normal,pressed,disabled"
  data-state-class-pressed="pressed"
  data-state-class-disabled="disabled"
>
  下一页
</button>
```

要求：

- `data-control-type` 描述控件类型，例如 `button`、`toggle`、`stepper`、`nav`、`tab`
- `data-action` 描述控件语义动作
- `data-states` 列出要导出的状态
- `data-state-class-*` 指向各状态的样式类名

## image 节点

```html
<div
  data-export-node="image"
  data-export-id="wifi-qrcode"
  data-bind="wifi.qrcode"
  data-image-type="qr"
></div>
```

适用于二维码、动态图标、设备图片占位区。

## indicator 节点

```html
<div
  data-export-node="indicator"
  data-export-id="wifi-signal"
  data-bind="wifi.signal"
  data-indicator-type="level"
  data-states="0,1,2,3,4"
></div>
```

适用于状态灯、信号强度、进度条、等级条等动态视觉元素。

## container 节点

```html
<section
  data-export-node="container"
  data-export-id="oxygen-panel"
  data-container-type="metric"
></section>
```

用于标记业务块边界，本身不一定直接导出资源。

## 分页导出接口

- 多页界面推荐提供：
  - `window.__EMBEDDED_EXPORT__.getPages()`
  - `window.__EMBEDDED_EXPORT__.activatePage(pageId)`
- 导航控件若需要切片，同样使用 `control` 节点标记

## 元素组织建议

- 同类型节点尽量保持一致 DOM 结构
- 数值、单位、标签、图标尽量拆成清晰的独立节点
- 不要把动态数字和单位写死在同一个不可分离节点里，除非后续确实不需要拆
- 页面协议优先于纯视觉类名
