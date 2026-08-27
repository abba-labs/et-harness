# Context Management v0.2

## 1. 定位

Context Management 是贯穿 Agent 任务生命周期的横向能力，不是任务分析完成后的末端步骤。

```text
Human Task
  ↓
Bootstrap Context
  ↓
Agent 初步分析
  ↕
Architecture / Rule / Knowledge / State / Gate
  ↕
Context Working Set
  ↓
Agent Work / Tool / Test
  ↓
Progress / Evidence
  ↓
Rebuild / Handoff / Complete
```

核心目标：

> 最小充分上下文，而不是最小上下文，也不是历史上下文堆积。

## 2. 长期层与 Context 分离

长期信息：

```text
Architecture
Rules
Knowledge
Gate
Evidence
State
Experience
```

Context State 不复制这些正文，只保存稳定引用和当前任务状态。

因此 Context 可以随时删除并重建。

## 3. Context Frame

```text
Context Frame
├─ Project Compass
├─ Task Ledger
├─ Progress Ledger
├─ Working Set
├─ Recent Tail
└─ Available Handles
```

### Project Compass

提供项目身份、资源入口和文件级 Route Map，解决新 Agent 没有方向的问题。

它只给地图，不深载正文。

### Task Ledger

保存任务当前认知：

```text
Goal
Phase
ScopeRefs
ConstraintRefs
Confirmed
Assumptions
OpenIssues
Plan
```

Confirmed 与 Assumptions 结构分开，避免推测天然混入确认事实。

### Progress Ledger

保存当前执行位置：

```text
LastAction
LastResult
TouchedRefs
CurrentProblem
Blockers
Next
EvidenceRefs
```

### Working Set

只保存 Agent 显式选择的 A/R/K/G 引用。

`buildFrame()` 时重新解析当前内容。

### Recent Tail

只保存最近少量关键 Action / Observation / Decision / Error。

固定环形上限，超出时最老事件自动退出当前 Context State。

### Available Handles

保存可以继续按需展开的轻量引用，例如：

```text
knowledge://global/K...
file://...
source://...
evidence://...
```

Handle 本身不加载正文。

## 4. 生命周期

```text
BOOTSTRAP
  ↓
DISCOVER
  ↓
FOCUS
  ↓
WORK
  ↓
ADAPT
  ↓
REBUILD / RESET
  ↓
HANDOFF / COMPLETE
```

实现接口：

```text
beginTask
updateTaskLedger
updateProgressLedger
attach / detach / replaceWorkingSet
addHandles / removeHandles
recordRecent
buildFrame
rebuild
pause / resume
createHandoff
complete
```

## 5. Rebuild 是主机制

Context 不采用 append-only 生命周期。

```text
阶段 A Working Set
  ↓
阶段变化
  ↓
rebuild
  ↓
阶段 B Working Set
```

Rebuild：

```text
保留 Task Ledger
保留 Progress Ledger
保留 Handles
替换 / 保留 Working Set
默认清空 Recent Tail
增加 generation
```

旧资源正文不会因为曾经加载过而继续存在于新 Frame。

## 6. Handoff

新 Agent 不需要读取前一个 Agent 的完整聊天历史。

Handoff 只需要：

```text
Project Compass（重新生成）
Task Ledger
Progress Ledger
Working Set refs
Handles
```

新 Agent 调用 `resume()` / `buildFrame()` 后，从当前长期层重新恢复正文。

## 7. State Storage

Context 生命周期复用 Evidence / State Manager：

```text
scope = context:<taskId>
key   = session
```

State version 提供并发更新保护。

EvidenceRefs 继续由 Evidence / State Manager 校验。

## 8. 当前边界

v0.2 不做：

```text
LLM 自动摘要作为事实源
Vector DB
Embedding Context Router
自动决定 Working Set
无限聊天历史
自动把 Agent 推理写成 Knowledge
```

Agent 仍是任务理解和资源选择主体。

## 9. 后续单独定义

Context Writing Rules 不属于本次实现。

后续再单独规定：

```text
句子长度
字段表达
日期要求
Confirmed / Assumption 写法
Evidence / Ref 写法
重复信息规则
过期信息规则
```
