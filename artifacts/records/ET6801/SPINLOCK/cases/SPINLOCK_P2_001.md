# SPINLOCK_P2_001 — SPINLOCK双Core Try竞争与恢复测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。关联Feature：SPINLOCK_F_002、SPINLOCK_F_003、SPINLOCK_F_007、SPINLOCK_F_009；资源等级 R2。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后DUT在当前Mode（ONE_STEP/TWO_STEP矩阵）获取代表Resource并确认Owner信息；启动Peer TRY Job竞争同一Resource并等待有界结果；确认Peer返回Timeout/Busy且Owner仍为DUT；DUT释放并确认Flag清零后，Peer再次TRY同一Resource并成功，确认Owner切换为Peer并由Peer释放；两个Mode重复同一因果链。

## 复测要点与判断边界

- 判定：DUT持锁时Peer TRY有界失败且Owner不变；DUT释放后Peer TRY成功；ONE_STEP与TWO_STEP均完成"竞争→保护→释放→恢复→移交"全链。
- 必须先证明Peer Job已进入预定状态再执行竞争与判定，禁止以固定sleep作为唯一同步依据；逻辑实体到硬件Master ID映射未验证时不得执行Owner Oracle（公共契约§0.4）。ET6801 Core0/Core1的Master ID映射已由P2 Case经Owner读回验证（芯片文档§5 F_007行）。
- Try有界返回的1000次上限是Driver软件轮询策略，不是硬件Timeout精度（芯片文档§2.3），报告不得写成硬件超时器行为。
- 竞争与等待逻辑放在异步Peer Job中，PC控制通道保持响应；判定以Peer结果加Flags/Owner读回双证据为准。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P2_001`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
