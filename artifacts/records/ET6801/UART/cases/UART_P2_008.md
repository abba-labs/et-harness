# UART_P2_008 — UART 软件复位后的实例身份和数据路径恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_005；资源等级 R0（Peer参与）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：Gate SOFTWARE_RESET确认能力存在并初始化DUT/Peer；读取reset前DUT组件Snapshot；执行software reset并显式重新初始化DUT；读取reset后组件Snapshot，在Assert前记录before/after身份字段；由Peer参与完成8字节恢复收发。

## 复测要点与判断边界

- 判定：SOFTWARE_RESET runtime feature存在（Gate通过）；三个组件身份字段（parameter/version/peripheral id）前后一致；8字节恢复数据完整一致。
- 本Case与P0_002的差异：复位后恢复走Peer真实数据路径，而不只是loopback自证；身份对比必须before/after两次Snapshot。
- Gate在修改任何状态前完成——SOFTWARE_RESET不存在的芯片上本Case无执行意义。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_008`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
