# FMAC_P1_001 — FMAC X1/X2/Y区域布局矩阵测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_001、FMAC_F_005、FMAC_F_006；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：由Capability的逻辑地址上限、各区域最小容量和非重叠约束确定性生成layout_min、layout_shifted、layout_end_boundary三布局（最小连续、整体右移一个逻辑单元、Y结束贴合地址上限）；每组布局提交X1/X2/Y起始与容量后调用config_snapshot_get读回六个CONFIG端点，并以probe_count=min(2, X1容量, Y容量)（且大于0）装载递增Q15样本，验证X1_SPARE_COUNT、Y_UNREAD_COUNT与Y读回序列。

## 复测要点与判断边界

- 判定：六个CONFIG端点均等于当前合法布局参数；X1 Spare和Y Unread符合当前布局下的状态模型；Y装载/读取序列保持元素数量和顺序。
- 仅选择Capability声明合法的布局实例；结构化证据按字段名和值转换，不把PC语言对象直接写入Canonical Result。
- 每个布局实例使用独立有界deadline。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_001`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
