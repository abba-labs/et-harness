# SPINLOCK_P1_002 — SPINLOCK Disable锁状态保持测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（双核运行，Profile `et6801_fpga_dualcore`，Core1 Peer 清单 `et6801_fpga_itcm.json`）；本轮 2026-09-11 20:46 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后按ONE_STEP/TWO_STEP模式矩阵执行——Enable当前Mode并由本执行实体获取代表Resource、记录Resource Flags与完整Owner信息；只Disable模块，不执行任何Release或Clear；读取Config/Flags/Owner确认锁状态未变；以相同Mode重新Enable再次读取；确认Disable/Re-enable全程Owner保持后由原Owner正常释放。

## 复测要点与判断边界

- 判定：关闭阶段CONFIG.ENABLE=0；锁前、关闭后、Re-enable后三个观测点的Locked、Master和Process信息一致；Re-enable后原Owner可正常释放。
- Disable不清锁是SVD明确硬件语义（芯片文档§3.3），必须用"只切换Enable/Mode、不执行Global Release"的测试扩展接口验证——`SPINLOCK_init()`/`deInit()`都会Global Release（芯片文档§2.1、§2.3），误用会直接掩盖本Feature。
- Enable/Disable与锁资源清除是两个独立动作（公共契约§0.1）；观测仍以无副作用Flag为主证据，Owner读回仅限Locked=1时。
- 本Case在两种模式下均需复验保持语义；模式矩阵覆盖不因一次模式PASS而豁免另一模式。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P1_002`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
