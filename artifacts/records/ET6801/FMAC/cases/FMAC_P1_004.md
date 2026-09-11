# FMAC_P1_004 — FMAC 流式Chunk连续性测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：one-shot与Chunk会话使用完全相同的12项非重复Q15输入、2的幂系数与配置；先在Clean baseline中对完整12项输入执行one-shot FIR保存原始参考序列；Stop/Clear后重新提交同一配置Start同一FIR，按[1,3,2,6]和[4,4,4]两种固定切分逐块有界STREAM_WRITE，每块完整接受后再写下一块，写入后统一有界轮询读取对应数量并按序拼接；非重复输入使丢样、重复或乱序可直接暴露。

## 复测要点与判断边界

- 判定：两种切分的拼接输出均12/12逐元素等于one-shot参考序列；每块和累计接受/读取数量精确匹配计划；Chunk边界不导致无因停止或滤波状态重置（会话中ACTIVE=1，显式Stop后=0）。
- 每块必须完整接受后才进入下一块；每Chunk独立有界且受Case顶层deadline约束。
- 不假设Chunk边界处输出可提前到达，按计划数量逐块读取。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_004`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
