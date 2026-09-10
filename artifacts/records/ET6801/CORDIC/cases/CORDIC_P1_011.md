# CORDIC_P1_011 — CORDIC参数数量溢出状态与恢复测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_029；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：溢出刺激使用Chip Execution Mapping冻结且已由current FPGATest/HIL证明的确定性未消费提交次数（该次数只作可复现刺激，不解释为硬件最小容量）；另备一个合法正常事务与独立Golden用于恢复证明。执行：清除ARG_OVERFLOW并确认STATUS.ARG_OVERFLOW=0→先完成并消费一个合法事务确认正常基线→按映射次数连续提交未消费请求自然触发ARG_OVERFLOW→在任何Clear前读取STATUS.ARG_OVERFLOW期望=1并记录提交次数→Clear后复读期望=0→重新建立正常配置执行合法恢复事务读取RESULT.PRIMARY→Actual与独立Golden比较确认错误路径未造成不可恢复状态。ET6801观测STATUS_RPT.WR_NARGS_OVF_RPT（bit0，sticky W1C）。

## 复测要点与判断边界

- 判定：正常基线可完成，随后已审核的未消费提交序列自然产生ARG_OVERFLOW；Clear前=1、Clear后=0；错误清除后合法事务结果满足独立Golden。
- 不声称测得最小容量：四次未消费提交是"已审核可复现刺激"，不等于硬件容量下界；精确容量仍属cordic_argument_capacity_mapping_gap。
- 判定顺序是红线：必须先取证溢出状态（Clear前=1）再做显式清除；跳过前置取证直接清除会让整个因果链不可证明。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_011`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
