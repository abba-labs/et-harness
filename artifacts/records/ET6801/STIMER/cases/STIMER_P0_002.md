# STIMER_P0_002 — STIMER周期终点与Overflow基本测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：选择本轮period_ticks并配置合法divider、ONE_SHOT和IMMEDIATE加载；清除IRQ_RAW.OVERFLOW及可清理历史状态确认起始Raw为0；START后在统一deadline内等待目标周期终点，验证Overflow事件在周期终点产生。

## 复测要点与判断边界

- 判定：周期终点处Overflow Raw置位且时间与period_ticks吻合；起始Raw必须为0（清理有效）。
- 等待用统一deadline（按divider/period换算理论时间加裕量），不盲等。
- Overflow语义是"计数到达周期终点"，与Compare事件（P1_006）来源不同，归因不能混。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P0_002`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
