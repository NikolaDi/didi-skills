# didi-skills

个人 Agent skills 仓库。每个子目录是一个独立 skill，包含 `SKILL.md` 及配套的 `references/`、`scripts/`、`assets/` 等资源，可直接软链或复制到 Agent 的 skills 目录（如 `~/.zcode/skills/`、`~/.claude/skills/`）使用。

## 已有 Skills

| Skill | 说明 |
| --- | --- |
| [wechat-miniprogram-automation](wechat-miniprogram-automation/) | 用微信开发者工具内置 wechatide CLI 对小程序做自动化联调：刷新模拟器、截图、执行 JS、mock wx API、查日志，无需第三方 SDK。 |
| [embedded-ui-prototype-generator](embedded-ui-prototype-generator/) | 生成符合 Embedded Export Spec v2 的嵌入式 HTML 原型页面（`data-ui-root/page/layer/export-node` 语义标记），为后续切片导出做准备。 |
| [embedded-ui-slice-exporter](embedded-ui-slice-exporter/) | 把符合 Spec v2 的原型页面切成嵌入式资源：静态底图、控件状态图、字库、动态图像区域和 manifest 坐标清单。 |

## 新增 Skill 约定

1. 在仓库根目录新建 `skill-name/` 目录，目录名与 skill 的 `name` 字段一致。
2. 必须包含 `SKILL.md`，头部 YAML frontmatter 至少有 `name` 和 `description`。
3. 参考资料放 `references/`，可执行脚本放 `scripts/`，模板放 `assets/`。
4. 新 skill 完成后更新本 README 的表格。

## 安装到本地

```bash
# 例如同步到 ZCode 用户级 skills 目录
cp -r <skill-name> ~/.zcode/skills/<skill-name>
```
