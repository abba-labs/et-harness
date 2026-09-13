# UART_P1_002 — UART RX data available 中断和事件计数测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT并使能RX_READY（RX_DATA_AVAILABLE）中断；读取激励前UART ISR session基线（event/fault/pending/active）；开启loopback并先启动4 Byte Capture；发送Payload等待Capture完成后对比增量。

## 复测要点与判断边界

- 判定：发送/接收完整且数据一致；RX_READY event_count_delta>0；fault_count_delta=0。
- 中断计数必须用基线差值（delta），绝对计数不能当证据；event>0与fault=0要同时成立，二者缺一会掩盖错误分类缺陷。
- 4字节低于常见RX阈值，走的是"有数据即中断"路径，与阈值中断（P1_004）路径不同，不能互相替代。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_002`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
