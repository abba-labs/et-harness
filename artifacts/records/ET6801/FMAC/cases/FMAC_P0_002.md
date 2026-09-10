# FMAC_P0_002 — FMAC Q15 IIR独立参考测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_011、FMAC_F_012、FMAC_F_014、FMAC_F_015；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：使用平台固化的IIR确定向量（7项Ladder前馈系数+6阶Reflection反馈系数+32项输入+6项X1/Y零初态）；显式Stop/Clear后提交X1=32、X2=16、Y=32互不重叠布局，按公共语义向X2装两段系数、向Y和X1装与Oracle一致的零初态；PC按Q15 Direct Form 1独立计算Oracle（累加统一右移15位并饱和），不调用DUT Driver计算Expected；32项硬件输出逐元素严格比较。

## 复测要点与判断边界

- 判定：32项输出逐元素等于bit-exact Golden；accepted_count=read_count=32；Disable后STATUS.ACTIVE=0。
- 不使用Tolerance、不搜索偏移；IIR语义固定为Q15 Direct Form 1，历史Lattice参考只作来源处置记录。
- 向量来源与目标适配证据记录在芯片事实文档，不在公共Case内重复解释。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P0_002`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
