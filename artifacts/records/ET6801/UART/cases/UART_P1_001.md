# UART_P1_001 — DUT UART 实例隔离和独立复位测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT与Peer并读取Peer组件身份Snapshot；仅对DUT执行software reset并重新初始化（明确禁止触碰Peer生命周期）；在DUT执行一次内部loopback恢复取证；关闭DUT loopback后由Peer向DUT发送另一组Payload并记录DUT Capture。

## 复测要点与判断边界

- 判定：Peer component parameter/version/peripheral id保持不变（复位前后对比）；DUT复位后回环恢复数据一致；Peer→DUT数据一致。
- F_046隔离语义的核心是"只动DUT"；任何对Peer的重初始化都会使隔离证明失效。
- Peer身份对比必须取复位前后两个时点，单时点读数不构成隔离证据。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_001`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
