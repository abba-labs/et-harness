# SPINLOCK_P0_002 — SPINLOCK一步模式全Resource获取释放测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case无额外Board/Bench要求，结论不外推到Silicon。关联Feature：SPINLOCK_F_002、SPINLOCK_F_004；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后Enable SPINLOCK并选择ONE_STEP，按Capability发布顺序逐Resource执行"获取→读无副作用Flag与Owner确认Locked=1且Owner为本执行实体→释放→重读Flag确认清零"的闭环；空闲Resource不读取Owner端点；最终确认Capability发布的全部Resource均各完成一轮获取与释放。

## 复测要点与判断边界

- 判定：Capability发布的每个Resource恰好执行一轮；获取后Locked=1且Owner正确；释放后对应Flag=0。
- 无副作用Flag是Locked/Free主证据；只有Flag证明Locked=1后才允许读取`SL_LOCK_INFO`类Owner端点——读空闲Resource的Owner寄存器会原子加锁（芯片文档§3.3），观测不得变成刺激。
- ET6801 Capability发布resource_count=64、双32-bit Flag Bank（芯片文档§3.1、§5）；公共Case不写死最大编号，复测以当次Capability发布为准。
- 历史PASS按状态块Case级记录；Case内部逐Resource执行粒度不可考（参数级明细已不在），复测以当次Canonical Session为准。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P0_002`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
