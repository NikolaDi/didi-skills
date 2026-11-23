# 嘉立创 EDA 连接与执行

适用范围：嘉立创 EDA 专业版桌面客户端与 API 网关。首次连接、重连、桥接报错时读本文件；编辑流程见 [operations.md](operations.md)。

## 连接

1. 先检查是否已有可用的 EDA 连接工具；有专用连接器时使用其已公开的接口。使用本包 HTTP 桥接时，在 Skill 根目录执行 `python scripts/lceda-pro/eda_bridge.py discover`。扫描本机 49620～49629，并检查 `/health` 的 `service` 为 `easyeda-bridge`，不能仅凭端口可访问判定成功。
2. 有桥接服务就复用。多个服务或多个客户端窗口时，根据当前任务的已知工程定位；仍无法确定目标才询问用户。不要默认取窗口列表第一项或沿用上次窗口 ID。`windows`、`probe` 均为只读；`probe --window-id <ID>` 可分别读取各窗口工程和文档信息。
3. 没有桥接服务时，需要 Node.js 18+。从 `hardware-design` 根目录读取随包文件，在独立的临时运行目录安装锁定依赖并启动服务。依赖和日志均写入该运行目录。

   ```powershell
   $bridgeSource = (Resolve-Path 'scripts/lceda-pro').Path
   $bridgeDir = Join-Path ([System.IO.Path]::GetTempPath()) ('hardware-design-bridge-' + [guid]::NewGuid())
   New-Item -ItemType Directory -Path $bridgeDir -ErrorAction Stop | Out-Null
   foreach ($name in 'bridge-server.mjs', 'package.json', 'package-lock.json') {
       Copy-Item -LiteralPath (Join-Path $bridgeSource $name) -Destination $bridgeDir -ErrorAction Stop
   }
   npm.cmd ci --prefix "$bridgeDir" --omit=dev
   if ($LASTEXITCODE -ne 0) { throw '桥接依赖安装失败' }
   $nodeExecutable = (Get-Command node).Source
   Start-Process -FilePath $nodeExecutable -ArgumentList @('bridge-server.mjs') -WorkingDirectory $bridgeDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $bridgeDir 'bridge.stdout.log') -RedirectStandardError (Join-Path $bridgeDir 'bridge.stderr.log')
   ```

   启动后重新运行 `discover`，确认后台服务可用。
4. EDA 客户端须已安装并加载 API 网关扩展 `run-api-gateway.eext`。扩展来源见 [API 速查的来源](api-usage.md#来源与版本)。桥接健康但窗口数为 0 时，检查客户端和扩展状态；若尚未安装则说明所缺步骤，不能声称已连接。安装、登录及界面权限操作遵循当前环境的实际授权规则。
5. 执行 `python scripts/lceda-pro/eda_bridge.py probe`，读取 `project`、`document`、`windowId`，确认目标名称和 UUID；多个桥接端口时显式添加 `--port`，多个窗口时添加 `--window-id`。客户端窗口 ID 与 Windows UI 窗口句柄是两种不同标识，不可混用。

## 执行代码

脚本仅依赖 Python 标准库。从 skill 根目录调用只读脚本，输出文件写入独立会话目录。`probe` 只读当前工程和文档。

```powershell
$sessionDir = Join-Path ([System.IO.Path]::GetTempPath()) ('hardware-design-eda-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $sessionDir -ErrorAction Stop | Out-Null
python scripts/lceda-pro/eda_bridge.py discover
python scripts/lceda-pro/eda_bridge.py windows --port 49620
python scripts/lceda-pro/eda_bridge.py probe --port 49620 --window-id <当前窗口ID> --output (Join-Path $sessionDir 'session.json')
python scripts/lceda-pro/eda_bridge.py execute --port 49620 --window-id <当前窗口ID> --project <当前工程UUID> --document <当前文档UUID> --file <操作脚本绝对路径> --output (Join-Path $sessionDir 'result.json')
```

示例端口以本次发现结果为准。尖括号标识换成本次读取的值，操作脚本存入会话或项目约定的工作目录，路径带空格时加引号。`execute` 在同一请求内先验证工程和活动文档 UUID，再运行文件中的 JavaScript；返回原始 `success/result/windowId` JSON。命令失败返回非零退出码，操作文件也要检查文档类型、API 返回值及修改后状态。

JavaScript 在网关提供的 EDA 上下文中执行，使用 `eda.xxx`，可用 `await` 和顶层 `return`。不要在该上下文使用 Node.js 的 `fs`、`process` 或任意浏览器 DOM；客户端文件交互使用已公开的 `eda.sys_FileManager` 等接口，本地保存交给外部 Python/工具。不要把用户代码拼接到 shell 命令；写入 `.js` 文件后通过 JSON 请求发送。

编辑脚本执行完后读回实际对象，保留对象 ID 与操作记录。EDA 可能在同网交点拆分、合并线段并改变 ID，后续修改要重新获取当前对象，不能盲信上一批创建时返回的 ID 列表。

## 断线和失败

| 现象 | 处理 |
| --- | --- |
| 没有桥接服务 | 检查 Node、依赖和后台启动日志；启动后重新探测。 |
| 服务正常、无 EDA 窗口 | 检查桌面客户端及网关扩展是否加载。 |
| 旧窗口离线 | 重新列出窗口，按原任务识别目标，再探测工程和图页；不重复沿用离线 ID。 |
| 多窗口、目标不明 | 只读探测各窗口；无足够上下文时询问目标。 |
| 活动文档不符 | 根据已读取的文档树激活正确图页，再重新 `probe`，不改用其他类型 API 碰运气。 |
| 请求超时 | 服务默认执行超时为 30 秒；长任务拆分。先读回实际结果，再决定补执行范围，不能认为超时已回滚。 |
| 返回 `null`、`undefined` 或失败 | 对照具体方法签名、库 ID、文档类型、单位和权限定位；不能把空对象记录为成功。 |
| 文档没有该 API | 查官方文档或当前已安装的 `easyeda-api` 参考；无公开接口时改用已授权的界面操作，不编造接口。 |

修复连接后先做只读探测。不要为了重连重建工程、清空 PCB、修改库映射或放宽 DRC；也不要在任务结束时擅自关闭用户仍在使用的共享桥接服务。
