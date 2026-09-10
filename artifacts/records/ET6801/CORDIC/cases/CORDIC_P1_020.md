# CORDIC_P1_020 — CORDIC多函数连续请求与结果对应测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_043；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：构造至少四种函数的确定性输入序列（含单结果与双结果事务），为每个request_id生成独立Golden；使用能够连续提交/消费的已审核工作模式，不假设未被硬件资料承诺的无限队列深度。执行：生成request_id/function_id/logical_input与Expected列表→设置稳定数值模式、结果数量与高精度节点→按已审核硬件容量/消费协议提交首批不同函数请求→按硬件结果消费协议读取RESULT.PRIMARY/SECONDARY并为每次Raw结果绑定request_id→消费产生空间后推进剩余请求（禁止越过未声明容量）→每个Raw结果按对应function codec解码并与该request_id Golden比较→检查全部request_id恰好消费一次、无重复/丢失/上一请求残留。来源为FPGATest case34的多函数连续提交/消费设计线索，但其读取顺序不被当作无限队列规格。

## 复测要点与判断边界

- 判定：全部计划request_id恰好产生一次结果集合；每个Actual满足本request_id独立Golden（不能用相邻请求Golden通过）；无重复消费、丢结果或跨函数残留；不产生ARG_OVERFLOW或PM_ARG2_ERROR。
- 结果绑定request_id是核心动作：只比对"算对了"不比对"归属对"，错配类缺陷会漏检；未声明容量前不批量提交。
- 队列容量未冻结前只按已审核消费协议推进（cordic_request_capacity_mapping_gap保持OPEN）；历史"parallel"测试代码不构成规格。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_020`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
