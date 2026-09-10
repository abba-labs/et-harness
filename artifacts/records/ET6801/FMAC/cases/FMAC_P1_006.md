# FMAC_P1_006 — FMAC Float转Q15钳位与Overflow状态测试

整理时间：2026-09-10 22:07 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：FMAC_F_020、FMAC_F_021；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；2026-08-25根因分析时期的历史失败已按"越界输入→正常输入→W1C清除时机"整改闭环（整改结论见该分析），本文件不复述参数级细节。方法要点：正超范围+2.0和负超范围-2.0分别形成独立四项恒定输入事务；使用0.5单抽头系数和零历史，配置RAW输出、Float输入转换开、Float输出转换关；越界输入先读Overflow基线（0），写四项同值超范围Float输入后读取STATUS.FLOAT_TO_Q15_OVERFLOW（1）与钳位Q15稳态输出（输入钳位边界再乘0.5）；随后每个越界事务继续输入一个0.25使硬件实时Overflow条件撤销（写入/读取各1项），最后Stop和Clear后确认Overflow清除。

## 复测要点与判断边界

- 判定：正负超范围先钳位到Q15边界再经0.5系数得对应稳态Expected；Overflow因果为基线0→越界1→正常输入撤销实时条件后Clear回到0；恢复输入写入和读取均完成1项。
- 状态清除必须先以正常输入解除实时Overflow条件再Clear，符合目标硬件W1C语义。
- 每个边界输入和状态清除动作均使用有界deadline。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P1_006`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
