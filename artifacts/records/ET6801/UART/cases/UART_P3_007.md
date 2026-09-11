# UART_P3_007 — UART Shadow FIFO 配置（SFE/SRT/STET）测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮（2026-08-05独立HIL、2026-08-13、2026-08-28全量）本Case均PASS。08-05独立HIL留有明确实测记录：CPR读数`0x13DF2`确认SHADOW能力存在；调用`shadow_fifo_config(enable,2,4)`后目标侧typed readback为enabled=True、TX阈值2、RX阈值4（分别记录为UART_SHADOW.ENABLED/TX_THRESHOLD/RX_THRESHOLD Observation）；`shadow_fifo_config(disable,0,1)`恢复读回enabled=False、TX=0、RX=1；恢复后4字节loopback完整一致。

## 复测要点与判断边界

- 判定：SHADOW runtime feature存在（Gate+读数双重确认）；enable读回True/2/4；disable读回enabled=False。
- 读回值必须来自目标侧typed readback，不能回显请求参数；enable/disable两个方向都要取证。
- 本Case只证单板单次配置与恢复，不含长稳、跨实例和异常复位覆盖（0805报告原文边界）。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P3_007`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)。实测值证据：[P2-010与P3-007独立HIL](../../../../../report/validation/dut/20260805_uart_split_cases_hil.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。

- 2026-09-09 10:13 CST：从0805报告与三轮全量运行状态提炼方法与实测记录；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
