# ET Harness / ATP — Current State, Machine Freeze, SRPWM Behavioral Validation Handoff V0.2

**状态**：CURRENT HANDOFF / NEXT-CONVERSATION ENTRYPOINT  
**日期**：2026-09-02  
**Repository**：`abba-labs/et-harness`  
**Canonical development branch**：`development/et-harness-mainline-v0.1`  
**Analysis baseline before this Handoff**：`83e3c1291352c4427e890e695a253ea99a7d7325`  
**Behavioral validation branch**：`validation/et6801-srpwm-behavioral-v0.1`  
**Behavioral validation tested source SHA**：`b3f32b3002d576ff75f3c4edee7fdd643bf415e0`  
**Behavioral validation Evidence SHA**：`fea9e454d100eaf175bfa8f9ed0589a104488d15`  

> **新对话必须先读本文件。**
>
> 本文件用于一次性恢复：ET Harness 的长期目的、角色分工、不可违反的架构规则、当前机器环境与 Git 分支边界、本轮 ChatGPT + Codex 完成的环境固化 / Machine Launcher / 分支收口 / ET6801 SRPWM 真实行为验证、已经证明的能力、真实发现的问题、问题来源归因、为什么旧测试没有抓到、已经建立的 `validation_analysis` 分析机制、当前尚未隔离的 Unknowns，以及下一阶段唯一正确的工作顺序。

---

# 0. 新对话先看这里

当前最准确的一句话状态：

> **ET Harness 的单次安全治理链已经基本成立，机器运行环境也已与 Git checkout 解耦；当前真正没有收口的是连续治理生命周期：Validation 失败恢复、Context task terminalization 与跨任务继承、Begin 失败原子性、Closed Turn replay，以及长期可审计数据质量。**

这不是“环境又坏了”，也不是“最近 Environment / Machine Launcher 优化把 Framework 修坏了”。

当前 Architecture Analysis 的因果结论是：

```text
最近 Environment / Machine Launcher 优化造成的已确认 NEW_REGRESSION = 0

Validation recovery                = PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Context Closure remains ACTIVE     = PRE_EXISTING_ROOT_DEFECT
Task B no priorContext             = INCOMPLETE_PREVIOUS_FIX + exact sub-cause still needs discrimination
Complete replay fails              = PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Failed begin creates orphan Turn   = PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Observation body not durable       = PRE_EXISTING_ROOT_DEFECT / NEWLY_TESTED_CAPABILITY_GAP
Context/Route too broad            = NEWLY_TESTED_CAPABILITY_GAP / OBSERVABILITY_GAP
Knowledge positive path            = PROJECT_CONTENT_GAP / NOT_EXECUTED
```

因此下一对话**不要重新折腾 Node/npm/环境，也不要直接凭感觉修改 Context selector 或 Ledger**。

正确入口是：

1. 读本 Handoff；
2. 读 `../validation_analysis/README.md`；
3. 读本轮 `../validation_analysis/rounds/2026-09-02_et6801_srpwm_behavioral_v1/FINAL_ANALYSIS.md`；
4. 读 Codex 原始 Evidence；
5. 先冻结下一轮 P0 lifecycle repair requirement / discriminating tests；
6. 根因未唯一隔离的地方先测试，不改代码；
7. 只对已经证明的 Owner 做最小修复；
8. 修复后同时跑 Fix Acceptance + 既有 PASS Non-regression；
9. 再用真实 ATP 任务验证。

---

# 1. ET Harness 的长期目的

ET Harness 的目标不是 Codex 的功能，也不是 Claude Code / DeepSeek / Cursor 的内部功能。

长期目标：

> **建立模型无关、Agent 无关、Host 尽量无关、项目可插拔的外部 Agent Governance System。**

核心设计思想：

```text
Agent / Model 可以更换
Host 可以更换
Project 可以更换

但是项目与治理资产：
Architecture
Rules
Knowledge
Context
Evidence
Supervision
Lifecycle
Closure
不能属于某一个 Agent，也不能因为换 Harness 而迁移重写。
```

目标 Host / Agent：

```text
Codex
Claude Code
DeepSeek Harness
Cursor
未来其他 Agent / Host
```

ATP（Automated Testing Platform）是当前真实项目验证场，不是公共 Framework 的业务内核。

公共 Framework 不应该硬编码：

```text
ET6801
SRPWM
XBAR
eTimer
IP-specific test semantics
```

这些属于 ATP Project Plugin / Project Architecture / Rules / Knowledge / Source / Capability / Test Contract。

---

# 2. 冻结的职责模型

当前角色：

```text
Project Owner / final product intent = 用户
Architecture Owner / Root-cause & Repair Design = ChatGPT
Test Executor = Codex
```

当前总体职责：

```text
Human
  -> 指定项目和业务目标

Agent / Semantic Reasoner
  -> 理解自然语言
  -> 结合 Architecture / Context 形成 bounded TaskIntent
  -> 完成开放语义分析

Project Plugin
  -> 提供项目 Architecture / Rules / Knowledge / Gate / Scope / Validation / Obligation
  -> 负责项目确定性约束
  -> 不承担开放自然语言理解器职责

Public Framework
  -> 决定治理步骤什么时候必须发生
  -> 管理 Route / Context / Evidence / Supervisor / Ledger / Lifecycle / Closure
  -> 验证结构化结果和 trusted event
  -> 不接受 Agent 自述作为 trusted PASS

Gateway / Host Adapter
  -> Host 事件翻译与 bounded public surface
  -> 不拥有项目真相

Execution Supervisor / Ledger
  -> 机械监管执行事实、义务、Evidence 和 Completion
```

冻结原则：

> **Agent 负责理解；Framework 负责治理。**

> **Agent 不负责治理自己。**

> **Agent narrative < exact source / exact runtime state / mechanical Evidence。**

---

# 3. 必须遵守的硬规则

## 3.1 可靠性优先级

```text
可靠 > 稳定 > 轻量化 > 易扩展
```

不能为了“功能更多”牺牲状态正确性和可审计性。

## 3.2 不新增第二治理系统

禁止为修一个问题新增第二套：

```text
Runtime
Ledger
Event Store
Closure
Validation system
Context Store
Knowledge Store
```

优先修真实 Owner / 真实状态转换。

## 3.3 禁止额外运行时基础设施

禁止：

```text
watcher
polling daemon
Windows Service
custom filesystem MCP
custom shell MCP
Plugin/Hook/Marketplace 重新成为主路线
```

## 3.4 Pure MCP 边界

保持：

```text
MCP required=false
Gateway = external independent Windows process
Pure MCP supervision = AUDIT
claimsMechanicalInterception = false
```

不要伪装 Host universal interception。

## 3.5 Evidence discipline

严格区分：

```text
unit PASS != Runtime PASS
Runtime COMPLETE != module behavioral PASS
historical FPGA PASS != current SHA PASS
Agent says read != trusted RESOURCE_READ
Agent says validation PASS != trusted VALIDATION_RESULT
```

同样：

```text
module invoked != PASS
module returned success != PASS
chain completed != PASS
```

一个治理模块只有同时满足：

```text
正确触发
-> 正确输入
-> 正确行为
-> 正确内容
-> 正确 provenance / trust
-> 正确 canonical state mutation
-> 正确 downstream consumption
-> 正确 later-task consumption
-> 正确 negative boundary
```

才算真正 PASS。

## 3.6 Codex 角色纪律

默认：Codex = Test Executor。

Codex 可以：

- 按冻结 Requirement 测试；
- 保存机械 Evidence；
- 定位 first failing boundary；
- 在 Architecture Owner 明确授权时做 scoped repair。

Codex 不可以：

- 为了变绿改 Policy/Rule/Scope；
- 随手重构多个 Owner；
- 用 narrative 造 Evidence；
- 把 test fixture PASS 当 Runtime PASS；
- 自己宣布 Architecture Owner acceptance。

---

# 4. 机器环境已经完成真正固化

这是本轮最重要的基础设施成果之一。

机器环境唯一 owner：

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

最终结构原则：

```text
Git repository
  -> 只保存 source / installer / build / verify / tests

D-drive machine environment
  -> fixed Node
  -> shared Toolchain
  -> machine-local Launcher
  -> immutable Runtime Releases
  -> active/previous pointers
  -> Runtime State / Event Store / snapshots / logs
```

本轮完成两个连续 Campaign：

## 4.1 Shared Toolchain / Runtime Environment

产品测试 SHA：

```text
0e44ea4cb7d9d589ee3f73ff18c95f9594fdc0d6
```

Evidence SHA：

```text
50c6af54d77ec2e1681ff66243353946421f56f2
```

真实完成：

```text
clean checkout without local node_modules
shared Toolchain
candidate v2 build
isolated candidate verify
real activation
real rollback to v1
v1 health validation
re-activate v2
8 MCP tools
Project Admission
state digest comparison
```

最终 active Runtime release：

```text
f976d8e32df64fa78075
```

## 4.2 Machine-local Launcher Freeze

Product SHA：

```text
6aaefb28a4c6776fb241617d3735b5c313ca4c7e
```

Evidence SHA：

```text
fee133c984c098407859a053678db62334c22f20
```

固定 Launcher SHA256：

```text
f4973e07baae0063a59735d9d6a182e183c6295571b3ef7a72a89af377de8c04
```

Codex 真实证明：

```text
checkout 切到旧 SHA 7ce711a...
旧分支甚至没有 Machine Launcher
只使用 D-drive machine entry
-> stop old Gateway
-> start v2 release
-> status / health PASS
-> 8 MCP tools PASS
-> Project Admission PASS
```

无 `ET_HARNESS_ENV_ROOT` / `ET_HARNESS_NODE` 环境变量的重启也 PASS。

结论：

```text
MACHINE_LOCAL_ENVIRONMENT_FREEZE_PASS
```

因此：

> **切 Git branch / 建 worktree / 修改源码本身，不再拥有 Runtime lifecycle side effect。**

只有显式动作允许改变机器环境：

```text
install-machine-launcher
Runtime build -> verify -> activate
```

注意：本 Handoff 不重新机械查询当前 PID；最后一轮 Machine Launcher Campaign 的最后机械记录为 PID `20124`、状态 HEALTHY。新对话如果需要“当前 PID”事实，应通过 machine launcher/status 重新查询，而不是把历史 PID 当当前事实。

---

# 5. 分支已经收口

旧阶段分支很多，已经建立新的长期主线和历史归档锚点。

当前长期分支模型：

```text
main
  -> 保留，不作为当前日常开发主线

development/et-harness-mainline-v0.1
  -> 唯一长期产品开发基线

validation/et6801-srpwm-behavioral-v0.1
  -> 当前 SRPWM behavioral Evidence branch
  -> 当前不能删除，因为 Evidence SHA fea9e454... 尚由本分支直接引用

archive/pre-mainline-history-2026-09-02
  -> 历史旧分支 ancestry archive，只读
```

历史 archive commit：

```text
dc6382cba054e7594902d880f71fee4bb623f8d8
```

不要再创建：

```text
work
work2
stage1
stage1a
final
finalize
hotfix-final
```

长期工作方式：

```text
development/et-harness-mainline-v0.1
  -> feature/* / fix/* / validation/* 临时工作
  -> 验证通过
  -> 回归 mainline
  -> 临时 branch 清理
```

---

# 6. 本轮对话与 Codex 实际完成了什么

本轮不是单一修复，而是完成了四个阶段。

## Phase A — 环境问题暴露与彻底解决

最初真实 SRPWM validation 被 checkout-local build dependency 阻断。

Architecture Review 发现旧环境问题：

- Node / Toolchain 与 checkout 耦合；
- candidate build/verify 需要 checkout `node_modules`；
- environment root 推导与 repo path 耦合；
- Gateway/source/runtime 可能混用不同 checkout；
- Runtime release 不完全 self-contained。

先由 ChatGPT 设计 Shared Toolchain / v2 Runtime 方案，随后真实 Windows resolver 暴露批处理问题；用户决定让 Codex 接管环境 repair + mechanical validation。

Codex 最终完成：

```text
shared immutable Toolchain
checkout-independent Environment Root
release-bundled Gateway
v2 self-binding Runtime Release
explicit activate/rollback
live Gateway release-switch guard
real v1/v2 rollback compatibility
```

然后继续完成 machine-local Launcher，让 Git 完全失去 start/stop/status/health ownership。

环境层正式封箱。

## Phase B — 分支收口

研究 20+ 历史分支 ancestry 后：

- 创建 `development/et-harness-mainline-v0.1`；
- 创建 `validation/et6801-srpwm-behavioral-v0.1`；
- 创建 `archive/pre-mainline-history-2026-09-02` 保存旧独立 commit ancestry；
- 建立 mainline branch policy 文档；
- 后续开发只基于 mainline。

## Phase C — ET6801 SRPWM 真实 Behavioral Validation

测试任务不是“看看 Harness 能不能跑”，而是：

> **用 ET6801 SRPWM 真实工程任务验证所有治理模块是否自动、正确、可靠、按照设计要求工作，并产生可持续消费、不污染长期状态的治理数据。**

真实场景：

```text
Task A       = real ET6801 SRPWM analysis
Task A-retry = clean retry after Task A validation recovery defect
Task B       = related ET6801 SRPWM follow-up
Task C       = clearly unrelated Companion/FPGA/Instrument task
+ project/scope/trust/completion negative controls
```

Codex 最终 Evidence：

```text
branch: validation/et6801-srpwm-behavioral-v0.1
Evidence HEAD: fea9e454d100eaf175bfa8f9ed0589a104488d15
baseline source: b3f32b3002d576ff75f3c4edee7fdd643bf415e0
```

测试提交只新增：

- SRPWM Evidence；
- `test_case_doc/srpwm/srpwm.md`；
- `test_case_doc/srpwm/ET6801_srpwm.md`。

没有为过测试修改 Framework 产品代码。

## Phase D — 建立 Validation Analysis Archive

为防止“修复 -> 新测试 -> 不知道新问题来源 -> 无限循环”，建立：

```text
agent_harness/validation_analysis/
├─ README.md
├─ ROUND_ANALYSIS_TEMPLATE.md
└─ rounds/
   └─ 2026-09-02_et6801_srpwm_behavioral_v1/
      └─ FINAL_ANALYSIS.md
```

职责严格区分：

```text
test_campaigns/**/evidence
  = Codex mechanical truth

validation_analysis
  = Architecture Owner evidence-to-code/root-cause/repair analysis
```

每轮分析固定要求：

1. Evidence Inventory；
2. Evidence -> Code；
3. Defect Provenance；
4. Why previous tests missed it；
5. Predictive Simulation；
6. Root-cause grouping；
7. Repair Decision；
8. Risk Analysis；
9. Acceptance Contract；
10. Freeze。

只有机械证明“旧基线正常、本轮修改后变坏”的问题才叫：

```text
NEW_REGRESSION
```

不能把“以前没测到、现在新发现”自动叫 regression。

---

# 7. SRPWM Behavioral Validation 最终结果

Codex Final Report：

```text
BEHAVIORAL_VALIDATION_FAIL
PASS: 25
FAIL: 9
OBSERVABILITY_GAP: 4
NOT_EXECUTED: 2
```

但不要理解为“Framework 整体失败”。

当前已经比较可靠的单次治理骨架：

```text
Admission
-> TaskIntent
-> Project / Rule / Architecture Route
-> Required Read
-> WRITE_SCOPE
-> Trusted Validation
-> Supervisor / Ledger
-> Reflection
-> one-shot Closure
```

强证明能力：

- machine environment isolation；
- exact 8 MCP tools；
- Project Admission staging；
- wrong project fail-closed without Runtime state；
- TaskIntent missing/malformed fail-closed；
- ET6801/SRPWM classification correct；
- natural-language `and` no longer parsed as IP；
- 7/7 required reads are Harness-owned trusted events；
- protected/out-of-scope mutation BLOCK；
- allowed SRPWM output path ALLOW；
- Agent forged validation PASS cannot satisfy Ledger；
- premature completion BLOCK；
- Supervisor basic pending/satisfied/violated/COMPLETE decisions；
- meaningful source-bounded Reflection；
- one-shot 8 mandatory Closure modules PASS；
- ordinary Agent prose does not pollute trusted Knowledge。

---

# 8. 当前真实 Framework 问题

## 8.1 Validation FAIL 后无法恢复

真实现象：

```text
validator FAIL
-> Agent 修正允许范围内 SRPWM output
-> 同一 validators 直接运行全部 PASS
-> harness_checkpoint returns validations=[]
-> old Ledger obligations remain VIOLATED
-> Turn cannot close
```

Root cause 已证明：

```text
Ledger trusted FAIL -> state VIOLATED
checkpoint scheduler only runs PENDING validation
recompute paths preserve/skip VIOLATED
```

Classification：

```text
PRE_EXISTING_ROOT_DEFECT + TEST_GAP
```

必须注意一个更危险的对称预测：

```text
PASS validator
-> later allowed mutation
-> old PASS may stay SATISFIED without rerun
```

这是 `PREDICTED_NOT_OBSERVED`，概率 HIGH、影响 CRITICAL。下一轮修 Validation 前必须先做这个判别测试，不能只修 FAIL->PASS。

## 8.2 Context successful task 不 terminalize

`ContextManagementService` 本身已有：

```text
complete(projectId, taskId)
-> status COMPLETED
-> phase complete
```

但是 `context-closure` Adapter 只调用：

```text
updateTaskLedger
updateProgressLedger
replaceWorkingSet
```

然后直接返回 APPLIED，没有调用 Context terminalization。

真实结果：

```text
A-retry Turn COMPLETE
B Turn COMPLETE
但 Context session 仍 ACTIVE
```

Classification：

```text
PRE_EXISTING_ROOT_DEFECT
```

上一轮 Context continuity repair 用：

```text
ACTIVE + Close governed Turn marker
```

作为兼容路径，这是“绕过旧 lifecycle 缺口”，不是根治。

## 8.3 Task B 没拿到 priorContext

真实事实：

```text
A-retry Context has 5 confirmed + 3 openIssues
B is related ET6801/SRPWM follow-up
B harness_begin has no priorContext
B confirmed/openIssues start empty
B rereads outputs/SVD/Driver
```

但是当前不能把唯一原因简单写成 `status=ACTIVE`，因为 selector 已允许：

```text
ACTIVE + Close governed Turn marker
```

作为候选。

当前至少有三个 code-supported candidates：

```text
C1 inline budget starvation
   remaining = min(4000, 16000 - existingInlineChars)
   if <= 0 -> no prior context

C2 ref overlap mismatch
   current refs 与 historical refs 没有真实 overlap

C3 selection/projection loss
   prior item 在 selector / context assembly / gateway projection 某层被丢弃
```

因此：

```text
Context terminalization defect = PROVEN
Task B exact omission sub-cause = NOT YET UNIQUELY PROVEN
```

分类：

```text
INCOMPLETE_PREVIOUS_FIX built on PRE_EXISTING_ROOT_DEFECT
```

下一轮先做 composed diagnostic，必须输出：

- historical candidates；
- status / lastAction；
- matchedRefs；
- existingInlineChars；
- remaining prior budget；
- omit reason；
- final prior-context item；
- Gateway projected priorContext。

在这些 Evidence 之前，不允许盲改 selector。

## 8.4 Context provenance 太粗

当前 Context Closure：

```text
refs = reflection.context.touchedRefs
```

同一个全量 refs 被附到每条 Decision / Confirmed / Assumption / OpenIssue。

这会产生事实级 over-association，并可能在未来 Prior Context 稳定流动后制造 false relevance / cross-task pollution。

Classification：

```text
PRE_EXISTING_ROOT_DEFECT / DATA_QUALITY_GAP
```

## 8.5 Successful complete 不能 replay

真实：

```text
first harness_complete -> COMPLETE
same request again -> RUNTIME_UNAVAILABLE / active Turn none
```

Kernel `ClosureCoordinator` 本身已经支持：

```text
existing COMPLETE receipt -> return existing
```

真正 broken boundary 是 Runtime/Gateway closed-turn replay：Runtime 在到达 Kernel idempotent receipt logic 前就拒绝 CLOSED Turn。

Classification：

```text
PRE_EXISTING_ROOT_DEFECT + TEST_GAP
```

不要重写 Closure Coordinator。

## 8.6 Failed begin 可以制造 orphan Turn

Gateway begin 当前顺序：

```text
Runtime openTurn
-> projectContextFromOpenTurn
-> snapshotStore.put
```

任何 `openTurn` 之后的异常都可能产生 partial commit。

Task C 真实产生：

```text
begin ERROR
Runtime OPEN Turn exists
ACTIVE Context exists
1-event Event Store exists
Gateway snapshot absent
status = TASK_NOT_FOUND
re-begin = unresolved Turn / RUNTIME_UNAVAILABLE
```

Classification：

```text
PRE_EXISTING_ROOT_DEFECT + TEST_GAP
```

修复不能通过“删 Event Store”回滚，因为 append-only audit history 不能删除。最终设计必须是 prepare/commit 或 explicit terminal compensation / abort。

## 8.7 Work Observation body 不 durable

当前 `GovernanceTurnObservationStore` 是纯内存 Map。

实时 governance 可以用 observation；进程/session 丢失后只能证明 observation ref 曾存在，不能重建 evaluated body。

Classification：

```text
PRE_EXISTING_ROOT_DEFECT / NEWLY_TESTED_CAPABILITY_GAP
```

P1，先不抢 P0 lifecycle scope。

## 8.8 Context / Route 太宽

Task A 初始 Context：

```text
17,485 / 18,000 chars
55 refs
```

包括核心 SRPWM/IP route，也有较多 generic PC/Firmware/Companion/CI/Knowledge/Gate material。

这是质量与 observability 问题，不应在 P0 状态机修复中一起重构。

---

# 9. 为什么上一轮测试 PASS，却没抓住这些问题

这是本轮最重要的方法论成果之一。

## 9.1 Context continuity test 只测 selector

旧单测手工构造 synthetic `COMPLETED` / `ACTIVE+marker` session，直接调用 `selectRelevantContextHistory()`。

没有真实组合：

```text
Context Closure
-> Evidence State persistence
-> next task bootstrap
-> real Gateway begin
```

所以只能证明 selector 局部逻辑。

## 9.2 Context Closure unit test 本身 codify 了不完整行为

fake manager 只提供：

```text
getTask
updateTaskLedger
updateProgressLedger
replaceWorkingSet
```

然后测试期待 APPLIED。

它根本没有提供 / assert `complete()`。

因此“测试 PASS”证明的是当前不完整 contract，而不是 end-to-end lifecycle correct。

## 9.3 Gateway contributor failure 只检查 snapshot

旧 T8 只 assert：

```text
Gateway snapshot absent
```

没有真实 Runtime，所以从未 assert：

```text
Runtime Turn / Context / Event Store == zero or terminal compensated
```

因此正好漏掉 Task C orphan。

## 9.4 Gateway complete 只调用一次

没有 same-request replay / response-loss / restart replay test。

## 9.5 Validation test 是静态 Evidence 语义，不是时间序列

旧测试证明：

```text
trusted FAIL can be recognized
```

没有测试：

```text
FAIL -> fix -> checkpoint -> PASS
PASS -> mutation -> checkpoint -> fresh revalidation
```

## 9.6 旧 real campaign 主要是 single-turn happy path

缺少系统性：

```text
fail -> fix -> retry
A -> related B
A -> unrelated C
complete -> same complete
post-open failure
restart active task
restart closed task
```

测试方法根因：

> **synthetic module test 证明了局部返回值，却没有总是把真实 lifecycle composition + durable state invariant 一起断言。**

以后每个修复必须同时有：

```text
exact Owner test
+
composed lifecycle test
+
real project behavioral test
```

---

# 10. 本轮 SRPWM 业务分析发现的项目问题

这些不是公共 Framework 缺陷。

真实 Source-based findings：

1. ET6801 SVD / Capability 显示 `SRPWM0..SRPWM17`，18 instances；SDK Driver 只允许 0..11（12 instances）；
2. `SRPWMCOM_enableDMA()` 接收并校验 channel，但 selection 寄存器写入被注释，只 enable DMA；
3. SRPWM UnitTest 调用当前 Header 不存在或参数数量不匹配的 API；
4. 没找到 ET6801 专属 SRPWM requirement；
5. 跨芯片 requirement JSON 存在乱码，不能作为可信目标 requirement；
6. Capability audit 仍有 7,686 `no_semantic_mapping` fields；
7. 历史 FunctionalTest 有 105 个入口，但不是 current SHA trusted PASS；
8. FPGA/HIL/真实硬件本轮 `NOT_EXECUTED`。

SRPWM 输出文档做对的关键边界：

- 不把历史源码当 current PASS；
- 不把 Driver 限制写成 Hardware 不支持；
- 不因 API 存在就宣称硬件 PASS；
- Case 仍保持 Candidate/BLOCKED；
- Machine-readable formal Case Contract 在证据不足时明确 `NONE`。

这些属于 ATP/SDK 项目 backlog，不进入下一轮 Framework P0 repair。

---

# 11. Knowledge 当前真实状态

已经证明：

```text
Agent narrative 不会直接成为 trusted Knowledge
Knowledge NONE 可以正常 Closure
没有重复 Candidate 污染
```

没有证明：

```text
新 SRPWM source-backed fact -> Candidate
PROJECT/PUBLIC classification
SUPPORT / CONTRADICT / UPDATE
Task B 自动消费
```

其中一个上游原因是 ATP Knowledge taxonomy 当前主要是治理类：

```text
Project Identity
Task Routing
Architecture
Validation
Project History
```

缺少：

```text
Chip/IP Hardware Fact
SDK Driver Gap
Test Constraint
Known Verification Fact
```

因此本轮 Reflection 对 `18 hardware vs 12 driver` 等事实选择 Knowledge NONE 是保守且合理的，不能把它机械判成 Knowledge Manager 写入 FAIL。

Knowledge positive path 在 P0 lifecycle 稳定后再做项目 taxonomy + A->Knowledge->B real test。

---

# 12. Validation Analysis 机制已经冻结

新目录：

```text
agent_harness/validation_analysis/
```

入口：

```text
README.md
ROUND_ANALYSIS_TEMPLATE.md
rounds/2026-09-02_et6801_srpwm_behavioral_v1/FINAL_ANALYSIS.md
```

必须遵守：

### Evidence first

所有结论回指：

- tested exact SHA；
- Evidence SHA / file；
- first failing boundary；
- source Owner；
- source/history；
- inference 必须标 `HYPOTHESIS` / `PREDICTED_NOT_OBSERVED`。

### Defect Provenance mandatory

每个新问题必须先分类：

```text
PRE_EXISTING_ROOT_DEFECT
INCOMPLETE_PREVIOUS_FIX
NEW_REGRESSION
NEWLY_TESTED_CAPABILITY_GAP
PROJECT_CONTENT_GAP
OBSERVABILITY_GAP
TEST_GAP
```

只有 `NEW_REGRESSION` 才允许说“本轮修复引入的新 bug”。

### 根因未隔离禁止修

如果一个现象有多个代码可解释候选，先做 discriminating test。

### 修复可靠性标准

方案进入 implementation 前必须同时证明：

1. first failing boundary 可机械复现；
2. root cause 已 Evidence + source isolation；
3. 修改发生在真实 Owner；
4. 状态转移和 failure path 明确；
5. retry/idempotency/process/task boundary 已考虑；
6. append-only Evidence / Trust Boundary 不被削弱；
7. 不新增第二 canonical state；
8. exact regression test；
9. composed integration test；
10. previous PASS non-regression；
11. real project task；
12. State diff 无新污染。

否则只能：

```text
REPAIR_NOT_YET_PROVEN
```

当前本轮 Final Analysis 结论正是：

```text
REPAIR_NOT_YET_PROVEN
```

因为 Validation / Closed replay 已基本隔离；Context B omission 仍需 discriminating test；Begin orphan 的最终轻量 transaction/compensation semantics 仍需先在设计上冻结。

---

# 13. 下一阶段真正要做什么

下一阶段不是直接“大修 Framework”。

第一目标是建立一个 **P0 Lifecycle Repair Requirement**，只包含下面 5 条 repair line + non-regression。

## R1 Validation current-state recovery

先做高风险判别：

```text
PASS validator
-> allowed mutation
-> checkpoint
```

必须确认旧 PASS 是否会 stale retain。

最终 repair 必须同时解决：

```text
FAIL -> correction -> later trusted PASS
PASS -> relevant mutation -> validation becomes stale and reruns
```

但历史 FAIL Evidence 必须保留 append-only。

不能允许 generic `VIOLATED -> SATISFIED`，WRITE_SCOPE 等安全 violation 不能被 Validation PASS 清掉。

## R2 Context task terminalization + module atomicity

首选轻量方向：ContextManager own 一个原子 closure operation，例如：

```text
finalizeTaskClosure(...)
```

在内存里组装：

```text
TaskLedger
ProgressLedger
WorkingSet
COMPLETED status
phase complete
```

然后一次 CAS/state update。

不要继续：

```text
update ledger
update progress
replace working set
complete
```

这种多次 durable semantic commit。

## R3 Prior Context diagnosis before patch

先做 composed diagnostic，记录：

```text
historical candidates
matched refs
base inline chars
remaining prior budget
omit reason
final prior-context item
Gateway priorContext
```

只有机械隔离 C1/C2/C3 后才改 selector/budget/provenance。

## R4 Begin failure atomicity

必须写小状态机再实现。

任何 open 后失败最终只允许：

```text
A. no durable governed task
or
B. durable terminal ABORTED/FAILED and publicly inspectable/recoverable
```

禁止 unreachable ACTIVE。

不能通过删除 append-only Event Store 来伪造 rollback。

设计候选：

```text
prepare/commit split
or explicit terminal compensation/abort
```

必须覆盖 contributor failure、malformed projection、snapshot I/O failure、process loss 等，不只修 Task C 一个 error code。

## R5 Closed Turn replay

复用 Kernel 已有 COMPLETE receipt authority。

要求：

```text
same exact complete -> same closure identity, zero new effects
same after Gateway restart -> same
same after Runtime rehydrate -> same
changed reflection/request -> explicit conflict
finalization count == 1
```

不要做第二 Gateway completion cache authority。

---

# 14. 下一轮强制 Non-regression

任何 P0 repair 不能只证明自己的 test 绿。

必须重新证明：

1. machine environment 仍 D-drive owned；
2. Node v22.23.2；
3. checkout-local node_modules absent；
4. npm invocation 0；
5. exact 8 MCP tools；
6. wrong project no Runtime state；
7. missing/unknown fingerprint staged；
8. missing/malformed TaskIntent fail-closed；
9. ET6801/SRPWM classification correct；
10. `and` 不误识别 IP；
11. Required Read 7/7 trusted；
12. WRITE_SCOPE protected/outside block；
13. forged validation remains non-authoritative；
14. premature completion block；
15. Supervisor state correct；
16. meaningful Reflection accepted；
17. 8 mandatory Closure modules one-shot happy path PASS；
18. Knowledge narrative no-pollution；
19. no silent machine Runtime activation；
20. no second Runtime/Ledger/Event/Context/Knowledge store。

这就是防止“修一个坏一个”的硬门槛。

---

# 15. 当前明确不要做的事情

下一轮 P0 不要混入：

### SRPWM project repair

- 18 vs 12 Driver；
- DMA selection；
- UnitTest drift；
- Requirement；
- 7,686 capability mapping；
- FPGA/HIL。

### P1 quality optimization

- 通用 Architecture route narrowing；
- generic Knowledge ranking；
- Gate/Evidence/Experience richer public projection；
- Observation durability，如果会扩大 P0 scope。

### Knowledge taxonomy

等 P0 continuity 稳定后再建 chip/IP taxonomy，并用真实 A->Knowledge->B 测试。

---

# 16. 当前 Remaining Unknowns

这些不能在新对话里被“顺手假设”：

1. Task B priorContext 到底是 inline budget、ref overlap 还是 selection/projection 边界丢失；
2. trusted PASS 在 later allowed mutation 后是否会 stale survive；
3. active supervised Turn 是否能跨真实 process restart 继续 status/observe/checkpoint/complete；
4. closed complete 是否能跨 restart replay；
5. valid ATP project task 没有 Project Context contributor 时，产品语义究竟是 generic bounded fallback 还是 fail-closed；无论哪种都不能 orphan；
6. Context fact-level provenance 的稳定 contract 形式；
7. realistic ATP Context pack 中应当为 priorContext 预留多少预算；
8. Context closure sequential durable writes 在第 2/3 步 injected failure 时是否会 partial commit（高概率预测，尚未机械执行）；
9. 1k/10k Context history 的 selector scaling；
10. domain Knowledge taxonomy 加入后与 generic governance Knowledge 的 budget/ranking competition。

---

# 17. 新对话启动顺序

新对话不要重新问用户项目是什么，也不要重新做已封箱环境设计。

优先读取顺序：

```text
1. 本文件
2. ../../AGENTS.md
3. ../validation_analysis/README.md
4. ../validation_analysis/rounds/2026-09-02_et6801_srpwm_behavioral_v1/FINAL_ANALYSIS.md
5. ../test_campaigns/governance_behavioral_validation_v1/evidence/et6801_srpwm_behavioral_20260902/FINAL_REPORT.md @ fea9e454...
6. 同目录 module_behavior_matrix.json / negative_controls.json / state_diffs.json / defect_backlog.md
7. 需要真实 IP 生产背景时读 20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md
8. 需要历史设计演进时再读 V0.1 / Round3 / 旧 Handoff
```

事实优先级：

```text
exact current source / exact Git SHA / mechanical Evidence
> current V0.2 Handoff
> validation_analysis Final Analysis
> frozen Test Requirement
> historical Handoff / Design
> Agent narrative / chat memory
```

新对话第一个工作目标应该是：

> **基于本轮 Final Analysis 形成 P0 lifecycle repair requirement 和最小判别测试，不直接修改尚未唯一隔离的 Context selector；然后按 R1-R5 小步修复并执行 Fix Acceptance + Mandatory Non-regression + real ATP task。**

---

# 18. 最终冻结判断

当前项目不是“Framework 全部 PASS”，也不是“Framework 越修越坏”。

最准确判断：

```text
Machine Environment                    PASS / frozen
Machine-local Runtime lifecycle        PASS / frozen
Single-task safe governance skeleton   substantially PASS
Trust Boundary                         PASS
WRITE_SCOPE / Required Read            PASS
Trusted Validation admission           PASS
Supervisor basic enforcement           PASS
One-shot Closure                       PASS

Validation recovery/current freshness  FAIL
Context task lifecycle                 FAIL
Cross-task Context continuity          FAIL / exact omission sub-cause unresolved
Begin failure atomicity                FAIL
Closed completion replay               FAIL
Observation durable replay             FAIL / P1
Knowledge positive accumulation        NOT_EXECUTED / taxonomy gap
Route/Context precision                needs P1 improvement
```

当前最重要的控制原则：

> **以后每轮先证明问题来源，再决定是否修；先冻结 Acceptance，再写实现；任何修复必须同时证明“目标缺陷修好”和“上一轮已 PASS 能力没有回归”。**

这就是防止 ET Harness 进入无限 `fix -> new test -> unknown regression -> fix` 循环的正式工程控制方法。
