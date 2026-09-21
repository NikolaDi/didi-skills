---
name: usb-device-stack-debug
description: Debug USB device enumeration and Bulk-Only Transport (MSC/BOT) failures on embedded MCUs. Use when a USB device shows "not recognized", enumerates but exposes no drive letter, or a mounted USB drive hangs while reading files. 排查嵌入式 MCU 的 USB 设备枚举与 Bulk-Only Transport（MSC/BOT）失败：设备报「无法识别的 USB 设备」、枚举成功但无盘符、或 U 盘读文件卡死时使用。不用于主机侧 USB 驱动 / 协议栈开发。
---

# USB 设备栈上硅调试（枚举 / BOT / MSC）

设备栈「第一次上硅」最容易坏在三个点：控制传输 toggle、大块数据传输、SCSI 命令集。本 skill 给出逐包追踪的方法与这三处的判据。

## 核心方法：逐包事件追踪

USB 中断里**禁止调用不可重入的日志**。改为：ISR 里只往环形缓冲 push 一个事件，主循环按变化 drain 并打印。事件要能还原枚举对话：

- 复位（`R`）、挂起（`U`）、Setup（`S`，带 8 字节）、端点 IN/OUT 完成（`I`/`O`，带端点号/长度/toggle 状态）、STALL（`X`）、BOT 的 CBW opcode（`C`）。
- **过滤噪声**：字符串/设备描述符请求会淹没缓冲区，只记非描述符 Setup 和非 EP0 数据包。

## 枚举失败：EP0 控制传输 toggle

- 控制传输的数据/状态阶段**双向从 DATA1 开始**（USB 2.0 §8.5.3）。很多 MCU 的 USB 控制器不在 SETUP 时自动复位 toggle——必须在 Setup 处理里显式置 DATA1，续传/结束包逐包翻转。
- 判据：主机反复 `GET_DESCRIPTOR` 后总线复位；抓包看到描述符首包 PID 是 DATA0 而非 DATA1。

## 挂载成功但无盘符：SCSI 层放弃

设备管理器里设备「正常」但不出盘符，通常是 SCSI 命令集不完整——主机会在某条命令失败后放弃挂载：

- 只读大容量设备至少应答：`INQUIRY(0x12)`、`READ CAPACITY(10)(0x25)`、`READ(10)(0x28)`、`REQUEST SENSE(0x03)`、`TEST UNIT READY(0x00)`，以及 `READ FORMAT CAPACITIES(0x23)`、`MODE SENSE(6/10)`（带写保护位）、`PREVENT/ALLOW MEDIUM REMOVAL(0x1E)`、`SYNCHRONIZE CACHE(0x35)`、`START STOP UNIT(0x1B)`、`VERIFY(0x2F)`。
- 未实现的命令回 CHECK CONDITION（`ILLEGAL REQUEST`/`INVALID COMMAND`）即可；但关键命令失败会导致挂载中止。

## 读文件卡死：大块数据传输

- 抓包看是否还有 READ(10) 流量：**卡死时如果没有任何 CBW 流量**，问题在主机侧（陈旧盘符/过滤驱动）；**有 READ(10) 但数据包没出去**，问题在设备数据阶段。
- 经典 bug：数据剩余长度用 16 位变量，主机一次读 ≥64KB（128 扇区）时截断为 0 → 零长包 → 主机超时复位。**数据长度一律用 32 位**。
- BOT 数据阶段每包 64B，多扇区读按包流式组装；CSW（13 字节：签名 `USBS` + tag + residue + status）必须在数据阶段末独立发送。

## 方法：对照厂商例程找「少的一步」

枚举/传输这类协议问题，先找芯片厂商的 USB 设备例程，逐行对比 Setup/toggle/DMA 初始化。少的一步往往是：Setup 里没置 toggle、没开某个中断门、DMA 缓冲没按双缓冲约定放置。

## 常见错误

- 在 USB 中断里直接用日志库打印 → 中断重入/时序错乱；改成计数 + 主循环打印。
- 只实现 INQUIRY/READ 就认为「能读」→ 主机在 MODE SENSE 或 READ FORMAT CAPACITIES 失败时直接放弃挂载。
- 抓到「没有流量」就断定固件死——先确认设备仍被枚举（设备管理器状态）、盘符是否陈旧。
