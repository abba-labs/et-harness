# STIMER_P2_002 — STIMER紧急故障触发计数捕获测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `b51bcdf9-7f4f-46ca-9f4b-c713fb2f1b15`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

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
