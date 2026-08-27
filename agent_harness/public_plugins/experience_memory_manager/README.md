# Public Experience / Memory Manager

公共跨任务经验机制 `v0.2`。

## 定位

```text
Experience = 有 Evidence 支撑、但尚未成为正式 Knowledge 的可复用经验
```

Agent 负责语义判断：

```text
是否值得记录 Experience
应该进入 Project 还是 Global Knowledge
选择 Category
何时显式晋级
```

插件负责治理闭环：

```text
Evidence 校验
项目隔离
经验持久化 / 跨任务检索
Knowledge Candidate 提交
Evidence -> Verification
Validation Policy 调用
显式 Promote
状态同步 / 失败回滚
```

## 生命周期

```text
Experience CANDIDATE
    ↓ submitToKnowledge()
Knowledge CANDIDATE
+ SUPPORT Verification
    ↓
Experience KNOWLEDGE_CANDIDATE
    ↓ evaluateKnowledgeCandidate()
READY / INSUFFICIENT / BLOCKED
    ↓ Agent 显式 promoteKnowledgeCandidate()
Knowledge VALIDATED
    ↓
Experience PROMOTED
```

Project Knowledge 当前需要 1 个不同 SUPPORT；Global Knowledge 当前需要 2 个不同 SUPPORT。任何当前 Claim 的 CONTRADICT 都会 BLOCKED。该判断完全复用 Knowledge Validation Policy，不在 Experience Manager 中复制策略。

## 安全边界

`knowledge-library-v0.2` 禁止旧 `promoteToKnowledge()` 直接写 `VALIDATED`。

```text
Experience -> VALIDATED Knowledge     禁止
Experience -> Knowledge CANDIDATE     允许
CANDIDATE -> Verification -> Policy -> explicit Promote
```

未完成验证的 `KNOWLEDGE_CANDIDATE` 仍可通过 `memory.context` 跨任务检索，供后续 Agent 继续验证。

旧 `knowledge-v0.1` 直写逻辑仅保留兼容，不属于 v0.2 主路径。
