# UART_P2_007 — UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：Gate MODEM并初始化DUT，开启内部modem loopback；把RTS/DTR置低并连续读取两次Modem状态确认CTS/DSR Delta清零基线；只拉高RTS，读取一次状态和一次clear后状态，记录CTS input/output/delta/raw事实；保持RTS高再拉高DTR，同法记录DSR事实。

## 复测要点与判断边界

- 判定：初始二次读取无CTS/DSR残留Delta；RTS上升形成CTS current+delta且二次读取清零；DTR上升形成DSR current+delta且二次读取清零。
- Delta清零语义靠"读一次+clear再读一次"的固定两拍取证；跳过clear读会累积Delta让后续判定失真。
- F_034已知边界：当前Formal Case动态覆盖CTS/DSR，RI/DCD保留Gap（Feature Catalog原文），复测时不要把RI/DCD缺失当成回归失败。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_007`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
