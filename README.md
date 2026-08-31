# didi-skills

个人 Agent Skills 仓库。

Skill（技能）是一个包含指令、参考资料、脚本和资源的文件夹，AI Agent（如 ZCode / Claude Code）在遇到匹配任务时动态加载，从而在专项任务上表现更好。本仓库用于沉淀和版本化管理我自己编写、日常会复用的 skills。

## 当前包含的 Skills

### [wechat-miniprogram-automation](wechat-miniprogram-automation/)

微信小程序自动化联调。基于微信开发者工具自带的 `wechatide` CLI（v0.3.x 起内置），对模拟器做真实操作：刷新重编译、截图验证 UI、页面导航、运行时执行 JS、读写页面 data、调用页面方法、mock/恢复 wx API、grep console/network 日志。

- 不依赖 `miniprogram-automator` 等第三方 SDK，不需要测试号，不改动项目代码
- 附带实测踩坑记录（tab 切换、数组参数、浮层点击、mock 恢复等 8 条）
- 平台：Windows（Git Bash）

### [embedded-ui-prototype-generator](embedded-ui-prototype-generator/)

嵌入式 UI 原型生成，符合 Embedded Export Spec v2。用于新建或修改单页/多页导航界面，生成带 `data-ui-root`、`data-ui-page`、`data-ui-layer`、`data-export-node` 语义标记的 HTML 原型页面，为后续稳定切片导出做准备。

- 先问询确认页面尺寸、页数、导航协议、动态节点类型、绑定字段，再生成
- 只生成 v2 结构，不保留旧格式写法
- 配套 `references/` 工作流文档与三套 HTML 模板（单页/多页/通用）

### [embedded-ui-slice-exporter](embedded-ui-slice-exporter/)

嵌入式 UI 切片导出，Embedded Export Spec v2 的另一半。把符合规范的原型页面切成嵌入式可直接使用的资源：按页面协议导出静态底图、控件状态图、字库、动态图像区域，并输出 manifest 坐标清单。

- 与 [embedded-ui-prototype-generator](embedded-ui-prototype-generator/) 配套使用：前者负责"生成符合规范的页面"，本 skill 负责"导出"
- 提供 `scripts/slice_ui_assets.py` 切图脚本，通过 `--html` 指向目标页面
- 只处理 v2 页面结构，不负责界面风格设计

## 仓库结构

```
didi-skills/
├── <skill-name>/              # 每个 skill 一个目录，目录名与 skill name 一致
│   ├── SKILL.md               # 必须：YAML frontmatter（name + description）+ 正文指令
│   ├── references/            # 可选：按需阅读的详细文档
│   ├── scripts/               # 可选：可执行脚本
│   └── assets/                # 可选：模板等静态资源
├── README.md
├── .gitignore
└── .gitattributes
```

## 安装使用

把需要的 skill 目录复制（或软链）到 Agent 的 skills 目录即可，例如：

```bash
# ZCode 用户级 skills
cp -r embedded-ui-prototype-generator ~/.zcode/skills/

# Claude Code 用户级 skills
cp -r wechat-miniprogram-automation ~/.claude/skills/
```

两个 embedded-ui skill 有依赖关系，建议一起安装。

## 新增 Skill

1. 根目录新建 `<skill-name>/`，目录名与 frontmatter 里的 `name` 保持一致。
2. 编写 `SKILL.md`：frontmatter 必须包含 `name` 和 `description`；`description` 要写清"做什么 + 什么时候该触发"，这直接决定 Agent 能否正确选中这个 skill。
3. 详细内容放 `references/`（SKILL.md 保持精炼，Agent 按需加载），脚本放 `scripts/`，模板放 `assets/`。
4. 新 skill 完成后更新本 README 的「当前包含的 Skills」一节，并提交。

## 说明

- 本仓库为个人使用沉淀，skills 中的路径、工具版本（如微信开发者工具 v0.3.x CLI）以本人实际环境为准，使用前请自行验证。
