# ET6801 AES Case知识

更新时间：2026-09-09 11:30 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖AES注册表全部26个已注册Case（P0×3、P1×17、P2×3、P3×3），与公共AES契约26个Formal Case一一对应，无未注册Case。本次为知识迁移整理，不是新增测试；未执行任何测试或硬件动作。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [AES_P0_001 — AES身份与运行时能力门禁测试](cases/AES_P0_001.md)
- [AES_P0_002 — AES标准向量加解密正确性测试](cases/AES_P0_002.md)
- [AES_P0_003 — AES关闭后重新使能与恢复运算测试](cases/AES_P0_003.md)
- [AES_P1_001 — AES ECB/CBC 填充输出契约测试](cases/AES_P1_001.md)
- [AES_P1_002 — AES CBC/CTR IV读回与算法影响测试](cases/AES_P1_002.md)
- [AES_P1_003 — AES高位数据长度读回与运算终态测试](cases/AES_P1_003.md)
- [AES_P1_004 — AES LITTLE/BIG字节序 canonical 输出测试](cases/AES_P1_004.md)
- [AES_P1_005 — AES CTR初始Counter运算测试](cases/AES_P1_005.md)
- [AES_P1_006 — AES非DMA输入请求状态测试](cases/AES_P1_006.md)
- [AES_P1_007 — AES非DMA输出请求与块读取测试](cases/AES_P1_007.md)
- [AES_P1_008 — AES FINISH状态置位与W1C清除测试](cases/AES_P1_008.md)
- [AES_P1_009 — AES输出冲突IRQ触发与恢复测试](cases/AES_P1_009.md)
- [AES_P1_010 — AES Key缺失IRQ触发与清除测试](cases/AES_P1_010.md)
- [AES_P1_011 — AES IV缺失IRQ触发与清除测试](cases/AES_P1_011.md)
- [AES_P1_012 — AES正常完成IRQ与清除测试](cases/AES_P1_012.md)
- [AES_P1_013 — AES未完成关闭IRQ与恢复运算测试](cases/AES_P1_013.md)
- [AES_P1_014 — AES IRQ传输会话状态与数据路径测试](cases/AES_P1_014.md)
- [AES_P1_015 — AES IRQ Force投递与清除测试](cases/AES_P1_015.md)
- [AES_P1_016 — AES IRQ Mask/Unmask语义测试](cases/AES_P1_016.md)
- [AES_P1_017 — AES IRQ单Source精确清除测试](cases/AES_P1_017.md)
- [AES_P2_001 — AES DMA Request Gate传递测试](cases/AES_P2_001.md)
- [AES_P2_002 — AES DMA REGISTER模式双向传输测试](cases/AES_P2_002.md)
- [AES_P2_003 — AES DMA FIFO模式双向传输测试](cases/AES_P2_003.md)
- [AES_P3_001 — AES八轮确定性与状态隔离测试](cases/AES_P3_001.md)
- [AES_P3_002 — AES CPU路径目标周期测量测试](cases/AES_P3_002.md)
- [AES_P3_003 — AES DMA路径目标周期测量测试](cases/AES_P3_003.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次AES运行（[芯片文档状态块](../../../../test_case_doc/aes/ET6801_aes.md)）：FPGA Lane，2026-08-28 17:13 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），26 Case/59 执行=26 PASS/0 FAIL/0 SKIP（状态块更新 2026-08-28 21:20 CST）。
- **原始Canonical证据已不在仓库**：原始Evidence `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/aes/` 已随早期清理不在两个工作树。本树知识依据芯片文档状态块与人读报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推具体观测值；芯片文档与人读报告已明确记录的个别事实按来源标注。
- 文档化历史结果链（均有在库依据）：
  - 2026-08-19 [AES试点最终评审](../../../../report/plans/20260819_aes_pilot_final_review.md)：当时历史FPGA记录59执行=56 PASS/3 FAIL（AES_P1_009、AES_P2_003、AES_P3_003）。
  - 2026-08-20 当次运行（芯片文档第七章）：59执行=58 PASS/1 FAIL，当次FAIL为AES_P1_009（旧CPU双输入刺激）。
  - 2026-08-28 08:08 AES_P1_009整改闭环（芯片文档7.1）：改用FIFO DMA输出Busy冲突刺激定向HIL PASS，`ISR.LATCHED.OUTPUT_CONFLICT=1`、`event_count 0→1`按该记录标注。
  - 2026-08-28 17:13 全量运行：26 Case/59 执行=26 PASS/0 FAIL/0 SKIP（芯片文档状态块）。
- 评审过程报告（AES试点/证据评审，非规则、非运行结论）：[最小硬件证明集审查](../../../../report/plans/20260818_aes_minimum_hardware_proofset_review.md)（已被证据闭环评审取代，仅历史记录）、[AES试点最终评审](../../../../report/plans/20260819_aes_pilot_final_review.md)、[AES证据闭环评审](../../../../report/plans/20260819_aes_evidence_closure_review.md)（26 Case分类：CLOSED=6/RECORD_ONLY=19/CASE_CHANGE=1）。
- 方法权威：[公共AES契约](../../../../test_case_doc/aes/aes.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 AES芯片文档](../../../../test_case_doc/aes/ET6801_aes.md#aes-record-index)。

## 未闭环问题

- 本轮（2026-08-28 17:13 全量运行）无FAIL/SKIP记录（状态块26 PASS/0 FAIL/0 SKIP）；本目录未新增未闭环问题。各Case的复测要点与判断边界见对应Case知识。

## 关键变化

- 2026-09-09 11:30 CST：建立AES固定Case档案，按R130 §8.1与R500 §6从芯片文档状态块与人读历史报告提炼26个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
