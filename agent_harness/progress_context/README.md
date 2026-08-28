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

## 新聊天恢复顺序

继续 Harness 开发前，按顺序阅读：

1. 本 `README.md`；
2. `20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md`（涉及 ATP 真实 Agent 测试时必须）；
3. `20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml`（机器可读冻结合同）；
4. `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`；
5. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`；
6. `20260826_HARNESS_CURRENT_STATE.md`；
7. `20260826_TEST_STRATEGY_AND_RESULTS.md`；
8. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`；
9. `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`；
10. `20260826_P0_P1_HARDENING.md`。

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
```

同步方向固定：

```text
main
  ↓ merge
project/<name>
```

项目分支不得整体反向合入 `main`。

## 当前最新 Handoff

### `20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md`

记录：

- 从 `abba-labs/et-tool` 提取公共 Harness 的来源基线与 SHA-256 校验；
- `main` 和 `project/<name>` 的长期分支边界；
- ET-TOOL Project Plugin、项目 Pilot 与项目型验证如何从公共 main 候选分离；
- 新仓库公共 package / synthetic-project CI 的职责；
- 为什么当前迁移保存的是可校验快照和明确 provenance，而不是逐提交过滤历史；
- 下一步如何建立 `project/automated-testing-platform`。

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

这些功能由原仓库完成正向、负向和真实任务矩阵验证。迁移到独立仓库后，`main` 还必须通过自己的 Harness-only boundary、公共 package 和 synthetic-project 集成门禁。

## 项目分支状态

```text
project/et-tool
status: STAGING
```

该分支当前用于保留从原始 Harness 快照中分离出的 ET-TOOL Project Plugin 和项目型 Harness 材料，尚未导入完整 ET-TOOL 产品代码，不能视为已完成项目迁移。

```text
project/automated-testing-platform
status: CREATED / ATP PROJECT CODE IMPORTED
```

ATP Project Plugin、基础 A/R/K/G 接入和真实 Agent Pilot 必须在独立 test / pilot 分支验证，再按证据决定是否合入长期项目分支。真实 Agent Pilot 必须遵守本 README 顶部列出的冻结 Test Charter。

## 执行原则

- 以 `et-harness/main` 为公共 Harness canonical 分支；
- 公共 Harness 变更先进入 `main`，再由项目分支合并；
- 项目业务代码、项目私有规则和 Project Knowledge 不得进入 `main`；
- 只继续最新 Handoff 明确留下的真实问题；
- 不重新推翻已经通过正向、负向和真实任务矩阵验证的架构；
- 结论必须来自代码、Runtime state、Evidence、Closure Receipt、CI marker 和精确 Run / HEAD，不能来自 Agent 自述；
- 真实项目必须通过对应 Project Plugin 接入公共 Runtime；
- 不能直接改项目后再事后补治理报告；
- 迁移完成前不删除原仓库中的旧 Harness 实现；
- ATP 真实项目的当前 GPT 测试必须使用 External Chat Agent Bridge，不得替换为 Copilot 或其他 Provider；
- GitHub Actions 可以运行 Harness 和确定性校验，但不得调用其他模型冒充当前 ChatGPT 对话；
- 当前 ChatGPT 宿主中的 GitHub / Drive 连接器访问只可作为语义治理层证据，不能冒充 Tool Gateway 机械拦截证据。

## 冻结原则

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

Framework 决定流程何时必须发生，Agent 提供需要智能判断的语义结论。不要回退成：

- 让 Agent 自己决定是否治理；
- 让 Host 重新实现 Governance business logic；
- 只允许正式路由 `VALIDATED` Knowledge、隐藏 CANDIDATE；
- 自动提升所有 Knowledge Candidate；
- 每轮或每次 Tool Error 强制产生 Knowledge；
- 暴露 raw shell / filesystem / J-Link 后期待 Agent 自觉 preflight；
- 把项目业务规则硬编码进 Public Governance Engine；
- 为追求理论完备引入当前没有真实收益的零信任复杂度；
- 让一个项目分支的私有改动长期成为公共 Harness fork；
- 为追求自动化方便而替换 Test Charter 中被冻结的 Agent 或测试对象。

## 后续文档命名

推荐继续使用：

```text
YYYYMMDD_HARNESS_CURRENT_STATE.md
YYYYMMDD_TEST_STRATEGY_AND_RESULTS.md
YYYYMMDD_<PHASE>_HANDOFF.md
```

阶段完成时新增文件，不覆盖历史。旧结论被新证据推翻时，必须在新文件中明确写出原因和替代结论。
