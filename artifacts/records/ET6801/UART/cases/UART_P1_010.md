# UART_P1_010 — UART break 发送、接收检测和退出恢复测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT/Peer并使能DUT LINE_ERROR；读IRQ基线后由Peer主动assert Break约10ms再release；DUT读取UART_STATUS.ERROR_FLAGS与IRQ session，在Assert前记录BREAK flag、IRQ来源/计数与fault增量；恢复正常收发验证。

## 复测要点与判断边界

- 判定：BREAK flag=1；LINE_ERROR event_count_delta>0且fault增量=0；Break后恢复Payload完整一致。
- Break由Peer主动发出（F_026双向语义中的发送侧由Peer承担），DUT只做接收检测；Break持续时间要有界（约10ms），过短可能采样不到，过长占用链路影响恢复。
- Break检测依赖ERROR_FLAGS位，与PE/FE共用LINE_ERROR中断源，归因靠flag位区分。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_010`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
