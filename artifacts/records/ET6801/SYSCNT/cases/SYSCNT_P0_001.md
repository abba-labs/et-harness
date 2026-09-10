# SYSCNT_P0_001 — 停止装载与双窗口读回测试

整理时间：2026-09-10 22:44 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-09-04 06:39 CST，源码 `2157037e3937d1d26a01390ae0bd652f40f788dd`（**dirty=true**，状态块如实记录）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：SYSCNT_F_001、SYSCNT_F_004；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一轮各参数节点PASS，无FAIL记录。方法：确认无其他消费者后按已批准复位映射建立实例基线，清Service状态和资源池；停止态（CONTROL.ENABLE=0）下调用VALUE_LOAD写入输入值，不隐式开启计数；双窗口（首次+延后）读取验证装载值稳定。

## 复测要点与判断边界

- 判定：所有位型的两个窗口首次和延后读数精确等于输入（无截断或高低字互换）；装载前后CONTROL.ENABLE均为0。
- 双窗口读回防的是"读数瞬时值"假象——停止态计数应绝对稳定，两次读数不同即失败。
- 高低字互换是最典型错误模式，位型参数要覆盖到能暴露字序问题的组合。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P0_001`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。原始参数级证据：[SYSCNT Session](../../../../../artifacts/runs/20260904_063646_997568_local_et6801_fpga_atp_testing/tests/syscnt/session.json)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
