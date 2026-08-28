# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent 或新聊天快速恢复公共 Harness 工程上下文的 Handoff Archive。

## 当前最高优先级恢复基线

继续 Execution Supervisor / ATP 真实 Agent 测试前，必须先读：

1. `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`
2. `20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md`
3. `agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`
4. `agent_harness/design/21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md`
5. `agent_harness/design/20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md`
6. `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`
7. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`
8. `20260826_HARNESS_CURRENT_STATE.md`
9. `20260826_TEST_STRATEGY_AND_RESULTS.md`
10. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`
11. `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`
12. `20260826_P0_P1_HARDENING.md`

如果旧聊天叙述、旧 Handoff 或分支名称与 `20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md` 冲突，以最新机械证据和该 Audit 为准。

---

## 当前公共仓库事实

```text
repo: abba-labs/et-harness
canonical branch: main
current audited main HEAD:
0474cea6da2b9618fd40a0167099f2c8477a0e3c
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

但截至 2026-08-29：

```text
Design 25 direction                                   VALID / FROZEN
Phase 0 canonical contract core                       PRESENT
Phase 0 source consistency                            FAIL
Phase 0 real CI/build/test/benchmark evidence         NOT EXECUTED
Phase 0 overall                                       FAIL / INCOMPLETE
Phase 1 persistent event store + replay               NOT IMPLEMENTED
Phase 2 Obligation Ledger                             NOT IMPLEMENTED
Phase 3 External Agent Event/Response Bridge          NOT IMPLEMENTED
Phase 4 Claim/Evidence/Completion evaluator           NOT IMPLEMENTED
Phase 5 Supervisor -> Reflection/Closure integration  NOT IMPLEMENTED
Phase 6 Host enforcement profiles                     CONTRACT-ONLY / INCOMPLETE
Phase 7 efficiency hardening                          BASELINE-ONLY / UNVERIFIED
Phase 8 ATP real Pilot                                NOT EXECUTED
```

PR #13 `feat/public-execution-supervisor-phase1-contract-builder-v0.1` is obsolete as a Phase 1 implementation and must not be merged.

---

## 为什么 Phase 0 不能算 PASS

`main` 已合入 PR #12，但机械检查显示：

```text
Harness Public Baseline run: 33192376336
runner_id: 0
steps: []
conclusion: failure
```

PR #12 的对应 Actions 也没有真正启动 Runner，因此 `npm test / npm run build / npm run benchmark` 没有形成可信 PASS Evidence。

同时 `main` 当前存在两套不兼容的 Execution Supervisor contract/type vocabulary。`tsconfig.json` 会编译 `src/**/*.ts`，所以这些额外文件不能因为没有从 `index.ts` export 就被忽略。

详细文件和证据见：

```text
20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md
```

---

## 唯一允许的下一步

先修 Phase 0，不继续扩功能：

```text
current main
  ↓
clean Phase 0 repair branch
  ↓
one canonical contract model
  ↓
remove/rewrite incompatible prototypes
  ↓
npm test
npm run build
npm run benchmark
Execution Supervisor Phase 0 CI
Harness Public Baseline
  ↓ all real PASS
Design 25 Phase 1
= persistent event store + cross-process replay
```

在 Phase 0 真实 PASS 前，禁止提前进行：

```text
ATP/eTimer 业务扩展
External Chat Mailbox 扩展
Obligation Ledger Phase 2
Claim/Evidence evaluator Phase 4
Closure integration Phase 5
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

这些历史能力不因当前 Execution Supervisor Phase 0 问题而自动失效；当前 Audit 只重新冻结 Execution Supervisor 新阶段的事实状态。

---

## 总冻结原则

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

以及本阶段新增恢复不变量：

> **不要从“最新看起来写了很多代码”的状态继续；只从最新机械验证、合同唯一、边界清晰的 canonical state 继续。**
