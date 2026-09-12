# STIMER_P1_004 — STIMER Immediate与Shadow周期加载时机测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `b51bcdf9-7f4f-46ca-9f4b-c713fb2f1b15`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：装载old_period并启动，等COUNT.LIVE到达中段后写new_period；Immediate模式等待COUNT.LIVE越过old_period，确认此时Overflow Event Count没有增加（当前周期未被中途篡改）；继续等新周期Overflow确认new_period已作用于当前周期；Shadow模式对照验证加载时机语义差异。

## 复测要点与判断边界

- 判定：Immediate写入对当前周期立即生效（越过old_period时无提前Overflow）；Shadow写入在下一周期边界生效；两种模式语义按定义区分。
- "越过old_period时Overflow Count不增加"是Immediate语义的关键负向证据——Shadow模式同一时点应有不同的计数表现，对照才成立。
- 写入时机要在周期中段（过早早写、过晚接近边界都会让判定模糊）。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_004`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
