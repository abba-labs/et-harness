# Agent Harness Progress Context Archive

本目录长期保存 **Agent Harness / ET-TOOL Governance** 的阶段进度、测试事实、失败根因、冻结决策和下一阶段入口。

它不是 Architecture / Rule / Knowledge / Gate 的替代品，而是供后续 Agent 或新聊天快速恢复工程上下文的 Handoff Archive。

## 新聊天恢复顺序

继续 Harness 开发前，按顺序阅读：

1. 本 `README.md`；
2. `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`；
3. `20260826_HARNESS_CURRENT_STATE.md`；
4. `20260826_TEST_STRATEGY_AND_RESULTS.md`；
5. `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`；
6. `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`；
7. `20260826_P0_P1_HARDENING.md`。

执行原则：

- 以 `main` 为 canonical 分支；
- 区分“当前仓库 HEAD”和“最后完成完整 Harness 回归的功能代码提交”；
- 只继续最新 Handoff 明确留下的真实问题；
- 不重新推翻已经通过正向、负向和真实任务矩阵验证的架构；
- 结论必须来自代码、Runtime state、Evidence、Closure Receipt、CI marker 和 Run 结果，不能来自 Agent 自述；
- 外部项目必须先接入对应 Project Plugin，不能直接改外部仓库后宣称公共插件已完成治理。

## 当前最新 Handoff

### `20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md`

记录：

- 从负向治理审查到 P0/P1、真实任务矩阵、Public Layer、分级 Knowledge 的完整阶段总结；
- 当前公共插件真正测试到的能力和不能证明的边界；
- `project-et-tool` 在线对话 Pilot PR #42 的实验结果与效率问题；
- 对 `Automated_Testing_Platform` PR #36 的方法纠错：直接 GitHub 修改没有经过 Project Plugin，不能计入公共插件验收；
- 下一阶段对 `Automated_Testing_Platform` 的只读分析、最小 Project Plugin 设计和跨项目测试路线。

## 当前 canonical 状态

```text
repo: abba-labs/et-tool
branch: main
last fully validated Harness code baseline: f37b1080ca65388fc0e32f7fa75567b512c86752
```

`f37b1080...` 之后当前新增的提交只更新了 `agent_harness/progress_context/` Handoff 文档，没有 Harness 生产代码变更。新对话应读取实时 `main` HEAD，但评估功能回归时以 `f37b1080...` 为最近完整验证基线。

已合入的主要功能阶段：

```text
PR #37 -> P0/P1 Harness hardening
PR #38 -> Real Task Matrix and minimal hardening
PR #39 -> Public Layer knowledge policy smoke alignment
PR #40 -> Tiered Knowledge retrieval and Evidence feedback
```

## 当前非 canonical 实验

```text
PR #42
branch: pilot/dialogue-real-project-code-fix-v0.1
purpose: project-et-tool 在线对话真实代码治理 Pilot
status: OPEN / DRAFT / NOT MERGED
```

```text
Automated_Testing_Platform PR #36
purpose: 直接 GitHub 改码样本
status: OPEN / DRAFT / NOT MERGED
classification: 不经过 Project Plugin，不计入公共插件验收
```

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
- 直接调用外部 GitHub 写工具后再事后补一份治理报告。

## 后续文档命名

推荐继续使用：

```text
YYYYMMDD_HARNESS_CURRENT_STATE.md
YYYYMMDD_TEST_STRATEGY_AND_RESULTS.md
YYYYMMDD_<PHASE>_HANDOFF.md
```

阶段完成时新增文件，不覆盖历史。旧结论被新证据推翻时，必须在新文件中明确写出原因和替代结论。
