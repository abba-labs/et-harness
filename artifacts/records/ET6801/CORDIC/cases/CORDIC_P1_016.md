# CORDIC_P1_016 — CORDIC第二参数错误状态、自然IRQ与恢复测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：错误刺激为"先提交PHASE_MODULUS的x，再向另一数学函数入口提交参数"自然触发PM_ARG2_ERROR，不使用Force；一次刺激同时证明错误状态、自然IRQ投递与恢复（同一硬件状态不重复触发）。执行：Clear PM_ARG2_ERROR状态/IRQ并记录event_count起点→Enable并Unmask启动IRQ会话→向PM提交x确认进入等待第二参数阶段→向另一函数入口注入参数制造已审核顺序错误→等待event_count增加后读取STATUS.PM_ARG2_ERROR、IRQ_RAW/STATUS与Service latch→Clear错误状态和IRQ Raw确认W1C报告位立即归零→经CRG专属Driver复位当前CORDIC实例并重新提交完整配置（ET6801 FPGA实测表明清报告位后仍需CRG复位才能清内部错误事务）→复位后执行x→y正常事务验证phase/modulus结果正确。

## 复测要点与判断边界

- 判定：x→其他函数参数序列产生PM_ARG2_ERROR真实投递（event_count增加、latch含PM_ARG2_ERROR）；状态、IRQ、Service指向同一Source；W1C报告位与Raw归零；外层模块复位后合法PM事务不再出错且数学结果正确。
- 恢复必须走模块复位：只W1C清报告位不足以恢复内部错误事务，跳过CRG复位会导致恢复判据假绿。
- 错误状态是一次性不可重复刺激：状态/投递/恢复合并进一次事务取证，不得为凑证据反复触发同一错误现场。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_016`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
