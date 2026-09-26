---
name: gitee-release-platform
description: 把 Gitee 公开仓库当作 App（APK）发布平台：Release tag/附件/body 三方契约、后端检查接口 /api/app/release/ 自动拉取透出、App 端按版本串一致性提示升级，附自包含上传脚本。当用户要求发布 App 新版本到 Gitee、搭建或排查应用内自升级（检查更新接口返回异常、版本号比较逻辑）、或把这套流程复用到新项目时使用。不用于 Gitee 代码仓库本身的代码发版/PR 流程，不用于服务器整体部署（systemd/Django 全量上线），不涉及非 Gitee 分发渠道（OSS/应用商店）的接入实现。
---

# Gitee Release 作为 App 发布平台

把 Gitee 公开仓库的 Release 当免运维的静态分发渠道：App 构建产物传上去，后端一个匿名接口做代理与缓存，客户端按版本串判断升级。发版零手工数字、服务器零配置（配一次仓库名单后不再动）。

## 架构与契约

```
git commit → 构建（版本串/versionCode 均由 git 派生）
    → scripts/upload_release.sh 上传 Gitee 公开仓库的 Release
        → 后端 GET /api/app/release/ 拉取+缓存+透出（匿名）
            → App 本地版本串 ≠ 服务端 version_name → 提示升级
```

三方契约（**只有**这些，极简原则）：

| 载体 | 含义 |
| --- | --- |
| Release 的 **tag** | 完整版本串，形如 `v1.0.7-555e02-260926`（下发时剥 `v` 前缀） |
| Release 的 **.apk 附件** | 安装包，命名 `<前缀>-<版本串>.apk`（与 App 端下载落盘名一致） |
| Release 的 **body** | 更新说明（notes），原样透传，无任何格式约定 |

版本串口径（git 派生，构建期计算）：

- 格式 `<tag剥v>.<count>-<hash6>-<YYMMDD>[-x]`：count = 最近 tag 起提交数（无 tag 回退全量数）；工作树不干净（含未跟踪文件）追加 `-x`
- Android `versionCode` = 全量提交数（平台要求的整数，仅 PackageManager 用，随提交单调递增）
- **发版前必须 commit**，否则版本串带 `-x` 或落 `none` 占位

## 一次性准备

1. Gitee 建公开仓库并**用 README 初始化**（空仓库建 Release 会 400，见 references/gitee-api-pitfalls.md 坑 1）
2. 个人访问令牌（勾 projects 权限），只在本地 `export GITEE_TOKEN=<pat>` 用，**不进代码、不上服务器**
3. 后端服务器配置发布仓库名（如 env 加 `APP_RELEASE_GITEE_REPO=<owner>/<repo>`）并重启服务，一次配置永久生效

## 发版流程

改了后端才需要先做服务端部署，App 发版本身与服务器无关：

```bash
# 1) 提交后构建（版本串/versionCode 自动派生，无需 bump 任何数字）
cd <项目>/android && ./gradlew assembleDebug
# 2) 上传（本地运行，不碰服务器；版本串从产物 output-metadata.json 读，保持一致）
GITEE_TOKEN=<pat> RELEASE_REPO='<owner>/<repo>' \
bash upload_release.sh android/app/build/outputs/apk/debug/app-debug.apk <版本串> "更新说明"
```

脚本自动完成：建 Release（拒绝重复 tag，防误覆盖）→ 传附件 → 匿名直链冒烟（期望 200）→ 可选回调服务器接口确认透出。参数与环境变量见 `scripts/upload_release.sh` 头注释。

## 接口定义

`GET /api/app/release/`（匿名）：

- `200` → `{"version_name": "...", "apk_url": "...", "notes": "..."}`
- `204` → 未配置发布仓库 / Gitee 无有效 Release / Gitee 挂且缓存为空（三种情况客户端一律当「无更新」）
- 服务端拉取后内存缓存 10 分钟，`?fresh=1` 绕缓存
- 有效性校验：有 `.apk` 附件 + 有 tag，否则视为无效 Release 不透出
- 参考实现：`references/porting.md`（Python 解析器约 50 行，仅依赖 requests；换分发渠道只换这个数据源）

客户端判断（纯函数，可单测）：

- 有更新 = `remoteVersion.isNotEmpty() && remoteVersion != localVersion`——**只比一致性，不比大小**；回滚重装、脏树 `-x` 构建天然触发，符合预期
- 无强更机制（历史字段 version_code/min_version_code 已废弃；如需强更，端上加布尔 force 标记，端先支持再改服务端）
- 「以后再说」按版本串去重；下载走 `.part` 临时文件防半包，成功才改名

## 排查

```bash
curl 'http://<host>/api/app/release/?fresh=1'                                  # 绕缓存看实时透出
curl -s https://gitee.com/api/v5/repos/<owner>/<repo>/releases/latest | head -c 300   # 直查 Gitee
```

`204` 排查顺序：env 没配仓库 → `releases/latest` 拉取失败（Gitee 挂/限频）→ latest 无 `.apk` 附件或无 tag。

Gitee API 的 9 条实测坑（空仓库 400、`target_commitish` 必填、`null` 响应、`file` 字段名等）逐条展开在 `references/gitee-api-pitfalls.md`——改脚本或换 API 端点前先读。

## 换项目复用

清单与参考实现（服务端解析器 / gradle 版本派生 / 客户端判断）在 `references/porting.md`。要点：发布仓库初始化 README、token、服务器 env 三件套；代码三块直接照抄。
