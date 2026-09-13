# STIMER_P1_003 — STIMER软件清零与Pause/Resume测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：配置FREE_RUN、合法divider与长period，清理历史状态后START确认COUNT.LIVE推进；运行中执行CLEAR_COUNT并读COUNT.LIVE确认从零附近重新开始且继续推进；执行PAUSE并连续两次读COUNT.LIVE确认有界窗口内计数冻结；RESUME后确认从冻结点继续。

## 复测要点与判断边界

- 判定：CLEAR_COUNT后计数归零附近且继续推进（软件清零不影响运行态）；PAUSE窗口内两次读数冻结；RESUME后从冻结点续计。
- 软件清零与PAUSE是两个独立动作，分别取证；清零后的"继续推进"证明清零不停表。
- 注意P2_003揭示的边界：软件PAUSE（本Case）与CPU Debug Halt联动暂停是两条不同路径，本Case PASS不外推到Debug Halt场景。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_003`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
