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

Evidence / State Manager、Knowledge Manager 和 Validation Policy 是 Framework 服务，
不能作为 raw model-visible tool 暴露给 Agent。

Turn Closure 完成后的 Knowledge Verification / Promotion 属于非阻断 Post-Closure
操作；失败通过 `knowledgePromotionWarnings` 返回，不重新打开 CLOSED Turn。

## 当前 v0.1 限制

- 同一进程内 unresolved Turn 会在下一 Turn 前自动 replay；
- Turn Observation Ledger 当前也是进程内状态；
- Kernel 持久化后、整个 Runtime 进程重启的 task + observation rehydration 尚未实现；遇到持久化 unresolved Turn 时 fail-closed，不会静默开启新 Turn。

后续应通过公共 Runtime State Store 解决，而不是把恢复逻辑塞进某个 Host Adapter。
