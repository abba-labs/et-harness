# Agent Harness Progress Context Archive

本目录长期保存 **ET Harness / Agent Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent 或新聊天快速恢复公共 Harness 工程上下文的 Handoff Archive。

## ATP 真实项目测试硬冻结（必须先读）

任何涉及以下目标的工作：

```text
当前 ChatGPT 对话 / GPT-5.6 Pro
→ ET Harness
→ Automated Testing Platform
→ 真实项目任务
```

必须首先完整阅读并遵守：

```text
20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md
20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml
```

两份文件共同冻结：

- 测试的唯一目的；
- 被测 Agent 必须是当前 ChatGPT 对话中的 GPT-5.6 Pro；
- External Chat Agent Bridge 的数据传输边界；
- ATP 项目、A/R/K/G、Task Context、Evidence、Reflection、Closure 的完整链路；
- Google Drive 作为外部只读资料源的边界；
- 语义治理与机械 Tool Gateway 治理必须分层声明；
- 禁止使用 Copilot、其他 Provider 或 CI 内置模型替代当前 GPT；
- 首个真实任务的原始输入及禁止人工提示项；
- PASS / FAIL 和证据要求。

未经用户明确批准，不得更换 Agent、Provider、测试对象、传输方式或验收口径，也不得因为另一条路线更容易自动化而重新解释测试目的。

## 执行监管与闭环设计基线（必须读）

完成冻结 Charter 后，必须立即阅读：

```text
agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md
```

该文档冻结下一阶段的公共框架方向：

- 当前真实缺口不是 eTimer 文档质量，而是外部 Agent 执行过程没有完整进入公共 Runtime；
- 必须新增 Public Execution Supervisor、Obligation Ledger、执行事件/回执合同和跨进程重放；
- 它是 Governance Runtime 的必需执行监管能力，不是第二套 Kernel、第二套 Context 或新 Agent；
- Project Plugin 只提供结构化义务、Evidence Policy 和成功条件；
- Host Adapter 只回传实际事件；
- Public Supervisor 负责义务状态、违规、Evidence 和 Completion；
- Kernel / Managers 继续负责 Reflection、Knowledge、Context 和 8/8 Closure；
- 必须同时满足可靠性、通用性和效率，不允许每个事件全量重路由或调用模型；
- 文档定义了分阶段实施、负向测试、效率测试和 ATP 最终复测标准。

后续开发不得绕过该文档，直接继续堆 Mailbox、Workflow 或 eTimer 产物。

## 当前事实纠正与历史 Handoff（必须读）

随后阅读：

```text
20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
```

该文件记录此前阶段的 exact Git HEAD、CI Run、Artifact、Route Receipt、失败实验和错误 PASS 纠正。它是历史机械事实，不得删除或覆盖。

其部分“当前状态”已被后续实现更新；最新执行方向和当前缺口以：

```text
25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md
+ 最新代码 / Run / Receipt
```

为准。

## 新聊天恢复顺序

继续 Harness 开发前，按顺序阅读：

1. 本 `README.md`；
2. `20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md`；
3. `20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml`；
4. `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`；
5. `20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md`；
6. `agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`；
7. `agent_harness/design/21_PUBLIC_AGENT_GOVERNANCE_KERNEL_V0_1.md`；
8. `agent_harness/design/20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md`；
9. `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`；
10. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`；
11. `20260826_HARNESS_CURRENT_STATE.md`；
12. `20260826_TEST_STRATEGY_AND_RESULTS.md`；
13. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`；
14. `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`；
15. `20260826_P0_P1_HARDENING.md`。

## 当前仓库与分支模型

公共 Harness 的长期上游仓库为：

```text
repo: abba-labs/et-harness
branch: main
```

分支职责：

```text
main
= 公共 Harness 唯一上游

project/<name>
= main 公共 Harness
  + 一个真实项目的完整代码
  + 该项目 Project Plugin / Architecture / Rules / Knowledge / Gates

pilot/<name>
= 只保存真实 Pilot 编排、请求/响应和验证证据
```

同步方向固定：

```text
main
  ↓ merge
project/<name>
  ↓ clean branch
pilot/<name>
```

项目分支不得整体反向合入 `main`；Pilot 分支也不得整体合入 `main`。

## 当前最新机械状态

截至 2026-08-28 当前 ATP Pilot：

```text
Public generic context.contribute                  PASS
ATP Project Context Contributor                    PASS
ATP Task Context compilation                       PASS
Frozen task Project/A/R/K/G/Scope/Output routing  PASS
Clean Route + Context Gate v0.3                    PASS
Current ChatGPT external work                      PARTIAL / OBSERVED OUTSIDE FULL RUNTIME LOOP
Cross-process Task/Turn rehydration                 PARTIAL IMPLEMENTATION
Host-neutral execution-event ingestion             NOT COMPLETE
Obligation Ledger                                  NOT IMPLEMENTED
Claim/Evidence completion evaluation               NOT IMPLEMENTED
Real-Pilot Unified Reflection                       NOT EXECUTED
Real-Pilot Knowledge forced classification          NOT EXECUTED
Real-Pilot Context/Knowledge/8/8 Closure             NOT EXECUTED
Follow-up Context/Knowledge reuse                   NOT EXECUTED
Overall governed real-project Pilot                FAIL / INCOMPLETE
```

Exact latest clean Route Gate evidence:

```text
branch: pilot/atp-et6801-etimer-current-chatgpt-v0.3
head:   67e3ac1732d00720e6eae22d82718ef7689c4ed1
run:    33164110828
result: success
```

该成功只证明确定性的 Route / Context 前半段，不证明当前 GPT 的完整执行、Evidence、Reflection、Knowledge、Context Closure 和 Task Completion。

当前 `rehydrateTask()` / `rehydrateTurn()` 是根因修复的第一步，但仍需按照 Design 25 完成持久化执行事件、Obligation Ledger、Completion Evaluator 和真实 Closure。

## 当前最重要的开发结论

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

进一步明确为：

```text
Project Plugin
= 提供项目规则、结构化义务、Evidence Policy、成功条件

Host Adapter
= 回传可观察的实际执行事件

Execution Supervisor
= 维护义务、违规、Evidence、完成状态和跨进程重放

Governance Kernel / Managers
= 强制 Reflection、分类、Context/Knowledge/8/8 Closure

Agent
= 执行业务任务和提供语义判断，不自证 PASS/Closure
```

## 当前实现顺序

必须按以下顺序推进：

```text
1. 从 main 创建公共 Execution Supervisor feature branch
2. 冻结通用事件、义务、Evidence、Completion 合同
3. 实现持久化 Event Store 和跨进程重放
4. 实现 Obligation Ledger 和负向测试
5. 实现 External Agent Response/Event ingestion
6. 接入 Claim/Evidence/Completion Evaluator
7. 接回 Unified Reflection、Knowledge、Context 和 8/8 Closure
8. 完成通用性矩阵和效率基线/回归门禁
9. 合入 main
10. main → project/automated-testing-platform
11. ATP Context Contributor 输出结构化 supervision contract
12. 从干净项目分支重建 current-ChatGPT Pilot
13. 运行冻结 eTimer 任务和第二 Turn 复用测试
14. 完整闭环通过后，再审阅两份 eTimer 文档质量
```

不得倒序先增加更多 eTimer 业务提示、人工 Rule ID、临时 Workflow 或自述式 PASS。

## 历史 Handoff

### `20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md`

记录：

- 公共 `context.contribute` 初始范围；
- ATP data-only Project Plugin 的历史状态；
- 旧 Context Contributor feature 为什么失败；
- 冻结 Route、Mailbox、Response、Verify 的历史失败结果；
- 错误乐观 PASS 的纠正；
- 干净 Provider 分支策略。

后续 Provider 已按该 Handoff 的干净路线实现并验证，但该文件仍保留为失败根因和过程证据。

### `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`

记录：

- 从 `abba-labs/et-tool` 提取公共 Harness 的来源基线与 SHA-256 校验；
- `main` 和 `project/<name>` 的长期分支边界；
- ET-TOOL Project Plugin、项目 Pilot 与公共 main 的分离；
- 新仓库公共 package / synthetic-project CI 的职责；
- 可校验快照和 provenance；
- Automated Testing Platform 项目分支的建立。

## 来源功能基线

迁移来源：

```text
source repo: abba-labs/et-tool
source branch: main
source repository HEAD:
496243ef2bdf56a5db7f81b2014970d3f8af34f9

last fully validated Harness code baseline:
f37b1080ca65388fc0e32f7fa75567b512c86752
```

迁移完成前，`abba-labs/et-tool` 保持为回滚与历史追溯源。新仓库通过 `MIGRATION_SOURCE.json` 保存来源、快照校验和与分离提交。

## 已验证的主要公共功能阶段

历史功能阶段：

```text
PR #37 -> P0/P1 Harness hardening
PR #38 -> Real Task Matrix and minimal hardening
PR #39 -> Public Layer knowledge policy smoke alignment
PR #40 -> Tiered Knowledge retrieval and Evidence feedback
```

这些功能由原仓库完成正向、负向和真实任务矩阵验证。迁移到独立仓库后，`main` 仍必须通过自己的 Harness-only boundary、公共 package 和 synthetic-project 集成门禁。

## 执行原则

- 以 `et-harness/main` 为公共 Harness canonical 分支；
- 公共 Harness 变更先进入 `main`，再由项目分支合并；
- 项目业务代码、项目私有规则和 Project Knowledge 不得进入 `main`；
- 只继续最新设计基线明确留下的真实问题；
- 不重新推翻已经通过正向、负向和真实任务矩阵验证的 Manager / Kernel 架构；
- 结论必须来自代码、Runtime state、Execution Receipt、Evidence、Closure Receipt、CI marker 和精确 Run / HEAD，不能来自 Agent 自述；
- 真实项目必须通过对应 Project Plugin 接入公共 Runtime；
- 不能直接改项目后再事后补治理报告；
- 当前 GPT 测试必须使用 External Chat Agent Bridge，不得替换为 Copilot 或其他 Provider；
- GitHub Actions 可以运行 Harness 和确定性校验，但不得调用其他模型冒充当前 ChatGPT；
- 当前 ChatGPT 宿主中的 GitHub / Drive 连接器访问只能声明 `AUDIT` 语义治理，不能冒充 Tool Gateway `ENFORCE`；
- 没有真实执行的验证不得记录为 PASS；
- Route PASS、文档存在或 Agent 自述均不能替代完整 Execution/Reflection/Closure PASS；
- 上游阶段失败后，下游必须记录 `NOT_EXECUTED` 或 `BLOCKED_BY_DEPENDENCY`。

## 冻结原则

不要回退成：

- 让 Agent 自己决定是否治理；
- 让 Host 重新实现 Governance business logic；
- 让 Project Plugin 实现公共 Agent Lifecycle；
- 每个工具事件都全量重路由、重建 Context 或调用模型；
- 把 Efficiency Observer 变成任务必需依赖；
- 自动提升所有 Knowledge Candidate；
- 每轮强制产生知识而不允许 `NONE`；
- 暴露工具后期待 Agent 自觉 preflight；
- 把项目业务规则硬编码进 Public Supervisor；
- 为自动化方便替换 Test Charter 中被冻结的 Agent；
- 用 generated `dist`、临时 Workflow 或 Agent 自述代替真实 Source、Receipt 和 Closure；
- 在 Route / Context Gate 未通过前启动 Agent 执行；
- 在 Execution / Obligation / Reflection / Closure 未通过时宣告整个 Pilot PASS。

## 后续文档命名

推荐继续使用：

```text
agent_harness/design/NN_<PUBLIC_CAPABILITY>_V0_1.md
agent_harness/progress_context/YYYYMMDD_<PHASE>_HANDOFF.md
```

阶段完成时新增 Handoff，不覆盖历史。旧结论被新机械证据推翻时，必须在新文件中明确写出原因和替代结论。
