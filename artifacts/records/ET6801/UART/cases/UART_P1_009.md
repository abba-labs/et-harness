# UART_P1_009 — UART RX overrun 错误检测和 FIFO 恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_022、UART_F_025、UART_F_028；资源等级 R1。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT、使能LINE_ERROR并开启内部loopback；读IRQ基线后**不启动Capture**保持RX读取压力；发送64字节确定性数据形成受控RX FIFO溢出（内部回环下无人读取导致overrun）；读取UART_STATUS.ERROR_FLAGS与IRQ session取证；软件复位后做8字节恢复验证。

## 复测要点与判断边界

- 判定：OVERRUN flag=1；LINE_ERROR event_count_delta>0且fault增量=0；溢出后数据恢复完整一致。
- "不启动Capture"是制造溢出的关键手段，与正常Case相反——复测时若顺手启动了Capture，溢出不会发生，overrun flag恒为0是方法错误不是硬件缺陷。
- 64字节需超过RX FIFO深度才能可靠溢出；恢复用软件复位，属于错误恢复路径验证。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_009`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
