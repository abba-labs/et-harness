---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_change_scope_review.yaml
    title: Change Scope Review
    summary: 审查任务意图与实际 diff、无关修改以及 shared change 的影响范围。
    aliases: [scope, diff, unexpected change, shared change, impact, 改动范围, 不该改, 无关修改, 影响范围]
  - id: G020
    file: 020_architecture_boundary_review.yaml
    title: Architecture Boundary Review
    summary: 审查代码是否写在正确层、芯片/route 是否保持独立、正式产品路径是否被绕过。
    aliases: [architecture, boundary, dependency, chip isolation, route isolation, product path, 架构, 分层, 芯片独立, 绕过CLI]
  - id: G030
    file: 030_rule_compliance_review.yaml
    title: Rule Compliance Review
    summary: 根据 Change Scope 选择适用规则并检查 MUST/MUST_NOT 合规性。
    aliases: [rules, compliance, must, must not, rule violation, 规则, 违规, 约束]
  - id: G040
    file: 040_logic_static_review.yaml
    title: Logic And Static Code Review
    summary: 审查控制流、错误/边界路径以及编译前的明显语法/API/类型风险。
    aliases: [logic, control flow, error path, early return, syntax, api misuse, 逻辑, 语法, 错误分支, 边界条件]
  - id: G050
    file: 050_resource_lifecycle_review.yaml
    title: Resource And Lifecycle Review
    summary: 审查资源所有权、退出清理以及异步进程/进度生命周期闭合。
    aliases: [cleanup, lifecycle, qprocess, qtimer, qthread, progress, disconnect, exit, 资源清理, 退出, 进度, 生命周期]
  - id: G060
    file: 060_regression_impact_review.yaml
    title: Regression And Impact Review
    summary: 推导潜在回归范围，并输出 Gate 之后必须执行的验证范围，不直接执行测试。
    aliases: [regression, blast radius, affected scope, validation plan, 回归, 影响, uart can, 测试范围]
  - id: G070
    file: 070_contract_compatibility_review.yaml
    title: Contract And Compatibility Review
    summary: 审查 CLI、typed contract、Profile、Progress、Result 与结构化数据兼容性。
    aliases: [contract, compatibility, cli args, profile, capability, progress schema, result schema, 接口, 兼容性, 参数, schema]
---

# ET-TOOL Gate Index

> 状态：CODE GATE TAXONOMY v0.1 / READY

ET-TOOL Gate 的职责是 **代码修改完成后、编译构建之前** 的代码质量与风险审查。

它回答：

```text
这次改动范围对不对？
有没有修改不该修改的内容？
有没有违反 Architecture / Rules？
控制流、错误路径、资源生命周期有没有逻辑缺陷？
可能影响哪些 Chip / Route / Feature？
有没有破坏既有 Contract / Schema？
Gate 之后需要编译、测试或硬件验证哪些范围？
```

Gate **不负责执行编译、测试或硬件验证**。

正式流程：

```text
Coding
  ↓
ET-TOOL Code Gates
  ↓ PASS
Release Build Script
  ↓
Automated / Hardware Validation as required
  ↓
Evidence
  ↓
DONE
```

所有正式 Gate 文件必须按 `gate-v0.1` 接入本索引；后续实际开发发现新的稳定审查约束时再增补，不为了覆盖率提前堆 Gate。
