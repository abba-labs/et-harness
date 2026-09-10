# UART_P2_003 — UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_035、UART_F_036；资源等级 R0（Peer+DMA×2）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：创建带Guard的TX/RX Resource并选择两个不同空闲DMA Channel；初始化DUT/Peer、使能UART DMA并配置TX/RX两条SYSCTRL route；配置DMA TX M2P与RX P2M两个Channel及TRANSFER_DONE IRQ；先启动Peer Capture，一次CHANNELS_START提交包含两个Channel的mask，再由Peer发送反向Payload完成双向128字节。

## 复测要点与判断边界

- 判定：一次mask包含且仅包含两个选定Channel；两个方向128字节数据均一致；四个Guard完整。
- "一次原子启动"是本Case区别于P2_001/P2_002单通道的全部意义：分两次启动就退化成单通道测试，F_036多request模式语义未被覆盖。
- mask只能含选定两Channel，多余bit=残留配置污染。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_003`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
