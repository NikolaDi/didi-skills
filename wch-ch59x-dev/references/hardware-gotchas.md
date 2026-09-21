# CH59x 高频硬件坑（详细）

## CodeFlash 擦除态读签名与 32 位对齐读

- 物理擦除的 CodeFlash 直接读取**不返回 0xFF**，每个 4 字节对齐双字固定读回 `0xF3F9BDA9`（字节序 `A9 BD F9 F3`）。wlink 整片擦除、ROM IAP 擦除后均如此；编程过的单元读出精确值。
- **数据读必须 32 位对齐**（同官方 `FLASH_ROM_READ` 的访存方式）：对签名单元做 16 位子字读取拿不到正确半字。
- 影响：任何「扫描空 Flash 区」的逻辑若把 0xFF 当擦除态会误判。正确做法：读路径把整双字签名归一为逻辑擦除态；编程值域与签名无交集时可直接归一。
- 验证方法：全片擦除 → `wlink dump` 读目标区（应为签名）；再 `wlink flash -a <addr> test.bin`（不擦）写已知字节 → 读回应为精确值。

## USB 枚举失败：EP0 toggle

- CH59x 硬件**不在 SETUP 时复位 DATA toggle**。控制传输数据阶段必须从 DATA1 开始，故收到 SETUP 时要显式置两个 toggle 位（`RB_UEP_R_TOG | RB_UEP_T_TOG`），续传/结束包逐包翻转 `RB_UEP_T_TOG`。
- 症状：主机反复发 `GET_DESCRIPTOR` 后总线复位（「无法识别的 USB 设备」）；抓包可见描述符首包 PID 是 DATA0。

## UART 接收中断

- 开接收中断除写 IER 的 `RB_IER_RECV_RDY` 外，还要开 MCR 的中断总门 `RB_MCR_INT_OE`（官方 `UARTx_INTCfg` 内部两步都做）。只写 IER 中断到不了中断控制器。
- RX FIFO 仅 8 字节：主循环有 10ms 级阻塞时轮询直读必丢字节，接收走中断 + 环形缓冲。

## RTC 触发

- `RTC_TRIGFunCfg(cyc)` 的入参是**相对当前时刻的间隔**，函数内部会 `RTC_GetCycle32k() + cyc`。调用方再叠加一次当前计数会把触发点推到约 2 倍当前计数之后。
- 触发匹配的合成计数值 = {高 16 位 CNT_2S（2 秒单位），低 16 位 CNT_32K}，按普通 32 位加减做触发点运算即可。

## 时钟 / USB

- CH59x **无内部 32M HSI**，USB 全速依赖外部 32MHz 晶振 + PLL（480M/10=48M）。无晶振时切 PLL 高频或 USB 不工作。
- 走时精度依赖外置 32.768kHz 晶振 + ppm 标定 + 温补；内部 32K RC 校准后仍有 ±0.2%。
- 切换系统主频后，UART 波特率分频需按新主频重算（调用方在切频后重配波特率）。

## Flash 布局（CH591F / CH592F）

- CH591F 192KB CodeFlash、CH592F 448KB；`InfoFlash`（配置字）在 0x7E000+，用户配置信息含读保护位 `CFG_ROM_READ`（0=禁止编程器读出）。
- 换 CH592F 时用户代码/日志区布局需按新容量重算（用户区 [0, 0x70000)，Boot 0x78000，DataFlash 0x70000-0x77FFF）。
