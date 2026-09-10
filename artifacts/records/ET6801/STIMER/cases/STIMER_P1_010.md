# STIMER_P1_010 — STIMER Compare重复事件诊断测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：确认Compare、Free-Run、事件脉宽、IRQ控制与原子Runtime Status读取均已映射；停止STIMER并单次读取Runtime Status消费前序read-to-clear诊断现场；设置短Free-Run周期、目标Compare门限和长于周期的事件脉宽；连续多个周期内验证Compare事件按周期重复产生且每次都被投递链捕获，event_count按周期数递增。

## 复测要点与判断边界

- 判定：Free-Run下Compare事件每周期重复触发且event_count单调递增（无丢事件）；脉宽长于周期时不产生事件合并或丢失；原子读取无撕裂。
- 与P1_006的差异：那是单次门限越界取证，本Case是重复事件连续性诊断——event_count的增量速率与周期频率的对应关系是核心。
- 长脉宽配置是刻意制造的边界（事件仍在拉高时下一周期到来），验证不丢事件。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_010`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
