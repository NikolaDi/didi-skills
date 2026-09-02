---
name: esp-idf-dev
description: Build, flash, and monitor ESP-IDF firmware on Windows from Git Bash. Use when compiling an ESP-IDF project, flashing to a COM port, viewing serial logs, or diagnosing idf.py environment problems. 在 Windows Git Bash 下构建、烧录、监控 ESP-IDF 固件（idf.py 编译、烧录 COM 口、看串口日志、排查 idf.py 环境问题时使用）。
---

# ESP-IDF 固件构建 / 烧录 / 监控（Windows Git Bash）

## 第一步：发现 IDF 环境

按顺序探测 IDF 的激活脚本 `idf_cmd_init.bat`（Espressif Windows 安装器的入口，通常在 IDF Tools 安装根目录）：

1. 常见安装位置：`C:\Espressif\`、`%USERPROFILE%\esp\`、各盘符下的 `sdk\Espressif\`、`Espressif\` 目录
2. 桌面若有 "ESP-IDF CMD" 快捷方式，读它的目标即可拿到确切路径和参数（快捷方式目标形如 `cmd.exe /k "...idf_cmd_init.bat" [idf-id]`）
3. 已安装的 IDF 框架本体在 `<IDF Tools 目录>\frameworks\esp-idf-v*`

拿到以下信息后即可继续：

- `idf_cmd_init.bat` 的完整路径
- 可选的 idf-id 参数（形如 `esp-idf-<hash>`，桌面快捷方式目标里通常带着）

**找不到、找到多个、或与用户预期不符时，直接问用户要路径**，不要猜。

## 第二步：wrapper 脚本 —— Git Bash 下必须使用

不要在 Git Bash 里直接调 `idf.py` 或 `idf_cmd_init.bat`，两个坑：

1. ESP-IDF 的 `export.bat` 检测到 `MSYSTEM` 变量（Git Bash 会注入）就静默退出；沙箱环境下 `env -u MSYSTEM` 在 cmd 进程里清不掉它。
2. `idf_cmd_init.bat` 创建的 `DOSKEY idf.py` 宏在批处理脚本/非交互 shell 里不生效。

解决办法：使用 wrapper 批处理（模板见 [scripts/idf_run.bat](scripts/idf_run.bat)）。它在 cmd 内部清掉 `MSYSTEM`、source IDF 环境、再显式用 venv Python 调 idf.py。

**安装 wrapper**：把模板复制到任何 git 仓库之外（如某个 `tools\` 或用户目录），并按模板开头的注释把 IDF 路径/idf-id 改成本机实际值。wrapper 会优先使用调用时所在目录（有 CMakeLists.txt 即视为项目目录），否则报错提示先 `cd` 进项目。

## 常用命令

统一走这个入口：`MSYS_NO_PATHCONV=1 cmd /c '<wrapper 路径> <idf.py 参数>'`
（`MSYS_NO_PATHCONV=1` 防止 Git Bash 改写 `/d` 之类的路径。）

```bash
# 编译 + 烧录 + 监控一条龙（monitor 会一直跑 —— 必须 run_in_background）
cmd /c '<wrapper> -p <COM口> build flash monitor'

# 仅编译（可前台）
cmd /c '<wrapper> build'

# 仅烧录
cmd /c '<wrapper> -p <COM口> flash'
```

**确定 COM 口**：`powershell -NoProfile -Command "[System.IO.Ports.SerialPort]::GetPortNames()"`。端口不唯一、或插拔后存疑时，列出候选问用户，不要猜。

**监控模式**：后台启动，然后轮询日志文件、结束时停掉任务释放串口。打开串口会复位开发板；首次输出前要等 IDF 环境激活（几十秒），不是卡死。

```bash
cmd /c '<wrapper> -p <COM口> monitor'   # run_in_background=true
sleep 70; grep -n -E "app_main|boot" <日志文件>
```

## 踩坑记录

- **COM 口被占用**：监控同时只能开一个。烧录前先停掉后台监控；报错长这样：`A fatal error occurred: Could not open COM56`。
- **严禁在 IDF 框架目录跑 idf.py**（`...\frameworks\esp-idf-v*`）——CMake 会把框架本身当项目去编译，报一堆看不懂的 clang/ld 链接错误。误操作生成的垃圾 `build/` 目录可以安全删除。
- **从 Git Bash 传参**：统一加 `MSYS_NO_PATHCONV=1`；路径含空格时整个 `/c` 后面的命令用单引号包裹。
- **构建失败先看目录**：`idf.py` 必须在含项目 `CMakeLists.txt` 的目录运行，报"找不到编译器/无法编译测试程序"多半是跑错目录而不是工具链坏了。
