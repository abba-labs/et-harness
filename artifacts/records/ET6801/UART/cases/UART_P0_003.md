# UART_P0_003 — UART 内部回环的基本发送、接收和回环开关测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `1e7bf0dc-1d5d-4f47-b1e2-a3f41a483fa0`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：115200 8N1初始化并建立loopback/capture清理责任；按1/16/17/64 Byte顺序构造不同seed的确定性Payload；每轮先开启内部loopback并启动等长Capture，再调用有界UART write发送并等待Capture完成。四条长度路径覆盖了FIFO阈值两侧（17字节跨16深度边界）的基本数据路径。

## 复测要点与判断边界

- 判定：四条路径全部执行（覆盖判据）；每轮发送/接收长度完整；每轮实际数据与Expected逐字节一致。
- 17/32等跨FIFO深度边界的长度不能换成任意值，否则丢失边界覆盖语义。
- 回环enable/disable语义体现在每轮建立与清理中；发送必须有界等待（F_018），不依赖无限轮询。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P0_003`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
