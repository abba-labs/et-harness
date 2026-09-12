# ET6801 FMAC Case知识

更新时间：2026-09-09 11:30 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖FMAC注册表全部23个已注册Case（P0×4、P1×15、P2×1、P3×3），与公共FMAC契约Case Catalog一致；X1/X2 Load Error与Y Store Error三个内部故障Feature按公共契约约定不建立Formal Case，无对应注册Case。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [FMAC_P0_001 — FMAC Q15 FIR稳态卷积测试](cases/FMAC_P0_001.md)
- [FMAC_P0_002 — FMAC Q15 IIR独立参考测试](cases/FMAC_P0_002.md)
- [FMAC_P0_003 — FMAC Clear与配置保持测试](cases/FMAC_P0_003.md)
- [FMAC_P0_004 — FMAC Enable/Disable与活动状态测试](cases/FMAC_P0_004.md)
- [FMAC_P1_001 — FMAC X1/X2/Y区域布局矩阵测试](cases/FMAC_P1_001.md)
- [FMAC_P1_002 — FMAC X1水位容量状态与Overflow测试](cases/FMAC_P1_002.md)
- [FMAC_P1_003 — FMAC Y水位容量状态与Underflow测试](cases/FMAC_P1_003.md)
- [FMAC_P1_004 — FMAC 流式Chunk连续性测试](cases/FMAC_P1_004.md)
- [FMAC_P1_005 — FMAC Float输入输出正常转换测试](cases/FMAC_P1_005.md)
- [FMAC_P1_006 — FMAC Float转Q15钳位与Overflow状态测试](cases/FMAC_P1_006.md)
- [FMAC_P1_007 — FMAC 内部Clip与Saturation状态测试](cases/FMAC_P1_007.md)
- [FMAC_P1_008 — FMAC 最终输出Saturate/Wrap测试](cases/FMAC_P1_008.md)
- [FMAC_P1_009 — FMAC 输出数据模式矩阵测试](cases/FMAC_P1_009.md)
- [FMAC_P1_010 — FMAC 输出Offset与负值状态测试](cases/FMAC_P1_010.md)
- [FMAC_P1_011 — FMAC 输出Shift全合法编码测试](cases/FMAC_P1_011.md)
- [FMAC_P1_012 — FMAC 十一源IRQ控制Force与投递矩阵测试](cases/FMAC_P1_012.md)
- [FMAC_P1_013 — FMAC 自然请求IRQ测试](cases/FMAC_P1_013.md)
- [FMAC_P1_014 — FMAC 自然运算与Buffer边界IRQ测试](cases/FMAC_P1_014.md)
- [FMAC_P1_015 — FMAC P/PQ/Q参数错误自然IRQ测试](cases/FMAC_P1_015.md)
- [FMAC_P2_001 — FMAC 双向DMA门控与FIR端到端测试](cases/FMAC_P2_001.md)
- [FMAC_P3_001 — FMAC 确定性长流FIR稳定性测试](cases/FMAC_P3_001.md)
- [FMAC_P3_002 — FMAC CPU路径周期性能表征](cases/FMAC_P3_002.md)
- [FMAC_P3_003 — FMAC DMA路径周期性能表征](cases/FMAC_P3_003.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次FMAC运行（[芯片文档状态块](../../../../test_case_doc/fmac/ET6801_fmac.md)）：FPGA Lane，2026-08-28 17:14 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），23 Case/46执行=23 PASS/0 FAIL/0 SKIP，状态块更新于2026-08-28 21:23 CST。
- **原始Canonical证据已不在仓库**：上述Evidence路径已随早期清理不在本机两个工作树。本目录知识依据芯片文档状态块与人读历史报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推具体观测值。
- 历史开发过程报告：[2026-08-25 FMAC HIL失败根因分析](../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)（早期HIL失败根因分析，当前PASS是整改后结果）、[2026-08-23 FMAC实施计划](../../../../report/plans/20260823_fmac_implementation_plan.md)。
- 方法权威：[公共FMAC契约](../../../../test_case_doc/fmac/fmac.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 FMAC芯片文档](../../../../test_case_doc/fmac/ET6801_fmac.md)。

## 未闭环问题

- 本轮无FAIL/SKIP记录：2026-08-28运行23 Case/46执行全部PASS。2026-08-25根因分析中的历史失败已整改，整改结论见该分析，不在本目录重复。

## 关键变化

- 2026-09-09 11:30 CST：建立FMAC固定Case档案，按R500 §6从芯片文档状态块与人读历史报告提炼23个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
