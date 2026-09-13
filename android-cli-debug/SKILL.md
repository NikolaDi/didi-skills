---
name: android-cli-debug
description: 在 Windows 命令行（无 Android Studio）构建 APK 并部署到真机调试：SDK/Gradle 环境搭建、国内镜像加速、低内存机器 Gradle daemon OOM 诊断、adb 无线调试、小米 HyperOS 安装拦截（INSTALL_FAILED_USER_RESTRICTED）、Git Bash 下 adb 路径转换、adb 驱动 App UI 自动化（input tap 的 INJECT_EVENTS 权限、安全锁屏、uiautomator dump 取 Compose 坐标、息屏断连）。当任务是「把 Android 工程编出包/装到手机/抓日志/用 adb 自动操作 App 界面」且没有 IDE 时使用。不用于：应用功能本身的编码、iOS/Flutter/跨端框架、已由 Android Studio 接管的 IDE 内构建流程、非 Windows 主机（命令示例为 Git Bash）。
---

# Android 命令行构建与真机调试（Windows）

单工作流三段：**搭环境 → 出包 → 上真机**。踩坑细节与诊断方法见 [references/pitfalls.md](references/pitfalls.md)。
全部命令经真机验证（2026-09，Win11 + 小米 HyperOS + Git Bash；SDK 35 / build-tools 35.0.0 / Gradle 8.9 / platform-tools 37）。

## 0. 环境探测（先跑这个，按缺什么跳对应节）

```bash
java -version                                # 缺 → 装 JDK 17（AGP 8.x 硬性要求）
ls "$LOCALAPPDATA/Android/Sdk" 2>/dev/null   # 缺 → §1
which gradle; echo "$ANDROID_HOME"
adb devices                                  # 旧版 adb 常以独立目录残留，配对/无线要用 ≥35 新版
```

## 1. 搭环境

```bash
SDK="$LOCALAPPDATA/Android/Sdk"
curl -sL -o cmdtools.zip "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
python -c "import zipfile; zipfile.ZipFile('cmdtools.zip').extractall('.')"
mkdir -p "$SDK/cmdline-tools" && mv cmdline-tools "$SDK/cmdline-tools/latest"
SDK_ROOT=$(cygpath -w "$SDK")   # sdkmanager 必须显式 --sdk_root，否则装错位置
yes | sdkmanager --licenses --sdk_root="$SDK_ROOT"
sdkmanager --sdk_root="$SDK_ROOT" "platform-tools" "platforms;android-35" "build-tools;35.0.0"
```

Gradle：zip 解压即用（国内走腾讯镜像，见 pitfalls §1）。工程 wrapper 缺 jar/gradlew 时从
`raw.githubusercontent.com/gradle/gradle/v<版本>/gradle/wrapper/` 单独补三件套
（gradle-wrapper.jar / gradlew / gradlew.bat），并写 `local.properties`：
`echo "sdk.dir=$(cygpath -m "$LOCALAPPDATA")/Android/Sdk" > local.properties`。

## 2. 出包

```bash
# 国内网络：加 -I mirror-init.gradle（腾讯 maven + google 直连，脚本全文见 pitfalls §1）
# 内存紧张机器：--no-daemon + 小堆 + 限 worker + Kotlin 进程内编译
gradle assembleDebug --no-daemon --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1200m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Dorg.gradle.workers.max=4 -Pkotlin.compiler.execution.strategy=in-process \
  -I mirror-init.gradle
```

产物：`app/build/outputs/apk/debug/app-debug.apk`。
构建失败先看工程根目录 `hs_err_pid*.log` 判断是「系统提交内存耗尽」还是「堆不够」（诊断见 pitfalls §2）；
提交内存 <1GB 时任何 JVM 配置都起不来，等回暖再跑。
首次编译才暴露的 Kotlin 新坑清单见 pitfalls §3。

## 3. 上真机

**无线捷径（推荐）**：手机插一次 USB → `adb tcpip 5555` → 拔线 → `adb connect <手机IP>:5555`。
手机 IP：`adb shell ip -f inet addr show wlan0`。重启/换网后重插 USB 重来。
配对码流程的坑与 Git Bash 路径转换规则见 pitfalls §4。

**安装被拒 `INSTALL_FAILED_USER_RESTRICTED`（小米/HyperOS）**：
1. 开发者选项开「USB 安装」（独立开关，需小米账号+SIM，否则静默还原）
2. 安装时盯手机屏幕——确认框几秒不点即超时拒
3. `adb shell pm install` 同样被拦（框架层），别浪费时间试
4. 兜底：`adb push xxx.apk //sdcard/Download/` → 文件管理器手动装

**启动验证**：
```bash
adb -s <dev> install -r app-debug.apk
adb -s <dev> shell am start -n <pkg>/.MainActivity && sleep 3 && adb -s <dev> shell pidof <pkg>
```

联调前调长手机息屏（息屏 = Wi-Fi 休眠 = 无线 ADB 断连），命令见 pitfalls §4。

## 4. 驱动 App UI（联调自动化）

替人点屏幕：自动重连、翻页、点按钮、截屏验收。命令只有四个——
`input tap/swipe`、`input text`、`keyevent`、`uiautomator dump`——但有一串权限与
坐标坑（HyperOS 需开「USB 调试（安全设置）」、安全锁屏 ADB 代解不了、截图估坐标
必偏、Compose 节点解析要点、bottom sheet 关法），**完整坑链见 pitfalls §6**。

最小可用流程：
```bash
adb shell dumpsys window | grep mCurrentFocus      # 先确认没锁屏（NotificationShade=锁着）
adb shell uiautomator dump //sdcard//ui.xml        # 拿控件 bounds（Git Bash 双斜杠）
adb exec-out cat //sdcard//ui.xml                  # 解析目标控件中心坐标
adb shell input tap <x> <y>                        # dump 后立即点（bounds 会过期）
adb exec-out screencap -p > shot.png               # 截屏验收
```

## 5. 抓日志

```bash
adb -s <dev> logcat -c                                # 清缓冲
adb -s <dev> logcat -v time "*:I" > session.log       # 会话期持续抓
adb -s <dev> logcat -d --pid=$(adb -s <dev> shell pidof <pkg>)   # 只看本 App
```

崩溃 grep `FATAL|AndroidRuntime`；多设备在线时所有 adb 命令加 `-s`。
