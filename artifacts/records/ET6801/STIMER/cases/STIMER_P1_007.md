# STIMER_P1_007 — STIMER IRQ控制链、Force与真实Delivery测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：清除目标IRQ Source、Enable并Unmask，记录event_count_before且确认RAW/STATUS起始为0；通过自然事件或IRQ_FORCE产生目标Source，立即记录IRQ_RAW与IRQ_STATUS；读ISR/Service latched_source与event_count_after，证明有效状态真实进入投递链。

## 复测要点与判断边界

- 判定：Enable+Unmask后事件真实投递（event_count_after>before、latched_source含目标位）；Force路径与自然事件路径都能到达投递链；RAW/STATUS分层取证。
- "立即记录"RAW/STATUS是时序敏感取证——延迟读取可能已被清掉，丢失Force瞬态证据。
- event_count用before/after差值，绝对值不构成证据。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_007`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
