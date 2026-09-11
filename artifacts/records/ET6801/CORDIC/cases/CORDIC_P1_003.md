# CORDIC_P1_003 — CORDIC Scale缩放语义测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS；2026-08-28定向HIL确认Scale 0..7在人工批准的ET6801 `1e-3`绝对误差预算内PASS（芯片文档状态块与[Scale7 ARCTAN金模型与缺陷分析报告](../../../../../report/analysis/20260826_cordic_scale7_arctan_golden_model_and_defects.md)记录的历史争议已按批准预算闭环）。方法要点：遍历Chip Execution Mapping声明的平台计划Scale选项（ET6801为CTRL0.SCALE 3-bit 0..7），同时选一个有直接证据的受影响函数（ARCTAN）和一个SVD明确不受影响的函数（SINCOS）；受影响函数的输入/输出Scale关系必须来自已审核Capability/Chip Adaptation，不从历史magic factor推导。执行：按已审核Scale公式构造节点Golden与Raw Expected→配置FIXED路径+当前Scale+高精度节点→提交事务有界等待→按Scale公式与Codec解码→受影响函数逐节点与独立数学Golden比较；不适用函数比较多个Scale下结果，确认Scale不改变其逻辑输出。

## 复测要点与判断边界

- 判定：Capability公开的全部计划Scale选项执行；受影响函数各节点Actual满足已审核Scale公式与accuracy budget；不受Scale影响的函数在Scale切换下Decoded结果不产生超出量化预算的逻辑变化。
- 本Case只宣称SINCOS不受Scale影响与ARCTAN Scale 0..7公式已证明；其余函数Scale公式仍属公共Gap（cordic_scale_formula_gap），不得由本Case宣称。
- 历史教训：固定单一向量遍历Scale使各档位实际工作点不同，Scale=7落入小角度量化敏感区；历史`1e-4`统一预算与实际LSB容差体系对不上。当前按人工复核批准的`1e-3`ET6801专属预算验收，不静默放宽公共容差，低迭代节点也不冒充逐节点精度包络。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_003`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块、批准的1e-3预算复核结论与缺陷分析报告提炼Scale方法要点与历史教训；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
