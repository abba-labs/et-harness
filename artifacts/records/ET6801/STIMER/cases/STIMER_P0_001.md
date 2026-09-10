# STIMER_P0_001 — STIMER基本计数、Start/Stop与实时读数测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准（公共契约feature_refs未登记）；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：确认目标实例可用并清理历史IRQ/诊断状态后，配置代表性divider、period和FREE_RUN；启动前读COUNT.LIVE作start_before，START后有界窗口内再读作running_after确认计数推进；STOP后两次读数确认冻结；Stop/Start/实时读数语义齐备。

## 复测要点与判断边界

- 判定：START后计数推进（running_after>start_before且在合法计数范围内）；STOP后读数冻结；实时读数（LIVE）与锁存读数（LATCHED）不混用。
- 启动前必须清理历史IRQ/诊断状态，否则前轮残留事件会污染读数窗口。
- 有界窗口采样，不做无限等待。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P0_001`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
