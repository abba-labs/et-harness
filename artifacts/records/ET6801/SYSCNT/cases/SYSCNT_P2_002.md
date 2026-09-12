# SYSCNT_P2_002 — CPU停核时的计数策略测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `7218fc2f-b90e-4480-8ba6-cff0001abb79`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：停止并归一SYSCNT/Service/资源池后由所属Driver配置系统Halt路由并确认计数器不被其他Core使用；设置参数策略（暂停/继续两种）、装载非边界值并启动，保存CONTROL.HALT_ON_DEBUG读回；调试器发起Halt并实际读取CPU.DEBUG_HALTED=1（停核后不等待固件串口响应）；停核内与恢复后分别取证计数变化，按策略判定暂停或继续。

## 复测要点与判断边界

- 判定：两次取样都获得CPU停核读回（未确认停核时不得形成计数暂停PASS）；两种策略各自满足暂停状态与计数变化判据。
- **与STIMER_P2_003的交叉参照**：本Case（SYSCNT HALT_ON_DEBUG路由）在同期硬件上PASS，而STIMER的CPU Halt联动PAUSE策略FAIL——说明停核信号本身可达、问题特定于STIMER的Halt路径；但两者是不同IP的独立结论，复测互不预支。
- "停核后不等串口响应"是方法红线，等待会假死。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P2_002`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
