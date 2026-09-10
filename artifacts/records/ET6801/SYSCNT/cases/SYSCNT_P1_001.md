# SYSCNT_P1_001 — 低字进位与最大值回绕测试

整理时间：2026-09-10 22:44 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-09-04 06:39 CST，源码 `2157037e3937d1d26a01390ae0bd652f40f788dd`（dirty=true）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：SYSCNT_F_003、SYSCNT_F_004；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：重建停止基线后检查counter_bits大于低字宽且K小于边界跨度；边界前装载并双窗口验证；启动后连续运行约100ms跨越约50ms余量的边界点；跨低字进位与最大值回绕两个边界验证模M展开读数连续。

## 复测要点与判断边界

- 判定：两类参数均取得真实边界前装载读数和边界后运行读数（边界确实被触发）；模M展开后读数不倒退；增量不超过采样时间上界×经确认最高频率的上限。
- 边界选点要保证运行窗口跨越边界（50ms余量设计），没跨过边界的运行不构成回绕证明。
- 增量上限检查防的是"计数器狂奔"类故障——只验证连续性不验证速率上限会漏掉分频错误。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P1_001`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。原始参数级证据：[SYSCNT Session](../../../../../artifacts/runs/20260904_063646_997568_local_et6801_fpga_atp_testing/tests/syscnt/session.json)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
