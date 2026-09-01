# PC Test Platform

PC端正式实现位于`pc/et_test_platform/`：

```text
core/                  # 小型稳定数据模型和公共错误
drivers/               # IP Driver、Codec和模型
clients/               # DUT、Peer和目标访问Client
communication/         # ET-Frame与Transport
scheduling/            # Fixture、注册和运行上下文
results/               # Canonical Result与报告输入
profiles/               # Capability、Bench和Execution Mapping
test_cases/             # Formal Case
framework_validation/   # 平台单元、契约、Native和集成验证
instruments/            # 外部仪器接口；当前尚未形成正式实现
programmers/            # 烧录器接口；当前尚未形成正式实现
```

本README只描述代码入口和当前目录状态。PC分层、Case、Python、Capability、证据和运行规则
分别由以下正文定义：

- [R200 PC分层与Driver](../report/design/rules/R200_pc_layer_responsibilities.md)
- [R210 Formal Case](../report/design/rules/R210_pc_case_responsibility.md)
- [R220 Python质量](../report/design/rules/R220_python_style_quality.md)
- [R410 Capability v2](../report/design/rules/R410_capability_v2.md)
- [R500 Operator Pipeline](../report/design/rules/R500_operator_pipeline.md)
