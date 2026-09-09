# didi-skills

个人 Agent Skills 仓库，可同时被多种 AI Agent 工具使用。

Skill（技能）是一个包含指令、参考资料、脚本和资源的文件夹（核心是 `SKILL.md`），AI Agent 在遇到匹配任务时动态加载，从而在专项任务上表现更好。本仓库用于沉淀和版本化管理我自己编写、日常会复用的 skills。

## 当前包含的 Skills

| Skill | 一句话说明 | 平台 / 环境 |
| --- | --- | --- |
| [wechat-miniprogram-automation](wechat-miniprogram-automation/) | 用微信开发者工具自带 `wechatide` CLI 驱动小程序模拟器，做刷新编译、截图验证、运行时执行 JS、mock wx API 与日志抓取。 | Windows（Git Bash），微信开发者工具 v0.3.x CLI |
| [embedded-ui-prototype-generator](embedded-ui-prototype-generator/) | 按 Embedded Export Spec v2 生成带 `data-ui-root` / `data-ui-page` / `data-ui-layer` / `data-export-node` 语义标记的嵌入式 HTML 原型页面。 | 通用 |
| [embedded-ui-slice-exporter](embedded-ui-slice-exporter/) | 把符合 v2 规范的原型页面切成底图、控件状态图、字库与动态图像区域，并输出 manifest 坐标清单。 | 通用（Python 脚本 `slice_ui_assets.py`） |
| [esp-idf-dev](esp-idf-dev/) | 在 Windows Git Bash 下驱动 `idf.py` 完成 ESP32/ESP-IDF 固件的构建、烧录、串口监控与主机测试、OTA 打包。 | Windows（Git Bash），IDF v5.5 |
| [iot-power](iot-power/) | 通过 Computer Use 操作合宙 IoT Power，连接 CC 系列设备、读取和连续监测电压/电流/功率/电量，或运行指定时长后保存监控数据。 | Windows，合宙 IoT Power 2.2.0.4 |
| [md-industrial-pdf](md-industrial-pdf/) | 把 Markdown 技术文档渲染成带设计感封面与页脚工程图签的工业风 A4 PDF，并自动质检。 | Windows + Edge/Chrome，Python（`markdown`、`pymupdf`） |

各 skill 的详细指令、脚本与踩坑记录见对应目录下的 `SKILL.md` 与 `references/`。

> `embedded-ui-prototype-generator` 与 `embedded-ui-slice-exporter` 是配套关系：前者负责「生成符合规范的页面」，后者负责「导出」，建议一起安装。

## 仓库结构

```
didi-skills/
├── <skill-name>/              # 每个 skill 一个目录，直接放在仓库根目录，目录名与 skill name 一致
│   ├── SKILL.md               # 必须：YAML frontmatter（name + description）+ 正文指令
│   ├── references/            # 可选：按需阅读的详细文档
│   ├── scripts/               # 可选：可执行脚本
│   └── assets/                # 可选：模板等静态资源
├── README.md
├── AGENTS.md             # 给 AI Agent 看的仓库约定（新增/修改 skill 时遵守）
├── .gitignore
└── .gitattributes
```

## 安装使用

各 Agent 工具读取 skills 的目录不同。推荐把本仓库克隆到本地，再为每个工具建立软链或复制仓库根目录下的 skill 目录，一份 skills 多工具共享：

```bash
git clone <本仓库地址> ~/didi-skills
```

| Agent 工具 | 用户级 skills 目录 | 安装方式 |
| --- | --- | --- |
| 通用（.agents 约定） | `~/` | 软链或复制根目录的 `<skill-name>/` |
| ZCode | `~/.zcode/skills/` | 同上 |
| Claude Code | `~/.claude/skills/` | 同上 |
| Codex CLI | `~/.codex/skills/`（视版本） | 同上 |

Windows（管理员或开发者模式的 PowerShell）示例：

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.zcode\skills\wechat-miniprogram-automation" -Target "$HOME\didi-skills\wechat-miniprogram-automation"
```

macOS / Linux 示例：

```bash
ln -s ~/didi-skills/wechat-miniprogram-automation ~/.zcode/skills/wechat-miniprogram-automation
```

项目级使用时，把 skill 复制或软链到项目的 skills 目录（如 `.agents/skills/`、`.claude/skills/`）即可随项目分发。

## 新增 Skill

1. 在仓库根目录新建 `<skill-name>/`，目录名与 frontmatter 里的 `name` 保持一致。
2. 编写 `SKILL.md`：frontmatter 必须包含 `name` 和 `description`；`description` 要写清"做什么 + 什么时候该触发"，这直接决定 Agent 能否正确选中这个 skill。
3. 详细内容放 `references/`（SKILL.md 保持精炼，Agent 按需加载），脚本放 `scripts/`，模板放 `assets/`。
4. 新 skill 完成后更新本 README 的「当前包含的 Skills」表格，并提交。

更完整的编写约定见 [AGENTS.md](AGENTS.md)。

## 说明

- 本仓库为个人使用沉淀，skills 中的路径、工具版本（如微信开发者工具 v0.3.x CLI）以本人实际环境为准，使用前请自行验证。
- 不同 Agent 工具对 skill frontmatter 字段的支持略有差异（如 `allowed-tools`、`model` 等扩展字段），本仓库的 skills 只依赖各工具通用的 `name` + `description`。
