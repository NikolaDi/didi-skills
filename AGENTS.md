# AGENTS.md

给在本仓库工作的 AI Agent 看的约定文件。修改仓库前先读完。

## 仓库是什么

个人 Agent Skills 仓库，供多种 AI Agent 工具（CodeBuddy / Claude Code / Codex CLI 等）共享。

本仓库**不是软件项目**：没有构建、依赖安装、测试套件或 CI。内容是 Markdown 指令文档 + 少量 Python/BAT 脚本 + HTML 模板。因此不要新建 `package.json`、`requirements.txt`、`Makefile` 或测试框架，除非被明确要求。

## 目录约定

```
<skill-name>/        # 一个 skill 一个目录，直接放在仓库根目录
├── SKILL.md         # 必须：YAML frontmatter（name + description）+ 正文指令
├── references/      # 可选：按需加载的详细文档、踩坑记录
├── scripts/         # 可选：可执行脚本
└── assets/          # 可选：模板等静态资源
```

- 目录名必须与 `SKILL.md` frontmatter 里的 `name` **完全一致**。
- skill 目录只允许出现在仓库根目录，不要嵌套子目录分层。

## 新增或修改 Skill 的规则

1. **frontmatter 只用 `name` + `description`**。不要写 `allowed-tools`、`model` 等某工具特有的扩展字段——本仓库的 skill 要跨工具可用，只依赖通用字段。
2. **`description` 必须回答三件事**：做什么、什么时候该触发、什么情况不该用它。这是 Agent 能否正确选中 skill 的唯一依据，写得含糊等于这个 skill 不会被用到。参考 `md-industrial-pdf` 的写法（含"不用于……"的排除项）。
3. **`SKILL.md` 保持精炼**，只放决策路径和必要参数。长篇细节、踩坑记录、API 清单放进 `references/`，由 Agent 按需加载。
4. **可执行逻辑放 `scripts/`，模板放 `assets/`**，不要把大段代码正文塞进 `SKILL.md`。
5. **修改已有 skill 的对外行为后**，同步更新它自己的 `SKILL.md` 正文和相关 `references/`，保持三者一致。

## 写作规范

- 正文、注释、文档一律**简体中文**；技术专有名词、命令、路径、字段名保持原文。
- 文档中的引号用中文直角引号「」或全角引号，不要混用直引号。
- 换行符：`.md`、`.py`、`.html` 均为 **LF**（已由 `.gitattributes` 强制）。
- 脚本约定：Python 用 argparse 暴露参数，不依赖全局状态；路径尽量通过参数传入，避免硬编码绝对路径。确需固化个人环境的（如 `esp-idf-dev` 的 IDF 路径），必须在文档中显式写明这是本机环境假设。

## 提交前检查清单

- [ ] 新 skill 或改动了 skill 的用途 → 已更新 `README.md` 的「当前包含的 Skills」表格（一行一句话，不要抄 `SKILL.md` 全文）。
- [ ] 目录名 == frontmatter `name`。
- [ ] frontmatter 只有 `name` + `description`，`description` 含触发与排除条件。
- [ ] 没有把导出产物（`dist/`、`output/`、`*.log`）加入版本控制。
- [ ] 没有引入只适用于单一 Agent 工具的字段或目录结构。

## 已知的 skill 依赖关系

- `embedded-ui-prototype-generator`（生成符合 Embedded Export Spec v2 的页面）→ `embedded-ui-slice-exporter`（切片导出）。改任一方时检查另一方是否受影响。

## 不要做的事

- 不要在仓库根目录新建与 skill 无关的文档或脚本。
- 不要为了"看起来完整"给仓库补 README/CHANGELOG/CI 配置，除非被要求。
- 不要把 `SKILL.md` 的内容复制到 README —— 会造成双份维护与内容漂移。
- skills 中的路径、工具版本以作者本机实际环境为准，不要擅自"通用化"重写，除非被要求。
