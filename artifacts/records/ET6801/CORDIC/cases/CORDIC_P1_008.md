# CORDIC_P1_008 — CORDIC中断工作模式计算与结果测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：选择确定性数学输入与独立Golden，目标Source为CALC_COMPLETE；IRQ会话要求运行前清除目标Source、Enable且Unmask，ISR/Service提供Source级latched与event_count。执行：清目标Source并记录event_count起点→配置INTERRUPT工作模式（ET6801 CTRL0.WORK_MODE=00）→Enable并Unmask CALC_COMPLETE启动IRQ会话→提交输入并等待event_count在deadline内发生目标增量→读取IRQ_RAW.CALC_COMPLETE、IRQ_STATUS.CALC_COMPLETE与IRQ_DELIVERY.LATCHED_SOURCE→读取结果与Golden比较→Clear目标IRQ与COMPLETE确认不再pending并停止会话→寄存器Observation、Service latch、event_count Measurement分来源保存，不合并。ET6801硬件为单IRQ line，Source级ISR latch/event_count由CORDIC IRQ Service提供（INT bit1=CALC_COMPLETE）。

## 复测要点与判断边界

- 判定：event_count相对基线增加且Service latch包含CALC_COMPLETE（真实投递）；Raw/Status/Service证据都只能解释本次目标Source；IRQ模式下数学Actual仍满足独立Golden；Case结束目标IRQ与完成状态按显式清除语义恢复。
- 四类来源分层是红线：Raw（Mask前寄存器）、Status（Mask后寄存器）、Service latch、event_count不得互相冒充；event_count不写入寄存器Observation。
- 证据读取存在ISR清除时序竞争，Raw快照允许与清除时序相容的实际值，但必须保留真实快照、不得回填理想值。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_008`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
