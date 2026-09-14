# 报告目录索引

`report/` 是平台代码仓库内正式、可审阅、可长期维护的人读文档库。它只保存结论、方法、设计和计划；日志、波形、截图、构建输出和自动生成报告放在仓库内 `artifacts/`，不复制到本目录。

本文件是 `report/` 的唯一人工索引入口。子目录不另建平行总索引；新增文档应在这里补充链接或分类说明。

## 当前软件交付状态

当前活动任务、最新工作树门禁和剩余风险只在外层
`project-control/work/ACTIVE.md` 维护。本索引不复制易漂移的测试数量或当前SHA状态。
历史构建、HIL和阶段结论保留在下方对应报告中；它们不得自动升级为当前SHA的PASS。

当前阶段结论见：

- [公共层冻结收口](final/20260811_public_layer_freeze_closure.md)
- [PC公共层与UART/DMA Driver收敛阶段收口报告](final/20260809_pc_driver_convergence_phase_closure.md)
- [ET自动化测试平台重构交付报告（2026-08-06/07历史结构重构闭环）](final/20260806_refactor_final_report.md)

说明：现行规则正文和Owner只由`design/rule_owner_catalog.yaml`与`design/rules/`共同登记。
计划、分析、Review和历史记录不具备现行规则权威。

## 固定目录与职责

```text
report/
├── README.md
├── design/
│   ├── rule_owner_catalog.yaml     # 规则Owner与文档机器索引
│   └── rules/Rxxx_<topic>.md       # 唯一活动规则正文
├── plans/                          # 实施、整改和测试执行计划
├── analysis/                       # 芯片/IP 演进、问题调查、技术评审与根因分析
├── review/                         # 代码审查、架构一致性检查和问题闭环记录
├── build/                          # 实际构建记录；未执行必须明确标记
├── hil/                            # 本轮真实硬件闭环记录
├── test_records/                   # 按测试主题长期归档的定点测试记录与详情
├── Weekly_report/                  # 周报；按YYYYMMDD_weekly_report.md命名
├── final/                          # 跨阶段交付结论与剩余硬件验证状态
├── validation/
│   ├── fpga/                       # FPGA 原型与能力验证报告
│   ├── dut/                        # MCU DUT 的固件、IP、Flash、UART、DMA 等验证报告
│   └── framework/                  # PC/固件协议、框架边界、构建与可靠性验证报告
└── archive/                        # 已替代或仅需追溯的历史文档
```

`design/rules/`只允许活动规则正文；计划、分析、Review和历史记录不得进入该目录，也不得使用Rxxx编号。

## 当前索引

### 设计

现行规则正文按责任域编号；正文的Owner和机器门禁以`design/rule_owner_catalog.yaml`为准：

- 治理与导航：[R001](design/rules/R001_agent_rule_governance.md)、[R002](design/rules/R002_task_context_navigation.md)
- 周报编写：[R003](design/rules/R003_weekly_report_authoring.md)
- 公共IP契约：[R100](design/rules/R100_public_ip_semantics_and_chip_adaptation.md)、[R110](design/rules/R110_contract_document_sync.md)、[R120](design/rules/R120_public_ip_machine_contract.md)、[R130](design/rules/R130_canonical_result_evidence.md)、[R140](design/rules/R140_ip_analysis_workflow.md)
- PC：[R200](design/rules/R200_pc_layer_responsibilities.md)、[R210](design/rules/R210_pc_case_responsibility.md)、[R220](design/rules/R220_python_style_quality.md)
- Firmware：[R300](design/rules/R300_firmware_service.md)、[R310](design/rules/R310_firmware_wrap.md)、[R320](design/rules/R320_interrupt_subsystem.md)
- Firmware手动诊断：[R340](design/rules/R340_firmware_manual_diagnostics.md)
- 协议与能力：[R400](design/rules/R400_et_frame_v1.md)、[R410](design/rules/R410_capability_v2.md)
- 执行流水线：[R500](design/rules/R500_operator_pipeline.md)
- 配测设备与仪器：[R600](design/rules/R600_companion_platform.md)

### Review

- [CAN P1/P2 极简重构：开发 Agent 执行指导与验收标准](review/chatgpt_review/can/003_can_p1_p2_agent_execution_guide.md)（实施指导，非完成报告）
- [CAN 极简重构方案与复核入口](review/chatgpt_review/README.md)（包含旧稿替代关系）
- [平台公共层冻结前软件收口Review](review/20260810_platform_freeze_convergence_review.md)
- [Formal Case P级别与ID迁移记录](review/20260810_formal_case_id_migration_review.md)
- [平台代码评审记录](review/20260805_platform_code_review.md)
- [UART全链路代码评审](review/20260805_uart_full_chain_code_review.md)
- [UART可靠性整改完成Review](review/20260805_uart_reliability_remediation_review.md)
- [DMA全链路代码评审与优化设计](review/20260805_dma_full_chain_code_review.md)
- [DMA第二轮代码复核与最终整改边界](review/20260805_dma_second_round_code_review.md)
- [DMA可靠性整改完成Review](review/20260805_dma_reliability_remediation_review.md)
- [公共层、UART与DMA架构一致性复核](review/20260805_common_uart_dma_architecture_re_review.md)
- [公共层、UART与DMA整改完成Review](review/20260806_common_uart_dma_remediation_review.md)
- [Phase 6最终交付Review](review/20260806_phase6_final_delivery_review.md)
- [软件层最终重构Review](review/20260807_software_layer_final_review.md)

### 计划

- [Case知识贡献机制与三份CAN样稿（待确认，非现行规则）](plans/20260908_case_knowledge_contribution_plan.md)
- [ET6801 FAIL Case分类整改与复测计划](plans/20260827_et6801_fail_case_remediation_plan.md)
- [平台公共层冻结前收口实施计划](plans/20260810_platform_freeze_convergence_plan.md)
- [ET自动化测试平台重构主实施计划](plans/20260806_refactor_master_execution_plan.md)
- [PC控制面与Firmware执行面重构实施计划](plans/20260806_pc_firmware_trust_boundary_refactor_plan.md)
- [DMA Unskip Case实施计划](plans/2026-08-03-dma-unskip-cases.md)
- [框架边界整改计划](plans/2026-08-04-framework-boundary-cleanup.md)
- [UART Case实施计划](plans/2026-08-04-uart-case-implementation.md)
- [UART可测试Case与HIL计划](plans/2026-08-04-uart-testable-cases-hil.md)
- [UART合规整改计划](plans/2026-08-05-uart-compliance-remediation.md)
- [UART Feature拆分实施计划](plans/2026-08-05-uart-feature-split-implementation.md)
- [Report文档迁移计划](plans/20260805_report_repository_migration_plan.md)

### 分析

- [Agent规则控制面研究（非现行规则）](analysis/20260813_agent_rule_control_plane_research.md)
- [ET MCU芯片共性、差异与自动化测试平台分析](analysis/20260702_chip_commonality_ip_automation_analysis.md)
- [ET6002/6003/3101/6801 SDK与IP演进分析](analysis/20260722_et6002_6003_3101_6801_sdk_ip_evolution.md)
- [XC7Z045以太网数据通路问题调查](analysis/20260722_xc7z045_ethernet_data_path_investigation.md)

### FPGA验证

- [XC7Z045 Fabric BIST](validation/fpga/20260721_xc7z045_fabric_bist.md)
- [XC7Z045 J58/J59边界回环](validation/fpga/20260721_xc7z045_j58_j59_boundary_loopback.md)
- [XC7Z045 DDR容量抽样](validation/fpga/20260722_xc7z045_ddr_capacity_smoke.md)
- [XC7Z045 DDR与L2自检](validation/fpga/20260722_xc7z045_ddr_l2_selftest.md)
- [XC7Z045 Ethernet PHY/MDIO Smoke](validation/fpga/20260722_xc7z045_ethernet_phy_mdio_smoke.md)
- [XC7Z045 JTAG扩展测试](validation/fpga/20260722_xc7z045_jtag_extended_tests.md)
- [XC7Z045 JTAG-only Fabric BIST](validation/fpga/20260722_xc7z045_jtag_only_fabric_bist.md)
- [XC7Z045 JTAG Transport基准](validation/fpga/20260722_xc7z045_jtag_transport_benchmark.md)
- [XC7Z045 CPU与Cache自检](validation/fpga/20260722_xc7z045_ps_cpu_cache_selftest.md)
- [ET6801/XC7VX980T命令行部署与GPIO验证](validation/fpga/20260723_et6801_xc7vx980t_cli_deploy_flash_gpio.md)
- [XC7Z045新板复测](validation/fpga/20260723_xc7z045_board_revalidation.md)

### DUT验证

- [ET6801 UART协议可靠性](validation/dut/20260724_et6801_uart_protocol_reliability.md)
- [ET6801正式Flash启动与UART HIL](validation/dut/20260726_et6801_formal_flash_uart_hil.md)
- [ET6801 DMA中断硬件前验证](validation/dut/20260727_et6801_dma_irq_pre_hardware_validation.md)
- [ET6801 DMA Transfer Done中断HIL](validation/dut/20260727_et6801_dma_transfer_done_irq_hil.md)
- [ET6801 DMA全Feature HIL](validation/dut/20260802_et6801_dma_all_features_hil.md)
- [ET6801 DMA动态能力HIL](validation/dut/20260802_et6801_dma_dynamic_capability_hil.md)
- [ET6801 DMA与UART外设链路HIL](validation/dut/20260802_et6801_dma_uart_peripheral_hil.md)
- [ET6801 DMA UART1/UART2全量HIL](validation/dut/20260803_et6801_dma_uart_pair_full_hil.md)
- [ET6801 UART地址中断修复HIL](validation/dut/20260805_uart_address_irq_driver_fix_hil.md)
- [ET6801 UART拆分Case HIL](validation/dut/20260805_uart_split_cases_hil.md)
- [ET6801 PC/Firmware公共层收口与全量HIL](validation/dut/20260810_et6801_pc_firmware_freeze_full_hil.md)

### 框架验证

- [公共命令协议与Framework Service实现验证](validation/framework/20260724_framework_service_protocol_implementation.md)
- [公共框架与ET-Frame可靠性评审](validation/framework/20260725_framework_protocol_reliability_review.md)
- [Framework边界整改验证](validation/framework/20260804_framework_boundary_cleanup.md)

### 本轮构建、HIL与最终交付

- [ET6801 Keil实际构建报告](build/20260806_et6801_keil_build_report.md)
- [ET6801真实HIL执行报告](hil/20260806_et6801_hil_report.md)
- [ET6801 CRC全量HIL验证报告](hil/20260811_et6801_crc_hil_report.md)
- [ET6801 CRC一键运行与Excel报告HIL验证](hil/20260812_et6801_crc_operator_excel_hil_report.md)
- [ET6801 GUI配置、完整Pipeline与UART HIL验证](hil/20260813_et6801_gui_pipeline_uart_hil_report.md)
- [ET6801 UART/DMA结构化观测与报告HIL验证](hil/20260813_et6801_uart_dma_observation_report_hil.md)
- [公共层冻结收口](final/20260811_public_layer_freeze_closure.md)
- [PC公共层与UART/DMA Driver收敛阶段收口报告](final/20260809_pc_driver_convergence_phase_closure.md)
- [ET自动化测试平台重构交付报告（历史结构重构闭环）](final/20260806_refactor_final_report.md)

### 定点测试记录

- [UART/DMA 按测试等级归档后的 HIL](test_records/case_layout/20260809_uart_dma_level_layout_hil.md)
- [review_code@bf940723 UART DMA TX HIL](test_records/uart_dma_tx/20260808_review_code_bf940723_uart_dma_tx_hil.md)
- [review_code@fc6a1ebb 全量HIL](test_records/full_hil/20260808_review_code_fc6a1ebb_full_hil.md)

### 周报

- [2026-09-07 周报](Weekly_report/20260907_weekly_report.md)
- [2026-08-26 周报](Weekly_report/20260826_weekly_report.md)
- [2026-08-24 周报](Weekly_report/20260824_weekly_report.md)

### 历史归档

- [文档迁移清单](archive/20260805_document_migration_manifest.md)
- [历史MCU HIL/SIL通用方案](archive/mcu_hil_sil_unified_test_platform.md)
- [旧设计目录索引](archive/legacy_docs_design_index.md)
- [旧架构设计HTML导出](archive/ET%20测试平台架构设计.dc.html)
- [旧软件设计HTML导出](archive/ET%20测试平台软件设计文档.dc.html)

### 历史阶段计划与Review（非现行规则）

以下文件只保留当时的实施意图和阶段结论。未勾选事项、旧Skill提示和旧架构描述均不作为当前开发指令；
当前开发只能从`AGENTS.md -> Task Context -> Rxxx`进入。

- [UART可靠性整改历史计划](plans/20260805_uart_reliability_remediation_plan.md)
- [Phase 0～2第一批Review](review/20260806_phase0_2_first_batch_review.md)
- [Phase 3 DMA PC Package Review](review/20260806_phase3_dma_pc_package_review.md)
- [Phase 4架构映射Review](review/20260806_phase4_architecture_mapping_review.md)
- [Phase 5可靠性收口Review](review/20260806_phase5_reliability_package_review.md)
- [剩余三阶段重排记录](review/20260806_three_remaining_phases_replan.md)
- [最终合规收口记录](review/20260807_final_compliance_closure.md)

## 新增文档放置与命名

- 新增或修改活动规则：按R001进入`design/rules/Rxxx_<topic>.md`
- 非规则技术设计与方案比较：`analysis/YYYYMMDD_<scope>_<topic>_analysis.md`
- 实施或测试计划：`plans/YYYYMMDD_<scope>_<topic>_plan.md`
- 技术分析：`analysis/YYYYMMDD_<scope>_<topic>_analysis.md`
- 代码评审：`review/YYYYMMDD_<scope>_code_review.md`
- 验证报告：`validation/<fpga|dut|framework>/YYYYMMDD_<scope>_<topic>.md`
- 实际构建：`build/YYYYMMDD_<target>_<topic>_report.md`
- 本轮HIL：`hil/YYYYMMDD_<target>_<topic>_report.md`
- 定点测试记录：`test_records/<topic>/YYYYMMDD_<source>_<topic>_<lane>.md`
- 周报：`Weekly_report/YYYYMMDD_weekly_report.md`
- 最终交付：`final/YYYYMMDD_<scope>_final_report.md`
- 被替代文档：移入 `archive/`，并注明替代关系。

文件名使用小写英文、数字和下划线；验证报告应包含目标、环境、方法、结果、证据相对路径和剩余风险；未实际执行的内容不得写成硬件 PASS。
