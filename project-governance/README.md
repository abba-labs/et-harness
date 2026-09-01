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

检查当前Task Context是否仍与工程地图、模块画像、规则目录、Git分支和当前任务记录一致：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py check
```

开发完成后，检查本任务相对编译时快照产生的源码变化是否都位于允许范围：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py scope-check
```

首次接入新IP时先单独使用`ip-package/analysis`创建公共契约；契约不存在时，Case、Driver、
Service、Wrap和Capability任务会失败关闭。

## 4. 模块任务速查

先按“正在修改哪个架构模块”选择路由，不按文件名猜规则：

| 开发目标 | module/change | 必要参数 |
|---|---|---|
| 新IP分析、Feature和Case规划 | `ip-package/analysis` | `--ip`，有目标芯片时加`--chip` |
| 芯片IP真实测试结果回写 | `ip-package/test-result` | `--ip --chip` |
| IP Formal Case、PC Driver、Firmware Service/Wrap | `ip-package/case|driver|service|wrap` | `--ip` |
| 某芯片IP能力与执行映射 | `ip-package/capability` | `--ip --chip` |
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
| 公共Gate、Provider和Evidence Producer稳定化 | `public-framework/gate-stabilization` | 无 |
| 公共Runtime跨进程恢复 | `public-framework/runtime-recovery` | 无 |
| Codex等Host的轻量MCP协议适配 | `harness-host-adapter/mcp-gateway` | 无 |

一次任务跨模块时可以重复传入`--module`和`--change`。每个显式选择的模块都必须实际匹配至少一个change；
零匹配模块会失败关闭，不能借其他模块的合法匹配扩大读取或写入范围。

## 5. 文件用途

- `system-map.yaml`：登记稳定工程模块。
- `modules/*.yaml`：登记模块入口、依赖、Owner、写入边界和验证命令。
- `runtime/current_task_context.json`：临时派生结果，不提交、不作为事实源。
- 新增模块、IP或芯片时的约束统一遵循R002，不在本使用说明另建规则。
