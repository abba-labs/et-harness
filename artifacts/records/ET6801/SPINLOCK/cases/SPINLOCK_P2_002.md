# SPINLOCK_P2_002 — SPINLOCK双Core阻塞获取与交接测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。关联Feature：SPINLOCK_F_002、SPINLOCK_F_003、SPINLOCK_F_008；资源等级 R2。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后DUT获取代表Resource并确认Owner；启动Peer异步BLOCKING Acquire Job并等待Job进入WAITING；在有界观察窗口内确认Peer未进入临界区且Owner仍为DUT；DUT释放并等待Job完成后，确认Peer只进入一次且Owner切换为Peer；最终由Peer释放，并在ONE_STEP/TWO_STEP两个Mode重复执行。

## 复测要点与判断边界

- 判定：Owner释放前Peer保持WAITING且ENTER_COUNT=0；释放后Peer完成获取且ENTER_COUNT=1；交接前后Master身份与实际执行实体一致。
- 阻塞获取必须放入异步Peer Job（ET6801驱动`SPINLOCK_acquire`无超时，禁止占用PC控制通道，芯片文档§2.1）；同步以PEER_JOB.STATE/ENTER_COUNT为准，禁止用固定sleep冒充同步。
- 持锁Job收到Release/Abort前不得自动释放（公共契约§0.3）；等待窗口是有界观察，不等价于无限期等待。
- 历史FPGA源码的固定Delay+打印判定已被Formal Case以Job状态、Owner读回和进入次数证据取代（芯片文档§4.1标记SUPERSEDED）。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P2_002`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
