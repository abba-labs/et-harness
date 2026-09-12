# ET6801 STIMER Case知识

更新时间：2026-09-09 11:45 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅Canonical事实与人读证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖STIMER注册表全部16个已注册Case。P1_008/P2_002/P2_003/P3_001依赖Observer、紧急路由、Debug Halt或独立参考时钟等高等级Bench条件（R3~R5），历史上因条件缺失SKIP或FAIL，详见各Case。本目录不表示公共STIMER全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [STIMER_P0_001 — STIMER基本计数、Start/Stop与实时读数测试](cases/STIMER_P0_001.md)
- [STIMER_P0_002 — STIMER周期终点与Overflow基本测试](cases/STIMER_P0_002.md)
- [STIMER_P1_001 — STIMER预分频比例与边界测试](cases/STIMER_P1_001.md)
- [STIMER_P1_002 — STIMER One-Shot与Free-Run生命周期测试](cases/STIMER_P1_002.md)
- [STIMER_P1_003 — STIMER软件清零与Pause/Resume测试](cases/STIMER_P1_003.md)
- [STIMER_P1_004 — STIMER Immediate与Shadow周期加载时机测试](cases/STIMER_P1_004.md)
- [STIMER_P1_005 — STIMER实时计数与重复锁存快照测试](cases/STIMER_P1_005.md)
- [STIMER_P1_006 — STIMER四通道Compare门限与来源隔离测试](cases/STIMER_P1_006.md)
- [STIMER_P1_007 — STIMER IRQ控制链、Force与真实Delivery测试](cases/STIMER_P1_007.md)
- [STIMER_P1_008 — STIMER Overflow/Compare事件脉宽测试](cases/STIMER_P1_008.md)
- [STIMER_P1_009 — STIMER Overflow历史状态read-to-clear测试](cases/STIMER_P1_009.md)
- [STIMER_P1_010 — STIMER Compare重复事件诊断测试](cases/STIMER_P1_010.md)
- [STIMER_P2_001 — STIMER事件触发真实DMA搬运测试](cases/STIMER_P2_001.md)
- [STIMER_P2_002 — STIMER紧急故障触发计数捕获测试](cases/STIMER_P2_002.md)
- [STIMER_P2_003 — STIMER CPU Debug Halt暂停与自由运行测试](cases/STIMER_P2_003.md)
- [STIMER_P3_001 — STIMER长时间周期、IRQ与计数稳定性测试](cases/STIMER_P3_001.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次运行：FPGA Lane 2026-09-03 14:32 CST，Source `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean），16 Case/27 执行=12 PASS/1 FAIL/3 SKIP（状态块更新 2026-09-03 14:35 CST）。该轮是STIMER P2_003 Debug Halt FAIL后的专项复测轮（session只含stimer_p2_003一个execution，Canonical证据锚为`artifacts/records/ET6801/STIMER/current`）。
- 全量轮：FPGA Lane 2026-08-28，其原始Canonical Session已随早期清理不在两个工作树；全量轮结果由状态块记录，参数级明细不可考。原始的 artifacts/runs 执行目录已废弃并从仓库删除，本树不引用它。
- P2_003 FAIL的参数级观测（PAUSE/RUN_FREE两策略的DHCSR、STM_SET、CNT_RPT增量）由状态块记录并在0903专项复测session中复核，是本目录唯一引用参数级数值的Case。
- 方法权威：[公共STIMER契约](../../../../test_case_doc/stimer/stimer.md)各Case的`ET_CASE_SPEC`（该契约的feature_refs字段未登记，本目录关联Feature以状态块为准）；芯片适配见[ET6801 STIMER芯片文档](../../../../test_case_doc/stimer/ET6801_stimer.md)。

## 未闭环问题

- [STIMER_P2_003](cases/STIMER_P2_003.md) FAIL：CPU Debug Halt的PAUSE策略未实际暂停STIMER计数（两种策略前后DHCSR=0x00030003、S_HALT=1，PAUSE时CNT_RPT仍增约520万计数）；已排除"CPU未停核"与"PAUSE配置未写入"，Halt信号路径/时钟域/多核关联待设计人员确认。
- [STIMER_P1_008](cases/STIMER_P1_008.md) SKIP：Bench未绑定stimer_output信号Observer，无法观测硬件输出脉宽。
- [STIMER_P2_002](cases/STIMER_P2_002.md) SKIP：Runtime Capability缺少EMERGENCY_CAPTURE等组合，属实现映射缺口。
- [STIMER_P3_001](cases/STIMER_P3_001.md) SKIP：Bench未绑定stimer_reference独立参考Observer，无法形成独立时基证据。

## 关键变化

- 2026-09-09 11:45 CST：建立STIMER固定Case档案，按R130 §8.1与R500 §6从状态块、0903专项session与公共契约提炼16个已注册Case知识；P2_003为唯一引用参数级观测的FAIL Case；未执行任何测试或硬件动作。
