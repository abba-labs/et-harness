# Public Governance Runtime v0.1

公共、Host-independent、Model-independent 的治理 Runtime。

它是未来所有 Agent Host 的统一治理入口：

```text
GPT / DeepSeek / Claude / Codex / Mock Agent
                    ↓
             SemanticExecutor
                    ↓
DSH / Codex / Claude / Generic Host Adapter
                    ↓
             Governance Runtime
                    ↓
           Auto Governance Engine
                    ↓
Kernel / Context / A-R-K-G / Evidence / Closure
```

## Runtime 负责

- Project 解析；
- Context Task 建立 / 恢复；
- Architecture / Rule / Knowledge / Gate 自动路由；
- Turn Journal；
- bounded Turn Observation Ledger；
- Work Observation；
- build/test preflight；
- 自动触发 Unified Reflection；
- 强制 Knowledge / Experience / Architecture / Rules / Evidence Scope 分类；
- 自动执行 8/8 Mandatory Closure；
- Closure Receipt；
- Turn close / unresolved Turn replay；
- Task complete / pause。

## Host 只负责

Host Adapter 只需要把自己的生命周期转换成这些调用：

```text
openTurn()
observeWork()
preflightAction()
closeTurn()
```

Host Adapter 不允许重新实现 Context、Knowledge、Rule、Gate、Reflection 或 Closure 逻辑。

## Baseline lifecycle supervision

当 Project Plugin 尚未提供结构化 supervision contribution 时，可信 Runtime
composition 可以调用 `compileGovernanceBaselineSupervisionContractV01()`。编译器只从
精确匹配的 Project / Task / Agent / Context / Route 身份生成 4 个公共生命周期义务：

```text
Reflection -> Knowledge Decision -> Context Update -> 8/8 Closure
```

它不从 Context 文本猜测业务规则，也不生成 Required Resource、Write Scope、Output、
Validation 或 Rule Compliance 义务。因此它只能声明
`BASELINE_LIFECYCLE`，不能声明 full project supervision；需要完整监管的 Project/Gate
必须等待结构化 Project contribution。

## Host supervision profile

受监管 Turn 可以在 `openTurn()`、`bindSupervisedTurn()` 或
`rehydrateSupervisedTurn()` 绑定严格校验的 `HostCapabilityContractV01`。Runtime
把 Host/Adapter 身份以及 `requestedLevel`、`effectiveLevel` 和协商原因固定到
当前 supervision session，并通过 `getStatus()` 如实返回：

```text
AUDIT
  允许事后/并行摄取可信执行事件
  缺证据或出现 violation 仍阻止 completion
  claimsMechanicalInterception = false

ENFORCE
  仅在 preflight + tool interception + stable event identity 都存在时成立
  所有受监管动作经唯一 GovernedToolGateway -> preflightAction()
  越界或不可证明的动作在 raw executor 前 BLOCK
```

能力不足时 `requested ENFORCE` 只会得到明确的 `effective AUDIT`，不会冒充已拦截。
Capability metadata 是受信 Host wiring 提供的能力事实，不是 Agent 自报 Evidence，
也不是密码学 Host 认证。

## Model 只负责

模型通过统一 `GovernanceSemanticExecutor` 做语义判断：

```ts
interface GovernanceSemanticExecutor {
  executorId: string
  reflect(request: GovernanceSemanticRequest): Promise<unknown> | unknown
}
```

Runtime 在 `closeTurn()` 内自动调用 SemanticExecutor。用户不需要在业务任务中提示：

- 做 Reflection；
- 管理 Context；
- 检查 Knowledge；
- 做 Scope 分类；
- 执行 Closure。

这些都是 Runtime 强制流程。

## Turn Observation Ledger

Host-independent Reflection 不能假定下一次模型调用仍然保留上一轮隐式会话记忆。因此 Runtime 会保存受限的、可见的 Turn 事实：

```text
TASK_INPUT
USER_MESSAGE
ASSISTANT_MESSAGE
TOOL_RESULT
RESOURCE_TOUCH
```

只允许业务任务、用户可见回答、工具结果摘要和资源引用进入 Ledger；隐藏 chain-of-thought/private reasoning 不属于治理数据。

每条 Observation 有单条/单 Turn 字符预算并生成 SHA-256 `governance-observation://...` 引用。引用会在 Turn OPEN 阶段写入 Journal，对应内容因此被 sealed Reflection fingerprint 间接绑定，失败重放不能静默替换语义输入。

`GovernanceSemanticRequest.turnObservations` 将这些 bounded observations 交给任意 SemanticExecutor。

## Knowledge 强制分类

Semantic request 会提供：

- Project Knowledge ACTIVE categories；
- Public Knowledge 是否可用；
- Public Knowledge ACTIVE categories；
- `knowledge-category://project/<id>` / `knowledge-category://public/<id>` 分类引用协议。

Knowledge Candidate 若没有合法分类，Knowledge Closure 会 fail-closed。

## 与工具系统的边界

Agent-facing Tool 必须通过 `GovernedToolGateway` 注册和执行：

```text
registered governed tool
-> preflightAction()
-> raw executor
-> observeWork()
```

Raw executor 保存在 Gateway 内部，模型调用时不能临时传入 callback。未注册工具和
`recordEvidence` 等 Governance mutation capability 在执行前 fail-closed。

在 supervised ENFORCE 中，工具注册方还必须声明：

```text
READ_ONLY
或 MUTATION + registration-side mutation intent mapper
或 GATE_EVIDENCE_PRODUCER + registration-side gateId / stepId
以及 registration-side stable event identity mapper
```

Agent-facing invocation 不能提供或替换 effect、Gate Step 绑定、scope decision 或稳定事件身份。
Gate Evidence Producer 使用 Gateway 到 Runtime 的专用 preflight，不进入最小权限 Host
Runtime Port；Host Adapter 不能通过普通 `preflightAction()` 自行标注 Producer。
MUTATION preflight 直接使用 Ledger 冻结的 Task Supervision Contract；不会解析 shell、
MCP 或 Host 专属参数。允许动作执行后，Host Adapter/Tool Plugin 仍负责把真实工具结果和
`RESOURCE_WRITE` receipt 摄入现有 Event Store；普通 Turn Observation 不是持久化 Evidence。

Evidence / State Manager、Knowledge Manager 和 Validation Policy 是 Framework 服务，
不能作为 raw model-visible tool 暴露给 Agent。

Turn Closure 完成后的 Knowledge Verification / Promotion 属于非阻断 Post-Closure
操作；失败通过 `knowledgePromotionWarnings` 返回，不重新打开 CLOSED Turn。

## 当前 v0.1 限制

- 同一进程内 unresolved Turn 会在下一 Turn 前自动 replay；
- `openTurn()` 遇到跨进程 unresolved Turn 仍 fail-closed，因为它没有对应 Event Store；
- Host 可用同一 durable Kernel Turn + Execution Event Store 显式调用
  `rehydrateSupervisedTurn()`，在 Reflection 前或 Reflection 后恢复原 Turn；
- Reflection 已存在时仍必须绑定最新 readiness；缺少或过期绑定不能恢复；
- 普通进程内 Observation 不会被猜测重建。跨进程 Closure 只投影 Event Store 中经过
  校验的可见消息和执行事实。
- Event Store 中存在 `RESOURCE_WRITE` 时，Runtime 会重建一个新的 fail-closed Review
  epoch；重启前仅驻内存的 Review 决定不会被当作 durable PASS 复用。

Host Adapter 不得自行实现第二套恢复生命周期。
