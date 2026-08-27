# Context Record Standard v0.1

> 标准 ID：`context-record-v0.1`  
> 所属：Public Context Manager / Builder  
> 目标：让 Agent 用最少上下文快速回答三个问题：**我在哪、我要做什么、下一步做什么。**

## 1. 核心原则

```text
Context 不是历史记录，也不是长期知识库。
Context = 当前任务的最小充分工作视图。
```

长期事实继续属于：

```text
Architecture / Rules / Knowledge / Gate / Evidence / State / Experience
```

Context 只保存：

```text
当前任务状态
当前工作引用
最近必要动作
可继续查询的 Handle
```

禁止把聊天历史、长篇推理、完整日志、整份文档长期堆积进 Context。

---

## 2. 固定阅读顺序

Context Frame 必须保持稳定顺序：

```text
1. Project Compass
2. Task Ledger
3. Progress Ledger
4. Working Set
5. Recent Tail
6. Available Handles
```

Agent 应按此顺序阅读，不要求扫描全部长期资料。

---

## 3. 记录语言

所有 Agent 写入 Context 的内容遵守：

```text
一句一事
短句优先
直接陈述
禁止长篇叙述
禁止记录完整思考过程
禁止重复已有信息
```

一个字段只表达一种语义。

错误示例：

```text
修改 reset 后测试失败，可能是 ready bit，也可能是时钟问题，后面还需要继续分析。
```

正确拆分：

```text
LastAction: 修改 reset sequence
LastResult: FAIL — timeout
Assumption: ready bit 可能未置位
OpenIssue: 时钟状态是否正常
Next: 检查 ready bit
```

---

## 4. Task Ledger 语义

### Goal

只记录当前任务目标，不记录历史过程。

### ScopeRefs

记录当前已确认任务范围的稳定引用。

### ConstraintRefs

记录 Agent 已确认必须遵守的 Rule / Gate / 其他约束引用。

### Confirmed

只能记录当前可作为工作前提的事实。

每条 Confirmed：

```text
必须单一事实
必须有可追溯 Ref
不得包含“可能 / 猜测 / 似乎 / 预计”等不确定判断
```

来源优先：

```text
Architecture
Rule
VALIDATED Knowledge
Evidence
Source / Code / RTL
```

### Assumptions

只记录尚未证实但当前有用的假设。

```text
Assumption != Confirmed
```

Assumption 不得作为硬约束或事实前提传播给后续 Agent。

### OpenIssues

只记录尚未解决的问题；问题解决后必须从当前 OpenIssues 删除。

### Plan

只记录接下来准备执行的动作，不保存已经完成的历史步骤。

---

## 5. Progress Ledger 语义

Progress Ledger 只回答“现在做到哪里”。

```text
LastAction     最近一个有意义动作
LastResult     最近动作的直接结果
Touched        当前阶段实际涉及的文件 / ID / URI
CurrentProblem 当前正在解决的一个主要问题
Blockers       阻止继续工作的事项
Next           紧接着准备执行的动作
EvidenceRefs   支撑最近结果的 Evidence
```

新状态替换旧状态；禁止为了保留历史不断追加文本。

---

## 6. Working Set

Working Set 只保存稳定引用，不保存长期展开正文。

允许：

```text
A-ID
R-ID
G-ID
Project K-ID
knowledge://global/...
knowledge://project/...
```

规则：

```text
当前需要 -> attach
当前不需要 -> detach
阶段切换 -> rebuild
```

删除 Working Set 引用不删除原始资源。

---

## 7. Recent Tail

Recent Tail 只保留少量短期因果链：

```text
ACTION
OBSERVATION
DECISION
ERROR
```

默认只保留最近少量高价值事件。

进入长期价值的信息必须沉淀到：

```text
Evidence / State / Experience / Knowledge
```

否则退出 Context。

---

## 8. Handles

Handle 是“可继续展开的地址”，不是正文。

最小格式：

```text
kind
reference
title? 
summary?
```

Agent 应优先读取 Handle，再决定是否加载正文。

禁止为了“可能有用”提前展开所有 Handle。

---

## 9. 时间规则

时间用于判断状态新旧，不作为事实可信度的主要依据。

系统自动维护：

```text
Task Ledger UpdatedAt
Progress Ledger UpdatedAt
Recent Event recordedAt
Handle addedAt
Frame builtAt
```

统一使用 ISO 8601 时间。

Agent 不手工伪造或重复填写系统时间。

静态 Architecture / Rule / Knowledge 不因为“日期更近”自动优先；优先判断：

```text
Current Effective
> Task Relevant
> Trusted
> Correct Scope
> Recency
```

---

## 10. 更新与淘汰

Context 默认采用“当前状态替换”，不是 append-only。

以下情况应更新或重建：

```text
任务范围发生变化
进入新 Phase
Working Set 明显膨胀
旧 Assumption 被证伪
Current Problem 已解决
出现新的硬约束
长任务需要 Handoff / Reset
```

旧内容退出 Context 后：

```text
有长期价值 -> Evidence / State / Experience / Knowledge
无长期价值 -> 丢弃
```

禁止用 Context 保存完整历史。

---

## 11. Budget 规则

目标是：

```text
Minimal Sufficient Context
```

优先级：

```text
required
high
normal
low
```

不得静默删除：

```text
MUST / MUST_NOT Rule
MUST Gate
Agent 明确标记 required 的内容
```

预算不足时优先移除低优先级正文，并保留 Handle。

Required 内容本身超过预算时，必须显式报告 overBudget，并触发 Agent 缩小任务范围或 rebuild；禁止静默截断语义。

---

## 12. Handoff

新 Agent 接手时默认只需要：

```text
Project Compass
最新 Task Ledger
最新 Progress Ledger
Working Set refs
Handles
```

不要求加载前一 Agent 的完整聊天、全部 Tool Output 或全部历史 Context。

Handoff 成功标准：

> 新 Agent 能快速回答“当前目标、当前范围、已确认事实、当前问题、下一步动作、需要去哪里查”。

---

## 13. 硬边界

```text
Confirmed 与 Assumption 必须分离
Context 不成为第二套 Knowledge
Context 不复制大量 Source / Evidence 正文
Context 不无限增长
Context 不依赖完整聊天历史才能恢复任务
Context 状态必须可重建
```

本标准只约束 Context 记录与生命周期内容质量，不替 Agent 做任务语义判断。
