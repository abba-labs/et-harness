# SPINLOCK_P1_001 — SPINLOCK跨状态组多Resource独立性测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（双核运行，Profile `et6801_fpga_dualcore`，Core1 Peer 清单 `et6801_fpga_itcm.json`）；本轮 2026-09-11 20:46 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后Enable ONE_STEP，一次性获取Capability从"首项、低组末项、高组首项、末项"生成的去重边界Resource集合且中途不释放；读取LOW/HIGH两个Flag Bank与各Resource Owner；再按获取逆序逐个释放，每次释放后只允许目标Resource Flag清零、其余已持有Resource保持锁定；全部释放后两个Flag Bank回到空闲基线。

## 复测要点与判断边界

- 判定：全部边界Resource可同时保持Locked=1；每次释放只清除目标Resource且其他Owner不变；结束后所有测试Resource均为空闲。
- ET6801的64个Resource对应`SL_LOCK_FLAG_RPT1/2`两个32-bit Flag Bank（芯片文档§3.1）；边界集合必须横跨两个Bank，才能证明跨状态组的资源独立性。
- 状态判定用Flag Bank原始值与前后差值计算变化集合，不依赖命令返回值；释放逆序保证覆盖"先释放高组"路径。
- Flag为无副作用证据源；Owner读回仍只对Locked=1的Resource执行。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P1_001`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
