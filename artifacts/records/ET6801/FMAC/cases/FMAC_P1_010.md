# FMAC_P1_010 — FMAC 输出Offset与负值状态测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_025、FMAC_F_026；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；2026-08-25根因分析时期的历史失败已按"正值恢复事务解除实时负值条件后再W1C清除"整改闭环（整改结论见该分析），本文件不复述参数级细节。方法要点：仅使用无歧义正向Offset code 0x0800（完整signed/高位扩展解释未闭合）；Output Mode固定SATURATE_16、Shift固定NONE；负值子实例基础输出-0x1000、Offset后期望-0x0800，触发STATUS.NEGATIVE_AFTER_OFFSET=1后，停止事务并重建相同配置与单抽头数据路径，提交正稳态输入撤销Offset后负值的实时硬件条件（恢复事务完整收发），再执行公共clear确认状态回0；非负子实例基础输出0x0400、Offset后期望0x0C00，状态保持0。

## 复测要点与判断边界

- 判定：两类子实例DATA.OUTPUT_STREAM逐元素等于独立Offset Expected；负值实例置位、正稳态恢复事务完成后清除回0、非负实例保持0。
- 全程SATURATE_16和Shift NONE（RAW模式不消费Offset）；offset参数不依赖未闭合的高位/符号扩展解释。
- 公共Gap `output_offset_full_domain_semantics_gap`：Offset完整域语义未闭合，本Case只覆盖无歧义范围。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_010`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
