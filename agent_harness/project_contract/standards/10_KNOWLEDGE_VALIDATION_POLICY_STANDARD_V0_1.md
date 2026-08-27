# Knowledge Validation Policy v0.1

> 输入：当前 Knowledge Claim + Verification Records
> 输出：`INSUFFICIENT | READY | BLOCKED`

## 1. 核心原则

Knowledge 的可信等级由 Framework Policy 根据 Source / Evidence 判断，不由 Agent
自行声明。Verification 始终绑定当前：

```text
knowledgeFingerprint = sha256(Fact + Scope)
```

## 2. Project Knowledge

```text
0 CONTRADICT
+ 至少 1 个文档级 SUPPORT
-> VALIDATED

0 CONTRADICT
+ 至少 1 个本 Project REAL_TEST PASS
-> FULL_VALIDATED
```

## 3. Global Knowledge

```text
0 CONTRADICT
+ 至少 2 个不同 Global 文档级 SUPPORT
-> VALIDATED
```

当前阶段不自动建立跨项目 empirical applicability。因此：

```text
Global Knowledge
+ 单个 Project REAL_TEST
-> 不得 FULL_VALIDATED
```

## 4. CONTRADICT

当前 Claim 只要存在一条 `CONTRADICT`，自动晋级必须 `BLOCKED`。不得使用多数票覆盖
反证，也不得删除历史 Verification 来制造 PASS。

## 5. Promotion

合法变化：

```text
CANDIDATE -> VALIDATED
CANDIDATE -> FULL_VALIDATED
VALIDATED -> FULL_VALIDATED
```

Promotion 可以显式调用，也可以由 Governance Runtime 在 8/8 Closure 完成后调用。
Post-Closure Promotion 失败只返回 warning；Turn 已经 CLOSED 时不得因 Promotion 失败
回退或重新打开。

## 6. 明确不做

```text
不做 AI 置信度百分比
不让 Agent 自己签发 FULL_VALIDATED
不让单项目测试变成公共真理
不强制每个错误生成 Knowledge Candidate
```
