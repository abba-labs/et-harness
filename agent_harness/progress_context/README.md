# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent、Codex 或新聊天快速恢复公共 Harness 工程上下文的 **Handoff Archive**。

---

# 1. 当前最高优先级恢复入口

从 2026-09-02 起，任何接手当前 ET Harness / ATP 工作的新聊天、Agent 或 Codex，优先按下面顺序读取：

1. `20260902_GOVERNANCE_BEHAVIORAL_VALIDATION_AND_PROJECT_ADMISSION_HANDOFF_V0_1.md`
2. `../../AGENTS.md`（仓库根目录 `AGENTS.md`）
3. `../test_campaigns/governance_behavioral_validation_v1/GOVERNANCE_BEHAVIORAL_VALIDATION_REQUIREMENT.md`
4. `../test_campaigns/governance_behavioral_validation_v1/evidence/FINAL_REPORT.md`
5. `../test_campaigns/governance_behavioral_validation_v1/evidence/08_defect_backlog.md`
6. `../test_campaigns/round3_p0_repair/evidence/ROUND3_P0_FINAL_REPORT.md`
7. `20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md`
8. `20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md`（需要继续真实 ATP IP 生产任务时）

当前事实优先级：

```text
当前分支实际源码 / exact Git SHA / 真实机械 Evidence
> 20260902 Current Handoff
> 当前 Test Campaign Requirement + Evidence
> Frozen Charter / Design
> 历史 Handoff / Audit
> Agent 自述或聊天记忆
```

如果历史文档与 `20260902_GOVERNANCE_BEHAVIORAL_VALIDATION_AND_PROJECT_ADMISSION_HANDOFF_V0_1.md` 冲突，当前工作以 **2026-09-02 Handoff + 当前源码/Evidence** 为准。

---

# 2. 当前两个必须区分的基线

## 2.1 已验证稳定行为基线

```text
repo: abba-labs/et-harness
branch: codex/fast-track-pure-mcp-atp-v0.1
SHA: 8cb771f6f3221501dc2ad6aea1785a6e959ae65e
```

该基线包含 Governance Behavioral Validation V1 Evidence，当前固定 D-drive Environment / external Gateway 不应被普通开发随意扰动。

## 2.2 待独立验证的 Architecture 调整

```text
branch: architecture/project-admission-bootstrap-v0.1
framework implementation baseline: 67676a2916b01316794da042a813d0c338d14182
```

该分支增加最小的：

```text
Human explicit Project
→ Project Admission
→ Architecture Bootstrap when context missing/stale
→ Agent bounded TaskIntent
→ original governed Runtime flow
```

它尚未激活到稳定 D-drive Runtime；不要把它当成已经通过真实环境验收的稳定基线。

---

# 3. 当前一句话状态

> **ET Harness 的固定环境、Pure MCP 主链、Supervisor / Ledger / Trusted Evidence 已经相对稳定；当前工作已经从“链路能否跑通”进入“每个治理模块是否在正确时间做正确事情”的行为验证阶段。Governance Behavioral Validation V1 找到了任务入口语义、跨任务 Context、Closure retry、Knowledge/Experience 与可观测性问题；Architecture Owner 已在隔离分支完成 Project Admission + Architecture Bootstrap 最小实现，下一步先独立验证，不直接继续扩框架。**

---

# 4. 不可违反的当前开发原则

```text
可靠 > 稳定 > 轻量化 > 易扩展
```

必须继续遵守：

- Agent 不负责治理自己；Framework 负责治理 Agent。
- Agent 负责语义理解；Framework / Project Plugin 负责确定性验证与治理。
- Agent 不能自报 PASS，也不能制造 trusted Evidence。
- Pure MCP 继续 truthful `AUDIT`，不伪装 universal Host interception。
- MCP `required=false`；Gateway 继续作为 Codex 外部独立进程。
- 不回到 Plugin / Hook / Marketplace 主路线。
- 不新增第二 Runtime / Ledger / Event Store / Closure / Context Store / Knowledge Store。
- 不新增 watcher / polling daemon / Windows Service / custom fs-shell MCP。
- 已稳定 D-drive environment 不因普通代码调整反复安装、重建、刷新。
- 一个根因一个 repair campaign；不要把多个 FAIL 一次性大改。
- Observability 缺口用现有 owner 的 bounded receipt/trace 解决，不另造监管运行时。

---

# 5. 当前测试结论

## Round 3 P0

核心执行闭环已经得到强证据，包括：

```text
WRITE_SCOPE
Required Read
Trusted Validation
Supervisor
Obligation Ledger
Event Store
Premature Complete block
Reflection / Context Update / Closure
Gateway restart / active Turn rehydrate
```

## Governance Behavioral Validation V1

```text
Overall: BEHAVIORAL_VALIDATION_FAIL
PASS: 19
FAIL: 7
OBSERVABILITY_GAP: 11
```

不要把 7 FAIL 机械当成 7 个独立 Framework Bug。Architecture Reviewer 已归并为主要根边界：

```text
P0  Task Bootstrap / ATP Classification / Contributor Contract
P0  Cross-task Context Continuity
P0  Closure Atomicity / Retry
RETEST Knowledge later-consumption（当前被上游 bootstrap 阻断）
ARCH DECISION Knowledge Observation trusted trigger
P1  Evidence → Experience → Later Task
P1  Governance Decision Observability
```

完整解释见当前 20260902 Handoff。

---

# 6. 当前下一阶段

第一阶段只验证：

```text
architecture/project-admission-bootstrap-v0.1
```

Codex 作为 Test Executor：

```text
只测试
只保存 Evidence
发现 first failing boundary
不修改 Framework
不触碰稳定 D-drive environment
不自行宣布 Architecture PASS
```

Project Admission 独立验证通过后，由 Architecture Owner 决定是否按：

```text
clean commit
→ freeze-runtime
→ verify-environment
→ controlled Gateway refresh
→ real black-box
```

进行受控激活。

随后再分别处理 Closure atomicity、cross-task Context 等剩余问题。

---

# 7. 历史文档的使用方式

本目录中的旧文档继续保留历史 Evidence 和设计演进，不删除。

典型历史入口：

```text
20260826_HARNESS_CURRENT_STATE.md
20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md
20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md
20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md
20260829_EXECUTION_SUPERVISOR_*_HANDOFF_V0_1.md
20260830_EXECUTION_SUPERVISOR_PHASE7_*_HANDOFF_V0_1.md
20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md
```

这些文件回答“当时为什么这样设计/测试”；当前下一步以最新 Handoff 为准。

---

# 8. 总冻结原则

> **Agent 可以更换，模型可以更换，Host 可以更换；项目 Architecture、Rules、Knowledge、Context、Evidence 和 Governance 不能依附于某一个 Agent。**

以及：

> **Framework 要保证该发生的治理步骤不能被 Agent 跳过，但不要把开放自然语言理解全部写成 if/else/regex；语义理解由 Agent 完成，Framework 验证结构化结果并执行确定性治理。**
