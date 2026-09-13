# UART_P1_003 — UART TX empty 中断在发送完成阶段的触发和关闭测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：初始化DUT并读取TX_READY使能前IRQ session基线；使能TX_READY并开启内部loopback；启动8 Byte Capture后发送确定性Payload；等待Capture完成并读取发送完成阶段IRQ session状态。

## 复测要点与判断边界

- 判定：数据完整一致；TX_READY event_count_delta>0；fault_count_delta=0。
- TX_READY事件必须在真实发送完成链路中判定；复测时要确认事件窗口对应的是本轮发送，而不是上一轮残留事件。
- 关闭语义在P1_011统一取证（关闭后enabled mask归零），本Case聚焦触发阶段。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_003`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
