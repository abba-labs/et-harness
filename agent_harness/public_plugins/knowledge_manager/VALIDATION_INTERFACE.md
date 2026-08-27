# Knowledge Validation Interface v0.1

> 所属插件：`public.knowledge-manager`
> 子服务：`knowledgeValidationPolicy`

## Evaluate

```text
knowledgeValidationPolicy.evaluate(knowledgeUri)
```

返回：

```text
INSUFFICIENT | READY | BLOCKED
```

当前最小策略：

```text
Project Knowledge
  1 个文档级 SUPPORT + 0 CONTRADICT -> VALIDATED
  1 个本项目 REAL_TEST PASS + 0 CONTRADICT -> FULL_VALIDATED

Global Knowledge
  2 个不同 Global 文档级 SUPPORT + 0 CONTRADICT -> VALIDATED
  单个 Project 的 REAL_TEST 不得晋级 FULL_VALIDATED
```

Verification 只统计与当前 `sha256(Fact + Scope)` 一致的记录。任何当前 Claim 的
`CONTRADICT` 都阻塞自动晋级。

## Promote

```text
knowledgeValidationPolicy.promote(knowledgeUri)
```

合法状态变化：

```text
CANDIDATE -> VALIDATED
CANDIDATE -> FULL_VALIDATED      # Project REAL_TEST
VALIDATED -> FULL_VALIDATED      # Project REAL_TEST
```

Runtime 可以在 Turn 8/8 Closure 完成后调用该 Policy 自动验证候选。Promotion 失败是
Post-Closure warning，不允许重新打开或破坏已经 CLOSED 的 Turn。

## 边界

```text
CANDIDATE 默认不进入正式 Knowledge Route
Agent 不能直接决定 validation tier
Project REAL_TEST 不能证明 Global applicability
不以多数 SUPPORT 覆盖 CONTRADICT
```
