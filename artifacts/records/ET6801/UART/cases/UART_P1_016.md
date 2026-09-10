# UART_P1_016 — UART FIFO 配置、边界收发和状态快照测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_012、UART_F_013、UART_F_014、UART_F_015、UART_F_016、UART_F_017、UART_F_018；资源等级 R1。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT并配置FIFO enable、TX threshold=2、RX threshold=4；逐1/15/16/17/32字节读取发送前UART FIFO level；开启loopback并启动等长Capture后有界发送；每轮记录FIFO状态快照并等待完成。

## 复测要点与判断边界

- 判定：五个长度全部执行；每轮发送/接收完整且数据一致；每轮终态RX FIFO level=0。
- 1/15/16/17/32是围绕FIFO深度的边界值集合（低于/贴边/跨过），换成任意值会丢边界覆盖语义。
- FIFO level快照取"发送前"与"终态"两个时点；终态非零说明有数据滞留，是F_013状态语义的判定点。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_016`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
