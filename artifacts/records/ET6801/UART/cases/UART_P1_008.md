# UART_P1_008 — UART 停止位失配导致的 framing error 检测和恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_022、UART_F_024、UART_F_028；资源等级 R0。 本轮已选节点 SKIP（见变化记录），脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

三轮运行（2026-08-10、2026-08-13、2026-08-28）本Case均被正式门禁判定SKIP，不是FAIL：当前UART1/UART2交叉连接下，改变两端停止位（DUT 2 stop / Peer 1 stop）仍不能稳定形成可重复的Framing Error状态和中断。Case自带门禁逻辑：Bench未声明deterministic framing-error stimulus时合法SKIP，不用不稳定刺激判定Feature。

## 判断边界与复测条件

- 有刺激时判定为：FRAMING flag=1且LINE_ERROR事件增加、IRQ fault增量=0、错误后恢复。
- SKIP原因：当前TX/RX板级连接无法确定性制造停止位采样错误；停止位失配产生的实际采样错误依赖位时序相位，交叉连线无法精确控制。
- 复测条件：可控错误帧发生器、FPGA波形发生器或可精确破坏停止位的Peer。不能用不稳定刺激硬跑后把偶发结果写成Feature结论。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_008`；芯片适配与SKIP归因见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`blocked_by_board: current TX/RX pair has no deterministic framing-error stimulus`。与既有板级刺激缺口一致。
