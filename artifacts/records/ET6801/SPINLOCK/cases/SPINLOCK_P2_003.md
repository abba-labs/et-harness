# SPINLOCK_P2_003 — SPINLOCK非Owner释放保护测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（双核运行，Profile `et6801_fpga_dualcore`，Core1 Peer 清单 `et6801_fpga_itcm.json`）；本轮 2026-09-11 20:46 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后DUT获取代表Resource并记录完整Owner信息（LOCKED、MASTER_ID、PROCESS_ID_VALID、PROCESS_ID）；命令非Owner Peer对同一Resource执行Release；重读同一组Owner字段与Flag，确认Resource仍Locked且Master/Process信息逐项不变；再由原Owner正常释放并确认Flag清零；在ONE_STEP和TWO_STEP下分别完成同一流程。

## 复测要点与判断边界

- 判定：非Owner Peer Release后Resource仍由原Owner持有；Master与有效Process信息逐项不变；原Owner Release后Resource变为空闲。
- 非Owner释放不得改变真实Owner（公共契约§0.3）；判定用Owner字段读回而非Peer命令返回值，防止"命令失败但锁已丢"或"命令成功但锁未变"两类误判。
- Owner读回只对Locked=1的Resource执行；原Owner释放后的空闲阶段不读Owner端点，避免观测变成Acquire刺激。
- ONE_STEP下Process字段无效时按公共契约的稳定语义判读，不把单模式下Process字段的表现外推为两步行为；两模式必须分别复验。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P2_003`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
