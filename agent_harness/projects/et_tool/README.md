# ET-TOOL Project Plugin

> 状态：`PHASE 4 / PROJECT CONTENT READY / CODE REVIEW ADAPTER v0.1`

ET-TOOL 通过公共 Project Contract 接入 Agent Harness。项目私有内容保持在 Project Plugin 内，公共管理机制继续由冻结的 Public Layer v0.2 提供。

## 当前接入链

```text
ET-TOOL Project Plugin
  ↓
project.yaml / Project Contract v0.1
  ↓
Public Project Manager
  ├─ Architecture Navigator → architecture-v0.1
  ├─ Rule Manager           → rule-v0.1
  ├─ Knowledge Manager      → knowledge-library-v0.2
  ├─ Gate Manager           → gate-v0.1
  └─ optional Review Adapter
```

主 Project Plugin 仍是薄加载器，只负责：

```text
发现 ET-TOOL 根目录
→ 校验 project.yaml + 四类标准资源入口
→ projectManager.registerProjectFromManifestFile(...)
→ 卸载时注销项目
```

主插件只注入 `projectManager`。

## 当前正式项目资源

```text
agent_harness/projects/et_tool/
├─ project.yaml
├─ architecture/   # Axxx
├─ rules/          # Rxxx
├─ knowledge/      # Kxxx / Source / Verification
├─ gates/          # Gxxx Code Gates
└─ src/
   ├─ index.ts
   ├─ review-adapter.ts
   ├─ review-service.ts
   └─ review-contracts.ts
```

当前项目层已经具备：

- Architecture 导航；
- Rule Taxonomy；
- Project Knowledge Library；
- Code Gate Taxonomy；
- 可选 ET-TOOL Code Review Adapter。

## Code Review Adapter v0.1

Adapter 通过子入口加载：

```text
@agent-harness/project-et-tool/review-adapter
```

提供 7 个受治理 Capability：

```text
change.analyze
code.review
architecture.review
rule.review
lifecycle.review
contract.review
validation.plan
```

它的职责不是替大模型自动判断代码正确，而是：

```text
收集/接收 Git Change
→ 推导 Chip / Route / Layer scope hints
→ 拉取 Architecture / Rules / Knowledge
→ 绑定当前 Gate Execution Plan
→ 生成 Review Packet
→ Agent/Human 显式审查
→ PASS / BLOCK Decision
→ Evidence Manager 记录 Gate Evidence
```

强制边界：

```text
Adapter never auto-PASS
BLOCK finding 存在时不能记录 PASS Evidence
Gate 不执行 build/test/hardware
validation.plan 只生成后续验证范围
```

编译构建仍然发生在 Code Gate PASS 之后，并遵守 ET-TOOL Release Script 规则。

## Cordis Loader

`cordis.patch.yml` 会加载：

1. `@agent-harness/project-et-tool` 主 Project Plugin；
2. `@agent-harness/project-et-tool/review-adapter` 可选 Review Adapter。

Review Adapter 依赖 Public Architecture / Rule / Knowledge / Gate / Evidence 服务，但不修改这些公共插件。

## 验收

Project Shell：

```bash
bash agent_harness/validation/phase4_ettool_project_shell_v0_1_integration.sh
```

Code Review Adapter：

```bash
bash agent_harness/validation/phase4_ettool_code_review_adapter_v0_1_integration.sh
```

Adapter 专项 Gate 必须证明：

```text
7 Capability Provider 注册
→ Review Packet 生成
→ Architecture / Rule / Knowledge 候选注入
→ BLOCK decision 不放行 Gate
→ BLOCK finding 禁止伪 PASS
→ 显式 PASS Evidence 后 MUST Gate 才可放行
→ Provider / Service 卸载清理
```
