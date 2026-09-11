# FMAC_P1_003 — FMAC Y水位容量状态与Underflow测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：Y容量固定4，遍历Capability发布的Y Empty Watermark矩阵；按0.5显式建立Known Baseline，装载单抽头系数与零历史后写入4项输入并暂不读取，确认STATUS.Y_UNREAD_COUNT=4；逐级读取至3、2、1、0并记录Empty（不假设FIFO读数据与状态同拍可见）；Unread=0后确认Y_EMPTY符合当前Watermark定义，再有界执行unchecked读直到Y_UNDERFLOW置位，CLEAR后归零。

## 复测要点与判断边界

- 判定：FIR输入和输出数量均为4、Unread从4降为0；Empty符合当前Watermark定义；Underflow因果为基线0→空后unchecked读1→Clear后0。
- 本Case只验证Y容量状态，不承担FIR数值Oracle；保存跨越Unread边界的原始读取次数与状态序列。
- 每个装载、读取和状态动作有界，禁止固定sleep作为唯一判据。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_003`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
