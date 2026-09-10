# FMAC_P1_011 — FMAC 输出Shift全合法编码测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_027；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：从Capability读取全部公开Shift逻辑选项（LEFT_8..LEFT_1、NONE、RIGHT_1..RIGHT_7共16个）逐一执行；使用基础输出+0x0020和-0x0020的两组恒定历史/输入（左移8位仍不越界，并覆盖负数右移符号保持），Output Mode固定SATURATE_16且Offset=0；NONE基线先行，之后每个参数实例CLEAR并重建同一baseline和相同历史后只改变当前Shift选项，运行同一稳态短事务，按有符号移位规则独立计算Expected并逐编码比较，16/16全部通过后才PASS。

## 复测要点与判断边界

- 判定：16/16公开选项逐元素匹配各自独立Expected；NONE不引入额外移位；全程SATURATE_16且Offset=0。
- 移位Expected由独立模型按有符号移位规则生成，不调用DUT Driver计算。
- 每个Shift参数实例使用有界deadline；记录逻辑Shift名称便于定位。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_011`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
