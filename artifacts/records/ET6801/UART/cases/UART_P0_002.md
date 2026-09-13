# UART_P0_002 — UART 软件复位、默认配置和实例生命周期测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法核心是"复位前制造可观察的自定义状态"：先以7 data bits/even parity/2 stop bits初始化并读复位前组件Snapshot，执行software_reset结束旧实例生命周期，再显式以115200 8N1重新初始化（是显式重配，不是读取硬件reset默认值），比较复位前后身份并读取TX/RX FIFO level，最后做1字节数据恢复验证。

## 复测要点与判断边界

- 判定：软件复位前后组件身份稳定；重新初始化后TX/RX FIFO level均为0；恢复收发长度1且数据一致。
- 复位后配置是显式重设，不能写成"读到了硬件默认值"；FIFO归零只佐证F014复位语义，不冒充独立FIFO reset API的完整证明。
- 复位前的自定义帧配置必须真的生效（先读Snapshot留证），否则复位对比无意义。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P0_002`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
