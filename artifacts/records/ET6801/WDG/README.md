# ET6801 WDG Case知识

更新时间：2026-09-10 22:09 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖WDG注册表全部14个已注册Case（P0×3、P1×8、P2×2、P3×1），与公共Case Catalog一致、无未注册缺口；其中4个当前FAIL（P0_004、P1_002、P1_003、P2_001）在索引与"未闭环问题"中标记，本目录不表示全部测试目标已硬件闭环。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [WDG_P0_002 — WDG使能禁用与计数基础测试](cases/WDG_P0_002.md)
- [WDG_P0_003 — WDG独立模式喂狗重载测试](cases/WDG_P0_003.md)
- [WDG_P0_004 — WDG真实超时复位与跨重启取证测试（FAIL）](cases/WDG_P0_004.md)
- [WDG_P1_001 — WDG复位输出关闭与自然中断测试](cases/WDG_P1_001.md)
- [WDG_P1_002 — WDG窗口喂狗区域测试](cases/WDG_P1_002.md)
- [WDG_P1_003 — WDG轮次工作模式测试（FAIL）](cases/WDG_P1_003.md)
- [WDG_P1_004 — WDG模块复位与恢复测试](cases/WDG_P1_004.md)
- [WDG_P1_005 — WDG配置写保护与解锁测试](cases/WDG_P1_005.md)
- [WDG_P1_006 — WDG中断控制矩阵测试](cases/WDG_P1_006.md)
- [WDG_P1_007 — WDG自然中断与中断记录测试](cases/WDG_P1_007.md)
- [WDG_P1_008 — WDG多实例隔离测试](cases/WDG_P1_008.md)
- [WDG_P2_001 — WDG时钟源与分频集成测试（FAIL）](cases/WDG_P2_001.md)
- [WDG_P2_002 — WDG超时NMI路由与处理域隔离测试](cases/WDG_P2_002.md)
- [WDG_P3_001 — WDG调试Halt行为测试](cases/WDG_P3_001.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次WDG运行（[芯片文档状态块](../../../../test_case_doc/wdg/ET6801_wdg.md)）：FPGA Lane，2026-08-28 17:15 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），14 Case/14执行=11 PASS/3 FAIL/0 SKIP（状态块更新 2026-08-28 21:30 CST）。
- **【关键声明】原始Canonical证据已不在仓库**：Evidence路径`artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/wdg/`已随早期清理不在两个工作树。本树依据芯片文档状态块与人读报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推；状态块明确记录的3个FAIL观测值按来源标注引用。
- 方法权威：[公共WDG契约](../../../../test_case_doc/wdg/wdg.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 WDG芯片文档](../../../../test_case_doc/wdg/ET6801_wdg.md)。

## 未闭环问题

- [WDG_P0_004](cases/WDG_P0_004.md) 本轮仍 FAIL：复位期限前目标未断连。
- [WDG_P1_002](cases/WDG_P1_002.md) 本轮新 FAIL（历史 clean 曾 PASS）：Counter 未进入 `[1, 4998999]`，last=4999051。
- [WDG_P1_003](cases/WDG_P1_003.md) 本轮仍 FAIL：复位期限前目标未断连。
- [WDG_P2_001](cases/WDG_P2_001.md) 本轮仍 FAIL：速率比 1.002018 < 1.5。


## 关键变化

- 2026-09-10 22:09 CST：对照本轮 Session（`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，10 PASS / 4 FAIL）更新 FAIL 证据；P1_002 由历史 PASS 记为当次 FAIL。

- 2026-09-09 11:30 CST：建立WDG固定Case档案，按R500 §6从芯片文档状态块与人读历史报告提炼14个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
