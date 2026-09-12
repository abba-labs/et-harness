# SYSCNT_P0_001 — 停止装载与双窗口读回测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `7218fc2f-b90e-4480-8ba6-cff0001abb79`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一轮各参数节点PASS，无FAIL记录。方法：确认无其他消费者后按已批准复位映射建立实例基线，清Service状态和资源池；停止态（CONTROL.ENABLE=0）下调用VALUE_LOAD写入输入值，不隐式开启计数；双窗口（首次+延后）读取验证装载值稳定。

## 复测要点与判断边界

- 判定：所有位型的两个窗口首次和延后读数精确等于输入（无截断或高低字互换）；装载前后CONTROL.ENABLE均为0。
- 双窗口读回防的是"读数瞬时值"假象——停止态计数应绝对稳定，两次读数不同即失败。
- 高低字互换是最典型错误模式，位型参数要覆盖到能暴露字序问题的组合。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P0_001`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
