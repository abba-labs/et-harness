# [R010] Project Governance Rules

## [R010.010] Governance And Task Navigation

### [R010.010.010] Repository Constitution Must Be Applied

Level: MUST
When: 每个非平凡任务开始、恢复或实质扩围时
Rule: 必须先应用AGENTS.md中的项目总约束；公共插件Context是执行载体，不得替代项目宪法。
Refs: AGENTS.md, A010.010.010, K001.001

### [R010.010.020] Task Context Must Be Compiled

Level: MUST
When: 新的非平凡任务开始或任务范围实质扩大时
Rule: 必须按R002通过现有Task Context链路解析模块、规则Owner、读取范围、写入范围和验证入口；路由缺失必须失败关闭。
Refs: report/design/rules/R002_task_context_navigation.md, project-governance/README.md, A010.010.020, K001.003, K001.004, G010.010.010

### [R010.010.030] Scope Check Must Precede Validation

Level: MUST
When: 当前任务产生代码、配置、规则、文档或工具变化并准备进入验证时
Rule: 必须先执行现有Task Context scope-check，确认所有新增变化位于write_scope.allowed；不得用后续测试PASS掩盖越界修改。
Refs: report/design/rules/R002_task_context_navigation.md, AGENTS.md, A010.010.020, K001.005, G010.010.020

### [R010.010.040] Public Main Must Not Receive Project Work

Level: MUST_NOT
When: 创建分支、提交、推送或合并 ATP 项目变化时
Rule: 禁止把 ATP 项目变化直接写入公共main，或把项目分支整体反向合入main；项目任务和测试分支必须基于project/automated-testing-platform。
Refs: MIGRATION_BOUNDARY.md, A010.010.010, K001.011

## [R010.020] Contract Source And Evidence

### [R010.020.010] Public Overlay Must Not Become A Second Rule Source

Level: MUST_NOT
When: 新增或维护本Project Plugin的Architecture、Rule、Knowledge或Gate资源时
Rule: 禁止在公共插件投影视图中复制专项规则正文或重新定义Owner；必须以短路由指向AGENTS.md、rule_owner_catalog和对应Rxxx正文。
Refs: agent_harness/projects/automated_testing_platform/README.md, report/design/rules/R001_agent_rule_governance.md, A010.010.030, K001.002, K001.007

### [R010.020.020] Contract Changes Must Follow Existing Owners

Level: MUST
When: 修改公共IP语义、芯片适配、机器契约、Case计划或相关文档时
Rule: 必须根据rule_owner_catalog路由R100、R110、R120和R140的当前Owner正文，并同步其要求的项目契约资源。
Refs: report/design/rule_owner_catalog.yaml, report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md, report/design/rules/R110_contract_document_sync.md, report/design/rules/R120_public_ip_machine_contract.md, report/design/rules/R140_ip_analysis_workflow.md, A010.020.010

### [R010.020.030] Evidence Classes Must Not Substitute For Each Other

Level: MUST_NOT
When: 描述、记录或判断软件、Keil、FPGA、SIL或HIL验证结果时
Rule: 禁止把未执行项写成PASS，也禁止用一种Backend或验证层级的Evidence替代另一种；结论必须与实际执行来源一致。
Refs: AGENTS.md, report/design/rules/R130_canonical_result_evidence.md, A010.030.030, A010.060, K001.008

### [R010.020.040] Historical Material Must Not Override Active Rules

Level: MUST_NOT
When: 使用report/plans、report/review或report/archive作为任务依据时
Rule: 禁止把计划、评审记录或归档材料当成活动规则；发生冲突时必须返回AGENTS.md、活动Rxxx正文和当前源码测试。
Refs: AGENTS.md, K001.012

## [R010.030] PC Platform Owner Routing

### [R010.030.010] PC Layer Changes Must Use R200

Level: MUST
When: 修改PC Core、Client、Backend、Communication、Scheduling、Profile或Result边界时
Rule: 必须读取R200及pc-platform模块画像，保持项目定义的稳定依赖方向和公共层职责。
Refs: report/design/rules/R200_pc_layer_responsibilities.md, project-governance/modules/pc-platform.yaml, A010.030

### [R010.030.020] Formal Case Changes Must Use R210

Level: MUST
When: 修改Formal Case、Case注册、Fixture、断言、清理或Case到Driver的编排时
Rule: 必须读取R210和公共IP机器契约；Case职责、Evidence与实现同步不得由本投影自行重新解释。
Refs: report/design/rules/R210_pc_case_responsibility.md, report/design/rules/R120_public_ip_machine_contract.md, A010.020.020, A010.030.030

### [R010.030.030] Python Changes Must Use R220

Level: MUST
When: 修改项目Python代码、注释、文档或质量Checker时
Rule: 必须读取R220并运行Task Context列出的最小专项检查；禁止通过弱化Checker、断言或覆盖使门禁通过。
Refs: report/design/rules/R220_python_style_quality.md, AGENTS.md, project-governance/modules/pc-platform.yaml

## [R010.040] Firmware Platform Owner Routing

### [R010.040.010] Service Changes Must Use R300

Level: MUST
When: 修改Firmware Service接口、注册、命令解析或执行边界时
Rule: 必须读取R300和firmware-platform模块画像，保持项目当前Service职责与公共协议边界。
Refs: report/design/rules/R300_firmware_service.md, project-governance/modules/firmware-platform.yaml, A010.040.020

### [R010.040.020] Wrap Changes Must Use R310

Level: MUST
When: 修改Firmware Wrap接口、实现、Chip Config或Wrap到Chip Driver的调用时
Rule: 必须读取R310和目标模块画像；公共Wrap与芯片适配事实不得在本Project Plugin中重新定义。
Refs: report/design/rules/R310_firmware_wrap.md, project-governance/modules/ip-package.yaml, A010.020.030, A010.040.020

### [R010.040.030] IRQ Changes Must Use R320

Level: MUST
When: 修改中断注册、分发、捕获、清理或IRQ公共类型时
Rule: 必须读取R320并执行Task Context路由的IRQ契约验证，禁止把相邻模块测试替代IRQ专项验证。
Refs: report/design/rules/R320_interrupt_subsystem.md, project-governance/modules/firmware-platform.yaml, A010.040.020

### [R010.040.040] Platform C Changes Must Use R330 And R340 Where Applicable

Level: MUST
When: 修改平台自有Firmware C源码、格式配置、Manual Test或C质量Checker时
Rule: 必须读取R330；涉及Manual Test时还必须读取R340，并保持其职责、格式、注释、语义常量和验证要求。
Refs: report/design/rules/R330_firmware_c_style.md, report/design/rules/R340_firmware_manual_diagnostics.md, AGENTS.md, A010.040.030

## [R010.050] Protocol Capability And Adaptation

### [R010.050.010] Wire Changes Must Use R400

Level: MUST
When: 修改ET-Frame、Transport、事务、重试、PC/Firmware协议或Golden Vector时
Rule: 必须读取R400，并同时验证PC、Firmware和Golden Vector要求的契约链；单侧测试不得授权Wire变化。
Refs: report/design/rules/R400_et_frame_v1.md, AGENTS.md, A010.030.020, A010.040.010

### [R010.050.020] Capability Changes Must Use R410

Level: MUST
When: 修改Capability生成、Profile、查询、Execution Mapping或芯片能力事实时
Rule: 必须读取R410及对应模块画像，并保持公共Capability语义与芯片适配事实分离。
Refs: report/design/rules/R410_capability_v2.md, project-governance/modules/ip-package.yaml, project-governance/modules/pc-platform.yaml, A010.020.040

### [R010.050.030] Public And Chip Facts Must Remain Separated

Level: MUST
When: 新增IP、芯片、Board、Capability、Driver、Service或Wrap相关变化时
Rule: 必须按R100和R110区分公共IP语义与芯片事实，并同步其Owner要求的公共或芯片文档。
Refs: report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md, report/design/rules/R110_contract_document_sync.md, A010.020

## [R010.060] Pipeline Companion And Completion

### [R010.060.010] Operator Changes Must Use R500

Level: MUST
When: 修改环境、Run Config、Operator、Pipeline、Report或Artifact事务时
Rule: 必须读取R500和operator-pipeline模块画像，保持一个调用对应一个受控运行与Artifact事务。
Refs: report/design/rules/R500_operator_pipeline.md, project-governance/modules/operator-pipeline.yaml, A010.050

### [R010.060.020] Companion Changes Must Use R600

Level: MUST
When: 修改Companion、FPGA配测路径、仪器接口或硬件观测边界时
Rule: 必须读取R600和companion-platform模块画像；公共Project Plugin只路由这些Owner，不实现硬件Adapter。
Refs: report/design/rules/R600_companion_platform.md, project-governance/modules/companion-platform.yaml, A010.060

### [R010.060.030] Project Software Gate Must Run Before Commit

Level: MUST
When: 准备提交代码、配置、规则、文档或工具变化时
Rule: 必须先运行Task Context专项验证，再运行python tools/validate_pc.py、git diff --check和git status --short；未执行项必须明确报告。
Refs: AGENTS.md, A010.050.010, K001.009, G010.010.030

### [R010.060.040] CI Success Must Match Exact Head SHA

Level: MUST
When: 推送分支并使用GitHub CI作为完成证据时
Rule: 只有适用的Required Workflow之head_sha等于当前提交SHA且结论为success，才允许声明CI闭环。
Refs: AGENTS.md, K001.010, G010.010.040
