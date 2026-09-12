# Project Governance Navigation

本目录只负责把一次工程任务确定性地路由到正确的模块、代码入口、规则 Owner、修改边界和验证入口。
它不是第二套规则正文，也不是第二套项目状态或历史记录。

## 1. 固定定位

```text
AGENTS.md
  = 仓库宪法与不可违反的总约束

project-control/
  = 当前任务、项目状态、ADR和证据索引

project-governance/system-map.yaml
  = 工程模块总图和模块入口

project-governance/modules/*.yaml
  = 每类模块的代码入口、依赖链、规则Owner、写入边界和验证入口

report/design/rule_owner_catalog.yaml
  = 每条活动规则的唯一Owner和唯一权威正文

project-governance/runtime/current_task_context.json
  = 针对当前任务生成的临时阅读与执行清单
```

`runtime/`内容由工具生成且不提交。Task Context不是事实源；它只引用上述权威来源，并记录输入摘要以便检查是否过期。

## 2. 使用边界

Task Context的强制执行链、失败关闭和扩展规则唯一由
[`R002_task_context_navigation.md`](../report/design/rules/R002_task_context_navigation.md)定义。
本文件只说明命令和文件用途，不重复规则正文。

## 3. 标准命令

先校验工程地图和全部模块画像：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py validate
```

为一个IP开发任务生成上下文：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py compile `
  --task-id AES-CASE-001 `
  --intent "开发AES Formal Case与PC Driver" `
  --module ip-package `
  --change case `
  --change driver `
  --ip aes `
  --chip et6801
```

已批准的跨IP任务使用逐IP范围，例如：

```powershell
python tools/governance/compile_task_context.py compile `
  --task-id SPI-CRG-ADAPT --intent "补齐CRG的SPI映射并同步SPI文档" `
  --module ip-package --chip et6801 --lane firmware `
  --ip-scope crg:wrap,driver,capability,chip-driver `
  --ip-scope spi:contract-sync
```

参数边界和授权要求见[R002第3.1节](../report/design/rules/R002_task_context_navigation.md#31-显式多ip任务)。

检查当前上下文：

人工已允许保留既有修改的新任务，可在上述compile命令追加
`--preserve-existing-changes --output project-governance/runtime/<task-id>.json`。
独立输出文件同时保留固定基线，具体限制见R002；检查该任务时传入对应`--context`。

总软件门禁同样使用`python tools/validate_pc.py --context project-governance/runtime/<task-id>.json`。
下表“无”仅指无实际目标的公共软件开发；带IP的非豁免任务须同时带`--chip`，fpga/hil亦须带chip，见R002。

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py check
```

开发完成后，检查本任务相对编译时快照产生的源码变化是否都位于允许范围：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py scope-check
```

首次接入新IP时先单独使用`ip-package/analysis`创建公共契约；契约不存在时，Case、Driver、
Service、Wrap和Capability任务会失败关闭。

新增IP的静态注册入口`test_cases/ip_registry.py`归入`ip-package/case`，
因此目标IP注册和公共IP契约同步使用同一任务路由；注册器的执行机制仍归`pc-platform/case-runtime`。

## 4. 模块任务速查

先按“正在修改哪个架构模块”选择路由，不按文件名猜规则：

| 开发目标 | module/change | 必要参数 |
|---|---|---|
| 新IP分析、Feature和Case规划 | `ip-package/analysis` | `--ip --chip` |
| 芯片IP真实测试结果回写 | `ip-package/test-result` | `--ip --chip` |
| IP Formal Case、PC Driver、Firmware Service/Wrap | `ip-package/case|driver|service|wrap` | `--ip --chip` |
| 某芯片IP能力与执行映射 | `ip-package/capability` | `--ip --chip` |
| 通用SVD能力生成器及生成合同测试 | `operator-pipeline/capability-generator` | 无；写回某IP能力时另选`ip-package/capability` |
| 某芯片SDK中补充本IP Driver/Test Extension | `ip-package/chip-driver` | `--ip --chip` |
| PC Core、Backend、通信、调度、结果 | `pc-platform/core|backend|communication|scheduling|result` | 无 |
| PC公共Profile、Bench、Case Runtime、CLI | `pc-platform/profile|bench|case-runtime|package` | Bench必须`--chip` |
| PC公共回归基础设施 | `pc-platform/validation` | 无 |
| Firmware入口、Framework、IRQ、Service注册、Wrap公共契约 | `firmware-platform/application|framework|irq|service-registry|wrap-contract` | 无 |
| 芯片Firmware手动诊断Case | `firmware-platform/manual-test` | `--chip` |
| Firmware平台自有C源码质量与格式化 | `firmware-platform/formatting` | 无 |
| 芯片工程、Board和构建 | `firmware-platform/chip|build` | `--chip` |
| 环境/CI、Run Config、流水线、报告、Artifact | `operator-pipeline/environment|config|pipeline|report|artifact` | 无 |
| 手动诊断串口日志捕获工具 | `operator-pipeline/manual-capture` | 无 |
| Companion、FPGA、仪器接口与实现 | `companion-platform/interface|companion|fpga|instrument` | 无 |
| 规则Owner或任务导航 | `governance/rule|navigation` | 无 |
| 编写或修订项目周报 | `governance/weekly-report` | 无 |
| 批量修复一组Bug | `governance/bug-remediation`，并同时选择实际修改模块 | 按实际模块提供`--ip/--chip` |

一次任务跨模块时可以重复传入`--module`和`--change`。每个显式选择的模块都必须实际匹配至少一个change；
零匹配模块会失败关闭，不能借其他模块的合法匹配扩大读取或写入范围。

## 5. 文件用途

- `system-map.yaml`：登记稳定工程模块。
- `modules/*.yaml`：登记模块入口、依赖、Owner、写入边界和验证命令。
- `runtime/current_task_context.json`：临时派生结果，不提交、不作为事实源。
- 新增模块、IP或芯片时的约束统一遵循R002，不在本使用说明另建规则。
