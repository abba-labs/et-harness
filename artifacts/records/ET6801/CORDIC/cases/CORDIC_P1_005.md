# CORDIC_P1_005 — CORDIC双结果数量选择测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：对SINCOS、PHASE_MODULUS、HSINCOS三类双结果函数分别执行ONE_RESULT与TWO_RESULTS选项（ET6801由CTRL0的SINCOS_NRES/PM_NRES/HSINCOS_NRES位承载，0=单结果消费/1=两结果均读取），输入使用可区分两个结果的确定性向量；每类函数两个逻辑Expected均由PC独立数学Oracle生成。执行：配置当前函数result_count与稳定数据格式/精度→提交完整事务并有界等待→按当前result_count只读取合同声明应消费的结果端点并保留Raw→ONE_RESULT只判断声明结果、TWO_RESULTS分别比较两个Decoded Actual与Golden→汇总确认三类函数两种选项均可重复进入，不对未声明结果端点编造有效性判据。

## 复测要点与判断边界

- 判定：三类双结果函数的计划result_count选项全部执行；所有实际消费的结果端点满足对应独立Golden与accuracy budget；ONE_RESULT节点不因报告方便而要求硬件提供未声明第二结果。
- 只读声明端点：未声明结果不作判据，也不虚构"第二个结果存在"的结论；单/双结果配置切换后须可重复进入下一事务。
- 与P1_002分工：本Case只测结果数量选择语义；16-bit打包与参数存储位置归P1_002，不在这里重复判定。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_005`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
