# SYSCNT_P2_001 — 时钟源与独立参考计时测试

整理时间：2026-09-10 22:44 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-09-04 06:39 CST，源码 `2157037e3937d1d26a01390ae0bd652f40f788dd`（dirty=true）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：SYSCNT_F_007、SYSCNT_F_008；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：确认参考计数器可用且不依赖SYSCNT后建立独占基线；停止SYSCNT由时钟Driver选择参数源并读回CLOCK.SOURCE，登记对应频率标识后使能；每个参数执行REFERENCE_SAMPLE_GET取参考前值/后值，五个测量窗口覆盖短到长时间尺度。

## 复测要点与判断边界

- 判定：每参数最坏误差不超过1ms、参考区间宽度不超过0.1ms（超出保留测量质量失败）；声明可用的每个源读回正确且五窗口完成——不能因参考位宽或软件未实现省略长窗口。
- "参考不依赖SYSCNT"是方法前提：参考若是SYSCNT自身，误差比较就是循环论证。
- CLOCK.SOURCE读回与频率标识登记要成对，只切源不登记会让后续Case的Expected失真。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P2_001`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。原始参数级证据：[SYSCNT Session](../../../../../artifacts/runs/20260904_063646_997568_local_et6801_fpga_atp_testing/tests/syscnt/session.json)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
