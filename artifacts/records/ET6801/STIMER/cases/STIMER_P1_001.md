# STIMER_P1_001 — STIMER预分频比例与边界测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：先读Runtime Capability的最大divider（至少需divider=1和一个更大合法节点，否则按能力发布缺口失败关闭）；对每个divider节点停止STIMER、配置相同最大周期与FREE_RUN并清零计数；交错执行三轮divider矩阵，在固定有界窗口前后读COUNT.LIVE形成count_delta和actual_rate。

## 复测要点与判断边界

- 判定：actual_rate与divider理论比例一致（比例关系而非绝对频率，绝对校准属P3_001需独立参考时钟）；全部divider节点覆盖。
- 交错执行三轮是为了抵消时钟漂移对速率比测量的影响，顺序跑会引入系统性偏差。
- Capability能力不足时失败关闭，不得降低divider矩阵冒充覆盖。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_001`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
