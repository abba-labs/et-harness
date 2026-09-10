# SPINLOCK_P2_004 — SPINLOCK Batch与Global Release范围测试

整理时间：2026-09-10 22:10 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA（双核运行）；最近一次历史测试 2026-08-28 20:20 CST，源码 `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean，来自芯片文档状态块）。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。关联Feature：SPINLOCK_F_010、SPINLOCK_F_011；资源等级 R2。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后分组占用——DUT获取两个Resource，Peer获取第三个Resource并进入HOLDING持续持锁；确认三个Resource均Locked且Owner分组正确；由DUT执行Batch Release，通过Flag确认DUT的两个Resource清零、Peer Job仍为HOLDING且Peer Resource Owner不变；再执行Global Release，通过LOW/HIGH Flag Bank确认三个Resource全部空闲；空闲资源不读取Owner端点。

## 复测要点与判断边界

- 判定：Batch只释放当前Master资源且不影响Peer Owner；Global释放所有Master的全部测试Resource；结论来自Flags与Owner读回，不依赖命令返回值。
- Batch/Global Clear寄存器回读恒为0（芯片文档§3.3），清除动作只能以Resource Flags为证据；Peer Job状态（HOLDING）是Batch阶段"未误伤Peer"的第二证据。
- Batch Release只清当前Master资源、Global Release忽略Master清全部64资源且仅用于初始化/恢复（公共契约§0.1、§0.4）；普通业务路径不得借Global释放掩盖Owner保护缺陷。
- Global后所有资源空闲，禁止为确认而读取Owner端点；如需Owner证据应在Global前的分组占用阶段取得。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P2_004`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
