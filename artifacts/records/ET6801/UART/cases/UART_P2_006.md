# UART_P2_006 — UART RTS/CTS 自动流控的暂停和恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_032、UART_F_017；资源等级 R1。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：Gate FLOW_CONTROL并初始化DUT/FIFO，开启内部loopback与自动流控（AFCE）；启动128字节Capture后撤销RTS使内部CTS进入not-ready；在有界pause窗口反复capture_get/write_partial，累计accepted与received直到出现accepted=0；记录暂停阶段accepted序列与Capture received事实；恢复RTS后在resume窗口确认全部pending数据被接受。

## 复测要点与判断边界

- 判定：pause窗口至少出现一次0字节acceptance（流控生效证据）；resume窗口内全部pending数据被接受；最终128字节Capture完整且数据一致。
- "至少一次accepted=0"必须在有界窗口内主动轮询取得，被动等最终结果测不出流控暂停事实。
- resume后pending数据一个不能丢：流控只暂停不丢弃，丢字节即FAIL。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_006`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
