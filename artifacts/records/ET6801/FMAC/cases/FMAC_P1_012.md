# FMAC_P1_012 — FMAC 十一源IRQ控制Force与投递矩阵测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：遍历11个公共Source，逐源执行Disable、Enable、Mask、Unmask、Force和Clear完整序列；每个Source开始前记录irq_delivery_count基线作投递Measurement——Disable后Force：IRQ_RAW=1而IRQ_STATUS=0且投递不增加（Disable抑制有效IRQ）；Enable+Unmask后Force：Raw/Status均为1、IRQ_DELIVERY.LATCHED_SOURCE=当前Source且投递相对基线恰增加一次；Mask后Force：Raw=1、Status=0（Mask不吞Raw事件事实）；精确Clear当前Source后其Raw/Status归零且未刺激Source保持0。11/11全部满足后才PASS。

## 复测要点与判断边界

- 判定：Source覆盖完整性（11/11完整控制序列）；投递Measurement正确性（Disable/Mask阶段不增加、Enable+Unmask恰增一次）；Clear隔离性（未选Source保持0）。
- 等待投递使用有界窗口与delivery-count Measurement，不得只靠固定sleep。
- 清理按IRQ_CLEAR→DISABLE→UNMASK→STOP并CLEAR FMAC逆序恢复。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_012`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
