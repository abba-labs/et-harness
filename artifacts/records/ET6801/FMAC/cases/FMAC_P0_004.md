# FMAC_P0_004 — FMAC Enable/Disable与活动状态测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_051；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：使用Capability给出的最小合法X1/X2/Y布局、Q15 FIR、P=1并经同一次coefficients_load装载单个前馈系数0x4000；初始化类动作完成后STATUS.ACTIVE由硬件自动回0；不向X1写数据直接start，等待输入期间ACTIVE=1并保持（证明活动态不会无因退出）；stop后ACTIVE回0；不做系统复位再次start确认可重新Enable，clear后ACTIVE回0。

## 复测要点与判断边界

- 判定：运行类功能Enable后ACTIVE在有界窗口内变为1并保持到显式Disable；显式Disable后变为0且允许再次Enable；X2单系数装载（初始化类）完成后ACTIVE=0。
- 全程有界轮询观测ACTIVE转换，禁止固定sleep作为唯一判据。
- 空闲基线先读ACTIVE=0，保证从已知idle状态开始。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P0_004`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
