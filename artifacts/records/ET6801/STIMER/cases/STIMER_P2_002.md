# STIMER_P2_002 — STIMER紧急故障触发计数捕获测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R3（紧急路由激励）。 本轮已选节点 SKIP（见变化记录），脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

三轮运行本Case均被正式门禁判定SKIP：Runtime Capability缺少`START_STOP`、`PERIOD`、`FREE_RUN`和`EMERGENCY_CAPTURE`组合，Case在刺激前停止；属当前Service/Capability映射未提供该Case需要的完整语义，是**实现映射缺口**，不是最终硬件SKIP结论。Case方法意图：确认Runtime声明四项能力后，停止旧会话并配置长period Free-Run清零计数；配置公开逻辑Source/Trigger Group并打开`stimer_emergency_input`对应的Bench激励器；紧急事件到达时验证计数被立即捕获锁存。

## 判断边界与复测条件

- 有能力时判定为：紧急事件触发计数捕获（捕获值反映事件时点计数）；紧急路由与正常计数互不干扰。
- SKIP归因在Capability映射层而非硬件——后续补齐公共命令、Capability和安全Source映射后即可复测，无需改硬件刺激假设。
- 不得绕过Runtime Gate强行执行。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P2_002`；芯片适配与SKIP归因见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`skip_by_runtime_feature: running STIMER service is missing feature`（缺 EMERGENCY_CAPTURE 等组合）。与既有 Capability 映射缺口一致。
