# 踩坑记录与诊断方法（android-cli-debug 按需加载）

## 1. 国内镜像：测速方法与实测数据

**小文件测速不可信**——TLS 握手延迟主导读数，会得出完全错误的镜像排序。用 8MB range 请求测真实吞吐：

```bash
curl -sL --max-time 30 -r 0-8000000 -o /dev/null -w "%{speed_download} B/s\n" <URL>
```

实测（2026-09，某国内家庭宽带）：

| 源 | 实测 | 结论 |
|---|---|---|
| dl.google.com | ~2.3MB/s | 快，SDK/cmdline-tools 直连下载 |
| services.gradle.org | ~24KB/s | 慢，Gradle zip 走腾讯 |
| repo.maven.apache.org | ~0.4MB/s（小文件仅 1.6KB/s） | 慢 |
| mirrors.cloud.tencent.com/gradle/ | ~2.6MB/s | Gradle zip 用它 |
| mirrors.cloud.tencent.com/nexus/repository/maven-public/ | ~5.6MB/s（8MB 实测） | Maven 依赖用它 |
| maven.aliyun.com | 慢且不稳 | 不推荐 |

mirror-init.gradle（`-I` 注入，不污染工程配置）：

```groovy
settingsEvaluated { s ->
    s.pluginManagement.repositories { clear()
        maven { url 'https://mirrors.cloud.tencent.com/nexus/repository/maven-public/' }
        maven { url 'https://dl.google.com/dl/android/maven2/' } }
    s.dependencyResolutionManagement.repositories { clear()
        maven { url 'https://dl.google.com/dl/android/maven2/' }
        maven { url 'https://mirrors.cloud.tencent.com/nexus/repository/maven-public/' } }
}
```

wrapper 慢时把 `gradle/wrapper/gradle-wrapper.properties` 的 distributionUrl 临时换成
`https://mirrors.cloud.tencent.com/gradle/gradle-<ver>-bin.zip`。

## 2. Gradle daemon 崩溃诊断（低内存机器）

现象：`The build build daemon disappeared unexpectedly` + 工程根出现 `hs_err_pid*.log`。

1. 读崩溃文件头部判断类型：
   - `Native memory allocation (mmap) failed to map ... G1 virtual space` → **系统提交内存耗尽**，不是堆不够
   - `malloc failed ... Chunk::new` → 同上（native 层都拿不到内存）
   - `Could not reserve enough space for object heap` → JVM 起步堆就保留失败，同样是系统层面
2. 查真实余量（**物理内存空闲 ≠ 提交内存空闲**，Windows 提交上限 = 内存 + 页面文件）：

   ```powershell
   Get-CimInstance Win32_OperatingSystem | ForEach-Object {
     "CommitFree {0:N1} GB / Limit {1:N1} GB, FreeRAM {2:N1} GB" -f ($_.FreeVirtualMemory/1MB), ($_.TotalVirtualMemorySize/1MB), ($_.FreePhysicalMemory/1MB) }
   ```

3. 提交内存 <1GB：任何 JVM 配置都起不来，等其它进程释放后再跑；可按进程名排占用找泄漏源。
4. 能起 daemon 后用低内存配方（SKILL.md §2 命令）；`--no-daemon` 避免残留 daemon 占着提交内存不还。
5. 诊断完删 `hs_err_pid*.log`（加入 gitignore）。

## 3. Kotlin/Compose 首次编译常见错误（AI 生成代码高频）

- API 33+ `g.writeDescriptor(descriptor, value)` 新签名返回 **int 状态码**（旧签名返回 boolean）：
  两分支类型合不成 Boolean 报出诡异的 inferred type 错——新签名要 `== BluetoothGatt.GATT_SUCCESS` 归一。
- `java.util.ArrayDeque` 没有 `removeFirstOrNull()`——用 kotlin.collections.ArrayDeque（去掉 `import java.util.ArrayDeque`）。
- `cond && try { ... } catch { false }` 表达式在 K2 推断失败——改显式 if/else。
- Compose：`mutableStateOf`/`setValue`/`getValue` 忘导报 "Unresolved reference 'mutableStateOf'" 及连环推断错误。

## 4. 无线调试与路径

- **配对码流程**：`adb pair <ip:port> <code>` 的码和端口只在「使用配对码配对设备」对话框停留期间有效，**每次打开都变**；报 `Unable to start pairing client` 多半是对话框已超时——重开对话框立刻执行。旧版 adb（<35）此命令直接不可用。
- **捷径**（免配对）：USB 插一次 → `adb tcpip 5555` → 拔线 → `adb connect <ip>:5555`。手机重启/换 Wi-Fi 后失效，重插 USB 重来。
- **Git Bash 路径转换**（MSYS）：远端 `/sdcard/...`、`/data/local/tmp` 会被转成 `C:/Program Files/Git/sdcard/...` 导致 push 失败。规则：**远端路径写 `//sdcard/...`（双斜杠），本地路径用 Windows 风格 `E:/...`**。`MSYS2_ARG_CONV_EXCL="*"` 会连本地 Unix 路径一起禁用，混用场景别开。
- 多设备（USB + 无线同时在线）：所有 adb 命令必须 `-s <serial>`，否则报 `more than one device/emulator`。

## 5. HyperOS 安装拦截细节

- `INSTALL_FAILED_USER_RESTRICTED` 且**秒拒无弹窗** = 「USB 安装」开关未生效。它与「USB 调试」是两个独立开关；需登录小米账号 + 插 SIM 卡才真正生效，否则表面开着、实际被静默还原（关掉重进开发者选项可验证）。
- 开关生效后 `adb install` 会在手机屏幕弹确认框，**几秒不点即超时拒**——安装时人要盯着手机。
- `adb shell pm install -r /data/local/tmp/xxx.apk` 同样被拦（框架层 UserRestriction），绕不过。
- 永远可行的兜底：push 到 `//sdcard/Download/` → 文件管理器手动装（首次需允许「安装未知应用」）。
- 无线通道 install/push/shell/logcat 与 USB 能力一致，只是 install 同样受上述限制。
