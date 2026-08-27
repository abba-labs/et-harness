# ET Automated Testing Platform

本目录是自动化测试平台的正式代码根：

```text
firmware/          # DUT测试固件、Board、Chip SDK和Keil工程
pc/                # PC运行时、Driver、Formal Case和Profile
companion/         # FPGA、Peer和配测设备代码入口
tools/             # 运行、构建、部署、报告和质量工具
test_case_doc/     # 各IP公共契约与芯片适配事实
report/            # 人读规则、分析、Review和验证报告
artifacts/         # runs原始证据和reports时间戳Excel报告
project-governance/# Agent任务导航与临时Task Context
```

Agent从[AGENTS.md](AGENTS.md)进入，按Task Context读取目标模块和Rxxx规则。人读文档索引位于
[report/README.md](report/README.md)。

## 快速开始

图形化配置：

```text
run_config_gui.bat
```

命令行完整运行：

```text
run_test.bat
  -> tools/runner/bootstrap.py
  -> tools/runner/run_pipeline.py
  -> 环境检查 / 代码检查 / 构建 / 部署 / 启动
  -> tools/runner/run_ip_tests.py
  -> Formal Case
  -> Excel报告
```

首次运行时，Bootstrap创建仓库内`.venv`并在本机配置缺失时由
`run_config.example.yaml`生成`run_config.yaml`。本地工具路径、串口、探针和镜像在
`run_config.yaml`中配置；该文件由Git忽略。

配置分区包括`config`、`target`、`pipeline`、`environment`、`dut`、`companions`、
`instruments`、`test`和`output`。GUI和命令行使用同一份配置。

测试集合来自`pc/et_test_platform/test_cases/ip_registry.py`及各IP的`case_registry.py`。
运行证据和Excel报告分别位于：

```text
artifacts/runs/<run_id>/
artifacts/reports/<timestamp>_<CHIP>_<IP>测试报告.xlsx
```

## 权威规则

- [R001 Agent规则治理](report/design/rules/R001_agent_rule_governance.md)
- [R002 Task Context导航](report/design/rules/R002_task_context_navigation.md)
- [R100 公共IP与芯片适配](report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md)
- [R200 PC分层与Driver](report/design/rules/R200_pc_layer_responsibilities.md)
- [R300 Firmware Service](report/design/rules/R300_firmware_service.md)
- [R310 Firmware Wrap](report/design/rules/R310_firmware_wrap.md)
- [R500 Operator Pipeline](report/design/rules/R500_operator_pipeline.md)
