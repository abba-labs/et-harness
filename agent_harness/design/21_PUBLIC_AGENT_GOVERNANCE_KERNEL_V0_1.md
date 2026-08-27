# Public Agent Governance Kernel v0.1

> 状态：DESIGN BASELINE  
> 适用范围：所有接入 Agent Harness 的项目  
> 第一验证项目：ET-TOOL  
> 核心目标：**公共层固定并强制 Agent 的工作生命周期；项目只提供项目资源，不决定治理是否发生。**

---

# 1. 为什么需要 Kernel

ET6003 Real Pilot 已经证明现有 Public Managers 能工作，但也暴露出一个结构性问题：

```text
Context / Knowledge / Experience / Architecture / Rules / Evidence / Gate
```

目前更像一组“可调用能力”。很多更新依赖某段流程主动调用，缺少一个统一、不可绕过的 Agent 生命周期收口机制。

本设计把公共层从：

```text
Auto Governance Orchestrator
= 监听若干事件并自动调用部分 Manager
```

升级为：

```text
Public Agent Governance Kernel
= 固定 Agent 生命周期
+ 固定 Turn Closure
+ 强制 Reflection
+ 强制调用 Mandatory Public Modules
+ 持久化 Closure Receipt
+ 失败可重放
```

Kernel 不关心项目这一轮有没有：

```text
改代码
编译
测试
硬件操作
发布
```

这些只是可能发生的工作内容，不是公共治理生命周期成立的条件。

---

# 2. 四条总原则

## 2.1 公共层强制触发

只要 Agent 开始工作，就进入公共治理生命周期。

项目不能关闭：

```text
Context Closure
Knowledge Reflection
Experience Reflection
Architecture Reflection
Rule Reflection
Evidence / State Reconcile
Working Set Reconcile
Checkpoint / Journal
```

项目只能提供项目内容和可选扩展。

## 2.2 Agent 负责语义判断

公共层不能替 Agent 判断：

```text
这条知识是否值得保存
它是项目专属还是跨项目通用
是否形成新的 Rule
是否暴露 Architecture 变化
本轮哪些结论是确定的
```

公共层负责强制 Agent 完成这个判断过程。

## 2.3 Manager 负责确定性执行

Agent 输出结构化 Reflection Result 后，各 Manager 只做确定性动作：

```text
查重
查冲突
校验引用
建立 Provenance
更新 Context
写 Candidate
更新 State
持久化 Receipt
```

## 2.4 自动触发不等于自动升级正式事实

每轮必须检查，但可以返回 `NO_CHANGE`。

```text
Context        → 可直接更新当前任务状态
Evidence       → 可 append 已发生事实
Experience     → 可生成 CANDIDATE
Knowledge      → 可生成 CANDIDATE
Architecture   → 可生成 CHANGE CANDIDATE
Rules          → 可生成 CHANGE CANDIDATE
```

禁止：

```text
Reflection → 自动 VALIDATED Knowledge
Reflection → 自动修改正式 Rule
Reflection → 自动修改正式 Architecture
```

正式升级继续走各自 Validation / Promotion Policy。

---

# 3. 一级架构

```text
DeepSeek / Codex / Claude / Cursor
                ↓
         Harness Lifecycle Adapter
                ↓
══════════════════════════════════════════
       PUBLIC AGENT GOVERNANCE KERNEL
══════════════════════════════════════════
                ↓
        Lifecycle Controller
                ↓
     ┌──────────┴──────────┐
     ↓                     ↓
 TURN_START             TURN_CLOSING
     ↓                     ↓
 Bootstrap          Turn Journal Seal
 Public Context            ↓
     ↓              Reflection Engine
 Agent Work                ↓
                    Agent Semantic Judge
                           ↓
                    Scope Resolver
                           ↓
                    Closure Coordinator
                           ↓
        ┌────────────────────────────────┐
        │ Mandatory Closure Modules      │
        │ Context                        │
        │ Knowledge                      │
        │ Experience / Memory            │
        │ Architecture                   │
        │ Rules                          │
        │ Evidence / State               │
        │ Working Set / Open Issues      │
        │ Obligation / Gate Reconcile    │
        └────────────────────────────────┘
                           ↓
                     Closure Receipt
                           ↓
                       TURN_CLOSED
```

项目层始终位于 Kernel 之下：

```text
Project Plugin
= Identity
+ Architecture
+ Rules
+ Project Knowledge
+ Gates
+ Optional Adapters
```

项目层不实现 Agent Lifecycle。

---

# 4. Agent 生命周期

Kernel 只管理 Agent 工作生命周期：

```text
AGENT_START
    ↓
TASK_START / TASK_RESUME
    ↓
TURN_START
    ↓
TURN_ACTIVE
    ↓
TURN_CLOSING
    ↓
TURN_CLOSED
    ↓
TURN_START
    ↓
...
    ↓
TASK_PAUSE / TASK_COMPLETE
    ↓
AGENT_END
```

## 4.1 TURN_START

固定公共动作：

```text
1. 检查上一轮是否存在 CLOSURE_PENDING
2. 如果存在，先 replay 上一轮 Closure
3. 恢复 Task / Context
4. 解析或确认 Project Binding
5. 加载 Public + Project Knowledge / Memory 候选
6. 加载相关 Architecture / Rules / Open Obligations
7. Reconcile Working Set
8. Build 当前 Context Frame
9. 允许 Agent 开始本轮工作
```

## 4.2 TURN_ACTIVE

Agent 正常工作。

Kernel 可以观察事件，但不以代码、Build、Test 等项目动作定义生命周期。

## 4.3 TURN_CLOSING

Agent 本轮主要工作完成、最终 Turn 即将提交时，公共层必须执行：

```text
1. Seal Turn Journal
2. Trigger Unified Reflection
3. Agent 输出结构化 Reflection Result
4. Closure Coordinator 调用所有 Mandatory Closure Modules
5. 收集 Module Receipt
6. 持久化 Closure Receipt
7. 所有 Mandatory Module 均成功后标记 TURN_CLOSED
```

如果 Closure 未完成：

```text
TURN_CLOSING
→ CLOSURE_PENDING
```

不能伪造 `TURN_CLOSED`。

## 4.4 TASK_PAUSE / AGENT_END

自动：

```text
完成最后一轮 Closure
→ createHandoff
→ persist checkpoint
→ pause / complete
```

不要求项目主动调用 Context 更新。

---

# 5. Project Binding 不是治理开关

现有实现存在一个风险：Project Identity 解析失败时，可能根本不进入 Auto Governance。

Kernel v0.1 禁止这种行为。

Task 必须先存在，再绑定项目：

```text
Task Binding State
= UNBOUND
| BOUND(projectId)
```

`UNBOUND` 时仍然执行：

```text
Context
Public Knowledge
Public Memory
Turn Journal
Reflection
Checkpoint
```

只是不执行需要 Project Resource 的模块动作。

项目一旦识别成功：

```text
UNBOUND → BOUND(projectId)
```

后续 Turn 自动增加 Project Architecture / Rules / Knowledge / Gates。

因此：

> 无法识别项目，不等于无法治理 Agent。

---

# 6. Turn Journal

Turn Journal 是 Closure 的事实输入和重放基础。

必须先 Journal，再 Reflection。

```text
TURN_ACTIVE
   ↓
Turn Journal append
   ↓
TURN_CLOSING
   ↓
Journal seal
   ↓
Reflection
```

## 6.1 Journal 最小结构

```text
TurnJournalRecord {
  taskId
  turnId
  agentId
  projectBinding
  startedAt
  closingAt
  userMessageRefs
  assistantMessageRefs
  toolEventRefs
  resourceTouchRefs
  stateVersionBefore
  sessionRef?
  status: OPEN | SEALED | CLOSURE_PENDING | CLOSED
}
```

Journal 不要求永久复制完整聊天历史。

优先保存：

```text
Message ID / Session Ref
Tool Event Ref
Resource Ref
稳定状态版本
```

Harness 无法提供可重放 Session Ref 时，可保存有上限的 Turn Envelope。

## 6.2 Journal 作用

```text
Agent/Harness 崩溃
Closure Module 失败
Reflection 中断
下一轮开始
```

都可以根据 Journal 重新执行 Closure，而不是丢掉上一轮认知结果。

---

# 7. Unified Turn Reflection

不能让每个 Manager 各自调用一次大模型。

每轮只进行一次统一的语义 Reflection：

```text
Turn Journal
+ 当前 Task Context
+ Public / Project candidate references
        ↓
Agent Reflection
        ↓
TurnReflectionResult
```

## 7.1 Reflection Result

```text
TurnReflectionResult {
  turnId

  context {
    progress
    decisions[]
    confirmed[]
    assumptions[]
    openIssues[]
    next[]
    touchedRefs[]
  }

  knowledge[]
  experience[]
  architecture[]
  rules[]
  evidence[]

  workingSet {
    keep[]
    add[]
    remove[]
  }

  obligations {
    opened[]
    resolved[]
    unchanged[]
  }
}
```

每个可沉淀条目统一包含：

```text
ReflectionCandidate {
  domain
  title
  factOrProposal
  scopeDecision
  rationale
  provenanceRefs[]
  evidenceRefs[]
  relatedRefs[]
  confidence
}
```

---

# 8. 公共 Scope Resolver

把“Project 还是 Public”的判断抽象成公共协议，而不是只给 Knowledge 使用。

统一语义：

```text
NONE
PROJECT
PUBLIC
BOTH
```

说明：

```text
NONE
= 本轮没有值得沉淀的该类信息

PROJECT
= 与当前项目实现、约束、架构或事实绑定

PUBLIC
= 跨项目可复用，属于公共 Harness / Governance / Engineering Knowledge

BOTH
= 项目内已经成立，同时存在值得进入公共候选池的可泛化结论
```

Agent 必须给出：

```text
scopeDecision
rationale
```

公共层只校验结构，不替 Agent 做语义分类。

## 8.1 Knowledge 映射

```text
PROJECT → Project Knowledge Candidate
PUBLIC  → Global/Public Knowledge Candidate
BOTH    → 两边各生成 Candidate，并建立互相引用
```

当前实现中的：

```text
knowledge://global
```

在 Kernel 语义上等价于：

```text
PUBLIC Knowledge Store
```

## 8.2 Architecture / Rules 映射

项目资源已有正式 Project Store。

Public v0.1 先进入公共 Change Candidate Store：

```text
architecture-change://public/...
rule-change://public/...
```

不在 Turn Closure 中直接修改 Public 正式架构或规则。

---

# 9. Closure Coordinator

Closure Coordinator 不做语义判断，只保证所有公共模块被执行。

每个 Module 必须实现统一接口：

```text
ClosureModule {
  id
  version
  mandatory
  domains[]

  apply(input: ClosureModuleInput): ClosureModuleReceipt
}
```

输入：

```text
ClosureModuleInput {
  taskId
  turnId
  projectBinding
  journalRef
  reflection
  idempotencyKey
}
```

输出：

```text
ClosureModuleReceipt {
  moduleId
  turnId
  status:
    APPLIED
    NO_CHANGE
    BLOCKED
    FAILED
  writes[]
  candidateRefs[]
  evidenceRefs[]
  stateVersionAfter?
  reason?
}
```

`NO_CHANGE` 是成功结果。

意味着：

> 模块必须被调用，但不要求每轮产生新内容。

---

# 10. Mandatory Closure Modules

Kernel v0.1 固定绑定以下模块。

## 10.1 Context Closure

每轮必定 `APPLIED`。

自动同步：

```text
Task Ledger
Progress Ledger
Recent Tail
Open Issues
Next
Working Set references
stateVersion
```

这是每轮 Context 更新的唯一公共入口之一。

项目不能关闭。

## 10.2 Knowledge Closure

每轮必须检查：

```text
本轮是否形成新知识？
PROJECT / PUBLIC / BOTH / NONE？
```

如果有 Candidate：

```text
搜索对应 Knowledge Store
→ duplicate check
→ contradiction check
→ provenance check
→ evidence/source binding
→ submit CANDIDATE
```

禁止自动 `VALIDATED`。

## 10.3 Experience / Memory Closure

每轮检查本轮是否存在可复用经验：

```text
问题
尝试
结论
已验证方法
失败模式
工作策略
```

有价值时生成 Experience `CANDIDATE`。

后续可由 Knowledge Closure 把它提交到 Project/Public Knowledge Candidate。

## 10.4 Architecture Closure

每轮检查：

```text
是否发现新的架构事实？
是否发现现有 Architecture 与真实项目不一致？
是否形成新的边界/依赖关系？
```

只生成：

```text
Architecture Change Candidate
```

不直接改正式 A-tree。

## 10.5 Rule Closure

每轮检查：

```text
是否发现稳定、可重复、应约束未来 Agent 的新规则？
现有 Rule 是否与真实行为冲突？
```

只生成：

```text
Rule Change Candidate
```

不直接改正式 R-tree。

## 10.6 Evidence / State Closure

把本轮已经发生的事实与 Reflection 结果建立关联：

```text
Turn Journal
Reflection
Candidate
Context
```

Evidence 只能记录已发生事实，不能把 Agent 猜测伪造成 PASS Evidence。

## 10.7 Working Set Closure

每轮按照 Reflection 自动：

```text
keep
add
remove
```

下一轮无需重新从完整聊天历史恢复工作集。

## 10.8 Obligation / Gate Reconcile

这个模块只处理“已经存在的治理义务”。

它不要求项目一定有 Build/Test，也不把 Build/Test 当作 Turn 生命周期。

每轮只是：

```text
当前有没有 open obligation？
本轮是否新增 obligation？
哪些已解决？
哪些仍 pending？
```

没有任何 obligation 时返回：

```text
NO_CHANGE
```

---

# 11. Closure Receipt

一轮最终必须形成唯一 Closure Receipt：

```text
TurnClosureReceipt {
  taskId
  turnId
  journalRef
  reflectionRef
  moduleReceipts[]
  status: CLOSED | PENDING | BLOCKED
  closedAt?
}
```

只有所有 Mandatory Module 返回：

```text
APPLIED | NO_CHANGE
```

才允许：

```text
status = CLOSED
```

`FAILED/BLOCKED` 时保留 Journal，下一轮重放。

---

# 12. 幂等与重放

每个 Closure Module 都必须使用：

```text
idempotencyKey = taskId + turnId + moduleId + reflectionVersion
```

同一轮重复执行不得产生重复 Candidate 或重复 Context Event。

重放规则：

```text
TURN_START
↓
发现 previous turn = CLOSURE_PENDING
↓
加载 Journal + Reflection
↓
只重跑缺 Receipt 的 Module
↓
Closure 完成
↓
再开始新 Turn
```

---

# 13. Reflection 失败策略

Reflection 是 Mandatory。

如果 Agent Reflection 失败：

```text
Journal 已 SEALED
Reflection = MISSING
Closure = PENDING
```

下一轮优先补 Reflection。

禁止：

```text
Reflection 失败
→ 假装没有新 Knowledge / Rule / Architecture
→ TURN_CLOSED
```

---

# 14. Harness Adapter 边界

Kernel 只认识标准生命周期事件：

```text
agent.started
agent.resumed
task.started
turn.started
turn.closing
turn.closed
task.paused
task.completed
agent.disposed
```

DeepSeek/Cordis、Codex、Claude、Cursor 分别实现 Adapter：

```text
Native Harness Event
→ Normalized Governance Lifecycle Event
```

Kernel 本身不能硬编码某个 Harness 的事件语义。

v0.1 第一实现仍可以使用 Cordis，但接口必须先按上述标准事件设计。

---

# 15. Mandatory Kernel 加载

Kernel 不能只是普通“推荐插件”。

治理模式下启动条件必须是：

```text
Governance Core
+ Lifecycle Controller
+ Turn Journal
+ Reflection Engine
+ Closure Coordinator
+ Mandatory Closure Modules
```

任何 Mandatory 组件缺失：

```text
Governance Runtime = DEGRADED / BLOCKED
```

不得静默退化成“没有治理也继续工作”。

项目 Plugin 加载失败不等于 Kernel 消失；Task 可以保持 `UNBOUND`。

---

# 16. Project Plugin 的新边界

项目仍只提供：

```text
project.yaml
architecture/
rules/
knowledge/
gates/
optional adapters/
```

项目不能实现或覆盖：

```text
Turn Lifecycle
Turn Journal
Reflection Trigger
Scope Resolver Protocol
Closure Coordinator
Mandatory Module List
Closure Receipt
Replay Policy
```

项目可以提供：

```text
项目资源内容
项目候选分类 metadata
项目特殊 Validation Policy
项目特殊 Adapter
```

但不能关闭公共 Closure。

---

# 17. 与现有 Public Managers 的关系

现有 Manager 不推翻，改成被 Kernel 调度：

```text
Project Manager
Architecture Navigator
Rule Manager
Knowledge Manager
Evidence / State Manager
Gate Manager
Context Manager / Builder
Experience / Memory Manager
```

新关系：

```text
过去：Agent / Orchestrator → Manager

v0.1：
Lifecycle Kernel
    ↓
Unified Reflection
    ↓
Closure Coordinator
    ↓
Manager
```

Manager 继续负责自己的数据一致性和接口标准。

---

# 18. 这次 Pilot 得到的架构经验

ET6003 Pilot 暴露出的经验进入本设计：

## 18.1 不能依赖 Agent “记得更新”

Context、Knowledge、Experience 等必须由公共生命周期触发。

## 18.2 自动化必须有收口阶段

只有 task bootstrap 和 code-change trigger 不够。

真正闭环必须有：

```text
TURN_CLOSING → Reflection → Closure → Receipt
```

## 18.3 公共层不能依赖项目动作

Build/Test 不是 Context 或 Knowledge 更新前提。

纯阅读、纯分析、纯设计的一轮也必须完整 Closure。

## 18.4 语义判断与确定性执行必须分离

```text
Agent = 判断
Kernel = 强制判断发生
Manager = 执行判断结果
```

## 18.5 Public / Project Scope 必须成为公共协议

Knowledge 已经证明需要双 Scope；同样机制应推广到 Experience、Architecture、Rules。

## 18.6 生成/索引副作用必须可审计

Turn Closure 的 Manager 写入必须出现在 Module Receipt 中。

不允许“读取过程中偷偷修改项目资源”。

---

# 19. v0.1 实施顺序

## Step 1 — Lifecycle Contracts

实现：

```text
NormalizedLifecycleEvent
TaskRuntime
TurnRuntime
TurnJournalRecord
TurnClosureReceipt
```

## Step 2 — Turn Journal

实现：

```text
open
append refs
seal
mark pending
mark closed
replay lookup
```

## Step 3 — Reflection Contract

实现统一：

```text
TurnReflectionResult
ReflectionCandidate
ScopeDecision
```

先允许测试 Fake Agent Reflection Provider。

## Step 4 — Closure Coordinator

实现：

```text
Module registration
Mandatory module set
idempotency
Receipt
failure replay
```

## Step 5 — 第一批 Module Adapter

接入：

```text
Context
Knowledge
Experience / Memory
Architecture
Rules
Evidence / State
Working Set
Obligation / Gate Reconcile
```

## Step 6 — Cordis Harness Adapter

把当前 Cordis 事件转换为标准 Agent/Turn Lifecycle。

## Step 7 — Pure Analysis Pilot

测试任务只允许：

```text
阅读
分析
形成结论
```

禁止把“改代码/Build/Test”作为验收条件。

验证每轮结束：

```text
Context updated
Knowledge reflection executed
Project/Public scope decision recorded
Experience reflection executed
Architecture reflection executed
Rule reflection executed
Evidence/State reconciled
Working Set reconciled
Closure Receipt persisted
```

---

# 20. v0.1 Acceptance Gates

必须通过以下场景。

## A. Pure Analysis Turn

Agent 只阅读项目并分析。

预期：所有 Closure Module 均被调用；无关模块返回 `NO_CHANGE`。

## B. Knowledge PROJECT

产生项目专属知识。

预期：Project Knowledge Candidate；Public Store 不写。

## C. Knowledge PUBLIC

产生跨项目通用知识。

预期：Public/Global Knowledge Candidate；Project Store 可仅保存引用。

## D. Knowledge BOTH

项目事实成立，同时具有公共泛化价值。

预期：两个 Candidate + Provenance 关系。

## E. No New Knowledge

预期：Knowledge Module Receipt = `NO_CHANGE`，Turn 仍可 CLOSED。

## F. Reflection Failure

预期：Turn = `CLOSURE_PENDING`；下一轮开始前自动 replay。

## G. One Module Failure

预期：不得标记 CLOSED；已成功 Module 不重复写入。

## H. Agent / Harness Dispose

预期：最后 Turn Closure → Handoff → Persist。

## I. Unbound Project

预期：Public Lifecycle 仍工作；Project-only Module 返回 no-project/no-change receipt，不绕过 Kernel。

## J. New Project

只接 `project.yaml + resources`，不实现任何 lifecycle hook。

预期：完整 Turn Lifecycle 自动成立。

---

# 21. 明确非目标

Kernel v0.1 不负责：

```text
强制每个项目必须 Build
强制每个项目必须 Test
替 Agent 判断业务正确性
自动把 Candidate 升级为正式 Knowledge/Rule/Architecture
复制完整聊天历史作为 Context
在项目层复制一套生命周期代码
```

---

# 22. 最终闭环

```text
Human Message
    ↓
TURN_START
    ↓
Public Bootstrap
    ↓
Agent Work
    ↓
TURN_CLOSING
    ↓
Turn Journal Seal
    ↓
Unified Reflection
    ↓
Agent Semantic Judgment
    ↓
Scope Resolver
    ↓
Closure Coordinator
    ↓
ALL Mandatory Public Modules
    ↓
Closure Receipt
    ↓
TURN_CLOSED
    ↓
下一轮从最新治理状态继续
```

最终原则：

> **项目只提供“是什么”；公共 Kernel 固定“什么时候检查、什么时候思考、什么时候沉淀、什么时候收口”。**

> **每轮 Agent 工作都必须经过同一条公共治理闭环，不依赖项目类型，也不依赖这一轮是否修改代码、编译或测试。**
