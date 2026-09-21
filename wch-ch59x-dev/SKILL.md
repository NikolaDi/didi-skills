---
name: wch-ch59x-dev
description: Build, flash, and debug WCH CH59x/CH591/CH592 (RISC-V) firmware on Windows Git Bash. Use when compiling with the MounRiver GCC toolchain, flashing via wlink/WCH-Link, reading UART serial logs, or diagnosing boot faults, flash-read anomalies, or USB enumeration failures on CH59x silicon. 在 Windows Git Bash 下构建、烧录、调试 WCH CH59x/CH591/CH592（RISC-V）固件：MounRiver GCC 编译、wlink/WCH-Link 烧录、看串口日志、排查 CH59x 上电故障 / Flash 读取异常 / USB 枚举失败时使用。不用于 ESP32 / STM32 等其他平台。
---

# WCH CH59x 固件开发与上硅调试（Windows Git Bash）

CH59x 是 WCH 的 RISC-V（青稞内核）芯片家族（CH591/CH592）。本 skill 覆盖该平台在 Windows Git Bash 下的编译、烧录、串口调试与高频硬件坑速查。

## 工具链与构建

- 编译器：MounRiver Studio II 自带 GCC（`riscv-wch-elf-gcc`，`rv32imac_zicsr`）。路径形如 `D:/soft/MounRiver/.../RISC-V Embedded GCC12/bin`。
- 工程由 Makefile 驱动：`make` 构建、`make clean` 清理；映射文件 `.map` 用于核对 Flash/RAM 占用与段放置。
- **DEBUG/量产变体分目录输出**：`make` 不跟踪编译参数变化，同目录混用不同宏（如 `-D<DEBUG_BUILD>`）会半新半旧混链。按变体分 `build/` 与 `build-dev/`，`clean` 两者都删。

## 烧写（wlink / WCH-Link）

- 命令：`wlink --chip CH59X --speed medium flash -e <hex>`；`-e` 先整片擦除。速度必须 `medium`（`high` 会导致 SDI 写失败）。
- 驱动：WCH-Link 需绑定 WinUSB（Zadig 选 Interface 0，勿选 SERIAL）；与官方 MRS OpenOCD 驱动互斥。
- **唤醒窗口**：固件运行即深睡（约 0.5s），睡后所有 SDI 命令报协议错误 `0x55`。烧写/复位/擦除要在「上电或复位后」的短窗口内做——用重试循环（约 1s 间隔）抓窗口；全片擦除后芯片处于「空片」态，可稳定连接。
- **写入无端到端校验**：偶发 4 字节写错，烧写后在同一窗口内 `wlink dump 0x0 <len>` 读回与 hex 逐字节比对。
- **SDI 读不可靠**：外设寄存器与 RAM 的 `wlink dump` 返回噪声，只有 CodeFlash 读回可信。调试外设状态用固件侧打印，不要依赖外部读内存。

## 串口日志 / 命令行

- 波特率 115200 8N1。**打开串口会复位开发板**，复位后约 1s 启动窗口内首条命令可能被丢——命令发送要带重试，或等启动日志出现后再发。
- **主频切换后重算波特率**：切到 PLL 高频（如 60MHz）后 UART 分频器若不按新主频重配，日志变乱码。
- **GBK 控制台编码坑**：Windows 控制台 GBK 下，Python 打印含异常字节的串口数据会抛 `UnicodeEncodeError`。把原始字节写文件再读，别直接 print。
- 串口被后台任务占用时报 `PermissionError(13, ... access denied)`——先停掉占用该口的后台任务。

## 高频硬件坑（速查）

完整说明见 [references/hardware-gotchas.md](references/hardware-gotchas.md)：

| 症状 | 根因 |
| --- | --- |
| 空 Flash 区读回固定 `A9 BD F9 F3`（不是 0xFF） | CH592 擦除态读签名，逻辑擦除态需归一 |
| 16 位子字读 Flash 拿不到正确半字 | CodeFlash 数据读必须 32 位对齐 |
| USB 枚举失败 / 反复总线复位 | EP0 SETUP 后未强制 DATA1 toggle |
| UART 接收中断不开 | 除 IER 外还要开 MCR 中断总门（`MCR.INT_OE`） |
| RTC 触发永不触发 | `RTC_TRIGFunCfg` 入参是相对间隔，内部自加当前计数 |
| USB 全速不工作 | CH59x 无内部 32M HSI，依赖外部 32MHz 晶振 + PLL |

## 常见错误

- 烧写报 `0x55` 协议错误：芯片在深睡，重插板子/复位抓窗口，或接 RST/3V3 用治具控制。
- 串口首条命令无应答：端口打开触发了复位，命令落在启动窗口里，重发即可。
- 「源码里有字符串但二进制里没有」：编译器按未定义行为折叠/删除了代码（典型如 `*(volatile uint32_t *)0` 空指针解引用 → `__builtin_trap`），用 `riscv-wch-elf-objdump` / `strings` 核对产物。
