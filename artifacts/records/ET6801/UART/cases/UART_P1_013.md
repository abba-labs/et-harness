# UART_P1_013 — UART 发送 halt、resume 和数据路径恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_037、UART_F_017；资源等级 R1。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT、开启loopback并先启动等长Capture；assert TX Halt后用write_partial把Payload装入TX FIFO；读取Halt状态下UART_FIFO.TX_LEVEL确认存在非零待发送数据；连续执行4次独立Capture读取，每次受Driver timeout约束，证明Halt期间接收进度保持0；解除Halt后无需重新提交Payload即可完成传输。

## 复测要点与判断边界

- 判定：Halt窗口存在非零待发送FIFO数据；4次独立Capture采样均received=0；解除Halt后同一Payload自然完成。
- "解除后无需重新提交"是Halt/Resume语义的核心：数据还在FIFO里，重新写入就测不出resume恢复点。
- 4次独立采样（而非1次长等待）证明的是"持续停住"而不是"恰好赶上"。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_013`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
