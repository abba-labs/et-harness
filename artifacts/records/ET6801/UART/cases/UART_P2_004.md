# UART_P2_004 — UART 9-bit 软件数据双向收发及普通模式恢复测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：在修改状态前Gate两端NINE_BIT Runtime Feature确认能力存在；初始化并开启软件9-bit模式；DUT发送第一组9-bit words由Peer读回并在Assert前记录PEER UART_9BIT.DATA；Peer发送第二组9-bit words由DUT读回记录；最后退回普通8-bit模式做恢复收发。

## 复测要点与判断边界

- 判定：两个方向9-bit元素数量完整且逐项相同；退出9-bit后普通8-bit恢复数据完整一致。
- NINE_BIT Feature必须先Gate确认再配置；软件9-bit（逐word软件标记）与硬件地址匹配（P2_005）是两条独立路径，不能互相替代证明。
- 9-bit word的高位语义由软件约定，比对必须在word级而非字节级。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_004`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
