# Knowledge Validation Policy v0.1

## 定位

Knowledge Manager 内部的轻量可信晋级策略，不新增公共插件。

```text
Verification
  ↓
Validation Policy
  ↓
INSUFFICIENT | READY | BLOCKED
  ↓
Agent 显式 Promote
  ↓
VALIDATED
```

## Policy

```text
Project:
1 个不同依据 SUPPORT + 0 CONTRADICT -> READY

Global:
2 个不同依据 SUPPORT + 0 CONTRADICT -> READY

当前 Claim 任意 CONTRADICT -> BLOCKED
其余 -> INSUFFICIENT
```

## Claim Version

每条 Verification 绑定：

```text
sha256(Fact + Scope)
```

Fact / Scope 修改后旧 Verification 自动退出当前判断，但历史记录保留。

## Promote

只有：

```text
CANDIDATE + READY
```

可以显式晋级。

晋级只修改 Status，不改 K-ID / Fact / Category / Verification。

## 不做

```text
不自动晋级
不做置信度百分比
不做 LLM 可信判断
不以多数 SUPPORT 覆盖 CONTRADICT
```
