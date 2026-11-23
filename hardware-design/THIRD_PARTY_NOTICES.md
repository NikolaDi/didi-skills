# 第三方来源

嘉立创桌面操作流程、Python 桥接客户端及打包脚本沿用 [Yiyang 的 yiyang-jlc-eda](https://github.com/AL1325651958/yiyang-jlc-eda)。本次迁移基线是 didi-skills 提交 `9234f336c755075da37aa3829da51592692b1a78` 中的精简版，调整了操作入口、依赖目录及整包收录范围。

[桥接服务](scripts/lceda-pro/bridge-server.mjs)沿用本地集成的 `easyeda-api` Skill 1.1.36 实现，保留原始代码头及仅监听 `127.0.0.1` 的调整。

来源：<https://github.com/easyeda/easyeda-api-skill>。来源 Skill 的元数据声明作者为 JLCEDA、许可证为 MIT；所用本地安装目录未附单独 LICENSE 文件，此处保留该声明及来源，不据此对本仓库其他内容授予许可证。

[API 速查](references/lceda-pro/api-usage.md)中的 TypeScript 签名摘自同一安装版本的类文档，仅选取本 skill 操作涉及的接口；正式语义及版本更新以官方文档为准。

桥接运行依赖 `ws`，由 npm 安装，其许可证和版权声明随 npm 包提供。
