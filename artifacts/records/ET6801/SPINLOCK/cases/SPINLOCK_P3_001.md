# SPINLOCK_P3_001 — SPINLOCK双Core共享计数互斥压力测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（双核运行，Profile `et6801_fpga_dualcore`，Core1 Peer 清单 `et6801_fpga_itcm.json`）；本轮 2026-09-11 20:46 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。本Case要求片内双Core Peer与已验证的逻辑执行实体到硬件Master ID映射，结论不外推到Silicon。

## 结果与可复用经验

历史最近运行本Case PASS（芯片文档状态块：11 Case/15执行=11 PASS/0 FAIL/0 SKIP，本IP无FAIL/SKIP记录）；参数级execution明细不可考，本文不引用具体观测值。方法要点：基线建立后在声明的共享可见内存中清零Shared Counter、临界区标志和Violation Count并完成可见性同步；两个执行实体用同一ONE_STEP Resource并发执行PC计划提供的固定loop_count轮——每轮获取锁、执行内存屏障/Cache维护、检查独占标志、递增Shared Counter、再同步并释放锁；PC轮询两个异步Job直到完成或deadline到期；终态读取两个Job结果、Shared Counter、Violation Count和Resource状态。

## 复测要点与判断边界

- 判定：两个执行实体均完成全部loop_count轮；SHARED_COUNTER.VALUE=2×loop_count；VIOLATION_COUNT=0且最终Resource为空闲。
- 计数器、临界区标志和违规计数必须位于两个执行实体都可见的Coherent或Uncached共享内存；ET6801使用AXI SRAM1共享计数区，volatile配合DMB/DSB屏障（芯片文档§5 F_013行）。若用Cacheable内存，执行映射必须定义屏障与Cache维护——禁止把可见性问题误判为Spinlock失败。
- loop_count由PC计划提供且固定可复现，不是硬件Feature参数；执行实体的阻塞轮询放入异步Peer Job，PC只轮询Job状态。
- Case deadline为30s（公共契约SPEC）；超时未完成按事实记录，不得以部分轮数外推互斥结论。

## 依据与变化

方法权威：[公共SPINLOCK契约](../../../../../test_case_doc/spinlock/spinlock.md)中的`SPINLOCK_P3_001`；芯片适配见[ET6801 SPINLOCK文档](../../../../../test_case_doc/spinlock/ET6801_spinlock.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与公共契约`ET_CASE_SPEC`提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:10 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
