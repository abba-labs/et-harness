# SPINLOCK_P0_001 — SPINLOCK配置模式读回测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case无额外Board/Bench要求，结论不外推到Silicon。关联Feature：SPINLOCK_F_001、SPINLOCK_F_002、SPINLOCK_F_003；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，不引用具体观测值。方法要点：先执行Global Release→Service State Reset→Resource Pool Reset建立基线，任何一步失败立即终止；随后Enable模块并选择ONE_STEP读取CONFIG快照判定ENABLE=1且MODE=ONE_STEP，切换TWO_STEP重读快照再判定，最后Disable模块判定ENABLE=0；每轮先记录CONFIG.ENABLE与CONFIG.MODE原始逻辑值，再作判定。

## 复测要点与判断边界

- 判定：三个阶段（ONE_STEP、TWO_STEP、Disable）的Enable与Mode读回逐项等于配置；Disable后Enable读回为0。
- 配置快照取稳定逻辑值（`config_snapshot_get`），不暴露芯片寄存器类型；判定依据为DUT侧读回，API返回成功不能替代硬件状态。
- ET6801的`SPINLOCK_init()`/`deInit()`会隐式Global Release（芯片文档§2.1），Enable/Mode切换必须使用不隐式清锁的测试扩展接口，否则配置动作与清锁副作用无法区分。
- Enable/Disable与锁资源清除是两个独立动作（公共契约§0.1）；本Case不把Disable当作清锁证据，也不验证锁状态保持（属于SPINLOCK_P1_002）。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P0_001`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
