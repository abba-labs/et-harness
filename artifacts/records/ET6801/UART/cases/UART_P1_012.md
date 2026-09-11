# UART_P1_012 — UART busy detect 中断、清除条件和恢复路径测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

三轮运行（2026-08-10、2026-08-13、2026-08-28）本Case均被正式门禁判定SKIP：FIFO开启持续发送期间修改LCR，Driver有界触发窗口内未形成确定性Busy Detect中断。Case方法本身已为取证设计好：通过隔离Test Driver的busy_detect_trigger接口完成trigger/observe/clear/recovery序列，取PRE_TRIGGER_USR、OBSERVED_IIR、OBSERVED_USR、trigger_count等字段，三个raw硬件字段分别记UART_BUSY.* Observation。

## 判断边界与复测条件

- 有刺激时判定为：trigger_count=1；raw USR/IIR事实支持busy与interrupt语义；clear/recovery派生判断为真。
- SKIP原因：Busy Detect的硬件触发时序（发送中途写LCR的相位窗口）在当前刺激下无法确定性命中；现有结果不足以判定Feature PASS或FAIL，三轮一致SKIP且无FAIL记录。
- 复测条件：取得ET6801 Busy Detect准确触发时序，或使用可控制发送与LCR写入相位的刺激。不放宽触发窗口超时硬凑结果。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_012`；芯片适配与SKIP归因见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`blocked_by_runtime: current UART did not form a deterministic Busy Detect conditi`。与既有不确定触发窗口一致。
