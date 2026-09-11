# STIMER_P1_006 — STIMER四通道Compare门限与来源隔离测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：选择channel/compare_ticks配置长period、合法divider并装载目标Compare门限；清除全部Compare Raw确认目标和非目标Source均为0；START后在COUNT.LIVE小于compare_ticks时读IRQ_RAW.COMPARE[n]期望为0（门限前）；越过门限后确认目标Source置位；门限对照（另一通道不同门限）验证来源隔离。

## 复测要点与判断边界

- 判定：门限前目标Source为0；越过门限后目标Source置位；非目标通道不受影响（隔离成立）；四通道逐个覆盖。
- 门限前采样必须在COUNT.LIVE<compare_ticks时点完成，事后补读无效。
- Compare与Overflow是不同Source，归因靠Source位区分（P1_010诊断重复事件时依赖此隔离）。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_006`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
