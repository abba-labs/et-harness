# FMAC_P3_001 — FMAC 确定性长流FIR稳定性测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_013、FMAC_F_016；资源等级 R0（无外部接线，要求稳定目标供电/时钟）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：固定[0x4000,0x2000,0x1000,0x0800]四抽头与0x2000恒定Q15输入，总样本4096，Chunk长度固定轮换31、47、64；输入/输出各一个64项Buffer，每Chunk完成后立即回传PC并复用同一Buffer，不让完整长流同时驻留目标资源池；建立Known Baseline装载系数与等长零X1历史后Enable，逐Chunk覆写同一输入Buffer按固定切分有界WRITE/READ；跳过全流前4项启动区后从第5项起每项Expected固定0x1E00（稳态Golden不依赖首输出对齐搜索），在线比较并保存首个Mismatch原始Chunk与全局索引；按里程碑读STATUS.ACTIVE；结束后Disable并核对累计数量与output_digest Measurement；重建Clean baseline再跑1轮比较两轮digest。

## 复测要点与判断边界

- 判定：每轮4092项稳态输出全部等于0x1E00；累计输入/输出均4096无丢样、重复或乱序；两轮output_digest一致且无跨轮状态泄漏；整个声明时段无无界等待或不可恢复错误。
- 总运行时段由Run Config声明，每个目标动作仍有独立有界deadline。
- 首个Mismatch保留原始硬件Chunk证据，不在知识文件中复述具体输出值。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P3_001`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
