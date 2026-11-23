# 第三方来源

`scripts/bridge-server.mjs` 复用本机已安装的 `easyeda-api` Skill 1.1.36 的桥接实现，保留原始代码头。本地源文件已带有仅监听 `127.0.0.1` 的调整；本次整合按该文件复制，没有覆盖或启动另一桥接实例。

来源：<https://github.com/easyeda/easyeda-api-skill>。来源 Skill 的元数据声明作者为 JLCEDA、许可证为 MIT；所用本地安装目录未附单独 LICENSE 文件，此处保留该声明及来源，不据此对本仓库其他内容授予许可证。

`references/api-usage.md` 中的 TypeScript 签名摘自同一安装版本的类文档，仅选取本 Skill 操作涉及的接口；正式语义及版本更新以官方文档为准。

桥接运行依赖 `ws`，由 npm 安装，其许可证和版权声明随 npm 包提供。`scripts/eda_bridge.py` 与中文操作说明为本次整合新增内容。
