# circuit-notebook JSON 数据约定

建议 schema_version: `circuit-notebook/1.0`

```json
{
  "title": "方案标题",
  "components": [
    {
      "ref": "R1",
      "original_ref": "R124",
      "type": "resistor",
      "value": "0.5mΩ",
      "visible_in_main": true,
      "pins": {
        "1": {"role":"A","net":"BUS_IN"},
        "2": {"role":"B","net":"BUS_LOAD"}
      }
    }
  ],
  "nets": [
    {"id":"BUS_IN","role":"input","members":["R1.1"]}
  ],
  "interfaces": [],
  "assumptions": [],
  "unknowns": [],
  "layout_groups": [],
  "learning_modules": []
}
```

要求：
- JSON 是唯一电气连接真源。
- SVG 元件/网络使用 data-ref/data-net 绑定。
- HTML 和知识地图引用同一份 JSON。
- 原始标号映射不得丢失。
