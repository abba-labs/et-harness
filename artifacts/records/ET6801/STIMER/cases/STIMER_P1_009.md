# STIMER_P1_009 — STIMER Overflow历史状态read-to-clear测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：确认目标实例提供Period、Runtime Status与自然Overflow IRQ能力；停止STIMER并单次读取Runtime Status——这次读取本身消费（清掉）前序轮遗留的read-to-clear诊断现场；配置短周期One-Shot、清零计数并建立Overflow IRQ投递；周期完成后先取Raw/Status取证再消费状态，验证"读即清"语义与历史现场隔离。

## 复测要点与判断边界

- 判定：新Overflow事件的Raw/Status正确置位；读取后状态归零（read-to-clear）；本Case读取不会误消费前序Case遗留现场之外的新事件。
- read-to-clear寄存器的读取就是消费动作——取证读与清理读必须区分时点，"先取证后清理"顺序错会丢证据。
- 基线读取（消费历史现场）本身要记录，作为本轮无历史污染的证据。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_009`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
