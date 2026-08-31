# Embedded Export Spec v2 导出契约

## 根节点

- 页面根节点使用 `data-ui-root`
- 根节点必须声明：
  - `data-ui-version="2"`
  - `data-screen-width`
  - `data-screen-height`
- 根节点宽高就是最终导出坐标的参考区域

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

## 页面协议

- 每个页面节点使用 `data-ui-page`
- 页面必须声明：
  - `data-page-id`
  - `data-page-title`
  - `data-page-index`
- 导出工具按页面协议逐页导出，不依赖旧的样式类名约定
- 多页界面推荐提供：
  - `window.__EMBEDDED_EXPORT__.getPages()`
  - `window.__EMBEDDED_EXPORT__.activatePage(pageId)`

```html
<section
  data-ui-page
  data-page-id="oxygen"
  data-page-title="氧浓度"
  data-page-index="1"
>
</section>
```

## 图层协议

- 页面内图层使用 `data-ui-layer`
- 推荐图层值：
  - `background`
  - `content`
  - `overlay`
  - `chrome`

```html
<div data-ui-layer="background"></div>
<div data-ui-layer="content"></div>
<div data-ui-layer="overlay"></div>
<div data-ui-layer="chrome"></div>
```

## 导出节点总则

- 所有需要导出的节点都使用 `data-export-node`
- 每个导出节点都必须声明 `data-export-id`
- 节点需要绑定业务字段时，使用 `data-bind`

支持的节点类型：

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

- `data-export-id` 全页面唯一
- `data-bind` 指向运行时字段
- `data-font-token` 表示页面样式 token
- `data-glyph-set` 表示导出的字库集合
- `data-format` 表示显示格式

## control 节点

```html
<button
  data-export-node="control"
  data-export-id="page-next"
  data-control-type="nav"
  data-action="next-page"
  data-target-page="wifi"
  data-states="normal,pressed,disabled"
  data-state-class-pressed="pressed"
  data-state-class-disabled="disabled"
>
  下一页
</button>
```

要求：

- `data-control-type` 描述控件类型
- `data-action` 描述控件语义动作
- `data-states` 列出导出状态
- `data-state-class-*` 指向各状态类名

## image 节点

```html
<div
  data-export-node="image"
  data-export-id="wifi-qrcode"
  data-bind="wifi.qrcode"
  data-image-type="qr"
></div>
```

适用于二维码、动态图标、图片占位区。

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

适用于状态灯、进度条、等级条、信号强度等动态视觉元素。

## static 节点

```html
<div
  data-export-node="static"
  data-export-id="wifi-divider"
></div>
```

用于需要单独导出的静态资源块。

## container 节点

```html
<section
  data-export-node="container"
  data-export-id="oxygen-panel"
  data-container-type="metric"
></section>
```

用于标记业务块边界，本身不一定直接导出资源。

## 字库限制

- 字库集合由 `data-glyph-set` 标识
- 具体导出字符集由导出工具和页面约定共同决定
- 字库与页面样式 token 解耦，不直接依赖旧的类名映射方式

## 输出内容

- `base/page_xx/static_base.png`
- `preview/page_xx/full_composite.png`
- `controls/page_xx/<control-id>/<state>.png`
- `glyphs/<glyph-set>/*.png`
- 其他节点类型需要的资源目录
- `manifest.json`

## Manifest 内容

`manifest.json` 中包含：

- 规范版本
- 屏幕区域尺寸
- 页面列表
- 每页底图和预览图路径
- 每页导出节点列表
- 每个节点的类型、绑定字段、坐标和资源路径
- 字库集合元信息

嵌入式侧以 `manifest.json` 作为资源映射基准。
