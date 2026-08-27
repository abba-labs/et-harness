# [A010] Project Governance Projection

Role: 将现有项目的宪法、模块总图、规则Owner和工程入口投影为公共Architecture接口。
Boundary: 本投影只负责导航，不定义项目业务，不复制规则正文，不替代Task Context。
Resources: AGENTS.md, project-governance/system-map.yaml, project-governance/modules/, report/design/rule_owner_catalog.yaml
Relations: R010, K001, G010

## [A010.010] Governance Entry And Source Authority

Role: 路由仓库宪法、Task Context和规则Owner入口。
Resources: AGENTS.md, MIGRATION_BOUNDARY.md, project-governance/README.md, project-governance/modules/governance.yaml, report/design/rule_owner_catalog.yaml
Relations: R010.010, R010.020, K001.001, K001.002, K001.003

### [A010.010.010] Repository Constitution

Role: 定位不可违反的项目总约束、安全边界、Harness项目分支边界和完成条件。
Resources: AGENTS.md, MIGRATION_BOUNDARY.md
Relations: R010.010.010, R010.010.040, K001.001, K001.011

### [A010.010.020] Deterministic Task Navigation

Role: 定位Task Context编译、检查、扩围和scope-check链路。
Resources: project-governance/README.md, project-governance/modules/governance.yaml, tools/governance/compile_task_context.py, report/design/rules/R002_task_context_navigation.md
Relations: R010.010.020, R010.010.030, K001.003, K001.004, K001.005, G010

### [A010.010.030] Rule Ownership

Role: 定位活动规则的唯一Owner、正文、Checker和测试。
Resources: report/design/rule_owner_catalog.yaml, report/design/rules/
Relations: R010.020, K001.002, K001.007

## [A010.020] IP Package Projection

Role: 路由公共IP契约、Formal Case、Driver、Service、Wrap和芯片适配入口。
Boundary: 公共插件不定义IP业务语义；具体语义、写入范围和验证由现有Owner资源决定。
Resources: project-governance/modules/ip-package.yaml, test_case_doc/, pc/et_test_platform/test_cases/, pc/et_test_platform/drivers/, firmware/services/, firmware/wrap/
Relations: R010.020, R010.030, R010.040, R010.050

### [A010.020.010] Analysis And Contract

Role: 路由IP分析资料、公共IP契约和芯片适配事实。
Resources: project-governance/ip-analysis-sources.yaml, test_case_doc/, report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md, report/design/rules/R120_public_ip_machine_contract.md, report/design/rules/R140_ip_analysis_workflow.md
Relations: R010.020.020, R010.050.030

### [A010.020.020] PC Case And Driver

Role: 路由Formal Case、PC Driver和相邻公共运行链。
Resources: pc/et_test_platform/test_cases/, pc/et_test_platform/drivers/, project-governance/modules/ip-package.yaml
Relations: A010.030, R010.030

### [A010.020.030] Firmware Service And Wrap

Role: 路由目标IP Service、Wrap和芯片本地Driver边界。
Resources: firmware/services/, firmware/wrap/, firmware/chips/, project-governance/modules/ip-package.yaml
Relations: A010.040, R010.040

### [A010.020.040] Capability And Chip Adaptation

Role: 路由Capability Profile、Execution Mapping和芯片适配文档。
Resources: pc/et_test_platform/profiles/, test_case_doc/, report/design/rules/R410_capability_v2.md
Relations: A010.030, A010.040, R010.050

## [A010.030] PC Platform Projection

Role: 路由PC公共运行时、Client、通信、调度、结果和验证入口。
Boundary: 依赖方向、写入范围和专项验证由pc-platform模块画像及规则Owner定义。
Resources: project-governance/modules/pc-platform.yaml, pc/README.md, pc/et_test_platform/
Relations: A010.020, A010.050, R010.030, R010.050

### [A010.030.010] Core Backend And Client

Role: 路由稳定核心模型、TargetClient和Programmer公共边界。
Resources: pc/et_test_platform/core/, pc/et_test_platform/clients/, pc/et_test_platform/programmers/
Relations: R010.030.010, R010.020.030

### [A010.030.020] Communication Scheduling And Profiles

Role: 路由ET-Frame、Transport、运行上下文和Capability/Profile。
Resources: pc/et_test_platform/communication/, pc/et_test_platform/scheduling/, pc/et_test_platform/profiles/
Relations: R010.030.010, R010.050.010, R010.050.020

### [A010.030.030] Cases Results And Validation

Role: 路由Formal Case、Canonical Result和PC公共回归入口。
Resources: pc/et_test_platform/test_cases/, pc/et_test_platform/results/, pc/et_test_platform/framework_validation/
Relations: R010.030.020, R010.030.030, R010.020.030

## [A010.040] Firmware Platform Projection

Role: 路由Firmware Application、Framework、Service、Wrap、Manual Tests、IRQ和Chip入口。
Boundary: 本投影不定义固件业务实现，不替代Firmware规则Owner和模块画像。
Resources: project-governance/modules/firmware-platform.yaml, firmware/README.md, firmware/
Relations: A010.020, A010.030, R010.040, R010.050

### [A010.040.010] Application And Framework

Role: 路由公共入口、协议、缓冲区、资源和命令分发。
Resources: firmware/application/, firmware/framework/, report/design/rules/R400_et_frame_v1.md
Relations: R010.040.010, R010.050.010

### [A010.040.020] Service Wrap IRQ And Manual Test

Role: 路由Service注册、IP Service、Wrap公共契约、IRQ子系统和项目现有Manual Test入口。
Resources: firmware/services/, firmware/wrap/, firmware/manual_tests/, report/design/rules/R300_firmware_service.md, report/design/rules/R310_firmware_wrap.md, report/design/rules/R320_interrupt_subsystem.md
Relations: R010.040.010, R010.040.020, R010.040.030

### [A010.040.030] Chip Build And Source Quality

Role: 路由芯片SDK、Board、工程配置、Core1 Peer和平台自有C源码质量入口。
Resources: firmware/chips/, firmware/boards/, firmware/build/, tools/firmware/, report/design/rules/R330_firmware_c_style.md, report/design/rules/R340_firmware_manual_diagnostics.md
Relations: R010.040.040, R010.050.030

## [A010.050] Operator Pipeline Projection

Role: 路由环境、Run Config、Pipeline、Report、Artifact和CI入口。
Boundary: 本投影不执行构建、测试或硬件动作，只提供公共框架导航。
Resources: project-governance/modules/operator-pipeline.yaml, tools/README.md, tools/runner/, tools/profiles/pipeline/, artifacts/
Relations: A010.030, A010.040, R010.060, G010

### [A010.050.010] Environment And Run Configuration

Role: 路由Python环境、CI、Operator Bootstrap和受控Run Config。
Resources: pyproject.toml, .github/workflows/, tools/runner/bootstrap.py, run_config.example.yaml, tools/runner/run_config_gui_schema.yaml
Relations: R010.060.010, K001.009, K001.010

### [A010.050.020] Pipeline Report And Artifact

Role: 路由Operator Launcher、Pipeline Profile、报告转换和Artifact事务。
Resources: tools/runner/, tools/profiles/pipeline/, tools/reporting/, artifacts/README.md
Relations: R010.060.010, R010.060.020

## [A010.060] Companion Platform Projection

Role: 路由Companion、FPGA和Instrument公共接口与实现入口。
Boundary: 本投影不暴露或实现硬件执行Adapter；硬件动作继续受项目人工门禁与公共Runtime治理。
Resources: project-governance/modules/companion-platform.yaml, companion/, pc/et_test_platform/instruments/, tools/fpga/
Relations: A010.030, A010.050, R010.060

### [A010.060.010] Public Interfaces And Companion

Role: 路由仪器/配测设备稳定接口与Companion代码。
Resources: pc/et_test_platform/instruments/, companion/
Relations: R010.060.020, R010.020.030

### [A010.060.020] FPGA And Instrument Paths

Role: 路由FPGA工具、观测路径和外部仪器实现入口。
Resources: tools/fpga/, tools/validation/, pc/et_test_platform/instruments/
Relations: R010.060.020, K001.008
