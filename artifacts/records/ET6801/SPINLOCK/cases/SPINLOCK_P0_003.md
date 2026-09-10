# SPINLOCK_P0_003 — SPINLOCK两步模式Process ID测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case无额外Board/Bench要求，结论不外推到Silicon。关联Feature：SPINLOCK_F_003、SPINLOCK_F_004、SPINLOCK_F_006；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后Enable SPINLOCK并选择TWO_STEP，对Capability发布的每个Process ID在代表Resource上执行"以当前Process ID获取→读LOCKED/MASTER_ID/PROCESS_ID_VALID/PROCESS_ID确认Owner登记→以相同Process ID释放→读Flag确认清零"的闭环；空闲状态不读取Owner端点；最终确认全部Process ID均独立完成获取与释放。

## 复测要点与判断边界

- 判定：Capability发布的每个Process ID均执行；获取后Master正确、PROCESS_ID_VALID=1且PROCESS_ID等于本轮配置；相同Process ID释放后Resource变为空闲。
- `RESOURCE_INFO.PROCESS_ID_VALID`与`PROCESS_ID`仅在Locked=1时有效（公共契约§0.2）；空闲Resource禁止读取Owner端点，避免把观测做成Acquire刺激。
- ET6801两步模式Process ID为4-bit 0..15（芯片文档§1.4、§3.2）；数量以Capability发布为准，不写死目标常量。
- 历史PASS按状态块Case级记录；逐Process ID执行粒度不可考（参数级明细已不在），复测以当次Canonical Session为准。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P0_003`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
