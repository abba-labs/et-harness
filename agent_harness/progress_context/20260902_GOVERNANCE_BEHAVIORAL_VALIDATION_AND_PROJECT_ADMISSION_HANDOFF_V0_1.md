# ET Harness / ATP — Governance Behavioral Validation 与 Project Admission 当前交接 V0.1

**状态**：CURRENT HANDOFF / NEXT-CONVERSATION ENTRYPOINT  
**日期**：2026-09-02  
**Repository**：`abba-labs/et-harness`  
**稳定验证分支**：`codex/fast-track-pure-mcp-atp-v0.1`  
**稳定验证 SHA**：`8cb771f6f3221501dc2ad6aea1785a6e959ae65e`  
**当前 Architecture 调整分支**：`architecture/project-admission-bootstrap-v0.1`  
**本轮 Framework 实现基线 SHA**：`67676a2916b01316794da042a813d0c338d14182`  

> **新对话必须先读本文件。**  
> 本文件用于恢复：ET Harness 的长期目的、当前架构边界、必须遵守的规则、已经机械验证的稳定能力、2026-09-02 Governance Behavioral Validation 结果、Architecture Reviewer 的重新归因、本轮 Project Admission / Architecture Bootstrap 最小调整、当前未验证边界，以及下一阶段唯一正确的工作顺序。

---

# 0. 下一对话先看这里

当前项目已经过了“环境能不能搭起来、Runtime 主链能不能跑通”的阶段。

当前最准确的状态是：

```text
固定 D-drive Environment             基本稳定
Pure MCP Gateway / Runtime 主链       基本稳定
Supervisor / Ledger / Trusted Evidence  已有强证据
WRITE_SCOPE / Required Read / Validation 已有强证据
Active Turn Replay                    已证明

Governance 模块行为正确性              仍在收口
跨任务 Context / Knowledge / Experience  尚未闭环
Closure 失败恢复                       存在 P0
Governance 决策可观测性                仍有缺口
```

下一对话不要重新从环境、Node/npm、Plugin/Hook、Marketplace 或旧 Runtime 路线开始。

当前最高优先级不是“大重构 Framework”，而是：

1. 独立验证本轮 `Project Admission + Architecture Bootstrap + Agent TaskIntent` 最小调整；
2. 验证通过后，才考虑合入/激活到稳定 Runtime；
3. 随后分别处理 `Closure atomicity/retry`、`cross-task Context continuity`；
4. 再复测 Knowledge later-consumption、Experience Memory、治理可观测性。

---

# 1. ET Harness 的长期目的

ET Harness 的目标不是成为某一个 Agent、某一个大模型或某一个 Host 的内部功能。

长期目标是建立一个：

> **模型无关、Agent 无关、Host 尽量无关、项目可插拔的外部 Agent Governance System。**

核心思想：

```text
Model / Agent 可以更换
Host 可以更换
项目可以更换

但是：
Rules
Knowledge
Architecture
Context
Evidence
Supervision
Lifecycle
Closure
不能跟着某一个 Agent 一起迁移或消失
```

目标适配：

```text
Codex
Claude Code
DeepSeek Harness
Cursor
其他未来 Agent / Host
```

当前 ATP（Automated Testing Platform）是真实项目验证场，不是公共 Framework 的业务内核。

公共 Framework 不应该理解 `ET6801 / eTimer / XBAR` 的业务语义；这些内容属于 ATP Project Plugin 和 ATP 项目资源。

---

# 2. 冻结的核心职责边界

当前正确的责任模型：

```text
Human
  → 指定项目、提出真实业务目标

Agent / Semantic Reasoner
  → 理解人类自然语言
  → 基于项目 Architecture / Context 形成结构化 TaskIntent
  → 做业务语义分析

Project Plugin
  → 提供项目 Architecture / Rules / Knowledge / Gates
  → 提供项目 Scope、Validation、具体 Obligation
  → 不应该成为通用 LLM 自然语言理解器

Public Framework
  → 负责什么时候必须发生治理
  → 负责路由、约束、Evidence、Supervisor、Ledger、Lifecycle
  → 负责验证 Agent 输出是否合法
  → 不替 Agent 用大量正则“理解人类语言”

Host Adapter / Gateway
  → 翻译 Host/Tool 事件
  → 暴露有界接口
  → 不拥有项目业务真相

Execution Supervisor / Ledger
  → 机械监管执行事实、义务、Evidence 和 Completion
```

一个关键原则：

> **Agent 负责理解；Framework 负责治理。**

另一个关键原则：

> **Agent 不负责治理自己。Framework 不接受 Agent 自述作为 trusted PASS / Evidence / Project Context。**

---

# 3. 必须遵守的硬约束

以下约束继续冻结，下一对话不得随意改变。

## 3.1 稳定环境优先

当前 D-drive deterministic Runtime 已稳定，不得为了普通 Framework 修改重新折腾环境。

禁止无必要执行：

```text
npm install / npm upgrade
prepare-environment
重新安装 Node
重新安装 Cordis / MCP SDK
改 Gateway 启动模式
改固定 D-drive 路径
重新引入 Plugin / Hook / Marketplace
```

只有在 Architecture Owner 明确批准版本激活时，才按标准链路：

```text
clean committed source
→ freeze-runtime
→ verify-environment
→ refresh external Gateway
→ black-box regression
```

不能边改源码边顺手刷新生产式环境。

## 3.2 Pure MCP 边界

继续保持：

```text
MCP required=false
Gateway = 独立外部 Windows 进程
Pure MCP supervision = AUDIT
claimsMechanicalInterception = false
```

不能因为希望“更强约束”就假装 Host 支持 universal native tool interception。

## 3.3 不新增重复治理系统

禁止新建第二套：

```text
Runtime
Ledger
Event Store
Closure
Validation system
Context store
Knowledge store
```

禁止：

```text
watcher
polling daemon
Windows Service
自定义 filesystem MCP
自定义 shell MCP
```

如果现有 owner 能承担职责，必须复用现有 owner。

## 3.4 Agent / Codex 权限

当前角色：

```text
Project Owner      = 用户
Architecture Owner = ChatGPT
Test Executor      = Codex
```

Codex 可以：

- 按冻结 requirement 执行测试；
- 保存机械 Evidence；
- 定位 first failing boundary；
- 做 Architecture Owner 明确授权的最小修复。

Codex 不可以：

- 自行重新设计架构；
- 为了变绿修改 Policy / Rule / WRITE_SCOPE；
- 自己宣布 Architecture Owner PASS；
- 用 Agent 文本制造 trusted Evidence；
- 发现失败后顺手扩大修改范围。

## 3.5 验证纪律

继续遵守：

```text
Agent narrative < exact source / exact runtime state / mechanical evidence
```

不同层 PASS 不互相替代：

```text
unit PASS ≠ Runtime PASS
Runtime COMPLETE ≠ module behavioral PASS
historical FPGA PASS ≠ current SHA PASS
Agent says read ≠ trusted RESOURCE_READ
Agent says validation PASS ≠ trusted VALIDATION_RESULT
```

---

# 4. 当前稳定 Environment / Runtime 基线

稳定验证分支：

```text
codex/fast-track-pure-mcp-atp-v0.1
HEAD = 8cb771f6f3221501dc2ad6aea1785a6e959ae65e
```

该 SHA 对应 Governance Behavioral Validation V1 Evidence 提交。

固定环境核心事实：

```text
Node 22.23.2
D-drive deterministic environment
external MCP Gateway
MCP required=false
Pure MCP = AUDIT
```

现有 8 个 public MCP tools：

```text
harness_health
harness_begin
harness_status
harness_observe
harness_preflight
harness_complete
harness_read_required
harness_checkpoint
```

Governance Behavioral Validation V1 明确证明：

```text
verify-environment 22/22 PASS
Gateway 外部进程健康
Direct MCP 在 controlled restart 前后工作
没有 dependency reinstall
没有 product rebuild
没有通过修改环境让测试变绿
```

因此当前结论：

> **Environment failure 不是当前 Framework 的主要问题。**

---

# 5. Round 3 P0 已经证明什么

Round 3 P0 最终状态由 Architecture Owner 在后续 Review 中正式接受为 PASS。

Codex 原始 Final Evidence 报告保持 Test Executor 身份，未自行声明 Architecture Owner acceptance，这是正确行为。

已实质证明的主链能力包括：

```text
Project Route
Architecture Route
Rule Route
Knowledge Route
Gate Route

WRITE_SCOPE protected preflight BLOCK
Required Read trusted ingress
Trusted checkpoint validation
Agent 无法伪造 trusted validation
Premature completion BLOCK

Execution Supervisor
Obligation Ledger
Execution Event Store
Runtime trusted event ingress
Reflection
Context Update
Closure

Gateway restart / active Turn rehydrate
Codex Desktop real black-box closed loop
```

特别重要：

```text
Direct VALIDATION_RESULT 仍然不能直接满足 Ledger
Runtime-owned trusted validation span 可以满足 Ledger
```

说明 trusted boundary 没有为了方便被削弱。

Round 3 Evidence：

```text
agent_harness/test_campaigns/round3_p0_repair/evidence/
```

---

# 6. 本轮 Codex Governance Behavioral Validation V1

Requirement：

```text
agent_harness/test_campaigns/governance_behavioral_validation_v1/
GOVERNANCE_BEHAVIORAL_VALIDATION_REQUIREMENT.md
```

目的不是再证明“系统能跑完”，而是证明：

> 每个 mandatory governance module 是否在正确时间自动触发、得到正确输入、做出正确决定、真正影响 Agent 行为、更新正确下游状态，并能持久化 / replay。

Codex 最终提交：

```text
8cb771f6f3221501dc2ad6aea1785a6e959ae65e
```

结果：

```text
BEHAVIORAL_VALIDATION_FAIL
19 PASS
7 FAIL
11 OBSERVABILITY_GAP
```

Evidence：

```text
agent_harness/test_campaigns/governance_behavioral_validation_v1/evidence/
```

重要文件：

```text
FINAL_REPORT.md
01_module_inventory.json
02_expected_trigger_plan.json
03_observer_trace.jsonl
04_module_behavior_matrix.json
05_negative_controls.json
06_state_diffs.json
07_replay.md
08_defect_backlog.md
```

## 6.1 本轮强证明的模块

不要因为 Overall FAIL 忽略已经非常重要的正向结果。

已得到较强机械证据：

```text
Project Manager / Discovery
Project Router / Runtime Binding
Rule Manager
Context Builder（单 task）
Gate Manager
Execution Supervisor
Obligation Ledger
WRITE_SCOPE Preflight
Required Resource Enforcement
Trusted Validation Admission
Turn Journal
正常 Unified Reflection 路径
Mandatory Closure Adapters 正常路径
Execution Event Store
Working Set Closure
Obligation / Gate Reconcile
```

Active supervised state replay 也已明确 PASS：

```text
same runtimeId
same turnId
same projectRevision
same contextRevision
12 SATISFIED + 2 PENDING preserved
Event Store line count/hash unchanged by status query
protected WRITE_SCOPE remained BLOCKED after restart
```

这说明：

> **当前不是“Framework 主数据链路没跑通”，而是更高层治理行为仍存在具体缺陷。**

---

# 7. Codex 原始 FAIL 与 Architecture Reviewer 重新归因

Codex 报告的 7 个 FAIL 不能机械理解为 7 个独立 Framework Bug。

Architecture Review 后，应按根因重新分组。

## 7.1 P0-A — Task Bootstrap / ATP Classification / Contributor Contract

现象：

```text
自然语言 XBAR task 被识别为 ip=and
governance-rich intent 可能返回 CONTEXT_CONTRIBUTOR_UNAVAILABLE
简化表达反而成功
```

直接技术原因：ATP `context-contributor.ts` 当前用正则 / token / stop words 从 raw human text 解析 chip/ip；英文连接词 `and` 未被 stop-word 排除，因此可被误认为 IP。

更深层架构原因：

> **Project Plugin 被迫同时承担了“理解开放自然语言”和“项目确定性治理”两种职责。**

这不是继续堆更多正则能科学解决的问题。

本轮 Architecture Owner 决策：

```text
Human 明确指定 Project
→ Framework 做 Project Admission
→ 如果 Agent 没有可验证 Project Context，则先给 Architecture Bootstrap
→ Agent 基于 Architecture 理解人类任务
→ Agent 输出 bounded TaskIntent
→ Framework / Project Plugin 验证并继续确定性治理
```

即：

> Agent 负责理解；Framework / Project Plugin 负责验证和治理。

## 7.2 P0-B — Cross-task Context Continuity

现象：

```text
Context Closure = APPLIED
open issue 已持久化
但是 later distinct task 没有自动收到该 issue
```

根因判断：

```text
Context 当前主要是 task-scoped persistence
已有 begin/resume/rebuild/handoff 能力
但新 task bootstrap 没有 project-level relevant-context retrieval/merge/injection 链
```

所以问题不是“Context 写不进去”，而是：

> **写进去之后没有成为后续相关任务的自动输入。**

下一步只能复用现有 Context Manager / Evidence State owner 建最小 query/merge chain，禁止创建第二 Context Store。

## 7.3 P0-C — Closure Atomicity / Retry

现象：

```text
malformed Reflection（例如缺 contractVersion）
→ request 返回 ERROR
→ 但 Turn 已经 seal / CLOSURE_PENDING
→ corrected Reflection retry 被拒绝
```

根因：

```text
当前 TurnReflectionController
先 sealTurn()
再执行 provider / schema validation
失败后 markClosurePending()
```

不可逆生命周期变化发生得太早。

因此以下三个 FAIL 实际属于同一根因：

```text
M25 Closure Coordinator
M26 Runtime/Gateway Replay（完整 closure-retry 场景）
M37 Governance Runtime Lifecycle
```

不要分别做三套修复。

正确修复 owner boundary：

```text
Reflection input/provider/schema validation
→ 成功后
→ idempotent irreversible seal / closure transition
```

## 7.4 Knowledge later-consumption 暂不能判 Knowledge Manager Bug

Scenario C 已证明：

```text
K001.014 CANDIDATE persisted
index updated
knowledge-closure APPLIED
promotionCount=0
```

下一任务在真正进入 Knowledge Consult 前，先因 bootstrap 返回 `CONTEXT_CONTRIBUTOR_UNAVAILABLE`。

因此当前正确分类：

```text
Knowledge persistence = PASS
Knowledge later consumption = BLOCKED_BY_UPSTREAM / NOT YET PROVEN
```

先验证新的 Project Admission / Bootstrap，再重新测 Knowledge consumption；不要先修改 Knowledge Manager。

## 7.5 Observation-stage Knowledge contradiction 需要架构决策

Scenario G 最终 source-backed Knowledge Verification 正确记录：

```text
relation = CONTRADICT
promotionCount = 0
```

说明 Knowledge trust boundary 本身工作。

争议在于：普通 `harness_observe` 阶段发现语义冲突时，是否必须立即自动升级为 CHECK。

当前 evaluator 主要对：

```text
source://
evidence://
TOOL_ERROR
```

等 deterministic trusted signals 做 capture/validation 提升。

Architecture Owner 当前原则：

> 不允许因为 Agent 自己说“我发现冲突”就直接形成 trusted Knowledge 判定。

下一阶段需要冻结 Knowledge Trigger Contract，而不是为了让测试 PASS 直接放宽信任边界。

## 7.6 P1 — Experience / Evidence 正向桥接

当前 Experience Manager 已有：

```text
recordCandidate
searchMemory
submitToKnowledge
```

并且要求真实 Evidence。

但实际 MCP 路径尚未证明完整链：

```text
Trusted Execution Evidence
→ canonical Evidence State / evidence:// ref
→ Experience Candidate
→ later task search/consumption
```

这是后续 P1，不应通过接受 caller-forged evidence 来解决。

## 7.7 P1 — Governance Observability

Behavioral Validation 暴露了大量：

```text
selected result 可见
但候选 / rejection / provider / reason 不可直接观察
```

典型包括：

```text
Catalog/provider snapshot
Architecture candidate/rejection trace
Rule candidate/rejection trace
Knowledge trust tier / consult trace
Gate provider/evidence packet
Auto Governance decision trace
```

目标是由现有 owner 输出 bounded read-only Decision Receipt / Trace。

禁止新增 watcher / daemon / second Event Store。

## 7.8 已发现的小接口问题

Knowledge decision 当前返回字段使用：

```text
consultMode
```

Gateway summary 部分路径读取：

```text
consultationMode
```

这可能造成 Knowledge consultation observability 丢失。

这是小接口问题，后续应独立修正，不要混进 P0 大修。

---

# 8. 本轮 Architecture 决策：不新增 Project Understanding Pack

讨论过程中曾考虑：每个项目增加一套 `Project Understanding Pack`，用 YAML 让新 Agent 快速认识项目。

最终否决。

原因：

```text
已有 Architecture 本来就是项目地图
再增加 Understanding Pack 会：
- 复制 Architecture 内容
- 增加维护成本
- 增加数据漂移
- 增加 Framework 体积
- 形成第二套项目认知来源
```

最终冻结方向：

> **Architecture 本身就是陌生 Agent 进入项目时的第一张地图。**

正确启动链路：

```text
Human 指定 Project
      ↓
Project Admission
      ↓
Framework 判断是否有当前有效 Project Context
      ↓
无 / stale
      ↓
Architecture Bootstrap（只提供最小 Root + 一级导航）
      ↓
Agent 理解 Project + Human Task
      ↓
TaskIntent
      ↓
原有 precise Architecture / Rule / Knowledge / Gate routing
      ↓
Scope / Required Read / Validation / Supervisor / Ledger
```

不能只问 Agent：

```text
“你了解这个项目吗？”
```

然后相信 Agent 回答 YES。

Framework 必须通过可验证 fingerprint / receipt 判断 Project Context 是否有效。

---

# 9. 本轮 Architecture Owner 已完成的 Framework 最小调整

这部分**不是 Codex 做的架构设计**；由 Architecture Owner 基于 Behavioral Validation 根因完成。

为了不影响稳定环境，修改没有放到稳定测试分支，而是在隔离分支：

```text
architecture/project-admission-bootstrap-v0.1
```

Framework 实现基线 SHA：

```text
67676a2916b01316794da042a813d0c338d14182
```

两次提交：

```text
b67439156eb84f078a46b8f42e8bdbd8edffffe8
feat(gateway): add architecture-backed project admission

67676a2916b01316794da042a813d0c338d14182
fix(gateway): preserve raw governance data boundary
```

## 9.1 刻意没有修改的稳定模块

本轮没有改：

```text
Project Manager
Architecture Navigator
ATP Project Plugin
Execution Supervisor
Obligation Ledger
WRITE_SCOPE
Required Read
Trusted Validation
Agent Governance Kernel
Closure implementation
Node/npm versions
D-drive environment paths
Gateway launcher/process-control model
```

这是有意的风险控制。

## 9.2 新增 Project Admission 薄层

新增：

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs
```

`harness_begin` 新流程要求人类明确 project：

```text
project = ATP / exact project alias / projectId
```

Project declaration 必须与 workspace 实际绑定项目精确匹配；不允许 Framework 猜一个近似项目。

错误项目：

```text
PROJECT_DECLARATION_MISMATCH
```

## 9.3 Project Context 不足时不打开 Runtime Turn

第一次进入项目：

```text
harness_begin(project, intent)
→ PROJECT_CONTEXT_REQUIRED
→ 返回 bounded Architecture Bootstrap + fingerprint
```

此时：

```text
baseGovernance.begin() NOT CALLED
Runtime Turn NOT OPENED
Ledger NOT CREATED
Event Store NOT CREATED
Closure state NOT TOUCHED
```

Agent 阅读 Architecture Bootstrap 后再次调用；如果 fingerprint 有效但还没有 TaskIntent：

```text
TASK_INTENT_REQUIRED
```

依然不打开 Runtime Turn。

只有：

```text
project valid
+ current projectContextFingerprint valid
+ bounded TaskIntent valid
```

三者都满足后，才进入原有 `baseGovernance.begin()`。

## 9.4 Architecture Bootstrap 不新增第二套 Architecture

新增：

```text
agent_harness/mcp_gateway_fast_track/src/project-bootstrap.ts
```

它只复用现有：

```text
Project Manager
Architecture Navigator
Architecture 00_INDEX
Architecture Root Node
Architecture first-level children
```

ATP 当前 Architecture 已有：

```text
A010 Project Governance Projection
```

可以作为新 Agent 的项目入口。

Bootstrap 硬预算：

```text
max Architecture root files = 32
max first-level children = 96
max serialized payload = 32 KiB
```

超预算 fail closed，避免 Architecture Bootstrap 演化成第二知识库。

Bootstrap fingerprint：

```text
sha256(current bounded architecture bootstrap payload)
```

如果 Architecture 变化，旧 fingerprint 不再直接放行。

## 9.5 Agent 输出 bounded TaskIntent

当前 schema：

```text
et-harness.task-intent.v0.1
```

字段：

```text
taskType
objective
entities[] = { kind, id }
constraints[] optional
```

示例：

```text
taskType = IP_ANALYSIS
objective = Analyze ET6801 ETIMER IP
entities:
  chip = ET6801
  ip = ETIMER
```

原则：

> Agent 负责把自然语言理解成结构化任务语义，但不能在 TaskIntent 里自行发明 Rule / Gate / Evidence / PASS。

## 9.6 对现有 ATP classifier 的兼容策略

本轮没有直接重写 ATP classifier。

Project Admission 会生成 canonical task text，并把 Agent 理解出的实体放在原始人类文本前面：

```text
Task type: IP_ANALYSIS
Entities: chip=ET6801; ip=ETIMER
Objective: ...
Original user request: ...
```

这样旧 ATP classifier 会先看到：

```text
ip=ETIMER
```

而不是后面自然语言中的：

```text
IP and SDK...
```

这是**低风险兼容层**，不是宣称旧 regex classifier 从此设计正确。

长期应在新 TaskIntent 路径稳定后，逐步减少 Project Plugin 对 raw natural-language parsing 的依赖。

## 9.7 Frozen Runtime source signature 已覆盖新增 Bootstrap

新增 `project-bootstrap.ts` 已加入：

```text
runtime-bundle-inputs.mjs
```

的 source signature 输入。

目的：防止未来出现：

```text
Project Bootstrap 源码变化
但 frozen Runtime sourceSignature 未变化
```

的完整性漏洞。

---

# 10. 本轮 Framework 调整已经做过的 Review / 仿真

Architecture Owner 对隔离分支做了 staged-flow review / simulation。

当前记录结果：

```text
1. 无 Project Context fingerprint
   → PROJECT_CONTEXT_REQUIRED
   → openTurn count = 0

2. fingerprint valid，TaskIntent absent
   → TASK_INTENT_REQUIRED
   → openTurn count = 0

3. fingerprint valid + TaskIntent valid
   → 原 baseGovernance.begin
   → openTurn count = 1

4. Project selector mismatch
   → fail closed
   → openTurn count = 0
```

专门针对 `ip=and` 做了兼容仿真：

```text
Human:
ATP项目：分析 ET6801 ETIMER 这个 IP and SDK contract

Canonical:
Entities: chip=ET6801; ip=ETIMER
...
Original user request: ... IP and SDK ...
```

现有 ATP regex 的第一个合法 `ip=` 候选为：

```text
ETIMER
```

不是：

```text
and
```

对应 focused test：

```text
agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
```

该测试覆盖：

```text
exact project alias / wrong alias
TaskIntent bounded validation
ETIMER canonical ordering
Architecture required before Runtime open
TaskIntent required before Runtime open
stale Architecture fingerprint refresh
```

重要边界：

> **这些是源码级 focused test / staged simulation，不等于新版本已经完成真实 frozen D-drive Runtime black-box acceptance。**

本轮为了保护已稳定环境，明确没有：

```text
freeze new runtime into active D-drive release
refresh current external Gateway
restart current stable Gateway for this feature
replace active release pointer
```

所以当前状态：

```text
SOURCE_IMPLEMENTED
FOCUSED_REVIEWED
NOT_YET_ACTIVATED_TO_STABLE_ENVIRONMENT
NOT_YET_FULL_BEHAVIORAL_ACCEPTED
```

---

# 11. 当前仍然存在的问题

按优先级处理，不要并行大修。

## P0-VALIDATION — Project Admission 新流程尚未做独立真实回归

当前隔离分支必须先由独立 Test Executor 验证。

重点证明：

```text
Human project declaration 必须精确生效
missing context 时 Runtime 不能提前 open
stale fingerprint 必须重新 bootstrap
TaskIntent 缺失不能进入原治理链
TaskIntent valid 后原治理链仍然可用
8 MCP tools 数量/其他接口不被意外破坏
raw Runtime/Ledger/Closure 数据仍不暴露
现有 Supervisor/Ledger/WRITE_SCOPE/Trusted Validation 不回归
```

在这一轮 PASS 前：

> **不要把 `architecture/project-admission-bootstrap-v0.1` 合入或激活到稳定环境。**

## P0 — Closure Atomicity / Retry

仍未修。

目标：

```text
invalid Reflection
→ validation error
→ Turn remains safely retryable
→ corrected Reflection can retry
```

不能再出现 invalid input 先 seal Turn。

## P0 — Cross-task Context Continuity

仍未修。

目标：

```text
Task A confirmed decision/open issue
→ canonical Context persistence
→ Task B relevant bootstrap
→ automatic relevant Context retrieval
→ bounded merge
→ Agent actually receives and uses it
```

禁止第二 Context Store。

## RETEST — Knowledge later-consumption

先不修 Knowledge Manager。

新的 Project Admission 验证通过后，重新执行：

```text
persist PROJECT candidate
→ new related task
→ bootstrap succeeds
→ Knowledge consultation reaches candidate
```

如果此时仍失败，才定位 Knowledge Manager / Context integration。

## ARCH DECISION — Knowledge observation trigger

需要 Architecture Owner 冻结可信触发规则：

```text
什么 source/evidence signal 必须触发 CHECK？
普通 Agent semantic statement 是否仅成为 candidate signal？
何时必须到 Checkpoint / Reflection 才能形成 trusted classification？
```

禁止为了测试 PASS 让 Agent 自述直接成为 trusted Knowledge Evidence。

## P1 — Evidence State → Experience → Later Task

需要证明完整正向链：

```text
trusted evidence
→ canonical Evidence State
→ Experience candidate
→ persistence/replay
→ later task search/consumption
```

## P1 — Governance Decision Observability

需要从现有 owner 提供 bounded receipts，解决：

```text
为什么选这个 Architecture？
为什么加载这个 Rule？
为什么拒绝另一个候选？
哪个 Knowledge trust tier 被使用？
哪个 Gate provider 产生了什么 packet？
Auto Governance 为什么形成这个 obligation？
```

这属于 Governance system 的能力，不只是 debug convenience。

## SMALL — Knowledge consultMode naming mismatch

独立最小修复，不和 P0 混在一起。

---

# 12. ATP 项目内容层仍有的已知 gap

Framework defect 与 ATP project-content gap 必须继续分开。

Governance Behavioral Validation 中：

```text
XBAR public/chip contract documents missing
```

Checkpoint 正确 FAIL CLOSED。

这是 ATP 项目内容缺口，不是 Framework failure。

已知 XBAR ATP 正式自动化层缺少或未完成：

```text
test_case_doc/xbar/xbar.md
test_case_doc/xbar/ET6801_xbar.md
PC Driver
Firmware Service
Common Wrap
```

eTimer 在 Round 3 已有公共/ET6801 文档和真实治理测试事实，可继续作为 Framework regression 的代表任务。

真实 ATP IP 工作仍然应该继续用于 Framework 行为验证，但不能把项目内容缺失误判成 Framework bug。

---

# 13. 下一阶段唯一正确的推进顺序

## Stage A — 独立验证 Project Admission 分支

被测对象：

```text
branch: architecture/project-admission-bootstrap-v0.1
framework implementation baseline: 67676a2916b01316794da042a813d0c338d14182
```

Test Executor：Codex。

测试阶段禁止源码修复。

至少验证：

```text
A1 exact Project admission
A2 project alias ATP accepted
A3 typo / wrong project fails closed
A4 no fingerprint → PROJECT_CONTEXT_REQUIRED
A5 no Runtime Turn/Event Store/Ledger before context accepted
A6 stale fingerprint → new Architecture bootstrap
A7 valid fingerprint + no TaskIntent → TASK_INTENT_REQUIRED
A8 malformed TaskIntent fails closed
A9 ET6801/ETIMER structured TaskIntent reaches ATP correctly
A10 human text contains “IP and ...” 仍不得产生 ip=and
A11 existing required reads / validations / scope still work after admission
A12 existing 8 public MCP tools remain exactly the intended public surface
A13 raw Runtime/Ledger/Closure not exposed
A14 existing Round 3 P0 safety regressions remain green
```

优先使用隔离 / disposable validation surface；不要为了测试这条功能先修改当前稳定 D-drive environment。

发现问题：

```text
record first failing boundary
preserve evidence
do not repair automatically
return Architecture Owner review
```

## Stage B — Architecture Owner Review

只有 Stage A Evidence 足够时，Architecture Owner 才决定：

```text
ACCEPT
MINIMAL_REPAIR_REQUIRED
REJECT_DESIGN
```

Codex 不得自行 merge/activate。

## Stage C — 批准后再做 deterministic activation

如果批准激活：

```text
clean commit
→ freeze-runtime
→ verify-environment
→ controlled external Gateway refresh
→ direct MCP smoke
→ real Host black-box
→ Rollback point preserved
```

这是有意识的版本升级，不是环境排错。

## Stage D — 重新跑 Behavioral Scenarios

Project Admission 激活后优先重跑：

```text
A natural ET6801/IP task
C reusable Project Knowledge + later consumer
E Context later consumption
G contradictory Knowledge
F active replay regression
```

并完整保留 Round 3 P0 regression。

## Stage E — 分别处理剩余 P0

顺序建议：

```text
1. Closure atomicity/retry
2. Cross-task Context continuity
3. Knowledge later-consumption（如果仍失败）
4. Knowledge trigger contract
5. Evidence/Experience bridge
6. Governance observability
```

一个根问题一个 repair campaign，禁止一次改完全部模块。

---

# 14. 下一对话明确禁止做的事情

不要：

```text
重新安装环境
重新设计 Pure MCP
回到 Plugin / Hook / Marketplace
新增 Project Understanding Pack
新增第二 Architecture 系统
把所有 Project 内容塞进一个巨大 bootstrap 文档
直接用正则补几十个 stop words 当最终 Task Understanding 方案
直接修改 Knowledge Manager 来“修”当前 later-consumption
同时修 M25/M26/M37 三套代码
用 watcher/daemon 解决 observability
为了 PASS 放宽 Agent evidence/trust boundary
在验证前合入/激活 Project Admission branch
把 stable branch 8cb... 当成已经包含 Project Admission
```

尤其注意：

> `codex/fast-track-pure-mcp-atp-v0.1 @ 8cb...` 是当前已验证稳定行为基线；  
> `architecture/project-admission-bootstrap-v0.1 @ 67676a...` 是当前待独立验证的新架构实现基线。

两者不能混为一个状态。

---

# 15. 当前关键文件导航

## Handoff / Charter

```text
agent_harness/progress_context/20260902_GOVERNANCE_BEHAVIORAL_VALIDATION_AND_PROJECT_ADMISSION_HANDOFF_V0_1.md
agent_harness/progress_context/20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md
agent_harness/progress_context/20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md
```

## Behavioral Validation

```text
agent_harness/test_campaigns/governance_behavioral_validation_v1/
  GOVERNANCE_BEHAVIORAL_VALIDATION_REQUIREMENT.md
  evidence/FINAL_REPORT.md
  evidence/04_module_behavior_matrix.json
  evidence/05_negative_controls.json
  evidence/07_replay.md
  evidence/08_defect_backlog.md
```

## Round 3 accepted evidence

```text
agent_harness/test_campaigns/round3_p0_repair/evidence/
```

## Project Admission implementation

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs
agent_harness/mcp_gateway_fast_track/src/project-bootstrap.ts
agent_harness/mcp_gateway_fast_track/src/gateway.mjs
agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts
agent_harness/mcp_gateway_fast_track/src/runtime-release.mjs
agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
agent_harness/mcp_gateway_fast_track/scripts/runtime-bundle-inputs.mjs
```

## ATP Architecture entry

```text
agent_harness/projects/automated_testing_platform/architecture/00_INDEX.md
agent_harness/projects/automated_testing_platform/architecture/010_project_governance_map.md
```

---

# 16. 新对话的第一轮工作指令

新对话读取本文件后，不要重新讨论项目历史。

首先确认：

```text
repo = abba-labs/et-harness
stable baseline = codex/fast-track-pure-mcp-atp-v0.1 @ 8cb771f...
architecture candidate = architecture/project-admission-bootstrap-v0.1
framework candidate baseline = 67676a...
```

然后第一件事：

> **作为 Architecture Owner，审查 Codex 对 Project Admission / Architecture Bootstrap 分支的独立验证证据；如果尚未执行验证，则先冻结 Test Executor requirement，不直接继续改 Framework。**

只有 Project Admission 行为被独立证明后，才决定是否进入受控 activation。

随后按本文件第 13 节推进。

---

# 17. 最终一句话状态

> **ET Harness 的固定环境、Pure MCP 主数据链、Supervisor/Ledger/Trusted Evidence 已经进入相对稳定阶段；Governance Behavioral Validation 已成功把问题收敛到任务入口语义、跨任务连续性、Closure 失败恢复和可观测性。当前 Architecture Owner 已在隔离分支完成一个不新增 Understanding Pack、不重写 Architecture、不触碰稳定治理链的 Project Admission + Architecture Bootstrap 最小实现；该实现已做 focused review/simulation，但尚未进入稳定 D-drive Runtime，下一阶段必须先独立验证，再决定是否激活。**
