# SYSCNT_P3_001 — 20轮装载启停重复验证测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `7218fc2f-b90e-4480-8ba6-cff0001abb79`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：每轮配置前独占并按批准映射归一SYSCNT、Service和资源池；停止态写入该轮初值并双窗口精确读回（避免前轮残留）；使能计数约1ms后读COUNT.READ确认高于初值；停止并验证两窗口一致不再增加；重复20轮。

## 复测要点与判断边界

- 判定：完成20轮且每轮输入、运行、保持判据全部满足（提前停止不能当完成）；每轮停止装载读回等于本轮Expected，停止后两窗口一致且不再增加（无状态污染）。
- "每轮重新归一"是长稳语义的核心——复用上轮状态跑20轮测的是别的（状态残留），不是重复可靠性。
- 关联Feature覆盖了F_001/F_002/F_004的组合稳定性，是P0两条Case的20轮加固版。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P3_001`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
