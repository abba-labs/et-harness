# ET Harness

ET Harness 是公共 Agent Governance、Project Plugin、Knowledge Governance 与受治理 Runtime 的上游仓库。

本仓库不承载某个具体项目的业务实现。它提供一套公共框架，使不同项目通过自己的 Project Plugin 接入统一的项目识别、Architecture / Rule / Knowledge / Gate 路由、Context 构建、Tool Preflight、Evidence、Reflection 与 Closure 生命周期。

## Repository contract

### `main`

`main` 是公共 Harness 的唯一上游，只允许保存：

- 公共 Contract、公共插件与公共 Runtime；
- Provider-neutral Model / Host Adapter；
- Global Knowledge；
- 不依赖真实项目代码的通用示例和 synthetic-project 验证；
- Harness 自身的设计、测试事实与 Handoff。

`main` 禁止保存：

- 真实项目业务代码；
- 真实项目私有 Project Plugin；
- 项目私有 Architecture / Rules / Knowledge / Gates；
- 依赖某个真实项目工作树才能运行的 Pilot 或验证脚本。

### `project/<name>`

每个长期项目分支由以下内容组成：

```text
当前 main 公共 Harness
+ 一个项目的完整代码
+ 该项目的 Project Plugin
+ 该项目的 Architecture / Rules / Knowledge / Gates
+ 该项目自己的 Workflow 与验证
```

公共 Harness 更新方向固定为：

```text
main
  ↓ merge
project/<name>
```

项目分支不得整体反向合入 `main`。项目开发中发现公共 Harness 缺陷时，应先在 `main` 修复并完成公共回归，再将 `main` 合入项目分支。

## Repository layout

```text
agent_harness/
├── governance_core/       # 公共治理目录、准入与 Provider 注册
├── project_contract/      # Project Manifest 与 A/R/K/G 接口标准
├── public_plugins/        # Project、Context、Knowledge、Gate、Runtime 等公共插件
├── model_adapters/        # Provider-neutral 与 OpenAI-compatible Model 边界
├── global_knowledge/      # 公共知识库
├── examples/              # 不依赖真实项目的示例插件
├── pilots/                # 仅保留通用 Pilot
├── validation/            # 公共与 synthetic-project 验证
├── design/                # Harness 设计
├── progress_context/      # 阶段事实、失败根因和 Handoff
└── projects/              # main 只保留接入说明；真实项目插件在项目分支
```

## Development flow

公共 Harness 变更：

```text
feature/harness-<topic>
→ main
→ 公共构建、单测、集成和负向回归
→ 各 project/<name> 分支合并 main
```

项目变更：

```text
project/<name>
→ feature/<project>-<topic>
→ project/<name>
```

长期项目分支使用 merge 同步 `main`，不通过长期 rebase 改写项目历史。

## Project Plugin boundary

Project Plugin 是协议适配层、资源路由层和项目知识挂载点。它不重新实现项目业务，也不要求项目为了 Harness 重构。

项目分支中的标准入口为：

```text
agent_harness/projects/<project>/
├── project.yaml
├── architecture/
├── rules/
├── knowledge/
└── gates/
```

公共插件负责统一解析和治理；项目插件只声明本项目事实、约束、来源与资源映射。

## Validation

`.github/workflows/harness-public-baseline.yml` 是 Harness-only 主线的基础门禁，至少检查：

- 仓库边界没有混入真实项目代码和真实 Project Plugin；
- 公共 package 按依赖顺序完成必要单测和构建；
- 公共 synthetic-project 集成链路可以完成 Project / A/R/K/G / Runtime 验证。

更细的验证事实与阶段入口见 `agent_harness/progress_context/`。

## Migration provenance

本仓库的初始公共实现从 `abba-labs/et-tool` 提取。迁移采用 SHA-256 校验的内容快照，源仓库在新仓库完成回归前保持不变。具体来源、提交、校验和与历史保留边界见：

- `MIGRATION_SOURCE.json`
- `MIGRATION_BOUNDARY.md`
- `agent_harness/progress_context/20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`
