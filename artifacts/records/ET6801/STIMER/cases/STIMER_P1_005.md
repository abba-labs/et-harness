# STIMER_P1_005 — STIMER实时计数与重复锁存快照测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：配置并START确认COUNT.LIVE推进；执行COUNT_LATCH后读COUNT.LATCHED保存latched_1；不再次Latch连续读COUNT.LATCHED，期望保持latched_1不变（锁存稳定性）；再次Latch后确认新值反映最新计数；与LIVE读数交叉验证锁存时点。

## 复测要点与判断边界

- 判定：LATCHED在不重复Latch时保持不变（快照语义）；重复Latch取新值；LIVE持续推进与LATCHED冻结并存。
- "连续读保持不变"证明的是锁存快照而非实时值——若两次读数不同，说明读的是LIVE或锁存被意外刷新。
- 锁存与读取的先后顺序不能颠倒，先Latch后读才有时点语义。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_005`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
