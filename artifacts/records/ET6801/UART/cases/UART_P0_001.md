# UART_P0_001 — 选定 UART 实例的运行时能力和身份信息测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行（2026-08-10全量HIL、2026-08-13 GUI Pipeline HIL、2026-08-28 UART全量）本Case均PASS，无FAIL记录。方法双链取证：先读Runtime Capability（Feature mask、最小/最大波特率、最大读写长度）并确认范围自洽、实例可由UART Service访问；再用代表波特率初始化后读取UART_COMPONENT Snapshot的component parameter/version/peripheral id/scratch，原始值先入Canonical Observation再判定。

## 复测要点与判断边界

- 判定：MIN_BAUDRATE>0且≤MAX_BAUDRATE；MAX_READ_SIZE/MAX_WRITE_SIZE均>0；三个身份字段取得稳定目标侧值。
- Scratch只证读值，不把单次读取冒充F043 Scratch写证明；F003普通/别名地址动态访问不在本Case扩大证明。
- 身份Expected必须来自目标侧Snapshot，不能回显请求；保持先取证后Assert顺序。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P0_001`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
