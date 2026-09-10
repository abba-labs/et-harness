# ET6801 DMA Case知识

更新时间：2026-09-09 11:30 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖DMA注册表全部28个已注册Case（P0×2、P1×13、P2×12、P3×1）。公共Case Catalog共39个Case，其中11个未注册项（P1_002、P1_003、P2_003、P2_007、P2_014、P3_001～006：优先级仲裁、Suspend/Resume、LLI无效节点、Bus Error、TCM地址视图、AHB Master、Protection、Flow Controller、Low-Power Timeout、DFT Test Slave）在芯片文档第六章标为IMPLEMENTATION_GAP、MAPPING_GAP或NEEDS_VERIFICATION，注册表未纳入、无执行记录，不补造记录；本目录不表示公共DMA全部测试目标已实现。本轮无FAIL/SKIP记录。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [DMA_P0_001 — DMA声明实例的运行时能力、组件身份与逐Channel静态参数一致性测试](cases/DMA_P0_001.md)
- [DMA_P0_002 — DMA Controller/Channel基础生命周期、空闲分配与重复M2M恢复测试](cases/DMA_P0_002.md)
- [DMA_P1_001 — DMA全部可用Channel原子并发启动与独立数据一致性测试](cases/DMA_P1_001.md)
- [DMA_P1_004 — DMA TRANSFER_DONE分类中断、数据完成与Channel终态一致性测试](cases/DMA_P1_004.md)
- [DMA_P1_005 — DMA单节点LLI的BLOCK_DONE中断与边界Channel行为测试](cases/DMA_P1_005.md)
- [DMA_P1_006 — DMA TRANSFER_DONE的RAW/STATUS/MASK/CLEAR状态机测试](cases/DMA_P1_006.md)
- [DMA_P1_007 — DMA Source/Destination/双端Reload连续Block与BLOCK_DONE测试](cases/DMA_P1_007.md)
- [DMA_P1_008 — DMA Source Gather Interval/Count与目标布局测试](cases/DMA_P1_008.md)
- [DMA_P1_009 — DMA Destination Scatter Interval/Count与目标布局测试](cases/DMA_P1_009.md)
- [DMA_P1_010 — DMA M2M Single/Half-Depth FIFO Mode配置读回与数据测试](cases/DMA_P1_010.md)
- [DMA_P1_011 — DMA LLI Descriptor DONE完成状态写回测试](cases/DMA_P1_011.md)
- [DMA_P1_014 — DMA M2M传输宽度与源/目标地址模式组合测试](cases/DMA_P1_014.md)
- [DMA_P1_015 — DMA M2M Block Count边界与Source/Destination Burst配置读回测试](cases/DMA_P1_015.md)
- [DMA_P1_016 — DMA受Resource管理SRAM Buffer的M2M数据完整性与TRANSFER_DONE测试](cases/DMA_P1_016.md)
- [DMA_P1_017 — DMA非法配置拒绝边界与同Controller恢复测试](cases/DMA_P1_017.md)
- [DMA_P2_001 — DMA双端LLI 2/3/4块有限Descriptor Chain传输测试](cases/DMA_P2_001.md)
- [DMA_P2_002 — DMA单侧Source/Destination LLI地址更新测试](cases/DMA_P2_002.md)
- [DMA_P2_004 — DMA Combined IRQ路由下TRANSFER_DONE交付与M2M数据测试](cases/DMA_P2_004.md)
- [DMA_P2_005 — UART RX DMA的P2M SOURCE_TRANSACTION+TRANSFER_DONE中断测试](cases/DMA_P2_005.md)
- [DMA_P2_006 — UART TX DMA的M2P DESTINATION_TRANSACTION+TRANSFER_DONE中断测试](cases/DMA_P2_006.md)
- [DMA_P2_008 — DMA M2P在1/17/257 Byte下的UART TX硬件握手数据路径测试](cases/DMA_P2_008.md)
- [DMA_P2_009 — DMA P2M在1/17/257 Byte下的UART RX硬件握手数据路径测试](cases/DMA_P2_009.md)
- [DMA_P2_010 — DMA P2P双UART Route在1/17/257 Byte下的数据路径测试](cases/DMA_P2_010.md)
- [DMA_P2_011 — DMA Destination Software Handshake逐Item Request推进测试](cases/DMA_P2_011.md)
- [DMA_P2_012 — UART TX Endpoint的Hardware/Software DMA Handshake Mode因果对照测试](cases/DMA_P2_012.md)
- [DMA_P2_013 — DMA NORMAL/ACC组件访问别名一致性测试](cases/DMA_P2_013.md)
- [DMA_P2_015 — DMA经CRG Clock Gate/Reset后的M2M恢复测试](cases/DMA_P2_015.md)
- [DMA_P3_007 — DMA 20轮跨实例/Channel/Count/Width/Burst/FIFO混合M2M稳定性测试](cases/DMA_P3_007.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近运行=FPGA Lane 2026-08-28 17:12 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），28 Case/88 执行=28 PASS/0 FAIL/0 SKIP（[芯片文档状态块](../../../../test_case_doc/dma/ET6801_dma.md)，更新 2026-08-28 21:22 CST）。
- **原始Canonical证据已不在仓库**：Evidence路径`artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/dma/`已随早期清理不在两个工作树。本目录知识依据芯片文档状态块与人读报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推具体观测值；本树所有参数级数值均只来自公共契约SPEC或芯片文档状态块的明确文字。
- 三轮独立Case级结果交叉印证（均无本IP FAIL）：
  - 2026-08-03 ET6801 FPGA DMA HIL：当时可安全执行实例68 PASS/0 FAIL/9 SKIP（芯片文档第四章Historical Evidence）。
  - 2026-08-10 公共层冻结全量HIL：Framework/UART/DMA合计121项，118 PASS/3 SKIP/0 FAIL，3个SKIP均为UART Case（[报告](../../../../report/validation/dut/20260810_et6801_pc_firmware_freeze_full_hil.md)），DMA无FAIL/SKIP。
  - 2026-08-13 UART+DMA观测HIL（[报告](../../../../report/hil/20260813_et6801_uart_dma_observation_report_hil.md)）与2026-08-28 DMA全量运行（芯片文档状态块）均无DMA FAIL。
- 方法权威：[公共DMA契约](../../../../test_case_doc/dma/dma.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 DMA芯片文档](../../../../test_case_doc/dma/ET6801_dma.md)。
- 可引用的人读报告：[DMA IRQ预硬件验证](../../../../report/validation/dut/20260727_et6801_dma_irq_pre_hardware_validation.md)、[TRANSFER_DONE IRQ HIL](../../../../report/validation/dut/20260727_et6801_dma_transfer_done_irq_hil.md)、[DMA全Feature HIL](../../../../report/validation/dut/20260802_et6801_dma_all_features_hil.md)、[DMA动态能力HIL](../../../../report/validation/dut/20260802_et6801_dma_dynamic_capability_hil.md)、[DMA UART外设HIL](../../../../report/validation/dut/20260802_et6801_dma_uart_peripheral_hil.md)、[DMA UART Pair全链HIL](../../../../report/validation/dut/20260803_et6801_dma_uart_pair_full_hil.md)、[UART+DMA观测HIL](../../../../report/hil/20260813_et6801_uart_dma_observation_report_hil.md)；修复/评审史补充：[DMA优化收口评审](../../../../report/review/20260819_dma_optimization_closure_review.md)、[DMA契约人工冻结评审](../../../../report/review/20260819_dma_contract_human_review.md)、[Gather/Scatter上限修复（芯片文档2.3，2026-07-26）](../../../../test_case_doc/dma/ET6801_dma.md)。

## 未闭环问题

本轮无FAIL/SKIP记录。公共契约中的OPEN GAP与11个未注册PLAN项（见定位段）仍属未实现测试目标，不在本目录补造记录。

## 关键变化

- 2026-09-09 11:30 CST：建立DMA固定Case档案，按R130 §8.1与R500 §6从人读历史报告与芯片文档状态块提炼28个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
