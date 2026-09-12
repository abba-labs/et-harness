# STIMER_P3_001 — STIMER长时间周期、IRQ与计数稳定性测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `b51bcdf9-7f4f-46ca-9f4b-c713fb2f1b15`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

三轮运行本Case均被正式门禁判定SKIP：当前Bench没有绑定`stimer_reference`独立参考Observer，无法形成独立时基和外部周期证据；缺少独立参考时钟、事件输出观测和稳定供电Bench条件。Case方法意图：打开stimer_reference逻辑Observer并读取参考频率作为Expected周期计算的独立时基；按参考频率、divider和period上限生成两个合法参数节点；每节点START前记录COUNT.LIVE和IRQ event_count并清除前序Raw/Status；长窗口内验证计数速率、Overflow IRQ稳定性和计数连续性。

## 判断边界与复测条件

- 有参考Observer时判定为：两节点实际周期与按独立参考计算的Expected一致（误差在参考精度内）；长窗口Overflow IRQ计数单调无丢失；计数无跳变回绕异常。
- SKIP原因：无独立时基，任何速率结论都只能依赖被测时钟自身，形成循环论证，故不执行。
- 复测条件：完成独立参考、输出Observer及对应接线后复测；P1_001的分频比例结论不能替代本Case的绝对时基验证。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P3_001`；芯片适配与SKIP归因见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`skip_by_bench_profile: target 'dut' has no signal observer for 'stimer_reference'`。与既有独立参考时基缺口一致。
