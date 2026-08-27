# Context Lifecycle Interface v0.2

## 1. Services

同一个公共插件提供两个服务：

```text
contextManager
contextBuilder
```

`contextManager` 管生命周期；`contextBuilder` 只装配当前 Frame。

## 2. Persistent State

Context 生命周期状态复用 Evidence / State Manager：

```text
scope = context:<taskId>
key   = session
```

持久化内容只有：

```text
Task Ledger
Progress Ledger
Working Set references
Handles
Recent Tail
Lifecycle metadata
```

不保存 Architecture / Rule / Knowledge / Gate 展开正文。

## 3. Start / Read

```text
contextManager.beginTask({
  projectId,
  taskId,
  goal,
  maxChars?,
  recentTailLimit?
})

contextManager.getTask(projectId, taskId)
```

新任务从：

```text
phase = bootstrap
status = ACTIVE
generation = 1
workingSet = []
```

开始。

## 4. Ledger

```text
contextManager.updateTaskLedger(projectId, taskId, patch, evidenceRefs?)
contextManager.updateProgressLedger(projectId, taskId, patch)
```

Task Ledger 结构分离：

```text
goal
phase
scopeRefs
constraintRefs
confirmed
assumptions
openIssues
plan
updatedAt
```

Progress Ledger：

```text
lastAction
lastResult
touchedRefs
currentProblem
blockers
next
evidenceRefs
updatedAt
```

## 5. Working Set

```text
contextManager.attach(projectId, taskId, references)
contextManager.detach(projectId, taskId, references)
contextManager.replaceWorkingSet(projectId, taskId, references)
```

Working Set 只保存稳定引用：

```text
A-ID
R-ID
K-ID / Knowledge URI
G-ID
```

正文由 `buildFrame()` 实时解析。

## 6. Handles

```text
contextManager.addHandles(projectId, taskId, handles)
contextManager.removeHandles(projectId, taskId, references)
```

Handle 只告诉 Agent “还有什么可以按需展开”，不自动加载正文。

## 7. Recent Tail

```text
contextManager.recordRecent(projectId, taskId, event)
```

Recent Tail 是固定上限环形队列；超过上限自动移除最老事件。

## 8. Build

```text
contextManager.buildCompass(projectId)
contextManager.buildFrame(projectId, taskId, maxChars?)
```

Frame 固定由以下部分组成：

```text
Project Compass      required
Task Ledger          required
Progress Ledger      high
Working Set          explicit priorities
Recent Tail          normal
Available Handles    low
```

## 9. Rebuild

```text
contextManager.rebuild({
  projectId,
  taskId,
  phase?,
  workingSet?,
  clearRecentTail?,
  evidenceRefs?
})
```

Rebuild：

```text
增加 generation
可替换 Working Set
默认清空 Recent Tail
保留 Task / Progress Ledger
保留 Handles
```

它是长任务控制 Context 膨胀的主机制，不依赖无限历史追加。

## 10. Handoff / Resume / Complete

```text
contextManager.createHandoff(projectId, taskId)
contextManager.pause(projectId, taskId)
contextManager.resume(projectId, taskId)
contextManager.complete(projectId, taskId)
```

新 Agent 接手时只需要恢复：

```text
Compass
Task Ledger
Progress Ledger
Working Set refs
Handles
```

再调用 `buildFrame()`，无需读取前一 Agent 的完整聊天历史。

## 11. Boundary

Context Manager 不负责：

```text
替 Agent 判断任务语义
自动决定应该 attach 哪条知识
把聊天摘要升级为事实
复制长期知识正文到 State
维护第二套 Architecture / Rule / Knowledge
```

Agent 仍然负责理解与选择；Context 体系只负责安全、轻量、可重建地维持工作视图。
