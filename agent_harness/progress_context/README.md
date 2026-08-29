# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent、Codex 或新聊天快速恢复公共 Harness 工程上下文的 Handoff Archive。

---

# 1. 当前最高优先级恢复入口

从 2026-08-29 起，公共 Execution Supervisor 开发切换为 **Local Codex first**。

任何第一次进入该开发工作的 Codex / Agent 必须按顺序阅读：

1. `../../AGENTS.md`（仓库根目录 `AGENTS.md`）
2. `20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md`
3. `20260829_EXECUTION_SUPERVISOR_PHASE1_CODEX_HANDOFF_V0_1.md`
4. `../design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`
5. `20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md`
6. `20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md`
7. `../design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`
8. `../design/21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md`
9. `../design/20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md`
10. `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`
11. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`
12. `20260826_HARNESS_CURRENT_STATE.md`
13. `20260826_TEST_STRATEGY_AND_RESULTS.md`
14. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`

优先级：

```text
最新 main 源码 / Git HEAD / 实际本地命令结果
> Local Development Charter + 当前 Phase Handoff
> Design 25
> 历史 Audit / Handoff
> Agent 自述
```

旧 Audit 记录的是 Phase 0 修复前事实；涉及当前 Execution Supervisor 状态时，以 Phase 0 Repair Worklog、最新 `main` 源码、Local Charter 和当前 Phase Handoff 为准。

---

# 2. 当前公共仓库事实

```text
repo: abba-labs/et-harness
canonical branch: main
```

Phase 0 源码修复已经通过 PR #15 合入：

```text
cae6c15ccea1aaa100db756bf943895e6af51e8c
fix(supervisor): restore canonical Phase 0 contract core
```

随后只增加了恢复/证据文档；Codex 本地启动时必须执行：

```bash
git fetch --all --prune
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

不要依赖本文件中的旧 SHA 代替 `git rev-parse`。

---

# 3. 当前架构方向

Design 25 仍然冻结：

```text
Public Execution Supervisor
= Host-neutral execution-event supervision
+ persistent event/replay state
+ Obligation Ledger
+ Evidence/claim/completion evaluation
+ bridge into existing Reflection/Knowledge/Context/Closure
```

核心所有权不变：

```text
Project Plugin  → 项目业务规则、知识、具体义务
Host Adapter    → Host 事件翻译，不做治理判断
Agent           → 语义分析和判断
Supervisor      → 执行事件、义务、Evidence、Completion 机械监管
Kernel/Managers → Reflection / Knowledge / Context / Closure
```

公共 Framework 不理解 ATP、ET6801、eTimer 等项目业务。

---

# 4. Phase 0 当前状态

Phase 0 已经修回唯一 canonical contract model。

生产源仅包含：

```text
agent_harness/public_plugins/execution_supervisor/src/
  baseline.ts
  contracts.ts
  hash.ts
  index.ts
  validation.ts
```

canonical 测试仅包含：

```text
committed-baseline.test.ts
contracts.test.ts
negative-contracts.test.ts
performance-baseline.test.ts
```

已记录的修复证据：

```text
single canonical contract model             PASS
conflicting PR #12 prototype removal        PASS
isolated source compile                     PASS
repository test logic                       PASS 17/17 (isolated)
additional fail-closed assertions           PASS 22/22
full benchmark                              PASS 2 x 10000 samples
committed baseline validation               PASS
```

详细证据：

```text
20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md
```

---

# 5. 为什么开发模式从 GitHub-hosted CI 改成 Local Codex

GitHub 私有仓库 Hosted Actions 达到当前预算/计费边界后，Workflow 出现：

```text
job created
runner_id = 0
steps = []
conclusion = failure
```

这既不是代码 FAIL，也不是可接受的 CI PASS。

为避免高频开发被 Hosted Runner 费用和调度阻断，后续采用：

```text
Local Codex + Local Repo
→ exact tests/build/benchmark/integration
→ evidence bound to exact Git HEAD
→ commit/push/PR
```

这不是降低测试要求。

冻结原则：

> **改变执行位置，不改变验证内容。**

两个状态必须区分：

```text
LOCAL_MECHANICAL_ACCEPTED
HOSTED_CI_ACCEPTED
```

Hosted CI 暂时不再作为高频开发的必需门禁；Codex 必须执行 Local Charter 中定义的 exact local mechanical gate。

---

# 6. Codex 进入开发后的第一件事

Codex 不能直接开始 Phase 1 写代码。

第一步必须在本地 `main` 做一次 **exact Phase 0 local acceptance**：

```text
execution_supervisor package npm test
execution_supervisor package npm run build
execution_supervisor benchmark + report validation
public repository boundary
public packages build/test
public synthetic integration gates
clean worktree / exact source HEAD evidence
```

通过后写：

```text
YYYYMMDD_CODEX_LOCAL_PHASE0_ACCEPTANCE_<SHORT_SHA>.md
```

状态只有：

```text
LOCAL_MECHANICAL_ACCEPTED
LOCAL_MECHANICAL_FAILED
BLOCKED_BY_ENVIRONMENT
```

只有 `LOCAL_MECHANICAL_ACCEPTED` 才授权开始真正 Phase 1。

---

# 7. 下一阶段与唯一授权分支

Design 25 Phase 1 的真实定义是：

```text
Persistent Event Store + Cross-Process Replay
```

授权的新分支：

```text
feat/execution-supervisor-phase1-event-store-replay-v0.1
```

它必须从最终包含 Codex Handoff 文档的最新干净 `main` 创建。

Codex 必须 **禁止继续**：

```text
feat/execution-supervisor-phase1-event-store-v0.1
```

该旧分支停留在 Phase 0 修复前的旧状态。

同时禁止继续：

```text
feat/public-execution-supervisor-phase1-contract-builder-v0.1
```

PR #13 已关闭为 `[OBSOLETE]`；Contract Builder 不是 Design 25 Phase 1。

---

# 8. Phase 1 为什么做

原 Governance Runtime 主要按同进程假设工作：

```text
open Turn
→ Agent work
→ observe
→ Reflection
→ Closure
```

真实外部 Agent 是跨进程：

```text
Process A opens Task/Turn
→ external Agent/Host works
→ Process B/C must ingest/recover the same execution
```

如果执行事件没有持久化和 replay：

```text
Framework 不知道实际发生了什么
无法验证顺序和 identity
无法判断 replay/tamper
进程重启后无法可靠恢复执行状态
后续 Obligation/Evidence/Closure 都没有可信输入
```

所以 Phase 1 是整个执行监管闭环的底座。

测试意义不是“能不能写 JSON”，而是证明：

> **同一个 governed execution 可以跨进程恢复为同一个有序、完整性绑定的执行历史。**

---

# 9. Phase 1 只允许做什么

允许：

```text
append-only durable execution event store
Task/Turn/Agent/Project/Runtime identity binding
sequence/hash integrity
idempotent duplicate replay
cross-process reopen / replay cursor
corrupt-state fail closed
bounded Host-neutral persistence
local performance measurement
```

暂不允许：

```text
Phase 2 Obligation Ledger evaluation
Phase 3 External Agent Bridge
Phase 4 Claim/Evidence/Completion evaluator
Phase 5 Reflection/Knowledge/Context/Closure integration
ATP/eTimer 业务
Tool Gateway enforcement
```

完整验收场景和负向测试见：

```text
20260829_EXECUTION_SUPERVISOR_PHASE1_CODEX_HANDOFF_V0_1.md
```

---

# 10. 分支模型

```text
main
= 公共 Harness 唯一上游

feat/<public-capability>
= 从最新 local-mechanically-accepted main 创建的单阶段公共能力分支

project/<name>
= main + 真实项目 + Project Plugin / A/R/K/G / Project Knowledge

pilot/<name>
= 真实 Pilot 编排和证据
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

# 11. 开发效率冻结原则

```text
one conversation = one phase
one phase = one responsibility
one phase = one clean branch
focused unit tests during iteration
package/integration tests at checkpoints
full local public baseline only at phase completion
no LLM/network/full reroute on event hot path
```

禁止再次发生：

```text
上一阶段未机械验证
→ 并行开发下一阶段
→ 多套 contract vocabulary 同时进入 main
→ 最后靠聊天判断哪个是真的
```

效率来自更快、更局部的机械反馈，不来自减少 Evidence 或跳过负向测试。

---

# 12. 历史 ATP Test Charter 的使用方式

Codex 如果需要理解“为什么我们这么严格区分测试层”，可以只读方式查看：

```bash
git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md

git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
```

历史 Charter 的重要方法论继续沿用：

```text
冻结真实目的
冻结被测对象
冻结分支/输入
不同层 PASS 不互相冒充
失败时修负责层，不弱化测试
Agent 自述不能替代机械 Evidence
```

但 Codex 本地开发不是 ATP current-ChatGPT Pilot 本身。

---

# 13. 总冻结原则

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

以及 Local Codex 开发新增不变量：

> **Codex 可以让开发更快，但必须从最新 canonical main 开始、一个对话只完成一个阶段，并用 exact local mechanical evidence 证明完成，而不是用 Agent 自述或旧分支代码证明完成。**
