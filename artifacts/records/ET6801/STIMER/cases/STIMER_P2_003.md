# STIMER_P2_003 — STIMER CPU Debug Halt暂停与自由运行测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 已确认现象

2026-08-28全量与2026-09-03专项复测两轮一致FAIL。两种策略（PAUSE/RUN_FREE）每组前后DHCSR均为`0x00030003`、S_HALT(bit17)=1（CPU确实停核）；但PAUSE策略时STM_SET=`0x00000003`、CNT_RPT由`0x013F16A9`增至`0x018F5043`（增量5,257,626），RUN_FREE时STM_SET=`0x00000083`、CNT_RPT由`0x00607D81`增至`0x018F5043`（增量5,131,614）——**PAUSE策略下计数未停**，与预期"停核时暂停计数"不符。已排除两个候选根因：CPU未停核（DHCSR证明停了）、PAUSE配置未写入（STM_SET回读证明写了）。当前FPGA的PAUSE行为不符合预期；Halt信号具体路径、时钟域与多核关联仍需设计人员确认，未证明具体RTL根因。

## 判断边界与复测条件

- 方法可复用：复位目标STIMER及Resource Pool→配置长period Free-Run与PAUSE策略后START（避免观测期自然Overflow）→Debugger Halt CPU并确认CPU.DEBUG.HALT_STATUS→停核内读取COUNT.LIVE与DEBUG_HALT.CONFIG→恢复对比RUN_FREE策略。停核后不等待固件串口响应（停核时串口不会回话）。
- 复测条件：设计人员确认当前FPGA目标CPU Halt与STIMER的关联后复测；Silicon需独立验证（FPGA Halt路由结论不外推到Silicon）。
- 不得把RUN_FREE的计数增长当成PAUSE路径证据，两策略分开判定。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P2_003`；芯片适配与观测值出处见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)状态块。历史结果与证据缺失声明见[历史来源与版本](../README.md)。

- 2026-09-09 11:45 CST：从状态块、0903专项session与公共契约提炼FAIL现象、已排除根因与复测条件；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
