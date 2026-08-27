# Generic Model Adapter v0.1

模型层适配器，不属于 Public Governance Plugin，也不属于 Tool Plugin System。

它只做两件事：

```text
GenericModelClient
  ├─ Governed Work Executor
  └─ GovernanceSemanticExecutor
```

## 边界

- 不创建/更新 Context；
- 不搜索/写 Knowledge；
- 不运行 Closure；
- 不决定 Turn 是否开始/结束；
- 不注册 DSH/Codex/Claude Host 事件；
- 不提供文件、Google Drive、GitHub、Web、J-Link 等 Tool；
- 不绑定 OpenAI / DeepSeek / Claude 等供应商 API。

Public Governance Runtime 才拥有自动治理生命周期。

## Work

`createGovernedModelWorkExecutor()` 保留原始 business task 文本不变，并把 Runtime 自动生成的 Governance Context 作为独立上下文交给模型。

模型只返回用户可见工作结果；Reflection 由 Runtime 在工作结束后自动触发。

## Reflection

`createGovernanceSemanticExecutor()` 将 `GovernanceSemanticRequest` 转成严格 JSON 请求：

- current Context；
- bounded Turn Observations；
- Project/Public Knowledge categories；
- fixed scope-classification requirements；
- TurnReflectionResult JSON schema。

模型必须输出单个 JSON 对象。Adapter 不会从带额外 prose 的输出中猜取 JSON；非法输出 fail-closed，由 Kernel 的 Reflection validator 做最终结构/scope 校验。

任何 hidden chain-of-thought 都不属于输入/输出契约。`rationale` 仅允许简短决策摘要。
