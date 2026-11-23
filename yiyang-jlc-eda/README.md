# yiyang-jlc-eda

操作入口见 [SKILL.md](SKILL.md)。开展设计任务时，将本 skill 与 [hardware-design](../hardware-design/SKILL.md) 放在同一 skills 父目录下。连接需已打开的嘉立创 EDA 专业版和已加载的 API 网关扩展。Python 客户端仅依赖标准库；启动本包的本地桥接服务需要 Node.js 18 或更高版本及其锁定依赖。详见[连接说明](references/connection.md)。

## 打包

在本 skill 根目录运行以下命令。默认输出也位于本目录的 `dist/`。

```sh
python scripts/package_skill.py --output dist/yiyang-jlc-eda.skill
```

脚本按源文件清单写入 ZIP，检验归档并输出路径、文件数、大小和 SHA-256。解包得到顶层目录 `yiyang-jlc-eda/`。包内只分发操作 skill；设计规则从同级安装的 `hardware-design` 读取。桥接实现与依赖的来源见[第三方说明](THIRD_PARTY_NOTICES.md)。
