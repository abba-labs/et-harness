# ET6801 UART Case知识

更新时间：2026-09-09 10:13 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖UART注册表全部33个已注册Case（P0×4、P1×17、P2×9、P3×3）。公共Case Catalog中另有7个未注册项（P3_001～006、P3_008：RS485/IrDA/低功耗SIR/位时序测量/访问保护，芯片文档第六章标为BENCH_GAP或NEEDS_VERIFICATION），无执行记录，不补造记录；本目录不表示公共UART全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [UART_P0_001 — 选定 UART 实例的运行时能力和身份信息测试](cases/UART_P0_001.md)
- [UART_P0_002 — UART 软件复位、默认配置和实例生命周期测试](cases/UART_P0_002.md)
- [UART_P0_003 — UART 内部回环的基本发送、接收和回环开关测试](cases/UART_P0_003.md)
- [UART_P0_004 — UART 逻辑 DUT 与 Peer 之间的双向基本收发测试](cases/UART_P0_004.md)
- [UART_P1_001 — DUT UART 实例隔离和独立复位测试](cases/UART_P1_001.md)
- [UART_P1_002 — UART RX data available 中断和事件计数测试](cases/UART_P1_002.md)
- [UART_P1_003 — UART TX empty 中断在发送完成阶段的触发和关闭测试](cases/UART_P1_003.md)
- [UART_P1_004 — UART RX FIFO 阈值中断边界测试](cases/UART_P1_004.md)
- [UART_P1_005 — UART TX FIFO 阈值中断边界测试](cases/UART_P1_005.md)
- [UART_P1_006 — UART character timeout 中断和低于阈值数据的收取测试](cases/UART_P1_006.md)
- [UART_P1_007 — UART 奇偶校验错误检测和恢复测试](cases/UART_P1_007.md)
- [UART_P1_008 — UART 停止位失配导致的 framing error 检测和恢复测试](cases/UART_P1_008.md)
- [UART_P1_009 — UART RX overrun 错误检测和 FIFO 恢复测试](cases/UART_P1_009.md)
- [UART_P1_010 — UART break 发送、接收检测和退出恢复测试](cases/UART_P1_010.md)
- [UART_P1_011 — UART 中断源的 mask 使能、关闭和 Service session 状态测试](cases/UART_P1_011.md)
- [UART_P1_012 — UART busy detect 中断、清除条件和恢复路径测试](cases/UART_P1_012.md)
- [UART_P1_013 — UART 发送 halt、resume 和数据路径恢复测试](cases/UART_P1_013.md)
- [UART_P1_014 — UART 数据位、停止位和校验方式的合法帧格式组合测试](cases/UART_P1_014.md)
- [UART_P1_015 — UART 代表性波特率配置和双向收发测试](cases/UART_P1_015.md)
- [UART_P1_016 — UART FIFO 配置、边界收发和状态快照测试](cases/UART_P1_016.md)
- [UART_P1_017 — UART 参数校验对非法输入的拒绝和合法路径恢复测试](cases/UART_P1_017.md)
- [UART_P2_001 — UART TX DMA 从内存到 UART TX 端点的单次传输测试](cases/UART_P2_001.md)
- [UART_P2_002 — UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输测试](cases/UART_P2_002.md)
- [UART_P2_003 — UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输测试](cases/UART_P2_003.md)
- [UART_P2_004 — UART 9-bit 软件数据双向收发及普通模式恢复测试](cases/UART_P2_004.md)
- [UART_P2_005 — UART 9-bit 硬件地址匹配和不匹配地址过滤测试](cases/UART_P2_005.md)
- [UART_P2_006 — UART RTS/CTS 自动流控的暂停和恢复测试](cases/UART_P2_006.md)
- [UART_P2_007 — UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态测试](cases/UART_P2_007.md)
- [UART_P2_008 — UART 软件复位后的实例身份和数据路径恢复测试](cases/UART_P2_008.md)
- [UART_P2_010 — UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径测试](cases/UART_P2_010.md)
- [UART_P3_007 — UART Shadow FIFO 配置（SFE/SRT/STET）测试](cases/UART_P3_007.md)
- [UART_P3_009 — UART Direct FIFO 访问（FAR/TFR/RFW）测试](cases/UART_P3_009.md)
- [UART_P3_010 — UART 双向混合收发 20 轮稳定性能力测试](cases/UART_P3_010.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次UART运行（[芯片文档状态块](../../../../test_case_doc/uart/ET6801_uart.md)）：FPGA Lane，2026-08-28 17:14 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），33 Case执行=30 PASS/3 SKIP/0 FAIL。其原始Evidence路径已不存在。
- **原始Canonical证据已不在仓库**：上述runs目录与2026-08-13报告引用的`artifacts/operator_hil/20260813_gui_pipeline/`在本机两个工作树均已随早期清理移除。本目录知识依据人读报告与芯片文档状态块整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推具体观测值；报告与状态块已明确记录的个别实测值（如P3_007 CPR）按来源标注。
- 三轮独立Case级结果交叉印证（均无本IP FAIL）：
  - 2026-08-10 公共层冻结全量HIL：Framework/UART/DMA合计121项，118 PASS/3 SKIP/0 FAIL，3个SKIP即本文档三个SKIP Case（[报告](../../../../report/validation/dut/20260810_et6801_pc_firmware_freeze_full_hil.md)）。
  - 2026-08-13 GUI完整Pipeline HIL：UART 33项，30 PASS/3 SKIP/0 FAIL，27.18s（[报告](../../../../report/hil/20260813_et6801_gui_pipeline_uart_hil_report.md)）。
  - 2026-08-28 UART全量运行：30 PASS/3 SKIP/0 FAIL（芯片文档状态块）。
- 环境身份（来自08-13报告）：固件Target `ET6801_SILICON_FLASH`、build ID `et6801-silicon-common-v0.1`；Bench `pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`；功能链路UART1/UART2交叉短接（J25.3←J30.5、J25.5→J30.3），控制链路J28 RS232 COM12 115200-8-N-1；08-28轮的bitstream与板卡身份未记录。
- 修复史：[P2-010与P3-007独立HIL](../../../../report/validation/dut/20260805_uart_split_cases_hil.md)（P2_010两次FAIL定位记录）、[9-bit地址中断Driver修复HIL](../../../../report/validation/dut/20260805_uart_address_irq_driver_fix_hil.md)（P2_010修复与IRQ回归）；早期链路层验证见[正式PFLASH启动与UART公共框架HIL](../../../../report/validation/dut/20260726_et6801_formal_flash_uart_hil.md)、[UART协议可靠性](../../../../report/validation/dut/20260724_et6801_uart_protocol_reliability.md)。
- 方法权威：[公共UART契约](../../../../test_case_doc/uart/uart.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 UART芯片文档](../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)。

## 未闭环问题

- [UART_P1_008](cases/UART_P1_008.md)：当前TX/RX交叉连线无法确定性制造framing error，三轮一致SKIP（正式门禁判定，非FAIL）。复测条件：可控错误帧发生器、FPGA波形发生器或可精确破坏停止位的Peer。
- [UART_P1_012](cases/UART_P1_012.md)：FIFO开启持续发送期间修改LCR，Driver有界触发窗口内未形成确定性Busy Detect，三轮一致SKIP。复测条件：取得ET6801 Busy Detect准确触发时序，或使用可控制发送与LCR写入相位的刺激。
- [UART_P3_009](cases/UART_P3_009.md)：ET6801当前UART组件Capability未声明Direct FIFO Access，Case未执行FAR/TFR/RFW访问，三轮一致SKIP。复测条件：后续RTL/芯片Capability明确支持Direct FIFO Access。

## 关键变化

- 2026-09-09 10:13 CST：建立UART固定Case档案，按R130 §8.1与R500 §6从人读历史报告与芯片文档状态块提炼33个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
