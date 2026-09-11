# SPINLOCK_P1_003 — SPINLOCK Clear Key保护测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（双核运行，Profile `et6801_fpga_dualcore`，Core1 Peer 清单 `et6801_fpga_itcm.json`）；本轮 2026-09-11 20:46 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后Enable ONE_STEP并由本Master获取两个不同Resource；先提交无效Batch授权并读两个Resource状态，再提交无效Global授权并重读；随后提交目标有效Batch授权读Flags；确认两次错误授权均不改变锁状态、有效Batch授权清除本Master的两个Resource后，执行有效Global Release为下一Case建立安全基线。

## 复测要点与判断边界

- 判定：两次错误授权后两个Resource仍由原Master持有；有效Batch授权后两个Resource均为空闲；判定依据为Resource Flags/Owner读回，而不是命令返回值。
- ET6801的Batch/Global Clear寄存器回读恒为0（芯片文档§3.3），不能用寄存器回读证明清除动作完成，只能观察Resource Flags；Owner读回仅限Flag仍为1的资源。
- Clear Key探测依赖受限Test Driver接口：只接收授权真假与作用域，不向公共层暴露ET6801具体Key值（芯片文档§第六章P1_003行）；错误授权不得释放资源。
- 授权矩阵必须同时覆盖无效Batch、无效Global与有效Batch三类刺激；仅验证有效授权不构成保护证明。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P1_003`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
