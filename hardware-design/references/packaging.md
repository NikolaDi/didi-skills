# 打包 hardware-design

在维护仓库的 skill 根目录运行以下命令，产物写入本目录的 `dist/`。从受管理的安装副本调用打包脚本时，用 `--output` 显式指定副本之外的交付路径。

```sh
python scripts/package_skill.py --output dist/hardware-design.skill
```

[打包脚本](../scripts/package_skill.py)生成 ZIP，校验后输出路径、文件数、大小和 SHA-256。解包后的 `hardware-design/` 包含[统一入口](../SKILL.md)、通用规则、SVG 图例、嘉立创流程、脚本、依赖清单及[来源说明](../THIRD_PARTY_NOTICES.md)。使用自带桥接服务时按[连接说明](lceda-pro/connection.md)安装锁定的运行依赖。
