# ET6801 CORDIC Case知识

更新时间：2026-09-09 11:30 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖CORDIC注册表全部24个已注册Case（P0×3、P1×18、P2×1、P3×3），其中23个PASS、1个SKIP（CORDIC_P2_001，NOT_APPLICABLE）。本目录不表示公共CORDIC全部测试目标已实现：公共Case Catalog中另有已停用或并入其他Case的ID（P0_001停用不复用；P1_010并入P1_007、P1_014并入P1_008、P1_012并入P1_016），不补造记录。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [CORDIC_P0_002 — CORDIC定点核心数学函数矩阵测试](cases/CORDIC_P0_002.md)
- [CORDIC_P0_003 — CORDIC浮点核心数学函数矩阵测试](cases/CORDIC_P0_003.md)
- [CORDIC_P0_004 — CORDIC复位后重新配置与运算恢复测试](cases/CORDIC_P0_004.md)
- [CORDIC_P1_001 — CORDIC正余弦输入范围模式等价性测试](cases/CORDIC_P1_001.md)
- [CORDIC_P1_002 — CORDIC参数/结果位宽与16-bit打包测试](cases/CORDIC_P1_002.md)
- [CORDIC_P1_003 — CORDIC Scale缩放语义测试](cases/CORDIC_P1_003.md)
- [CORDIC_P1_004 — CORDIC迭代周期与精度表征测试](cases/CORDIC_P1_004.md)
- [CORDIC_P1_005 — CORDIC双结果数量选择测试](cases/CORDIC_P1_005.md)
- [CORDIC_P1_006 — CORDIC相位模长双参数顺序与当前计数测试](cases/CORDIC_P1_006.md)
- [CORDIC_P1_007 — CORDIC轮询完成状态机测试](cases/CORDIC_P1_007.md)
- [CORDIC_P1_008 — CORDIC中断工作模式计算与结果测试](cases/CORDIC_P1_008.md)
- [CORDIC_P1_009 — CORDIC零开销写读功能测试](cases/CORDIC_P1_009.md)
- [CORDIC_P1_011 — CORDIC参数数量溢出状态与恢复测试](cases/CORDIC_P1_011.md)
- [CORDIC_P1_013 — CORDIC浮点转定点溢出/下溢状态测试](cases/CORDIC_P1_013.md)
- [CORDIC_P1_015 — CORDIC参数溢出IRQ自然投递测试](cases/CORDIC_P1_015.md)
- [CORDIC_P1_016 — CORDIC第二参数错误状态、自然IRQ与恢复测试](cases/CORDIC_P1_016.md)
- [CORDIC_P1_017 — CORDIC IRQ使能/禁用与软件Force测试](cases/CORDIC_P1_017.md)
- [CORDIC_P1_018 — CORDIC IRQ Mask/Unmask与Raw/Status分层测试](cases/CORDIC_P1_018.md)
- [CORDIC_P1_019 — CORDIC IRQ单Source精确清除隔离测试](cases/CORDIC_P1_019.md)
- [CORDIC_P1_020 — CORDIC多函数连续请求与结果对应测试](cases/CORDIC_P1_020.md)
- [CORDIC_P2_001 — CORDIC DMA工作模式真实搬运等价性测试](cases/CORDIC_P2_001.md)
- [CORDIC_P3_001 — CORDIC Float32代表节点重复稳定性测试](cases/CORDIC_P3_001.md)
- [CORDIC_P3_002 — CORDIC目标侧单次执行周期表征测试](cases/CORDIC_P3_002.md)
- [CORDIC_P3_003 — CORDIC零开销原子窗口抗IRQ干扰测试](cases/CORDIC_P3_003.md)

<!-- ET_RECORD_AUTO_END -->

注：索引中仅CORDIC_P2_001为SKIP（NOT_APPLICABLE，DMA工作模式），其余23个Case最近一次FPGA全量运行均PASS；此状态标记由人工维护，重跑`maintain_test_records.py index`会重新生成索引块并剥离条目后缀标记，届时刻意恢复。

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近运行（[芯片文档状态块](../../../../test_case_doc/cordic/ET6801_cordic.md)）：FPGA Lane，2026-08-28 17:11 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），24 Case/53 执行=23 PASS/1 SKIP/0 FAIL（状态块更新 2026-08-28 21:25 CST）。
- **【关键声明】原始Evidence 已随早期清理不在两个工作树**。本树依据芯片文档状态块与人读报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推。文档已明确记录并经复核确认的个别事实按来源标注（见P1_003案例知识）。
- 方法权威：[公共CORDIC契约](../../../../test_case_doc/cordic/cordic.md)各Case的`ET_CASE_SPEC`；芯片文档锚：[ET6801 CORDIC芯片文档](../../../../test_case_doc/cordic/ET6801_cordic.md)。
- 可引用报告：[2026-08-26 Scale7 ARCTAN金模型与缺陷分析](../../../../report/analysis/20260826_cordic_scale7_arctan_golden_model_and_defects.md)（Scale7 arctan金模型与缺陷分析；已明确记录的实测数值仅限该报告与芯片文档，本树不新增参数级观测值）。

## 未闭环问题

- [CORDIC_P2_001](cases/CORDIC_P2_001.md) SKIP（NOT_APPLICABLE）：Runtime Capability明确拒绝CORDIC DMA工作模式，Case未向硬件发起DMA刺激；2026-08-28设计人员确认ET6801 CORDIC不支持DMA工作模式。不是Case逻辑FAIL，也不是外部接线阻塞。复测条件：仅当设计人员重新确认ET6801硬件支持该模式时复测。

## 关键变化

- 2026-09-09 11:30 CST：建立CORDIC固定Case档案，按R500 §6从芯片文档状态块与人读历史报告提炼24个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
