# UART_P1_005 — UART TX FIFO 阈值中断边界测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：0/2/4/8四个TX阈值；配置TX Halt后向FIFO写入受控短Payload并读取UART_FIFO.TX_LEVEL建立阈值前in-flight状态；在Halt窗口读取IRQ session确认当前状态不会被发送完成自然事件混淆；解除Halt让同一FIFO数据继续发送并等待Capture完成。

## 复测要点与判断边界

- 判定：四个阈值均形成可审计的in-flight/终态证据或明确报告Gap；TX_READY事件只在解除Halt后的真实发送链路中判定；全部实际数据一致且fault增量为0。
- 本Case与P1_004的核心差异：TX阈值事件容易被"发送完成"自然事件混淆，Halt窗口取证是排除混淆的关键，不能省略。
- in-flight证据靠TX_LEVEL读数，不能只看最终结果。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_005`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
