# CORDIC_P1_001 — CORDIC正余弦输入范围模式等价性测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：选择0、典型正负角、象限边界附近及扩展范围内代表角度构成角度矩阵，每个逻辑角度分别构造NORMALIZED与DIRECT_ANGLE两种合法Raw编码；Expected直接由PC sin/cos计算，两条路径共享同一逻辑Golden。执行：先配置FIXED+归一化范围+稳定高精度节点提交并读取两路结果，再重建同等数值/精度配置仅切换到直接扩展角度范围提交；分别按各自Codec解码cos/sin Actual并记录Raw与逻辑值，双路径分别与同一sin/cos Golden比较后汇总全部角度节点。ET6801由CTRL0.DMODE（bit13，0=归一化/1=直接[-2π,+2π]）承载两种Range。

## 复测要点与判断边界

- 判定：两种输入范围模式和全部计划角度节点执行完整；两路径各自Actual满足同一Golden与对应accuracy budget；同一逻辑角度两路径Decoded差异不超过两路径预算合成上界。
- 两路径必须共享同一逻辑Golden，不能各自造Golden再互相"对齐"；只切换Range、其余配置保持同等是等价性成立的前提。
- Normalized/Direct各自的Raw Codec不同（角度除数 vs 小数位编解码），解码错误首先查Codec映射，不直接归因硬件。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_001`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
