# UART_P1_014 — UART 数据位、停止位和校验方式的合法帧格式组合测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：逐个合法帧格式组合（数据位/停止位/校验的代表组合），每组合用独立DUT/Peer生命周期初始化为相同帧格式；Payload按data_bits做有效位裁剪（如5-bit只保留低5位有效）；先启Peer Capture由DUT发送，再启DUT Capture由Peer发送，双向记录实际数据。

## 复测要点与判断边界

- 判定：五个代表性合法组合全部执行；每组合两个方向收发长度完整且逐字节一致。
- 5-bit等非整字节数据的有效位裁剪在Expected侧完成，不能拿原始字节直接比对后用掩码解释结果。
- 每组合独立生命周期：上一组合的校验位残留会让下一组合首帧失配，这不是Feature缺陷是方法污染。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_014`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
