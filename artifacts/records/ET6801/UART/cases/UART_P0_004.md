# UART_P0_004 — UART 逻辑 DUT 与 Peer 之间的双向基本收发测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：DUT与Peer初始化为相同帧格式；构造DUT→Peer与Peer→DUT两组不同的64 Byte确定性Payload；每方向先启动对端Capture再发送，双向各一轮。板级链路为UART1/UART2交叉短接（J25.3←J30.5、J25.5→J30.3），这是所有Peer类Case共用的物理基础。

## 复测要点与判断边界

- 判定：两个方向发送/接收长度均为64；两个方向数据逐字节一致。
- 双向都要跑：单向PASS不等于F_010全双工证明；两组Payload必须不同，防止回环假象冒充跨板收发。
- 复测前先确认交叉链路物理状态；链路松动会造成单向偶发丢字节，属环境问题不属Feature判定。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P0_004`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
