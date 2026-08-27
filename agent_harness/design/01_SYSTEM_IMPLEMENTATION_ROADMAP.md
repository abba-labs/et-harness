# 智能体治理与进化系统实施路线图

> 路线图：v0.6  
> 基座：DeepSeek Harness / Cordis  
> 第一试点：ET-TOOL  
> 总原则：**公共层固定 Agent 的工作生命周期；Agent 负责语义判断；Manager 负责确定性执行；项目只提供项目资源，不决定治理是否发生。**

---

# 1. 当前路线

```text
Phase 0   Harness / Cordis 能力盘点                         DONE
   ↓
Phase 1   Governance Core                                  DONE
   ↓
Phase 2   Project Contract / Resource Meta Standard        IMPLEMENTED
   ↓
Phase 3   Public Managers v0.2                             DONE / MANAGER BASELINE FROZEN
   ↓
Phase 4A  Public Agent Governance Kernel v0.1              DESIGN / NEXT IMPLEMENTATION
   ↓
Phase 4B  ET-TOOL Real Agent Pilot                         PAUSED FOR KERNEL VALIDATION
   ↓
Phase 5   Plugin Recommender / Multi-Agent / Learning
   ↓
Phase 6   Cross-Harness Gateway
```

关键调整：

> Phase 3 冻结的是各 Public Manager 的接口和数据模型基线，不再把“自动治理生命周期”视为已经完成。ET6003 Real Pilot 证明 Manager 能力已经存在，但缺少统一、强制、每轮自动收口的 Agent Lifecycle Kernel。

---

# 2. 长期职责边界

```text
Human / Agent Turn
        ↓
Public Agent Governance Kernel
  = Agent / Task / Turn Lifecycle
  = Turn Journal
  = Unified Reflection Trigger
  = Scope Resolver Protocol
  = Closure Coordinator
  = Mandatory Closure Modules
  = Closure Receipt / Replay
        ↓
Agent
  = 理解需求
  = 阅读项目
  = 推理 / 判断
  = 实施
  = 对 Reflection 做语义判断
        ↓
Public Managers
  = Project / Architecture / Rule / Knowledge
  = Evidence / State
  = Gate / Obligation
  = Context
  = Experience / Memory
  = 确定性读写、校验、查重、持久化
        ↓
Project Plugin
  = project.yaml
  = architecture/
  = rules/
  = knowledge/
  = gates/
  = optional adapters/
```

核心边界：

```text
项目决定“是什么”
公共 Kernel 决定“什么时候检查、什么时候思考、什么时候沉淀、什么时候收口”
Agent 决定“语义上应该怎么判断”
Manager 决定“如何一致地执行判断结果”
```

---

# 3. Phase 0 — Harness / Cordis

状态：**DONE**。

复用：

```text
Context / Service / Inject / Event / Effect
Bundle / Profile
Session / Tools
Subagent / Agent Teams
Workflow / Jobs
Approval / Credential / Sandbox
```

不制造第二套 Harness Runtime。

---

# 4. Phase 1 — Governance Core

状态：**DONE**。

已有：

```text
Capability Catalog
Manifest Validation
Plugin Admission
Provider Registration
Project Registration
Plugin State
Governance Events
Cordis Service Adapter
```

后续 Kernel 作为强制公共治理层运行在 Governance Core + Harness Runtime 之上。

---

# 5. Phase 2 — Project Contract

状态：**IMPLEMENTED**。

已有：

```text
project.yaml v0.1
ProjectContext
Project Root Discovery
Resource Handle / Standard Version
00_INDEX machine interface
NNN numbered file
Stable Node ID
Common Resource Admission Validator
```

资源标准：

```text
Architecture → architecture-v0.1 / Axxx
Rule         → rule-v0.1         / Rxxx
Knowledge    → knowledge-v0.1 + knowledge-library-v0.2
Gate         → gate-v0.1         / Gxxx
```

Project Contract 不新增生命周期 hook；生命周期属于 Public Kernel。

---

# 6. Phase 3 — Public Managers v0.2

状态：**DONE；MANAGER CONTRACT BASELINE FROZEN。**

| Manager | 能力 | 主要职责 |
|---|---|---|
| Project Manager | `governance.project` | 项目识别、ProjectContext、资源入口 |
| Architecture Navigator | `architecture.navigate` | Architecture 校验 / Cache / 路由 |
| Rule Manager | `rule.navigate` | Rule Tree / 候选路由 |
| Knowledge Manager | `knowledge.navigate / knowledge.library` | Public(Global) + Project Knowledge、Source / Verification / Validation |
| Evidence / State Manager | `evidence.* / state.*` | Evidence append-only / State versioned |
| Gate Manager | `gate.navigate` | Gate Route / Execution Plan / MUST Evidence Guard |
| Context Manager / Builder | `context.build / context.manage` | Ledger / Working Set / Rebuild / Handoff / Lint |
| Experience / Memory Manager | `experience.manage / memory.context` | Experience、Memory、Knowledge Candidate 链路 |

Phase 3 已证明这些 Manager 可以独立工作。

Phase 4A 不推翻这些 Manager，而是给它们增加统一公共调度层：

```text
Lifecycle Kernel
→ Unified Reflection
→ Closure Coordinator
→ Existing Public Managers
```

---

# 7. 为什么增加 Phase 4A

ET6003 Auto Governance Pilot 暴露出以下事实：

```text
1. 任务开始和代码变化可以自动触发，但 Turn 结束没有统一 Closure。
2. Context 更新依赖若干显式事件，不是每轮强制行为。
3. Knowledge / Experience / Architecture / Rules 没有每轮统一 Reflection。
4. Public / Project Scope 判断没有抽象成所有沉淀模块共享协议。
5. Manager 有能力，但 Agent 仍可能需要“记得调用”。
6. Build/Test 等项目动作不应该成为 Context / Knowledge 沉淀的前提。
```

因此必须先补 Agent Lifecycle，而不是继续给单个 Manager 增加零散 trigger。

详细设计：

```text
agent_harness/design/21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md
```

---

# 8. Phase 4A — Public Agent Governance Kernel v0.1

状态：**DESIGN / NEXT IMPLEMENTATION**。

## 8.1 Step 1 — Lifecycle Contract

实现标准事件：

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

实现运行状态：

```text
TaskRuntime
TurnRuntime
ProjectBinding = UNBOUND | BOUND(projectId)
```

## 8.2 Step 2 — Turn Journal

实现：

```text
open
append refs
seal
closure pending
closed
replay lookup
```

Journal 必须先于 Reflection 持久化。

## 8.3 Step 3 — Unified Reflection

每轮只触发一次统一 Agent Reflection，不让每个 Manager 单独调用模型。

输出：

```text
Context
Knowledge
Experience
Architecture
Rules
Evidence
Working Set
Obligations
```

并统一使用 Scope Decision：

```text
NONE
PROJECT
PUBLIC
BOTH
```

## 8.4 Step 4 — Closure Coordinator

实现 Mandatory Module Registry：

```text
Context Closure
Knowledge Closure
Experience / Memory Closure
Architecture Closure
Rule Closure
Evidence / State Closure
Working Set Closure
Obligation / Gate Reconcile
```

每个模块必须返回：

```text
APPLIED
NO_CHANGE
BLOCKED
FAILED
```

`NO_CHANGE` 是正常成功结果。

## 8.5 Step 5 — Closure Receipt / Replay

一轮只有在所有 Mandatory Module 返回 `APPLIED | NO_CHANGE` 时才能：

```text
TURN_CLOSED
```

失败则：

```text
CLOSURE_PENDING
```

下一轮开始前自动 replay 未完成模块。

## 8.6 Step 6 — Cordis Adapter

把 DeepSeek Harness / Cordis 原生事件转换为统一 Lifecycle Event。

Kernel 本身不得依赖 Cordis 事件名称。

## 8.7 Step 7 — Pure Analysis Pilot

第一个 Kernel Pilot 不修改代码、不编译、不测试。

任务示例：

> 阅读项目 Architecture / Knowledge，分析目前知识体系存在的问题并提出建议。

验证每轮结束是否自动：

```text
Context 更新
Knowledge Reflection
PROJECT / PUBLIC / BOTH 判断
Experience Reflection
Architecture Reflection
Rule Reflection
Evidence / State Reconcile
Working Set Reconcile
Closure Receipt
```

只有该 Pilot PASS，才继续 ET6003 代码类 Pilot。

---

# 9. Phase 4B — ET-TOOL Project + Real Agent Pilot

状态：**已有大量内容；当前暂停在 Kernel 前置验证。**

已经完成/验证过的项目内容：

```text
Architecture
Rules
Knowledge taxonomy + Batch 1
Code Gates
Code Review Adapter
No-Hardware Real Agent Pilot
Auto Governance Orchestrator v0.1 Pilot
```

ET6003 Pilot 已作为 Kernel 设计的重要输入。

后续顺序：

```text
Kernel Pure Analysis Pilot PASS
↓
恢复 ET6003 Real Pilot
↓
验证代码开发场景同样自动经历 Turn Closure
↓
验证 Handoff / Resume / Multi-Turn Knowledge Evolution
```

ET-TOOL 不新增任何项目级 Lifecycle 实现。

---

# 10. Public / Project 沉淀策略

所有需要 Agent 语义判断的沉淀模块统一使用：

```text
NONE
PROJECT
PUBLIC
BOTH
```

## Knowledge

```text
PROJECT → Project Knowledge CANDIDATE
PUBLIC  → Public(Global) Knowledge CANDIDATE
BOTH    → 两边 Candidate + Provenance
```

## Experience

```text
先进入 Experience CANDIDATE
→ Scope Reflection
→ 可继续进入 Project / Public Knowledge Candidate
```

## Architecture / Rules

```text
PROJECT → Project Change Candidate
PUBLIC  → Public Framework Change Candidate
BOTH    → 两边 Candidate
```

Turn Closure 不直接修改正式 A-tree / R-tree。

---

# 11. 强制边界

项目不能关闭或覆盖：

```text
Agent / Task / Turn Lifecycle
Turn Journal
Reflection Trigger
Scope Resolver Protocol
Mandatory Closure Module List
Closure Receipt
Replay Policy
```

项目只能提供：

```text
Identity
Architecture
Rules
Knowledge
Gates
Optional Adapters
Project-specific validation metadata
```

无法识别 Project 时，Kernel 仍运行：

```text
Task = UNBOUND
Context / Public Knowledge / Public Memory / Journal / Reflection 继续工作
```

Project Identity 不是治理开关。

---

# 12. Phase 4A Acceptance Gate

必须覆盖：

```text
A. Pure Analysis Turn
B. Project Knowledge Candidate
C. Public Knowledge Candidate
D. BOTH Scope Candidate
E. No-Change Turn
F. Reflection Failure + Replay
G. Closure Module Failure + Idempotent Replay
H. Agent Dispose + Final Handoff
I. Unbound Project Governance
J. New Project Without Lifecycle Code
```

唯一关闭条件：

```text
PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1=PASS
```

---

# 13. Phase 5 — 后续增强

Kernel v0.1 和 ET-TOOL Pilot 稳定后再做：

```text
Plugin Recommender
Multi-Agent Governance
Semantic duplicate / conflict enhancement
Knowledge aging
Distributed Evidence / State Storage
Public Architecture / Rule Promotion workflow
```

---

# 14. Phase 6 — Cross-Harness Gateway

目标：

```text
DeepSeek / Cordis Adapter
Codex Adapter
Claude Adapter
Cursor Adapter
        ↓
Normalized Governance Lifecycle
        ↓
同一个 Public Agent Governance Kernel
```

跨 Harness 时，Project Plugin 与 Public Manager 不重写。

---

# 15. 当前最近工程动作

```text
1. 完成 Public Agent Governance Kernel v0.1 设计基线
2. 实现 Lifecycle Contract + Turn Journal
3. 实现 Unified Reflection Schema + Fake Reflection Provider
4. 实现 Closure Coordinator + Mandatory Module Adapter
5. 做完全不涉及代码/Build/Test 的 Pure Analysis Pilot
```

> **当前不继续扩展 ET6003 业务 Pilot；先证明任何 Agent Turn 都会自动完成公共治理收口。**
