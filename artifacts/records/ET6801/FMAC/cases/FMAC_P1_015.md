# FMAC_P1_015 — FMAC P/PQ/Q参数错误自然IRQ测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `60187638-d43b-41ac-9179-66cccfbe0b57`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；2026-08-25根因分析时期的历史失败已整改闭环（该分析D/E组根因，整改结论见该分析），本文件不复述参数级细节。方法要点：P、PQ、Q三个Source独立子实例，各用仅超出对应容量1项的最小非法参数——Spec方法为FIR布局X1=16以P=17启动（P Error）、IIR布局X2=8以P=5/Q=4启动（PQ Error）、IIR布局X2=8/Y=4以P=1/Q=5启动（Q Error）；每子实例先Stop/Clear提交合法布局并只Enable/Unmask当前Source；采集IRQ_RAW的P/PQ/Q三位（截取后必须精确等于当前Source bit）、IRQ_STATUS与LATCHED_SOURCE并记录delivery count；随后Stop/Clear提交合法参数使电平错误条件消失，再精确Clear当前Source确认Raw/Status归零。

## 复测要点与判断边界

- 判定：每个子实例截取后的参数错误Raw Mask精确等于当前Source bit；合法对照不产生对应Raw/Status且delivery count不增加；Delivery Source与当前Source一致。
- X1/Y请求等无关Raw位不参与本Case判定（`parameter_error_stimulus`公共gap约定）。
- 错误刺激、IRQ观测和合法恢复使用统一有界deadline；清理恢复三个Source的Enable/Mask状态。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_015`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
