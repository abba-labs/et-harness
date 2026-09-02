# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent、Codex 或新聊天快速恢复公共 Harness 工程上下文的 **Handoff Archive**。

---

# 1. 当前最高优先级恢复入口

从 2026-09-02 当前阶段起，任何接手 ET Harness / ATP 的新聊天、Agent 或 Codex，优先按下面顺序读取：

1. `20260902_ET_HARNESS_CURRENT_STATE_AND_SRPWM_BEHAVIORAL_HANDOFF_V0_2.md`
2. `../../AGENTS.md`（仓库根目录）
3. `../validation_analysis/README.md`
4. `../validation_analysis/rounds/2026-09-02_et6801_srpwm_behavioral_v1/FINAL_ANALYSIS.md`
5. `../test_campaigns/governance_behavioral_validation_v1/evidence/et6801_srpwm_behavioral_20260902/FINAL_REPORT.md`（Evidence SHA `fea9e454d100eaf175bfa8f9ed0589a104488d15`）
6. 同一 Evidence 目录中的 `module_behavior_matrix.json`、`negative_controls.json`、`state_diffs.json`、`defect_backlog.md`
7. `20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md`（需要继续真实 ATP IP 生产任务时）
8. `20260902_GOVERNANCE_BEHAVIORAL_VALIDATION_AND_PROJECT_ADMISSION_HANDOFF_V0_1.md`（历史阶段说明，不再作为当前入口）

当前事实优先级：

```text
当前实际源码 / exact Git SHA / 真实机械 Evidence
> 当前 V0.2 Handoff
> validation_analysis Final Analysis
> 当前 Test Requirement
> 历史 Handoff / Design
> Agent 自述或聊天记忆
```

若历史文档与 V0.2 冲突，以 **当前源码/Evidence + V0.2 + validation_analysis** 为准。

---

# 2. 当前 canonical Git / Machine 边界

## 2.1 长期开发主线

```text
repo: abba-labs/et-harness
branch: development/et-harness-mainline-v0.1
```

V0.2 Handoff 写入前的 Architecture Analysis baseline：

```text
83e3c1291352c4427e890e695a253ea99a7d7325
```

后续 Handoff / README 文档提交只推进文档，不代表 Framework 产品行为变化。

## 2.2 当前真实 Behavioral Evidence branch

```text
validation/et6801-srpwm-behavioral-v0.1
Evidence HEAD: fea9e454d100eaf175bfa8f9ed0589a104488d15
Tested source: b3f32b3002d576ff75f3c4edee7fdd643bf415e0
```

在 Evidence 被正式归档/合并前不要删除该 validation branch。

## 2.3 历史 archive

```text
archive/pre-mainline-history-2026-09-02
dc6382cba054e7594902d880f71fee4bb623f8d8
```

用于保存旧阶段分支 ancestry，只读。

## 2.4 Machine Environment

真正运行环境唯一 owner：

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

已经机械验证：

```text
Git checkout / branch / worktree
不会自动拥有 Runtime lifecycle

Machine-local Launcher
Node
Toolchain
Runtime Releases
Runtime State
Gateway
都由 D-drive machine environment 管理
```

当前 active v2 release 的最后机械验证记录：

```text
f976d8e32df64fa78075
```

若需要当前 PID/health，必须重新通过 machine launcher 查询，不能把历史 PID 当当前事实。

---

# 3. 当前一句话状态

> **环境与单次安全治理链已经基本成立；当前主要缺口集中在连续治理生命周期：Validation 恢复与 freshness、Context task terminalization / cross-task continuity、Begin failure atomicity、Closed Turn replay，以及长期治理数据质量。**

当前没有 Evidence 证明这些核心问题是最近 Environment / Machine Launcher 优化新引入的 regression。

当前 Architecture Analysis 分类：

```text
Validation recovery                 PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Context closure remains ACTIVE      PRE_EXISTING_ROOT_DEFECT
Task B no priorContext              INCOMPLETE_PREVIOUS_FIX + unresolved sub-cause
Complete replay                     PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Failed begin orphan                 PRE_EXISTING_ROOT_DEFECT + TEST_GAP
Observation body not durable        PRE_EXISTING_ROOT_DEFECT / NEWLY_TESTED_CAPABILITY_GAP
Context/Route breadth               NEWLY_TESTED_CAPABILITY_GAP / OBSERVABILITY_GAP
Knowledge positive path             PROJECT_CONTENT_GAP / NOT_EXECUTED
```

---

# 4. 当前已经强证明的能力

```text
Machine Environment freeze
Machine-local Launcher
exact 8 MCP tools
Project Admission staging
TaskIntent fail-closed
ET6801/SRPWM classification
natural-language `and` no longer parsed as IP
Required Read trusted ingress
WRITE_SCOPE block/allow
Trusted Validation authority
Agent forged PASS rejection
Premature completion block
Supervisor basic enforcement
Meaningful Reflection
one-shot 8-module Closure
Knowledge narrative no-pollution
```

不要因为 Behavioral Overall FAIL 否定这些稳定资产。

---

# 5. 当前最重要的未解决问题

P0：

1. `FAIL -> correction -> PASS` 无法在同 Turn 恢复；
2. 需要先判别 `PASS -> later mutation` 是否存在 stale validation；
3. successful task Context 未 terminalize 为 `COMPLETED`；
4. related Task B 无 priorContext，exact omission sub-cause 仍需 budget/ref/projection discriminating test；
5. Gateway begin 在 Runtime open 后失败可留下 unreachable orphan state；
6. successful complete 无法 same-request replay / restart replay。

P1：

- Work Observation durable replay；
- Context/Route 精度和预算；
- Gate/Evidence/Experience bounded observability；
- Knowledge domain taxonomy / positive reuse。

Project backlog：

- ET6801 SRPWM 18 hardware instances vs 12 Driver；
- DMA selection write gap；
- UnitTest API drift；
- missing ET6801 SRPWM requirement；
- cross-chip requirement mojibake；
- 7,686 capability `no_semantic_mapping`；
- FPGA/HIL not executed。

---

# 6. Validation Analysis 是后续强制流程

目录：

```text
agent_harness/validation_analysis/
```

职责：

```text
test_campaigns/**/evidence = Test Executor mechanical truth
validation_analysis        = Architecture Owner root-cause / provenance / repair analysis
```

每轮必须：

```text
Evidence Inventory
-> Trace to Code
-> Defect Provenance
-> Why previous tests missed it
-> Predictive Simulation
-> Root-cause Grouping
-> Repair Decision
-> Risk Analysis
-> Acceptance Contract
-> Freeze
```

根因没有机械隔离前，不允许凭感觉改代码。

只有有证据证明“旧基线正常、本轮修改后变坏”才能标：

```text
NEW_REGRESSION
```

---

# 7. 当前下一阶段

下一阶段第一个产物不是代码，而是：

```text
P0 Lifecycle Repair Requirement
```

仅包含：

```text
R1 Validation current-state recovery + stale-PASS discriminating test
R2 Context task terminalization + closure module atomicity
R3 Prior-context composed diagnostic before selector change
R4 Begin failure transaction/terminal compensation semantics
R5 Closed Turn idempotent replay
+ Mandatory Non-regression matrix
```

之后才允许最小 scoped repair。

任何 repair 都必须同时证明：

```text
Fix Acceptance PASS
+
Previous proven behavior Non-regression PASS
+
real ATP behavioral task PASS
+
State diff no new pollution
```

---

# 8. 不可违反的当前开发原则

```text
可靠 > 稳定 > 轻量化 > 易扩展
```

必须继续遵守：

- Agent 不负责治理自己；Framework 负责治理 Agent。
- Agent 负责语义理解；Framework / Project Plugin 负责确定性验证与治理。
- Agent 不能自报 trusted PASS，也不能制造 trusted Evidence。
- Pure MCP 继续 truthful `AUDIT`。
- MCP `required=false`；Gateway 保持独立外部进程。
- 不新增第二 Runtime / Ledger / Event Store / Closure / Context Store / Knowledge Store。
- 不新增 watcher / daemon / Windows Service / custom fs-shell MCP。
- Git branch 切换不能影响 D-drive Runtime lifecycle。
- 一个根因一个 repair line；不要把 9 个 FAIL 当 9 个独立补丁。
- Observability 缺口复用现有 owner 的 bounded receipt/trace，不另造监管 Runtime。
- append-only Evidence 不通过删除来“回滚”。
- 修复设计必须考虑 retry / idempotency / failure interruption / cross-task / cross-process。

---

# 9. 历史文档的使用方式

旧文档继续保留，用于回答“当时为什么这样设计/测试”，但不拥有当前状态。

典型历史入口：

```text
20260826_HARNESS_CURRENT_STATE.md
20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md
20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md
20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md
20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md
20260902_GOVERNANCE_BEHAVIORAL_VALIDATION_AND_PROJECT_ADMISSION_HANDOFF_V0_1.md
```

---

# 10. 总冻结原则

> **Agent 可以更换，模型可以更换，Host 可以更换；项目 Architecture、Rules、Knowledge、Context、Evidence 和 Governance 不能依附于某一个 Agent。**

> **Framework 要保证必须发生的治理不能被 Agent 跳过，但不要把开放自然语言理解堆成 if/else/regex；Agent 做语义，Framework 验证结构并执行确定性治理。**

> **以后每轮先证明问题来源，再决定是否修；先写 Acceptance，再写实现；任何修复必须同时证明目标缺陷修好且上一轮已 PASS 能力没有回归。**
