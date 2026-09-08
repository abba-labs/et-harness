# Tools

`tools/`保存平台运行、构建、部署、报告、Capability生成和质量验证工具：

```text
tools/
├─ validate_pc.py          # 软件总门禁
├─ runner/                 # Operator、Pipeline和GUI
├─ governance/             # Task Context编译与范围检查
├─ quality/                # 静态Checker和文档/契约Validator
├─ reporting/              # Canonical Result到人工报告
├─ profiles/pipeline/      # 受控Pipeline Profile
├─ capabilities/           # SVD与Capability生成工具
├─ firmware/               # 固件工程生成、编译和部署
├─ fpga/                   # FPGA配置和JTAG工具
└─ validation/             # 专项诊断、Smoke和硬件验证入口
```

## 常用入口

CAN盒子人工诊断：`tools/runner/can_box.py`；配置和设备能力边界见
[CAN盒子说明](../pc/et_test_platform/instruments/can_boxes/README.md)。该入口复用正式仪器Adapter，不代替Formal Case。

完整Operator Pipeline：

```powershell
.\run_test.bat
```

配置与环境检查：

```powershell
.\.venv\Scripts\python.exe tools\runner\run_pipeline.py `
  --config run_config.yaml `
  --check-only
```

软件总门禁：

```powershell
.\.venv\Scripts\python.exe tools\validate_pc.py
```

Case知识辅助：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py extract `
  --chip ET6801 --ip can --lane fpga --source artifacts/runs/current/tests/can
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py check --chip ET6801 --ip can
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py index --chip ET6801 --ip can
# Agent逐Case整理或确认无新知识后，显式确认当前现场可以复用：
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py review `
  --chip ET6801 --ip can --lane fpga --source artifacts/runs/current/tests/can
```

`extract/check/index/review/archive`共用原维护入口。长期入口为
`artifacts/records/<CHIP>/<IP>/cases/*.md`；当次事实摘要与可选Excel在
`artifacts/runs/current/tests/<ip>/`。脚本不编写Case正文。
精确键查询、旧记录只读与显式现场归档示例见
[产物导航](../artifacts/README.md)，唯一语义见R130与R500第6节。

Firmware平台自有C源码格式化与检查：

```powershell
.\.venv\Scripts\python.exe tools\quality\check_firmware_c_format.py --fix firmware\services\src\et_uart_service.c
.\.venv\Scripts\python.exe tools\quality\check_firmware_c_format.py --review-diff
.\.venv\Scripts\python.exe tools\quality\check_firmware_c_format.py
```

固定范围仅为`firmware/application`、`firmware/framework`、`firmware/services`和
`firmware/wrap`；芯片SDK与生成工程不在格式化范围。普通任务必须显式传入本任务已修改的文件；不带路径的`--fix`只用于独立的全目录格式迁移。

Task Context：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py validate
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py compile <task-arguments>
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py check
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py scope-check
```

Capability生成：

```powershell
.\.venv\Scripts\python.exe tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --semantic-output-dir <chip>\ip `
  --audit-output-dir <chip>\audit
```

本README只提供目录和命令导航。工具归属、Run Config、Pipeline Profile、硬件确认、Artifact、
规则Owner和Task Context边界由以下正文定义：

- [R001 Agent规则治理](../report/design/rules/R001_agent_rule_governance.md)
- [R002 Task Context导航](../report/design/rules/R002_task_context_navigation.md)
- [R410 Capability v2](../report/design/rules/R410_capability_v2.md)
- [R500 Operator Pipeline](../report/design/rules/R500_operator_pipeline.md)
- [R600 Companion Platform](../report/design/rules/R600_companion_platform.md)
