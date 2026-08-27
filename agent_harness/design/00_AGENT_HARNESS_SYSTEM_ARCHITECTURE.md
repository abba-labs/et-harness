# 智能体治理与进化系统架构设计

> 架构基线：v0.7  
> 第一运行基座：DeepSeek Harness / Cordis  
> 第一试点项目：ET-TOOL  
> 核心原则：**公共层固定 Agent 的工作生命周期；Agent 负责语义判断；Manager 负责确定性执行；项目只提供项目私有资源；Observation Plane 只能旁路观察。**

---

# 1. 系统本质

系统服务对象不是某一种代码项目，而是 **Agent 的持续工作过程**。

```text
Human Message
    ↓
Public Agent Governance Kernel
    ↓
TURN_START
    ↓
Public Bootstrap / Context / Project Resources
    ↓
Agent 理解 / 阅读 / 分析 / 实施
    ↓
TURN_CLOSING
    ↓
Turn Journal
    ↓
Unified Reflection
    ↓
Agent Semantic Judgment
    ↓
Closure Coordinator
    ↓
Context / Knowledge / Experience / Architecture / Rules / Evidence / Working Set
    ↓
Closure Receipt
    ↓
TURN_CLOSED
```

这个生命周期与以下项目动作没有绑定关系：

```text
改代码
编译
测试
硬件
发布
```

纯阅读、纯分析、纯设计的一轮同样必须完整 Closure。

长期职责：

```text
Agent                     = 理解、判断、推理和实施主体
Public Governance Kernel  = 固定 Agent / Task / Turn 生命周期并强制公共治理收口
Public Managers           = 路由、校验、查重、持久化等确定性机制
Context                   = 当前任务的可重建工作内存
Project Plugin            = 项目私有地图、规则、知识、Gate 与可选 Adapter
Governance Core           = 能力治理、准入、Provider、硬边界
Harness                   = Agent / Plugin Runtime
Observation Plane         = 可选旁路效率观测
```

---

# 2. 一级架构

```text
┌─────────────────────────────────────────────┐
│                Human / Agent Turn           │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│       PUBLIC AGENT GOVERNANCE KERNEL        │
│                                             │
│ Lifecycle Controller                        │
│ Turn Journal                                │
│ Unified Reflection Engine                   │
│ Scope Resolver Protocol                     │
│ Closure Coordinator                         │
│ Closure Receipt / Replay                    │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│                    Agent                    │
│      理解 / 推理 / 判断 / 阅读 / 实施        │
└─────────────────────┬───────────────────────┘
                      ↕
┌─────────────────────────────────────────────┐
│              Public Managers                │
│ Project / Architecture / Rule / Knowledge   │
│ Gate / Evidence-State / Context             │
│ Experience-Memory / Working Set             │
└─────────────────────┬───────────────────────┘
                      ↓ Standard Contract
┌─────────────────────────────────────────────┐
│                 Project Plugin              │
│ Identity / Architecture / Rules / Knowledge │
│ Gates / Optional Adapters                   │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│             Real Project / Repository       │
└─────────────────────────────────────────────┘

 Execution Plane ── optional metrics ──→ Observation Plane

Harness Runtime: DeepSeek Harness / Cordis
Governance Sidecar: Governance Core
Shared Resource: Public(Global) Knowledge
```

三条硬原则：

```text
1. Kernel 是 Agent 工作生命周期的强制横切层。
2. Project Identity 不是治理开关；项目未绑定时 Kernel 仍运行。
3. Observation Plane 可拆卸，绝不进入 Turn Closure / Task Completion 条件。
```

---

# 3. 三种顺序必须区分

## 3.1 插件技术依赖顺序

```text
Harness / Governance Core
↓
Project Manager
↓
Architecture / Rule / Evidence-State / Knowledge / Gate
↓
Context / Experience-Memory
↓
Public Agent Governance Kernel
```

Kernel 在运行时要求 Mandatory Manager 可用，但 Manager 本身保持独立接口。

## 3.2 Agent 工作生命周期顺序

```text
AGENT_START
↓
TASK_START / RESUME
↓
TURN_START
↓
Public Bootstrap
↓
Agent Work
↓
TURN_CLOSING
↓
Journal → Reflection → Closure Modules → Receipt
↓
TURN_CLOSED
↓
下一轮
↓
TASK_PAUSE / COMPLETE
↓
AGENT_END
```

## 3.3 Observation 顺序

```text
Execution Plane 正常工作
↓ optional metric
Observer 轻量采集
↓
任务结束后离线分析
```

Observation 不参与 Kernel 判断。

---

# 4. Harness 层

第一阶段复用 DeepSeek Harness / Cordis：

```text
Plugin Lifecycle
Context / Service
Dependency Injection
Typed Event
Effect / Cleanup
Bundle / Profile
Session / Tools
Subagent / Agent Teams
Workflow / Jobs
Approval / Credential / Sandbox
```

原则：**不重新制造第二套 Harness Runtime。**

不同 Harness 通过 Lifecycle Adapter 转成统一事件：

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

Kernel 不能长期硬编码 Cordis 原生事件名称。

---

# 5. Governance Core

Governance Core 负责：

```text
Plugin Admission
Capability Contract
Provider Registration
Project Registration
Plugin State
Permission / Trust
Hard Governance Boundary
Lifecycle infrastructure
```

它仍提供可选 Metrics Seam：

```text
frameworkMetricsActive()
emitFrameworkMetric()
observeFrameworkOperation()
```

Observer 未安装时不影响主链。

Governance Core 不负责 Agent Turn 的语义 Reflection；该职责属于 Public Governance Kernel。

---

# 6. Public Agent Governance Kernel

Kernel 是 v0.7 架构的核心调度层。

详细设计：

```text
21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md
```

核心组件：

```text
Lifecycle Controller
Turn Journal
Unified Reflection Engine
Scope Resolver Protocol
Closure Coordinator
Mandatory Module Registry
Closure Receipt
Replay / Idempotency
```

Kernel 强制：

```text
每轮开始必须 Bootstrap
每轮结束必须 Reflection
每个 Mandatory Module 必须返回 Receipt
Closure 失败必须保留并可重放
```

Kernel 不负责：

```text
替 Agent 做业务语义判断
强迫所有项目 Build/Test
直接把 Candidate 升级为正式长期事实
```

---

# 7. Public Managers

| 公共 Manager | 核心职责 |
|---|---|
| Project Manager | Project Binding、ProjectContext、资源入口 |
| Architecture Navigator | 架构地图、候选、正式 A-tree 读取 |
| Rule Manager | Rule Tree、规则候选、正式 R-tree 读取 |
| Knowledge Manager | Public(Global) + Project Knowledge、Source、Verification、Validation |
| Gate Manager | Gate Route、Execution Plan、已有 Obligation / Evidence Guard |
| Evidence / State Manager | Evidence append-only、State versioned |
| Context Manager / Builder | Task / Progress Ledger、Working Set、Frame、Handoff |
| Experience / Memory Manager | Experience、跨任务 Memory、Knowledge Candidate 链路 |
| Tool Plugins | Git、编译、测试、硬件、仪器等项目工作工具 |

Manager 不自行决定“什么时候应该做 Turn Closure”。

统一关系：

```text
Lifecycle Kernel
↓
Unified Reflection
↓
Closure Coordinator
↓
Public Manager
```

---

# 8. Project Plugin

```text
projects/<project>/
├── project.yaml
├── architecture/
├── rules/
├── knowledge/
├── gates/
└── adapters/          # optional
```

普通项目只需要：

```text
Manifest + Private Resources
```

项目不能实现或关闭：

```text
Turn Lifecycle
Turn Journal
Reflection Trigger
Mandatory Closure
Scope Resolver Protocol
Closure Receipt
Replay Policy
```

---

# 9. Project Binding

Task 先于 Project Binding 存在：

```text
UNBOUND
→ BOUND(projectId)
```

`UNBOUND` 时仍然运行：

```text
Context
Public Knowledge
Public Memory
Turn Journal
Reflection
Checkpoint
```

识别项目后再加载：

```text
Project Architecture
Project Rules
Project Knowledge
Project Gates
```

因此 Project Identity 解析失败不能让治理静默消失。

---

# 10. Context Management

Context 仍然不是长期知识库存储。

```text
Architecture / Rules / Knowledge / State / Evidence / Experience / Gate / Code
                                ↓
                         Context Management
                                ↓
                       Current Context Frame
                                ↓
                              Agent
```

Frame：

```text
Project Compass
Task Ledger
Progress Ledger
Working Set
Recent Tail
Available Handles
```

变化：

> Context 更新不再依赖某个业务动作；每次 `TURN_CLOSING` 都由 Context Closure Module 强制同步。

---

# 11. Unified Reflection / Scope Resolver

每轮只进行一次统一 Reflection，避免每个 Manager 各调用一次模型。

Reflection 同时检查：

```text
Context
Knowledge
Experience
Architecture
Rules
Evidence
Working Set
Open Obligations
```

需要长期沉淀的条目统一判断：

```text
NONE
PROJECT
PUBLIC
BOTH
```

公共层负责强制这个判断发生；Agent 负责给出语义判断和理由。

---

# 12. Knowledge / Experience

Knowledge 双层：

```text
Public(Global) Knowledge
Project Knowledge
```

Turn Closure：

```text
Reflection
↓
Agent 判断 NONE / PROJECT / PUBLIC / BOTH
↓
查重 / 冲突 / Provenance
↓
Knowledge CANDIDATE
↓
Verification / Validation Policy
↓
显式 Promote
↓
VALIDATED
```

Experience：

```text
Turn Reflection
↓
Experience CANDIDATE
↓
Memory
↓
可进一步提交 Project / Public Knowledge Candidate
```

禁止 Experience 直接写 VALIDATED Knowledge。

---

# 13. Architecture / Rules Evolution

Turn Closure 每轮都检查：

```text
Architecture 是否发现新事实/边界/不一致？
Rules 是否发现稳定约束/冲突/缺口？
```

项目范围：

```text
PROJECT → Project Change Candidate
```

跨项目公共范围：

```text
PUBLIC → Public Framework Change Candidate
```

Turn Closure 不直接修改正式 A-tree / R-tree。

---

# 14. Gate / Evidence / State

Gate 不定义 Agent Turn 生命周期。

Gate Manager 只管理已存在的工程/治理义务：

```text
Obligation Open
↓
Evidence
↓
Resolved / Pending
```

每次 Turn Closure 都调用 Obligation Reconcile：

```text
有 obligation → 更新状态
没有 obligation → NO_CHANGE
```

Build/Test/HW 不是 Context、Knowledge、Experience 更新的前提。

```text
Evidence = 不可变历史事实
State    = 当前状态投影
```

Evidence 不能把 Agent 推测直接写成 PASS。

---

# 15. Turn Journal / Closure Receipt

每轮先 Journal，再 Reflection：

```text
TURN_ACTIVE
↓
Journal append
↓
TURN_CLOSING
↓
Journal seal
↓
Reflection
↓
Closure Modules
↓
Closure Receipt
```

状态：

```text
OPEN
SEALED
CLOSURE_PENDING
CLOSED
```

任何 Mandatory Module 失败：

```text
不能标记 CLOSED
下一轮开始前自动 replay
```

Module 必须幂等，重复执行不能重复写 Candidate。

---

# 16. Observation Plane

`Framework Efficiency Observer` 是独立可选 Sidecar。

依赖方向：

```text
Observer → Governance Core / Cordis / Kernel Metrics
```

禁止：

```text
Kernel → Observer mandatory dependency
Agent → Observer dependency
Context → Observer dependency
Gate → Observer dependency
```

运行期只采低频 Framework Metrics。

Agent / Token / Tool 指标优先在任务结束后读取 Harness Session Log。

Observer 未安装、卸载或故障时主框架必须继续。

详细设计：`20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md`。

---

# 17. Agent 判断与框架强制边界

Agent 判断：

```text
用户真正想做什么
哪些候选相关
结论是否值得沉淀
Project / Public Scope
Knowledge / Experience 内容
Architecture / Rule Change 语义
业务实现与失败分析
```

Kernel 强制：

```text
Turn Lifecycle
Turn Journal
Reflection 必须发生
Mandatory Closure Module 必须运行
Closure Receipt
Replay / Idempotency
Project Binding 不得成为治理开关
```

Manager 强制：

```text
Resource Interface Validation
Stable Address / Index
Context Lint
Evidence / State Format
Knowledge Verification / Promotion Policy
Data consistency
```

Observation Plane：

```text
只能观察和报告
不能改变执行决策
```

---

# 18. Capability

已有 Manager 能力：

```text
governance.project
architecture.navigate
rule.navigate
knowledge.navigate
knowledge.library
gate.navigate
context.build
context.manage
evidence.record
evidence.read
state.read
state.update
experience.manage
memory.context
```

Kernel v0.1 新增概念能力：

```text
governance.lifecycle
governance.turn.journal
governance.turn.reflect
governance.turn.close
governance.scope.resolve
governance.closure.replay
```

可选旁路：

```text
observability.framework
```

---

# 19. ET-TOOL 定位

ET-TOOL 是第一套真实 Project Plugin，用于验证：

```text
Project Contract 是否够轻
公共 Manager 是否项目无关
Kernel 是否真正每轮自动触发
纯分析任务是否能完整 Closure
Project / Public Knowledge 是否正确分类
Rule / Architecture Candidate 是否自动检查
新 Agent 是否可恢复最新治理状态
代码类 Pilot 是否无需项目级 Lifecycle 代码
```

ET-TOOL 项目层保持：

```text
project.yaml
architecture/
rules/
knowledge/
gates/
adapters/
```

Kernel、Context、Evidence、Memory、State、Lifecycle、Observability 都不在 ET-TOOL 私有层重复实现。

---

# 20. 最终目标

```text
Human Message
↓
TURN_START
↓
Public Governance Bootstrap
↓
Agent + Progressive Project Navigation
↓
Agent Work
↓
TURN_CLOSING
↓
Journal + Unified Reflection
↓
Agent Semantic Judgment
↓
ALL Mandatory Public Closure Modules
↓
Closure Receipt
↓
TURN_CLOSED
↓
下一轮从最新 Context / Knowledge / Memory / Candidates 继续

        └── Optional Observation Plane
            → 量化效率与瓶颈
```

新项目接入成本只应是：

```text
Project Identity
+ Architecture
+ Rules
+ Knowledge
+ Gates
+ Optional Adapters
```

**项目不需要实现任何 Agent Lifecycle 逻辑。公共 Kernel 固定整个 Agent 工作闭环，并确保每一轮都自动检查、思考、沉淀和持久化。**
