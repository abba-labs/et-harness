# FMAC_P3_003 — FMAC DMA路径周期性能表征

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_031、FMAC_F_032、FMAC_F_013；资源等级 R2（DUT片内FMAC、DMA、内存与目标周期源）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：从目标Profile解析双向Execution Mapping，使用240项0x2000固定输入和四抽头稳态FIR；资格门禁确认双向Mapping、16-bit传输宽度、FMAC X1/Y Watermark=1以及DMA target-local timing API可用；按0.5建立FMAC Known Baseline、装载系数与等长零X1历史、清DMA并执行定义次数预热；FMAC保持idle时配置两条DMA Channel并设置目标Watermark和双向Request Gate；先启动输出DMA计时，再启动输入DMA和FMAC，两Channel完成后读取目标侧elapsed cycles；功能校验要求两Channel无ERROR回到Free、传输数量一致且DMA目的序列最后4项均为0x1E00；失败或Evidence不完整样本不进入性能聚合。

## 复测要点与判断边界

- 判定：周期必须来自目标Observer，禁止PC wall-clock或历史magic correction；双向DMA终态无ERROR并回到Free且目的数据Golden通过；保存240项事务的原始cycles、两个Channel终态和功能结果。
- `timing_observer_gap`已由CPU/DMA目标周期接口采样闭环（芯片文档）；与P2_001共享逆序清理约定。
- 每DMA性能样本有界，FMAC和DMA共享Case deadline。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P3_003`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
