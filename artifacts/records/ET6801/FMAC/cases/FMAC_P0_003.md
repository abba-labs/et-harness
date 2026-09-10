# FMAC_P0_003 — FMAC Clear与配置保持测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_017；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：先按0.5显式建立Known Baseline并提交X1/X2/Y容量均为4的完整配置；装载单抽头系数和零历史启动FIR产生一个真实Y输出，再在活动会话中执行Y容量+1次Unchecked Read使STATUS.Y_UNDERFLOW由0变1；执行Stop终止活动（Clear不承担活动控制职责），随后执行公共CLEAR，验证动态错误状态恢复为0而完整准静态配置快照与Clear前提交值逐字段一致。

## 复测要点与判断边界

- 判定：Clear前STATUS.Y_UNDERFLOW=1、Clear后=0；Stop后STATUS.ACTIVE=0；Clear后完整配置快照与提交配置一致。
- 活动控制由Stop独立负责，Clear只清动态指针与错误状态。
- 超量读取幅度有界（Y容量+1），异常刺激不扩大到其他区域。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P0_003`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
