# FMAC_P1_002 — FMAC X1水位容量状态与Overflow测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：遍历Capability发布的X1 Full Watermark矩阵，X1容量由逻辑地址空间与单次最大传输数量共同确定；先以半容量X1装载核对Spare Count（含FIR启动消费1项）；CLEAR后重装X2并预装"容量-Watermark+1"项补偿启动消费，确认Spare=Watermark且Full=0；FIR运行态直写1项，Spare减1且Full=1；再CLEAR重装并按容量装满X1启动FIR，第1次直写补回启动空位、第2次直写在无空闲空间时自然触发STATUS.X1_OVERFLOW，CLEAR后归零。

## 复测要点与判断边界

- 判定：装载半容量后Spare=容量-实际写入数量；Full在目标允许的可见窗口内匹配当前Watermark边界；Overflow因果为基线0→无空间unchecked写1→Clear后0。
- 状态可见性使用目标适配定义的有界轮询，不把芯片固定cycle写进公共Case。
- Overflow必须由真实无空间写入条件产生，不人工伪造状态。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_002`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
