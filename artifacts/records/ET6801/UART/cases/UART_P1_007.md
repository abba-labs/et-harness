# UART_P1_007 — UART 奇偶校验错误检测和恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_022、UART_F_023、UART_F_028；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：DUT配置ODD、Peer配置EVEN制造校验失配（无需破坏性仪器，两端配置差即可产生）；使能DUT LINE_ERROR中断并读基线；Peer发送失配Payload；读取UART_STATUS.ERROR_FLAGS与IRQ session，在Assert前记录PARITY错误、IRQ mask/计数与失配阶段实际数据；恢复正常帧配置后做完整帧收发验证。

## 复测要点与判断边界

- 判定：失配阶段PARITY flag=1；LINE_ERROR event_count_delta>0且fault增量=0；错误后恢复帧完整一致。
- 失配数据是"收到但标记错误"，与framing（P1_008）的区分靠flag位；取证必须先于Assert，防止断言失败中断取证链。
- 恢复验证要换回合法配置后重跑完整帧，错误收下不等于错误恢复。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_007`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
