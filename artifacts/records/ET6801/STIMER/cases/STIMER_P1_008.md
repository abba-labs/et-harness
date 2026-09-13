# STIMER_P1_008 — STIMER Overflow/Compare事件脉宽测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

三轮运行本Case均被正式门禁判定SKIP：当前Bench没有绑定`stimer_output`信号Observer，无法观测硬件输出脉宽；缺少STIMER事件输出路由和示波器或FPGA采样接线。Case方法意图：通过Bench逻辑名stimer_output建立事件到数字Observer的稳定路由；固定Compare0门限、周期和FREE_RUN仅改变event_pulse_width_cycles；每个宽度节点清除历史IRQ、Arm并启动单次采集，测量输出脉宽与配置的一致性。

## 判断边界与复测条件

- 有Observer时判定为：各宽度节点实测输出脉宽与event_pulse_width_cycles配置一致（在Observer采样精度内）；Overflow/Compare两类事件输出均覆盖。
- SKIP原因：无物理信号路由与观测手段，属Bench条件缺失，不是Feature或硬件判定。
- 复测条件：完成输出路由、Observer和物理接线后复测；不得用软件读IRQ替代硬件脉宽观测。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P1_008`；芯片适配与SKIP归因见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`skip_by_bench_profile: target 'dut' has no signal observer for 'stimer_output'`。与既有 Bench Observer 缺口一致。
