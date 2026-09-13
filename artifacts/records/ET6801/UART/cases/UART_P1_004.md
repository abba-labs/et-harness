# UART_P1_004 — UART RX FIFO 阈值中断边界测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：按1/4/8/14四个RX阈值逐一测试；每个阈值先做threshold-1字节的负对照（有界窗口内确认RX_READY未形成阈值事件），完成数据收取与清理后重建独立IRQ基线，再发送恰好threshold字节的正对照并等待Capture/IRQ事实形成。

## 复测要点与判断边界

- 判定：四个阈值全部执行；每个threshold-1负对照不产生对应阈值事件；每个threshold正对照产生RX_READY事件。
- 负对照与正对照必须分别建立独立IRQ基线，共用基线会把两次激励混在一起；负对照观察窗口必须有界。
- 阈值字节数是"恰好等于"，多一字节少一字节都失去边界语义。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_004`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
