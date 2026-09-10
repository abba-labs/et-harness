# CORDIC_P1_013 — CORDIC浮点转定点溢出/下溢状态测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_032、CORDIC_F_033；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：仅使用Chip Execution Mapping已审核的OVF、UDF和合法恢复向量（ET6801冻结SQRT确定性OVF/UDF刺激与恢复向量）；这些向量不被解释为精确硬件阈值。执行：Clear FLOAT2FIXED.OVERFLOW/UNDERFLOW并确认两状态均为0→提交已审核OVF向量，有界等待相关状态出现→Clear前原子读取OVERFLOW与UNDERFLOW两状态确认仅目标语义生效→清理后提交UDF向量同样记录→分别Clear目标状态并复读，确认对应bit归0且另一bit不被误改→执行恢复向量确认普通计算路径恢复。ET6801观测RPT_CORDIC_FLOAT2FIXED的OVF（bit1）/UDF（bit0），sticky W1C。

## 复测要点与判断边界

- 判定：OVF与UDF刺激分别只触发对应已声明状态（异常可区分）；目标状态Clear后归零且不误清另一状态；异常路径结束后合法运算可再次完成。
- 向量≠阈值：冻结向量只证明状态因果路径，精确OVF/UDF阈值与所有适用函数仍属cordic_float2fixed_boundary_gap，不得宣称边界测全。
- 双状态必须原子快照：每种刺激同时读取另一状态作隔离对照，事后补读无法证明"未误触发"。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_013`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
