# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent 或新聊天快速恢复公共 Harness 工程上下文的 Handoff Archive。

## 当前最高优先级恢复基线

继续 Execution Supervisor / ATP 真实 Agent 测试前，必须先读：

1. `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`
2. `20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md`
3. `20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md`
4. `agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`
5. `agent_harness/design/21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md`
6. `agent_harness/design/20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md`
7. `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`
8. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`
9. `20260826_HARNESS_CURRENT_STATE.md`
10. `20260826_TEST_STRATEGY_AND_RESULTS.md`
11. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`
12. `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`
13. `20260826_P0_P1_HARDENING.md`

旧 Audit 记录的是修复前事实；涉及 Execution Supervisor Phase 0 当前状态时，以 `20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md`、最新 `main` 源码和最新机械证据为准。

---

## 当前公共仓库事实

```text
repo: abba-labs/et-harness
canonical branch: main
Phase 0 source-repair merge:
cae6c15ccea1aaa100db756bf943895e6af51e8c
```

当前 Design 25 方向不变：

```text
Public Execution Supervisor
= deterministic execution-event supervision
+ Obligation Ledger
+ Evidence/claim/completion evaluation
+ cross-process replay
+ mandatory bridge into existing Reflection/Knowledge/Context/Closure
```

截至 2026-08-29，当前状态必须写成：

```text
Design 25 direction                                   VALID / FROZEN
Phase 0 canonical contract core                       PRESENT
Phase 0 source consistency                            PASS / REPAIRED
Phase 0 conflicting PR12 prototypes                   REMOVED
Phase 0 isolated source compile                       PASS
Phase 0 repository test logic                         PASS 17/17 (isolated)
Phase 0 additional fail-closed assertions             PASS 22/22
Phase 0 full benchmark                                PASS 2 x 10000 samples
Phase 0 committed baseline validation                 PASS
Phase 0 GitHub Actions runner                         BLOCKED / STEPS=[]
Phase 0 exact repository CI acceptance                BLOCKED / NOT EXECUTED
Phase 0 overall                                       SOURCE REPAIRED / CI ACCEPTANCE BLOCKED
Phase 1 persistent event store + replay               NOT STARTED
Phase 2 Obligation Ledger                             NOT IMPLEMENTED
Phase 3 External Agent Event/Response Bridge          NOT IMPLEMENTED
Phase 4 Claim/Evidence/Completion evaluator           NOT IMPLEMENTED
Phase 5 Supervisor -> Reflection/Closure integration  NOT IMPLEMENTED
Phase 6 Host enforcement profiles                     CONTRACT-ONLY / INCOMPLETE
Phase 7 efficiency hardening                          BASELINE-ONLY
Phase 8 ATP real Pilot                                NOT EXECUTED
```

PR #13 `[OBSOLETE] feat: compile project obligations into Task Supervision Contracts` 已关闭且未合入。

PR #15 `fix: repair Execution Supervisor Phase 0 canonical contracts` 已合入 `main`，其作用是修复源码状态，不代表 GitHub CI 已通过。

---

## Phase 0 现在已经修了什么

Phase 0 公共包已收敛回唯一 canonical 模型。

当前 `agent_harness/public_plugins/execution_supervisor/src/` 只有：

```text
baseline.ts
contracts.ts
hash.ts
index.ts
validation.ts
```

当前 canonical 测试只有：

```text
committed-baseline.test.ts
contracts.test.ts
negative-contracts.test.ts
performance-baseline.test.ts
```

修复分支与 pre-PR12 canonical Phase 0 commit `4d7c2ffcfe05f938ac309a98f80e37576a2db552` 做树级比较后，Execution Supervisor package 没有剩余差异；后加的第二套 contract/runtime prototype 已全部移除。

详细证据见：

```text
20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md
```

---

## 为什么 Phase 0 仍不能写最终 PASS

源码问题已经修复，但 GitHub Actions 当前仍然在 Runner 分配前失败。

PR #15 Phase 0 Workflow 以及手工 rerun 都表现为：

```text
job created
conclusion: failure
steps: []
```

合并后的 `main` Public Baseline：

```text
run: 33220975191
head: cae6c15ccea1aaa100db756bf943895e6af51e8c
repository-boundary: failure
steps: []
public-integration: skipped
package-build-and-test: skipped
```

因此：

```text
GitHub CI failure != source test failure
```

但同样：

```text
local/isolation PASS != GitHub repository CI PASS
```

所以最终状态必须保持：

```text
Phase 0 source repair             PASS
Phase 0 local mechanical evidence PASS
Phase 0 repository CI acceptance  BLOCKED
```

---

## 唯一允许的下一步

**不要开始 Design 25 Phase 1。**

下一步只处理 Phase 0 最后一个未关闭项：

```text
resolve / restore GitHub Actions runner execution
  ↓
run exact repository npm test
run exact repository npm run build
run exact repository npm run benchmark
run Phase 0 public/domain boundary checks
run Harness Public Baseline
  ↓ all real executed PASS
mark Phase 0 ACCEPTED
  ↓
only then start Design 25 Phase 1
= persistent event store + cross-process replay
```

在 Phase 0 exact repository CI acceptance 之前，禁止提前进行：

```text
Persistent Event Store 实现
Obligation Ledger Phase 2
External Chat Bridge Phase 3
Claim/Evidence evaluator Phase 4
Closure integration Phase 5
ATP/eTimer 业务扩展
真实 ATP Pilot Phase 8
```

---

## 分支模型

```text
main
= 公共 Harness 唯一上游

project/<name>
= main 公共 Harness
  + 真实项目代码
  + Project Plugin / A/R/K/G / Project Knowledge

feat/<public-capability>
= 从最新机械验证的 main 创建的单阶段公共能力分支

pilot/<name>
= 真实 Pilot 编排和证据，不作为公共 Runtime 实现基线
```

同步方向：

```text
validated main
  ↓
project/<name>
  ↓
clean pilot branch
```

项目分支和 Pilot 分支不得整体反向合入 `main`。

---

## 开发效率冻结原则

后续提高效率靠收敛流程，而不是跳过治理：

```text
one conversation = one phase / one repair target
one phase = one responsibility
one canonical contract model
one clean branch from validated main
focused tests before next phase
no LLM/network/full reroute on event hot path
no next phase before current phase has mechanical PASS
```

禁止再次发生：

```text
上一阶段还没有真实 PASS
→ 并行创建下一阶段分支
→ 多套 contract vocabulary 同时进入 main
→ 最后再靠聊天叙述判断哪个是真的
```

---

## 历史来源与已验证功能

迁移来源：

```text
source repo: abba-labs/et-tool
source branch: main
source repository HEAD:
496243ef2bdf56a5db7f81b2014970d3f8af34f9

last fully validated Harness code baseline:
f37b1080ca65388fc0e32f7fa75567b512c86752
```

历史已验证主要功能：

```text
PR #37 -> P0/P1 Harness hardening
PR #38 -> Real Task Matrix and minimal hardening
PR #39 -> Public Layer knowledge policy smoke alignment
PR #40 -> Tiered Knowledge retrieval and Evidence feedback
```

这些历史能力不因当前 Execution Supervisor Phase 0 的 CI Runner 问题而自动失效。

---

## 总冻结原则

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

以及当前恢复不变量：

> **不要从“最新看起来写了很多代码”的状态继续；只从合同唯一、边界清晰、机械证据明确的 canonical state 继续。**
