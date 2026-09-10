# UART_P1_011 — UART 中断源的 mask 使能、关闭和 Service session 状态测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_019、UART_F_020、UART_F_021、UART_F_028；资源等级 R1。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT并逐项使能RX_READY/TX_READY/CHARACTER_TIMEOUT三个请求source；读取激励前IRQ session基线；开启loopback并启动12 Byte Capture后发送Payload；等待完成并读取启用阶段UART_ISR.ENABLED/PENDING/ACTIVE mask与event/fault计数；再逐项关闭并读取关闭后mask状态。

## 复测要点与判断边界

- 判定：启用mask包含三个source；关闭后enabled mask中三个source均为0；event_count_delta>0且fault增量=0。
- 本Case是F_028"独立使能、识别、稳定清除"的集中取证点：ENABLED/PENDING/ACTIVE三个mask都要读，只看event计数不构成mask语义证明。
- 逐项使能再逐项关闭；批量开关会掩盖"关闭A误清B"这类独立清除缺陷。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_011`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
