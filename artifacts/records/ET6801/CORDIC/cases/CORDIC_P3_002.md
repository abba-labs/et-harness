# CORDIC_P3_002 — CORDIC目标侧单次执行周期表征测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：性能矩阵覆盖代表单输入单结果、单输入双结果、双输入双结果函数并区分FIXED/FLOAT32配置；计时来源只允许目标侧独立cycle counter或等价硬件Observer（ET6801为CORDIC Test Extension在目标侧DWT边界内返回cycle count，timed命令经公共Service交付，PC wall-clock禁止作为周期结论）。执行：确认TIMING.CYCLE_COUNT Observer可用且测量开销处理方法已冻结→选择函数/格式/输入并生成独立Golden→目标侧读取start_cycle后执行恰好一个CORDIC原子事务→结果可读后取得end_cycle计算delta并保留Raw结果→先解码Actual与Golden比较，功能错误节点不得进入性能统计→每节点重复固定次数记录原始cycle samples→报告min/median/max等冻结统计量。

## 复测要点与判断边界

- 判定：只有数学结果满足accuracy budget的样本进入性能统计；各计划节点达到规定重复次数并保留Raw cycle samples；所有cycles来自目标侧独立周期Observer；无冻结性能阈值时只发布表征值，不把"更快/更慢"判为硬件PASS/FAIL。
- 表征不达标判定：当前无权威绝对阈值（cordic_accuracy_budget_gap保持OPEN），本Case结论只含分布统计，不含性能合格声明。
- 计时事务必须恰好一个CORDIC原子事务：循环内多事务、缓存干扰未处理都会使cycle delta不可追溯。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P3_002`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
