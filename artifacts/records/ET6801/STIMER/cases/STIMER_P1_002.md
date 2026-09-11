# STIMER_P1_002 — STIMER One-Shot与Free-Run生命周期测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：清理Overflow状态后配置ONE_SHOT、短period和合法divider；START等待首次IRQ_RAW.OVERFLOW=1；读取COUNT.LIVE并Clear Overflow后继续观察一个完整下一周期窗口——One-Shot应不再产生新Overflow，Free-Run对照应继续周期循环。

## 复测要点与判断边界

- 判定：One-Shot只产生一次Overflow（清后观察窗口内不再触发）；Free-Run持续周期触发；两种模式生命周期差异明确。
- 清除Overflow后的观察窗口必须覆盖至少一个完整周期时长，否则"未再触发"证据不足。
- 首次Overflow到达即记录COUNT.LIVE终态，One-Shot停止位置是模式语义的一部分。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_002`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
