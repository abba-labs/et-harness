# FMAC_P1_014 — FMAC 自然运算与Buffer边界IRQ测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：三类自然事件独立子实例、每实例只Enable/Unmask当前Source并记录投递基线——Saturation用16抽头0x7FFF远越界向量与最终Wrap策略（只判状态与IRQ因果链，不对未闭合量化策略下的输出值作Oracle）；X1 Overflow先装满200项Buffer再启动单抽头FIR并补偿其启动消费，随后额外直写（第1项补空位、第2项无空间触发）；Y Underflow先形成并读完4项真实FIR输出后在容量+1的严格上界内继续读取触发。每子实例验证STATUS→IRQ_RAW→IRQ_STATUS→Delivery因果链，完整IRQ Raw/Status Source Mask精确等于当前Source bit。

## 复测要点与判断边界

- 判定：三类事件先形成对应硬件状态，再有完整Raw/Status Mask与正确Delivery Source及预期新增投递；未刺激Source不产生Raw/Status或新增投递。
- 逐源Clear后分别确认目标Raw和Status归零，恢复正常Buffer操作且无残留错误/IRQ。
- 每个自然事件子实例使用独立有界deadline。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_014`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
