# ET6801 SPINLOCK Case知识

更新时间：2026-09-09 11:30 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖SPINLOCK注册表全部11个已注册Case（P0×3、P1×3、P2×4、P3×1）。公共Case Catalog同为11个且全部IMPLEMENTED，无未注册缺口；其中P2/P3共5个Case依赖已部署片内双Core Peer，其历史PASS来自FPGA双核运行，不外推到Silicon。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [SPINLOCK_P0_001 — SPINLOCK配置模式读回测试](cases/SPINLOCK_P0_001.md)
- [SPINLOCK_P0_002 — SPINLOCK一步模式全Resource获取释放测试](cases/SPINLOCK_P0_002.md)
- [SPINLOCK_P0_003 — SPINLOCK两步模式Process ID测试](cases/SPINLOCK_P0_003.md)
- [SPINLOCK_P1_001 — SPINLOCK跨状态组多Resource独立性测试](cases/SPINLOCK_P1_001.md)
- [SPINLOCK_P1_002 — SPINLOCK Disable锁状态保持测试](cases/SPINLOCK_P1_002.md)
- [SPINLOCK_P1_003 — SPINLOCK Clear Key保护测试](cases/SPINLOCK_P1_003.md)
- [SPINLOCK_P2_001 — SPINLOCK双Core Try竞争与恢复测试](cases/SPINLOCK_P2_001.md)
- [SPINLOCK_P2_002 — SPINLOCK双Core阻塞获取与交接测试](cases/SPINLOCK_P2_002.md)
- [SPINLOCK_P2_003 — SPINLOCK非Owner释放保护测试](cases/SPINLOCK_P2_003.md)
- [SPINLOCK_P2_004 — SPINLOCK Batch与Global Release范围测试](cases/SPINLOCK_P2_004.md)
- [SPINLOCK_P3_001 — SPINLOCK双Core共享计数互斥压力测试](cases/SPINLOCK_P3_001.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次SPINLOCK运行（[芯片文档状态块](../../../../test_case_doc/spinlock/ET6801_spinlock.md)）：FPGA Lane，2026-08-28 20:20 CST（双核 spinlock exact-SHA 专项运行），Source `ba1304b458148b681ec5f0a6a392cdf7c0757f76`（clean），11 Case / 15 执行 = 11 PASS / 0 FAIL / 0 SKIP；状态块更新时间 2026-08-28 21:24 CST（引用前已读原文核对）。
- **原始Canonical证据已不在仓库**：原始Evidence 已随早期清理不在两个工作树（芯片文档状态块仍保留该路径引用）。本目录知识依据芯片文档状态块与公共契约整理；参数级execution明细（session.json、result.json、Observation原始值）不可考，一律不引用、不外推具体观测值。
- 方法权威：[公共SPINLOCK契约](../../../../test_case_doc/spinlock/spinlock.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 SPINLOCK芯片文档](../../../../test_case_doc/spinlock/ET6801_spinlock.md)。

## 未闭环问题

- 本轮无 FAIL/SKIP 记录：芯片文档状态块"当前非PASS Case"为NONE，本目录暂无未闭环Case。

## 关键变化

- 2026-09-09 11:30 CST：建立SPINLOCK固定Case档案，按R130 §8.1与R500 §6从芯片文档状态块与公共契约提炼11个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
