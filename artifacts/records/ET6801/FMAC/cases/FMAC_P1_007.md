# FMAC_P1_007 — FMAC 内部Clip与Saturation状态测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：使用16项0x7FFF系数、16项0x7FFF X1历史和16项0x7FFF持续输入，使内部s(26,22)累加范围发生确定性正向越界；保持RAW输出、Offset=0、Shift=NONE、DMA Gate关闭，最终输出策略固定Wrap以免掩盖内部Clip差异；同一越界刺激分别以CLIPEN=0（Wrap）和CLIPEN=1（Clip）各重复两轮，固定比较最后4个稳态输出——两组各自跨轮完全一致且Wrap与Clip稳态尾段不同；单项0x4000系数×0x2000输入正常对照两策略相同且Saturation不置位；CLEAR后Saturation归零。

## 复测要点与判断边界

- 判定：相同刺激只改CLIPEN后Wrap与Clip稳态尾段必须不同且各自重复运行一致；STATUS.ACCUMULATOR_SATURATION越界=1、正常=0、Clear后=0。
- 越界必须发生在内部累加器，与最终输出Saturate/Wrap策略隔离证明。
- Clear后确认恢复清洁基线且正常路径可继续。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_007`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
