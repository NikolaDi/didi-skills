---
name: wechat-miniprogram-automation
description: 用微信开发者工具自带的 wechatide CLI 对微信小程序做自动化联调——刷新模拟器、截图验证 UI、在页面运行时执行 JS、调用页面方法、mock wx API、grep console/network 日志。当用户要在微信开发者工具里联调/调试小程序、操作模拟器、自动点击页面元素、截图检查界面、验证接口请求，或提到"微信开发者工具""小程序模拟器""小程序联调""模拟器截图"时使用，即使用户没有点名这个工具。不要安装 miniprogram-automator 等第三方自动化 SDK——优先用本 skill 的官方 CLI，它不依赖测试号、不需要改项目代码。
---

# 微信小程序自动化联调（wechatide CLI）

微信开发者工具自带一个 skill CLI（`wechatide.cmd`，v0.3.x 起内置），能直连正在运行的 IDE，对模拟器做真实操作。比 miniprogram-automator 方案省掉一整套 npm 依赖和测试号配置，且截图、日志、mock 能力都是现成的。

## 前置条件（先核对，缺哪个补哪个）

1. 微信开发者工具已安装，记下安装目录（下文记作 `<IDE_DIR>`，如 `D:\soft\Tencent\微信web开发者工具`）。
2. IDE 保持运行并已登录。查登录态：
   ```bash
   cd "<IDE_DIR>" && ./wechatide.cmd -c <client> check_wechatide_status
   ```
   未登录时二选一：
   - `./wechatide.cmd -c <client> login --type image` —— 二维码直接返回给你，转给用户扫码（**推荐**，避开 IDE 登录弹窗太小显示不全二维码的坑）；
   - `./wechatidecli.cmd login` —— 经典 CLI 登录。
3. 项目已导入 IDE 项目列表（`project_import` 只导入不打开；`open_project_window --project <项目绝对路径>` 打开带模拟器的窗口）。项目根目录必须有 `project.config.json`。
4. 若 `check_wechatide_status` 返回 `tokenRequired: true`，之后所有命令加 `--token <令牌>`（令牌在 IDE 设置 → 安全设置里查看）。

`<client>` 是调用方名字，任意起（如 `kimi-code`），用于 IDE 侧审计日志。

首次调用时 CLI 可能输出 `Failed to connect ... running toolCall:auth`——这是正常的自动授权流程，它会自动完成鉴权并拉起 IDE 服务，紧接着就会返回真实结果，不用手动干预。

## 调用骨架

```bash
cd "<IDE_DIR>" && ./wechatide.cmd -c <client> <toolName> --project <小程序项目绝对路径> [flags]
```

除 `check_wechatide_status` / `login` 外，几乎所有工具都要 `--project`。查看某个工具完整参数：`./wechatide.cmd <toolName> -h`。

## 标准联调循环（改代码后验证的黄金路径）

```
改代码 → simulator_refresh → （按需 automation_navigate 到目标页）
       → simulator_screenshot --wait 2 → 用读图工具看截图，肉眼确认 UI
       → automation_page_action getData / automation_evaluate 断言数据
       → get_simulator_console 'grep -i error' / get_simulator_network 'grep -i fail' 查异常
```

**改完代码必须先 `simulator_refresh` 再测。** 模拟器有缓存，不刷新会吃到旧包，你会对着旧代码的行为怀疑人生。这是整个流程里最容易被跳过、代价最高的一步。

截图一定要 `--wait 2`（或 `--wait-for-selector`）让页面渲染稳了再截，并且**真的去读那张图**——截图不看不等于验证。

## 工具速查（按用途）

| 目的 | 工具 | 关键参数 |
|---|---|---|
| 刷新/重编译 | `simulator_refresh` | `--project` |
| 编译并打开指定页 | `simulator_open_page` | `--project --page <path>` |
| 截图 | `simulator_screenshot` | `--wait 2` `--path <输出路径>`；返回 path+尺寸 |
| 页面导航（含 tab） | `automation_navigate` | `--action navigateTo/redirectTo/switchTab/reLaunch/navigateBack --url <路径>` |
| 运行时执行任意 JS | `automation_evaluate` | `--fn-source "function() { ... }"` |
| 读/写页面 data | `automation_page_action` | `--action getData/setData --data-path <路径> --patch <json>` |
| 调页面方法 | `automation_page_action` | `--action callMethod --method <名> --args <json>`（数组参数见坑 2） |
| 点/输入元素 | `automation_element_action` | `--action tap/input/trigger --selector <选择器>` |
| mock/恢复 wx API | `automation_wx_api` | `--action call/mock/restore --method showModal --result <json>` |
| 读 console | `get_simulator_console` | `--command 'grep -n .'`（全部）/ `'grep -i error'` |
| 读 network | `get_simulator_network` | `--command 'grep -n .'` / `'grep -i fail'` |
| 清缓存 | `debug_clear_cache` | 模拟器行为诡异时用 |

console/network 的 `--command` 是 grep 命令字符串；返回空串只代表没命中，不代表缓冲区为空。

## 踩坑记录（都是实测换来的，别重踩）

1. **切 tab 页别用 navigate**：`automation_navigate --action switchTab`换新项目实测报 `Uncaught [object Object]`（v0.3.9）。直接用 `automation_evaluate` 包 `wx.switchTab({url: '/pages/xxx/xxx'})`，稳定可靠。navigate 的 navigateTo/redirectTo 没踩过雷，但凡是切换失败都先退到 evaluate。
2. **刷新后立刻截图可能截到刷新前的页面**：`simulator_refresh` 是异步重编译，画面可能还停在旧页。截图前给足 `--wait`，并用 `automation_evaluate` 查 `getCurrentPages()` 的 route 确认当前页——route 和截图对不上时以 route 为准，别对着旧截图分析。
3. **数组参数传不进去**：`automation_page_action callMethod --args-file` 传数组参数不可靠。需要带参调页面方法时，改用 `automation_evaluate` 直接拿页面实例调：
   ```bash
   ./wechatide.cmd -c <client> automation_evaluate --project <路径> \
     --fn-source "function() { return getCurrentPages().slice(-1)[0].myMethod(arg1, arg2); }"
   ```
4. **浮层/弹层里的元素 tap 不可靠**：`automation_element_action tap` 对 overlay 内元素经常点不中。别死磕坐标，用上面 evaluate 的方式直接调页面方法触发同样的逻辑，更稳也更接近"验证业务"而非"验证坐标"。
5. **mock 弹窗后必须恢复**：`automation_wx_api --action mock --method showModal --result '{"confirm":true}'` 用完立刻 `--action restore --method showModal`，否则后续用例全被污染。
6. **验证后端数据用脚本，不用手点**：需要造数据/断言服务端状态时，直接打后端 API。Windows 下 `curl` 发含中文的 JSON 必乱码——用 Python `urllib` 发请求。终端打印保持纯 ASCII（Windows 控制台是 GBK，中文打印会变乱码，只是显示问题但会干扰判断）。
7. **模拟器请求本地后端**：小程序里配 `http://127.0.0.1:<端口>` 即可，真机才需要域名；IDE 详情 → 本地设置里勾"不校验合法域名"。
8. **截图坐标**：`simulator_screenshot` 默认把长边压到 1280 JPEG。要按坐标操作时，以返回的 `imageWidth/imageHeight` 换算，别拿截图显示尺寸直接当逻辑像素。

## Windows 注意

- 在 Git Bash 里执行：`cd "<IDE_DIR>" && ./wechatide.cmd ...`（cmd 文件可直接跑；路径含中文/空格务必加引号）。
- 命令输出是 UTF-8，工具里显示中文正常；自己写的辅助脚本输出请用 ASCII（见坑 5）。
