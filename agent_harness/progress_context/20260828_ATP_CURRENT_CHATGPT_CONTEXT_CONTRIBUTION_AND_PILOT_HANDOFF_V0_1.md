# ATP Current ChatGPT Context Contribution 与真实项目 Pilot 总结及交接 v0.1

> 文档性质：当前事实总表 / 失败根因分析 / 下一阶段强约束 Handoff  
> 记录日期：2026-08-28  
> 仓库：`abba-labs/et-harness`  
> 当前记录分支：`pilot/atp-et6801-etimer-current-chatgpt-v0.1`  
> 适用范围：公共 ET Harness、ATP Project Plugin、`context.contribute`、当前 ChatGPT External Agent Pilot  
> 结论优先级：**代码、Git HEAD、CI Run、Artifact、Receipt > 文档叙述 > Agent 自述**

---

## 0. 先看结论：当前真实状态是什么

本轮已经解决的是：

1. 公共 Harness 已经有一个通用、可选、项目隔离的 `context.contribute` 能力；
2. 没有把 ATP、ET6801、eTimer 或 `compile_task_context.py` 硬编码进公共 Harness；
3. 没有增加第五类公共项目资源，也没有新建第二套公共 Task Context 系统；
4. 公共 `main` 的仓库边界、公共包构建与测试、synthetic-project 集成门禁全部通过；
5. ATP 原有的 data-only Project Plugin 能识别 ATP 项目并加载 A/R/K/G 资源；
6. 冻结原始任务能够自动解析到 ATP 项目，并路由到一部分 IP Analysis Architecture / Rule 投影。

本轮**没有解决**的是：

1. ATP 项目级 Context Contributor 的真实源码没有进入有效分支；
2. ATP `project.yaml` 仍然是 `adapters: {}`；
3. ATP Project Plugin 没有注册 `context.contribute` Provider；
4. 冻结 Pilot 没有调用 ATP 的 `tools/governance/compile_task_context.py`；
5. 冻结 Pilot 的 Knowledge / Gate 路由为空；
6. `must_read`、`rule_owners`、完整 `write_scope`、Validation 与 Output Contract 没有进入 Pilot Context Pack；
7. External Chat Agent Mailbox 请求没有创建；
8. 当前 ChatGPT 对话没有被 Harness 机械调用或完成一次可验证的真实任务闭环；
9. `test_case_doc/etimer/etimer.md` 与 `test_case_doc/etimer/ET6801_etimer.md` 没有由本轮 Pilot 生成；
10. Google Drive 外部资料没有形成文件级、可回放的 Harness Evidence Receipt；
11. Keil、J-Link、FPGA、SIL、HIL、仪器及真实硬件均未执行。

因此当前总状态必须写成：

```text
Public generic context.contribute        PASS
ATP data-only Project Plugin             PASS
ATP project Context Contributor source   FAIL / NOT IMPLEMENTED ON BRANCH
Frozen task project resolution           PASS
Frozen task partial A/R routing          PASS
Frozen task compiled Task Context        FAIL
Frozen task K/G routing                  FAIL
External Chat mailbox dispatch           FAIL / NOT CREATED
Current ChatGPT Agent invocation          NOT EXECUTED
eTimer analysis artifacts                NOT CREATED
External source Evidence closure          NOT IMPLEMENTED
Hardware validation                       NOT EXECUTED
Overall real-project Pilot                FAIL / INCOMPLETE
```

### 0.1 对此前乐观结论的纠正

此前对话中曾出现“ATP Context Contributor 已完成”“冻结路由已通过”“Mailbox 已真正运行”“当前 GPT 已返回结构化 Response”等口头结论。最新代码和 CI 证据不支持这些说法。

本文件以以下机械事实替代此前口头判断：

- ATP Context Contributor feature branch 中不存在 `src/context-contributor.ts`；
- `src/index.ts` 仍只注册 Project；
- `project.yaml` 仍为 `adapters: {}`；
- ATP Project Plugin 构建报 `TS2307 Cannot find module '../src/context-contributor.js'`；
- 冻结 Route Receipt 明确记录 `pass: false`；
- `contextContributions` 不存在；
- `projectTaskContextCompiled: false`；
- `externalChatAgentInvoked: false`；
- Mailbox request / response 文件均不存在；
- 后续 respond / verify 工作流均因 `request.json` 不存在而失败。

后续 Agent 不得再次使用此前乐观叙述作为事实基础。

---

## 1. 新对话必须按什么顺序恢复上下文

本文件不是重新定义需求，而是把已有需求、架构决策、实现状态和机械证据串起来。

### 1.1 必须先读的冻结需求

涉及“当前 ChatGPT 对话作为被测 Agent，经过 ET Harness 执行 ATP 真实任务”时，必须先完整阅读：

```text
agent_harness/progress_context/
  20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md
  20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml
```

这两份文件冻结了：

- 被测 Agent 的身份；
- 唯一原始任务；
- 禁止人工提示和业务硬编码；
- Project / A/R/K/G / Task Context / Evidence / Reflection / Closure 链路；
- External Chat Agent Bridge 的职责；
- Google Drive 只读资料边界；
- 软件、硬件与机械 Tool Gateway 证据的分层；
- PASS / FAIL 的验收标准。

### 1.2 然后读本文件

```text
agent_harness/progress_context/
  20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
```

本文件回答：

- 当前究竟完成了什么；
- 哪些只是尝试而没有成功；
- 走了哪些弯路；
- 哪些结论可以被证明；
- 现在真实阻断在哪里；
- 下一步必须按什么顺序做。

### 1.3 再读公共框架和项目接入背景

```text
agent_harness/design/records/00_INDEX.md
agent_harness/progress_context/20260826_HARNESS_CURRENT_STATE.md
agent_harness/progress_context/20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md
agent_harness/progress_context/20260827_ET_HARNESS_REPOSITORY_MIGRATION_HANDOFF.md
```

其中：

- Design Records 是设计决定的 Source of Truth；
- Current State 说明 Harness 是治理基础设施，不是 ATP 业务平台；
- 20260827 Handoff 说明 ATP 最初以 data-only Project Plugin 接入；
- Migration Handoff 说明 `main` 与 `project/<name>` 的单向同步边界。

### 1.4 不得重新讨论或推翻的已冻结原则

除非新机械证据证明已有设计不可行，否则不要重新开启以下讨论：

1. 公共 Harness 只理解通用合同，不理解 ATP 业务；
2. ATP 项目规则和项目事实继续由 ATP 拥有；
3. 项目差异通过 Project Plugin / Adapter / Provider 接入；
4. A/R/K/G 是四类公共资源，不增加第五类“Task Context Resource”；
5. 项目 Task Context 是项目编译结果，通过 Context Contribution 注入；
6. Agent 不负责决定是否治理；Framework 决定治理流程；
7. GitHub Actions 不能冒充当前 ChatGPT 对话；
8. 没有执行的验证不得记录为 PASS；
9. 外部资料被“搜到”不等于形成了可审计 Evidence；
10. 项目分支不得整体反向合入公共 `main`。

---

## 2. 我们最初真正想解决什么问题

### 2.1 产品级目标

我们要构建的不是某一个 Agent 的记忆插件，也不是只服务 Codex、Claude Code、DeepSeek 或 ChatGPT 的 Prompt 集合。

目标是建立一套独立于具体 Agent、模型和 Harness 的项目治理能力：

```text
项目规则体系
项目知识体系
项目上下文编译体系
项目证据与状态体系
项目验证与闭环体系

通过标准插件 / Provider 合同
接入任意 Harness、任意 Agent、任意模型
```

今天可以接入 Codex，明天可以接入 Claude Code、DeepSeek Harness、ChatGPT 或其他 Host，而无需迁移项目规则和项目知识的所有权。

### 2.2 Agent 实际工作时的理想链路

用户只给真实任务：

```text
分析6801芯片etimer这个IP。
```

Framework 应自动完成：

```text
原始任务
  ↓
识别 Project
  ↓
A/R/K/G 初始路由
  ↓
发现项目声明了 context.contribute Provider
  ↓
项目 Provider 解析 module / change / chip / ip
  ↓
调用项目原有 Task Context Compiler
  ↓
获得 must_read / rule_owners / scope / validation / output contract
  ↓
把结果注入公共 Context Pack
  ↓
当前 ChatGPT 读取代码与允许的外部资料
  ↓
生成项目合同要求的产物
  ↓
执行允许且必要的软件验证
  ↓
记录 Source Disposition / Evidence / Reflection
  ↓
Framework 决定 PASS、BLOCK 或继续
```

Agent 不应该：

- 盲目扫描整个仓库；
- 自己猜目录、规则和写入范围；
- 因为熟悉 eTimer 而绕过项目规则；
- 自己决定是否需要治理；
- 自己宣布已经通过；
- 把没读到的外部资料写成已验证事实。

### 2.3 为什么首个真实任务选 eTimer

它不是为了证明模型会解释定时器，而是为了验证一个跨资源、跨资料源、跨项目合同的真实任务：

- 需要识别 ATP 项目；
- 需要识别 `module=ip-package`、`change=analysis`；
- 需要解析 `chip=et6801`、`ip=etimer`；
- 需要读取项目 Rule Owner；
- 需要读取 SDK Driver、SVD、需求、验证和历史测试资料；
- 需要区分公共 IP 语义与 ET6801 芯片事实；
- 需要生成公共文档和芯片适配文档；
- 需要保存未知项、冲突和证据状态；
- 需要证明 Harness 在复杂项目中能约束强模型，而不是给强模型一段超长 Prompt。

### 2.4 这次测试明确不是什么

本轮不是：

- 调一个 OpenAI API 模型做任务；
- 用 Copilot、Codex 或其他 Provider 代替当前 ChatGPT；
- 只做一轮 A/R/K/G 搜索演示；
- 只证明 `compile_task_context.py` 能独立运行；
- 只生成一份看起来合理的 eTimer 报告；
- 由 Agent 自己写自评报告；
- 在没有硬件时伪造 Hardware PASS；
- 把 ATP Task Context 逻辑搬进公共 Harness。

---

## 3. 正确的所有权和架构边界

### 3.1 公共 Harness 拥有什么

公共 `main` 应只拥有：

- Project 识别合同；
- Architecture / Rule / Knowledge / Gate 公共资源合同；
- 通用关系展开与路由；
- Context 生命周期与 Inline Context 承载；
- 通用 `context.contribute` 请求和返回合同；
- Provider 准入、项目隔离、大小预算、路径安全和失败关闭；
- Evidence、Reflection、Closure 的公共机制；
- synthetic-project 测试。

公共 Harness 不应知道：

```text
ATP
ET6801
eTimer
ip-package
compile_task_context.py
test_case_doc/etimer/
R100 / R140 的 ATP 业务含义
Google Drive 中某个 ET6801 文件夹
```

### 3.2 ATP Project Plugin 拥有什么

ATP Project Plugin 应负责：

- 注册 ATP 项目；
- 暴露 ATP 的 A/R/K/G 投影视图；
- 声明 ATP 的 `context.contribute` Adapter；
- 注册项目级 Context Contributor Provider；
- 把公共请求转换成 ATP Task Context Compiler 输入；
- 把 ATP Compiler 输出转换成公共 Contribution 合同；
- 不复制 ATP 活动规则正文；
- 不执行 Build、J-Link、Flash、FPGA 或硬件动作，除非未来另有明确 Adapter。

### 3.3 ATP 项目本体继续拥有什么

ATP 项目继续拥有：

```text
AGENTS.md
project-governance/system-map.yaml
project-governance/modules/*.yaml
project-governance/ip-analysis-sources.yaml
report/design/rule_owner_catalog.yaml
report/design/rules/Rxxx_*.md
tools/governance/compile_task_context.py
源码、测试、test_case_doc 和业务合同
```

### 3.4 Current ChatGPT Host / Transport 应拥有什么

External Chat Host 只应负责：

- 接收 Harness 生成的 Context Pack；
- 把它交给“当前 ChatGPT 对话”；
- 暴露允许的 GitHub / Drive 等工具；
- 收集结构化响应、产物引用和 Source Receipt；
- 把结果交回 Harness。

Host 不应：

- 重新实现 ATP 业务路由；
- 在 Request 里人工塞入 eTimer 文件路径、R140 章节或分析提纲；
- 替换 Agent；
- 根据自己的判断宣布任务闭环。

---

## 4. 本轮实际做了什么

## 4.1 公共 A/R/K/G 关系路由修正

此前公共路由容易表现为四次相互独立的搜索：

```text
Architecture search
Rule search
Knowledge search
Gate search
```

这会导致：

- 搜到 Architecture，但没有跟到它引用的 Rule；
- 搜到 Rule，但没有跟到 Knowledge / Gate；
- 精确关键词不足时，真实关系链不能补全；
- Agent 看到的是散点候选，不是项目导航图。

公共框架随后引入了有界的关系展开：

- 从初始候选出发；
- 沿稳定 `Relations / Refs` 展开；
- 设置深度和每类资源预算；
- 去重并终止循环；
- 保持项目隔离；
- 不加入 ATP 特例。

这解决了“公共路由只做平行搜索”的框架问题，但它仍不能代替 ATP 项目自己的 Task Context 编译。

## 4.2 公共 `context.contribute` 能力

公共 `main` 已合入：

```text
commit: 24d7c209f3731cc3b2acd20c4428d66781f25e2d
message: feat: add optional project context contribution capability
```

它提供：

1. Provider-neutral 请求合同；
2. Provider-neutral Contribution 合同；
3. 项目通过 `project.adapters` 显式声明 Provider；
4. 未声明 Provider 的项目保持原行为；
5. 声明 Provider 但 Provider 不存在时失败关闭；
6. Provider 跨项目时拒绝；
7. 异步 Provider 在 v0.1 中拒绝；
8. A/R/K/G 引用 ID 类型检查；
9. read / write scope 规范化与路径安全检查；
10. Validation Obligation 和 Output Contract 的通用承载；
11. Provider Inline Context 的持久化、重建与 Handoff；
12. 只替换旧的 Provider-owned Inline Context，不覆盖 Host-owned Context；
13. 内容数量和字符预算；
14. 每次路由阶段重新计算 Contribution；
15. Context Contribution Receipt 和 fingerprint。

公共能力的完整 CI 已通过，详见第 7 节。

## 4.3 ATP data-only Project Plugin 基础接入

ATP 长期项目分支已经具备：

- 完整 ATP 项目代码；
- 项目标识和 root discovery；
- Architecture 投影；
- Rule 投影；
- Knowledge Library；
- Gate 投影；
- Project Plugin 基础测试；
- Public Manager 路由测试。

但它当前仍是：

```yaml
adapters: {}
metadata:
  adapter_kind: data-only-project-plugin
```

这意味着它只能让公共 Harness 识别项目和搜索 A/R/K/G，不能自动调用 ATP Task Context Compiler。

## 4.4 增加 IP Analysis 的薄路由投影

Pilot / feature 尝试中增加了 `R020`，用于告诉公共 Rule Manager：

- IP Analysis 必须编译已有 Task Context；
- 编译结果中的 scope / owner / validation 是约束；
- Output Contract 来自 ATP 活动 R100/R110/R120/R130/R140/R410；
- 不得把未执行验证或未知资料写成 PASS。

该投影是正确方向，但仅有投影还不够。当前 Pilot 只路由到 `R020.010`，没有真正执行项目 Compiler，也没有把完整 R020 / Owner 合同注入 Context。

## 4.5 为冻结任务建立 Route Dry-Run

冻结任务始终保持：

```text
分析6801芯片etimer这个IP。
```

Dry-run 机械检查了：

- 原始任务是否被改写；
- ATP 项目是否绑定；
- A/R/K/G 是否非空；
- 是否进入 IP Analysis Architecture；
- 是否出现项目 Context Contribution；
- 是否附加 compiled Task Context；
- 是否解析 chip / ip / module / change；
- 是否包含 Rule Owner、Source Disposition 和 Output Contract；
- 是否调用了模型。

该 Dry-run 的价值是把“看起来路由到了”拆成多个可验证信号。结果是部分通过、总体验收失败。

## 4.6 尝试建立 External Chat Mailbox

后续又尝试：

1. 由 GitHub Actions 生成 Harness Request；
2. 创建 GitHub Issue 作为 Mailbox；
3. 当前 ChatGPT 在 Issue 中回结构化 JSON；
4. 后续 Workflow 验证 Request ID、Agent ID、Response Schema 和 Issue Comment。

但因为前置 Route Receipt 为 FAIL，Request 工作流在创建 Issue 之前停止。后续 respond / verify 又因为 `request.json` 不存在而失败。因此 Mailbox 没有真正运行。

---

## 5. 走过的弯路、为什么错、得到什么教训

| 弯路 | 现象 | 为什么不对 | 正确做法 |
|---|---|---|---|
| 把 A/R/K/G 当四次独立搜索 | Architecture 有结果，Knowledge / Gate 经常为空 | 没有利用资源之间的稳定关系 | 公共层做有界关系展开 |
| 试图让公共 Harness 理解 ATP Task Context | 容易想新增 TaskContextManager 或 ATP 路由逻辑 | 破坏通用性，形成第二套项目规则 | 公共层只提供 `context.contribute`，ATP 自己编译 |
| 先写 Workflow 和测试，再补真实源码 | feature 分支里有测试和 dist，却没有 `src/context-contributor.ts` | 测试目标不存在，生成物制造“像实现过”的假象 | 先完成最小源代码，再写聚焦测试 |
| 用临时 apply/finalize/correct 工作流反复修改分支 | 多个 workflow run 失败，分支堆积临时脚本和生成物 | 变更链难追踪，失败时很难知道哪个状态有效 | 在干净 feature branch 做正常源码提交和普通 CI |
| 把 `dist/`、lockfile、临时 evidence 一并提交 | compare 中出现大量生成文件，源码与生成物不一致 | 生成物不能替代 Source of Truth | 默认只提交源码、合同、测试；CI 生成 dist |
| Evidence Workflow 在依赖失败后仍写部分 PASS | `projectCompilerIntegration: PASS`，但 Project Plugin 本身 FAIL | 控制流没有把“未执行”和“通过”严格分开 | 依赖失败后记录 `NOT_EXECUTED`，总状态 fail-closed |
| Pilot 没有基于已实现 Provider 的项目分支 | Pilot 仍看到 `adapters: {}`，`contextContributions=None` | 分支基线错误，验证对象不是预期实现 | Provider 先在干净项目 feature 分支通过并合入，再重建 Pilot |
| Route 没通过就尝试 Mailbox | Request 工作流直接在 Route 校验处退出 | 违反阶段依赖，扩大噪声 | Route Gate 全绿后才启动 Agent Transport |
| 认为 GitHub Actions 可以“调用当前 ChatGPT 对话” | Actions 只能运行脚本，不能获得当前会话模型实例 | 当前对话属于 ChatGPT Host，不在 CI 执行环境内 | 需要明确的 External Chat Host / 人工中继 / 可调用会话桥 |
| 手工搜索 Drive 后口头说“资料已读取” | 没有 file ID、revision、hash、claim linkage 进入 Harness | 连接器访问不等于可回放 Evidence | 建立 External Source Receipt Adapter |
| 依据实现意图和聊天叙述宣告 PASS | 后续机械证据显示 source 不存在、CI fail、receipt fail | 结论没有回到 exact HEAD / exact Run | 每个结论绑定 HEAD、Run ID、Receipt 和 Artifact |

### 5.1 最重要的流程教训

以后必须坚持：

```text
需求冻结
→ 设计边界确认
→ 最小源码实现
→ 单元测试
→ 项目插件集成测试
→ 合入长期项目分支
→ 从干净项目分支创建 Pilot
→ Route / Context Gate
→ Agent Transport
→ 真实任务执行
→ 项目产物验证
→ Evidence / Reflection / Closure
```

不能再倒序：

```text
先做 Mailbox / Response / Closure
→ 再补 Route
→ 再补 Provider
→ 最后发现源码根本不存在
```

---

## 6. 当前问题矩阵：现象、原因、影响和解决方向

## 6.1 P0：ATP Context Contributor 源码不存在

### 现象

在：

```text
branch: feat/atp-context-contributor-v0.1
head:   095948d395df5f0535514c964cae1d8e940358ba
```

检查到：

```text
agent_harness/projects/automated_testing_platform/src/context-contributor.ts
→ NOT FOUND
```

同时：

```text
src/index.ts
→ 仍只 inject projectManager
→ 只调用 registerProjectFromManifestFile

project.yaml
→ adapters: {}
→ adapter_kind: data-only-project-plugin
```

CI Artifact 中出现：

```text
TS2307: Cannot find module '../src/context-contributor.js'
Cannot find module '@agent-harness/auto-governance-engine'
Vitest failed to load ../src/context-contributor.js
Project Plugin test/build FAIL
```

### 原因

- 真实实现曾在工具调用或临时 Tree 构造过程中被设计出来，但没有成为有效 Git commit / branch source；
- 后续测试、Workflow 和 generated dist 被提交，造成“实现似乎存在”的错觉；
- 分支更新和 ref 操作多次失败后，没有重新从 HEAD 验证 source 文件；
- 过程依赖临时 Workflow 自动改代码，而不是普通源码开发流程。

### 影响

- ATP 无法注册 Provider；
- Project Manifest 无法声明 Adapter；
- Pilot 无法获得 Contribution；
- Task Context Compiler 不会被调用；
- 后续 Route、Mailbox、Agent 执行全部失去前提。

### 正确解决

从干净长期项目分支创建新分支，真实实现并提交：

```text
src/context-contributor.ts
src/index.ts
project.yaml
package.json
cordis.patch.yml
root-discovery.ts（仅在确有必要时）
tests/context-contributor*.test.ts
```

旧 feature 分支只保留失败证据，不继续修补。

## 6.2 P0：冻结 Pilot 没有 Context Contribution

### 现象

Route Receipt 明确记录：

```text
contextContributions: None
knowledgeIds: []
gateIds: []
projectTaskContextCompiled: false
externalChatAgentInvoked: false
pass: false
```

缺失信号：

```text
knowledgeRouteNonEmpty
gateRouteNonEmpty
taskContextGateRelated
taskContextKnowledgeRelated
ipAnalysisRuleSetReferenced
sourceDispositionContractPresent
outputContractPresent
```

### 原因

Pilot 使用的项目插件仍是 data-only 版本，没有 Context Adapter / Provider。公共 Runtime 只能做 A/R/K/G 搜索与关系展开，不能凭空调用 ATP Compiler。

### 影响

虽然项目和部分 A/R 路由成功，但 Agent 仍然没有获得完整任务授权：

- 不知道所有必须读取的文件；
- 没有完整 Rule Owner；
- 没有完整 Write Scope；
- 没有 Validation Obligations；
- 没有项目 Output Contract；
- 不能开始真实 eTimer 分析。

### 正确解决

先完成并合入 ATP Provider，再从更新后的 `project/automated-testing-platform` 创建一个全新 Pilot 分支。不要继续在当前污染 Pilot 上叠补丁。

## 6.3 P0：Mailbox Request 没有创建

### 现象

Run：

```text
33144107143
job: create-request
result: FAILURE
```

工作流先运行 frozen route validator。Route 返回 FAIL 后，`set -euo pipefail` 立即终止，尚未执行：

```text
生成 request.json
生成 mailbox body
gh issue create
```

Artifact 也显示没有 mailbox body 文件。

### 原因

Mailbox 是 Route Gate 的下游，但被过早启动。根因不是 GitHub Issue API，而是前置 Route / Context Contribution 没通过。

### 影响

- 没有 Issue；
- 没有 Request ID；
- 没有 Request metadata；
- 当前 ChatGPT 无法收到一次机械可关联的 Harness Request。

### 正确解决

只有 Route Receipt 全部 PASS 后，才允许创建 Mailbox Request。

## 6.4 P0：Response 与 Verify 是伪下游，实际没有 Agent 响应

### 现象

Respond Run：

```text
33144827302
FileNotFoundError:
agent_harness/pilot_results/atp_current_chatgpt_mailbox_v0_1/request.json
```

Verify Run：

```text
33144871424
FileNotFoundError:
agent_harness/pilot_results/atp_current_chatgpt_mailbox_v0_1/request.json
```

### 原因

上游 Request 从未创建。后续工作流却直接假设 Request 已存在，并尝试构造 Response 或校验 Comment。

更重要的是，Respond Workflow 内嵌的结构化 `BLOCKED` 响应是脚本预先写死的内容，不是当前 ChatGPT 对话实际接收 Request 后自主执行任务产生的响应。即使该脚本成功，也不能证明“当前 ChatGPT Agent 已被测试”。

### 影响

不能证明：

- 当前 ChatGPT 收到了 Harness Context；
- 当前 ChatGPT 使用了 GitHub / Drive 工具；
- 当前 ChatGPT 遵守了项目规则；
- 当前 ChatGPT 形成了真实 Reflection；
- External Chat Bridge 已工作。

### 正确解决

Transport 必须把 Request 真正交给当前会话，并接收该会话真实返回，而不是让 CI 预制一份“像 Agent Response”的 JSON。

## 6.5 P1：GitHub Actions 与当前 ChatGPT 对话之间没有真实执行桥

### 现象

GitHub Actions 能：

- checkout；
- build；
- test；
- 生成 Context Receipt；
- 创建 Issue / Artifact；
- 校验文件和结构。

但它不能直接获得当前 ChatGPT 网页对话中的 GPT-5.6 Pro 实例。

### 原因

当前 ChatGPT 对话运行在 ChatGPT Host 中；GitHub Actions 是独立 CI Runtime。两者没有可调用 Session Handle、Callback 或受信 Transport Adapter。

### 影响

仅靠 CI 无法满足冻结 Charter 中“被测 Agent 必须是当前 ChatGPT 对话”的要求。

### 正确解决方向

需要选择并明确实现一种真实 Transport：

1. 当前 ChatGPT Host 提供的连接器 / Action 回调；
2. 人工中继：Harness 生成不可篡改 Request，用户把它交给当前会话，当前会话返回签名/哈希关联 Response；
3. 可访问当前会话的 Host Plugin；
4. 其他能证明 Agent Identity 和 Request/Response 关联的桥。

在 Transport 完成前，只能证明 Harness Route，不得宣称完成真实 Agent Pilot。

## 6.6 P1：Google Drive 访问没有进入 Harness Evidence

### 现象

对话中曾通过 Drive Connector 定位到 ET6801 相关目录和部分文件，但这些结果没有以稳定 Source Item 进入 Pilot State：

```text
source id
file id
title/path
retrieved revision or modified time
content hash
query
FOUND / NO_MATCH / UNAVAILABLE
purpose
supported claims
```

### 原因

当前公共 Context Contribution 负责提供“应读哪些资料”和 Scope，但尚没有 External Source Receipt Adapter 将 Host Connector 返回值规范化、持久化并链接到 Claim / Evidence。

### 影响

- Agent 无法证明每个注册资料根已处理；
- 无法区分 NO_MATCH 与 UNAVAILABLE；
- 无法重放来源；
- 无法安全生成完整 Feature / Case 结论；
- R140 Source Coverage 不能 PASS。

### 正确解决

增加通用、Host-neutral 的 External Source Receipt 合同，而不是为 Drive 或 eTimer 写公共特例。Receipt 至少包含：

```yaml
source_id:
provider:
locator:
item_id:
title:
status: FOUND | NO_MATCH | UNAVAILABLE
purpose:
retrieved_at:
revision_or_modified_at:
content_hash:
claim_refs:
error:
```

Project Rule 决定哪些 Source Root 必须处理；Host Adapter 决定如何搜索和读取；Harness 只管理 Receipt、Evidence 和 Closure。

## 6.7 P1：测试 Evidence 的状态语义不够严格

### 现象

Feature branch 的 evidence 曾记录：

```text
publicPackages: PASS
projectPlugin: FAIL
projectCompilerIntegration: PASS
atpSoftwareValidation: FAIL
exit code: 90
overall: FAIL
```

但 Project Plugin 本身无法编译，所谓 Compiler Integration PASS 不能证明端到端 Provider 工作；`90` 更接近“因为上游失败而未执行”，不应写成普通 FAIL 或 PASS。

### 原因

Workflow 的阶段依赖、跳过状态和 Evidence Schema 没有严格区分：

- PASS；
- FAIL；
- BLOCKED_BY_DEPENDENCY；
- NOT_EXECUTED；
- SKIPPED_NOT_APPLICABLE。

### 影响

可能出现局部字段让人误判“某能力已经通过”。

### 正确解决

后续 Evidence Schema 必须显式记录：

```text
status
executed
blockedBy
exitCode
sourceHead
command
artifact/log
```

上游失败时，下游必须是 `NOT_EXECUTED` 或 `BLOCKED_BY_DEPENDENCY`，不得生成 PASS。

## 6.8 P2：临时 Workflow 和生成物污染分支

### 现象

feature / pilot 分支出现多次：

```text
apply
finalize
correct
validate-and-mark
respond
verify
```

同时存在 generated `dist/`、lockfile、临时 evidence、失败 marker branch 等噪声。

### 原因

把 GitHub Actions 当成远程编辑器和补丁执行器，代替常规源码分支开发。

### 影响

- HEAD 的真实源码状态难以确认；
- 失败链复杂；
- 生成物可能掩盖缺失源码；
- 新 Agent 容易从错误分支继续；
- Review 成本增加。

### 正确解决

- 保留旧分支作为失败 Evidence；
- 从干净长期项目分支重新创建 feature；
- 不再使用一次性自动改代码 Workflow；
- 采用正常 source commit + stable CI；
- CI 只验证，不自动修改产品源码并回推。

---

## 7. 测试进度与机械证据

## 7.1 公共 Harness `context.contribute`

```text
branch/head: main@24d7c209f3731cc3b2acd20c4428d66781f25e2d
workflow run: 33141904098
result: SUCCESS
```

通过的 Job：

```text
repository-boundary       PASS
package-build-and-test    PASS
public-integration        PASS
```

覆盖内容：

- 公共仓库边界；
- 所有公共 package 按依赖顺序 test + build；
- synthetic-project 集成脚本；
- Context Inline Item 持久化；
- Provider 合同和负向校验；
- 没有 Provider 的兼容路径；
- Provider 缺失 / 跨项目 / 异步 / 非法 scope 的 fail-closed；
- Runtime 接收 Contribution 和 Receipt。

**可以证明：** 公共通用能力在公共 main 上成立。  
**不能证明：** ATP 已经实现自己的 Provider。

## 7.2 ATP data-only Project Plugin 基础集成

```text
branch/head:
test/automated-testing-platform-harness-integration-v0.1
@2021857983956163b0052f9ea66a57c91244a9ca

ATP Harness Basic Integration run: 33131570599
result: SUCCESS
```

同一提交的：

```text
Software Quality Gate run: 33131570607
result: FAILURE
```

因此必须分开解释：

- Project Plugin 注册、root discovery、资源接口和公共 Manager 路由基础测试通过；
- ATP 更广的软件质量门禁当时仍有失败；
- 不能因为 Basic Integration PASS 就宣布整个 ATP 软件基线 PASS；
- 也不能把既有 ATP Quality Gate 失败误判成公共 Context Capability 回归。

## 7.3 ATP Context Contributor feature branch

```text
branch/head:
feat/atp-context-contributor-v0.1
@095948d395df5f0535514c964cae1d8e940358ba

latest exact validation run: 33143509088
result: FAILURE
```

机械结果：

```text
public packages                  PASS
ATP Project Plugin source test   FAIL
ATP Project Plugin build         FAIL
Provider source present          FAIL
Manifest adapter registered      FAIL
ATP software validation          NOT RELIABLY EXECUTED
Overall                          FAIL
```

核心报错：

```text
TS2307 Cannot find ../src/context-contributor.js
Cannot find @agent-harness/auto-governance-engine
Vitest cannot load context-contributor module
```

## 7.4 冻结任务 Route Dry-Run

```text
raw task:
分析6801芯片etimer这个IP。

route validation run: 33143873571
result: FAILURE
```

通过信号：

```text
exactRawTaskPreserved            PASS
projectBound                     PASS
architectureRouteNonEmpty        PASS
ruleRouteNonEmpty                PASS
ipAnalysisArchitectureRouted     PASS
R020.010 routed                  PASS
sourceRegistryReferenced         PASS
partial scope text present       PASS
modelInvoked                     false
```

失败信号：

```text
knowledgeRouteNonEmpty           FAIL
gateRouteNonEmpty                FAIL
taskContextGateRelated           FAIL
taskContextKnowledgeRelated      FAIL
ipAnalysisRuleSetReferenced      FAIL
sourceDispositionContractPresent FAIL
outputContractPresent            FAIL
contextContributions             NONE
projectTaskContextCompiled       false
```

总状态：

```text
pass: false
```

## 7.5 Mailbox Request

```text
run: 33144107143
result: FAILURE
```

失败位置：

```text
Generate exact Harness request and open the mailbox issue
```

真正原因：前置 Route Receipt FAIL，脚本在生成 Request 和创建 Issue 之前退出。

证据：

```text
request.json   NOT CREATED
mailbox body   NOT CREATED
GitHub Issue   NOT CREATED
```

## 7.6 Mailbox Response

```text
run: 33144827302
result: FAILURE
```

核心报错：

```text
FileNotFoundError:
agent_harness/pilot_results/atp_current_chatgpt_mailbox_v0_1/request.json
```

这不是 Agent 返回了 BLOCKED，而是脚本连 Request 都读不到。

## 7.7 Mailbox Verify

```text
run: 33144871424
result: FAILURE
```

核心报错同样是：

```text
request.json NOT FOUND
```

因此没有 Response Record，也没有可验证 Issue Comment。

## 7.8 未执行的测试

下列项目没有执行，状态只能是 `NOT_EXECUTED`：

```text
当前 ChatGPT 对话真实接收 Harness Request
当前 ChatGPT 实际执行 eTimer 分析
Google Drive 注册 Source Root 完整处置
etimer.md / ET6801_etimer.md 生成和验证
Keil 产品构建
J-Link 连接与下载
Flash
FPGA 编程与波形
SIL
HIL
仪器联动
真实硬件功能测试
```

---

## 8. 当前到底能证明什么

### 8.1 已经可以证明

1. **公共 Harness 的插件边界是可行的。**  
   项目可以通过可选 Provider 贡献 Context，而公共 Runtime 不需要知道 ATP 业务。

2. **未声明 Provider 的项目不会被破坏。**  
   公共回归覆盖了 backward compatibility。

3. **公共 Context 可以承载动态项目内容。**  
   Inline Context、Scope、Validation、Output Contract 和 Handoff 有公共承载路径。

4. **公共 Provider 有基本安全边界。**  
   项目隔离、Provider 声明、路径安全、内容预算和失败关闭已有实现与测试。

5. **ATP 可以作为真实 Project Plugin 被公共 Manager 识别。**  
   基础 Project 注册和 A/R/K/G 资源加载有通过记录。

6. **冻结原始任务不需要人工写 ATP Project ID，也能绑定 ATP。**

7. **冻结原始任务能够路由到 IP Analysis Architecture 和部分 Rule。**

8. **当前失败已经从“Agent 不聪明”定位到具体工程缺口。**  
   当前主阻断是 Provider Source / Adapter / Transport / External Evidence，而不是 eTimer 语义能力。

### 8.2 当前不能证明

1. ATP 项目 Context Contributor 已实现；
2. ATP Compiler 已被公共 Runtime 调用；
3. `module=ip-package`、`change=analysis`、`chip=et6801`、`ip=etimer` 已由 Pilot 编译；
4. Agent 已收到完整 `must_read` / `rule_owners` / `write_scope`；
5. Agent 已按 R140 处理全部 Source Root；
6. 当前 ChatGPT 对话已被 Harness 调用；
7. 当前 ChatGPT 能在没有人工提示时完成 ATP eTimer 分析；
8. eTimer 文档达到 ATP 合同；
9. External Source Receipt 链路成立；
10. Reflection / Knowledge Candidate / Closure 成立；
11. ATP 软件整体质量门禁通过；
12. 任何硬件结论成立。

---

## 9. 分支状态与后续分支策略

记录时的关键 HEAD：

```text
main
24d7c209f3731cc3b2acd20c4428d66781f25e2d
status: public context.contribute merged and green

project/automated-testing-platform
eff0c8b15d9878930c62637876d699cf55b9fc7a
status: complete ATP project + data-only Project Plugin

feat/atp-context-contributor-v0.1
095948d395df5f0535514c964cae1d8e940358ba
status: failed / polluted experiment; provider source missing

pilot/atp-et6801-etimer-current-chatgpt-v0.1
205edeb23db70c0fcab585f33d5f7f8d91ee66a3
status: failed / polluted Pilot; route and mailbox not complete
```

### 9.1 后续不要在哪些分支继续开发

不要继续把实现补到：

```text
feat/atp-context-contributor-v0.1
pilot/atp-et6801-etimer-current-chatgpt-v0.1
```

它们应作为失败实验和证据保留，直到新链路通过并完成对照。

### 9.2 正确的新分支起点

建议：

```text
base:
project/automated-testing-platform@eff0c8b15d9878930c62637876d699cf55b9fc7a

new feature branch:
feat/atp-context-contributor-clean-v0.1
```

在 Provider 合入长期项目分支后，再创建：

```text
pilot/atp-et6801-etimer-current-chatgpt-v0.2
```

不得从旧 Pilot merge 或 cherry-pick 大量临时 Workflow；只迁移必要的冻结 Charter 和经过 Review 的稳定测试资产。

---

## 10. 下一阶段严格执行计划

## Step 0：重新核对事实，不写代码

新对话开始后先执行：

1. 读取本文件和冻结 Charter；
2. 获取 `main`、`project/automated-testing-platform`、旧 feature、旧 pilot 的最新 HEAD；
3. 确认公共 `main` 仍为 green；
4. 确认长期 ATP 项目分支仍为 data-only；
5. 不依据旧 `dist/` 判断源码存在。

## Step 1：创建干净 ATP Provider 分支

从长期项目分支创建：

```text
feat/atp-context-contributor-clean-v0.1
```

第一批提交只包含真实 Source 和合同，不加 Mailbox，不加 eTimer 专用路径。

## Step 2：实现最小项目 Provider

最小实现职责：

1. 接收公共 `ProjectContextContributionRequestV01`；
2. 检查 `projectId`；
3. 从原始任务解析通用 chip / IP analysis 参数；
4. 识别为：
   ```text
   module=ip-package
   change=analysis
   chip=et6801
   ip=etimer
   ```
5. 调用 ATP 已有：
   ```text
   tools/governance/compile_task_context.py
   ```
6. 校验返回 Schema、项目参数和完整性指纹；
7. 转换为公共 Contribution：
   - A/R/K/G refs；
   - compiled Task Context Inline Item；
   - read scope；
   - write / protected scope；
   - validation obligations；
   - project-owned output contract；
8. 不适用任务返回 `applicable: false`；
9. 编译失败或参数不确定时失败关闭。

## Step 3：真实注册 Provider

必须修改：

```text
src/index.ts
project.yaml
package.json
cordis.patch.yml
```

机械验收：

```text
project.yaml adapters.context exists
provider id exactly matches registration
provider capability == context.contribute
service/method metadata resolvable
plugin admission PASS
uninstall cleans provider and project
```

## Step 4：聚焦测试，不再先造大工作流

至少覆盖：

1. 中文任务分类；
2. 英文任务分类；
3. 另一个 chip/IP 示例，证明没有 eTimer hardcode；
4. 非 IP Analysis 返回 not-applicable；
5. Compiler Bridge 精确调用；
6. must_read / owner / scope / validation 映射；
7. Output Contract 来自项目规则；
8. Provider project mismatch；
9. Compiler missing / invalid output；
10. unsafe scope；
11. plugin install / uninstall；
12. exact raw task integration。

先让以下命令在源码分支通过：

```text
npm test
npm run build
```

再跑稳定 CI。

## Step 5：Evidence 必须 fail-closed

CI 记录状态时使用：

```text
PASS
FAIL
NOT_EXECUTED
BLOCKED_BY_DEPENDENCY
SKIPPED_NOT_APPLICABLE
```

禁止在上游失败时给下游写 PASS。

## Step 6：Provider 合入长期项目分支

只有以下全绿才允许合入：

```text
public dependency build/test       PASS
ATP Project Plugin test/build      PASS
compiler bridge integration        PASS
project isolation negative test    PASS
clean tracked worktree             PASS
no temporary workflow source edits PASS
```

## Step 7：创建全新 v0.2 Pilot

从更新后的长期项目分支创建新 Pilot。冻结：

```text
Agent: 当前 ChatGPT 对话 GPT-5.6 Pro
Raw task: 分析6801芯片etimer这个IP。
No manual business hints
```

## Step 8：先通过 Route / Context Gate

Route Receipt 必须证明：

```text
exact raw task preserved
project bound
A/R/K/G non-empty
one declared ATP context contribution
compiled Task Context attached
chip/ip/module/change resolved
must_read present
rule_owners present
read/write/protected scope present
validation obligations present
source disposition contract present
output contract present
modelInvoked=false
pass=true
```

不满足时不得启动 External Chat Agent。

## Step 9：实现真实 External Chat Transport

必须先解决“如何把 Request 交给当前 ChatGPT 对话”这一宿主问题。

Transport 验收至少包括：

- Agent Identity；
- Request ID；
- Task Context Hash；
- Response ID；
- Request / Response 不可混淆；
- Host 不增加业务提示；
- Agent Tool Calls 能形成 Receipt；
- Response 来自当前会话，而不是 CI 内嵌 JSON。

## Step 10：实现 External Source Receipt

在真实 Agent 执行前，先让 GitHub / Drive 连接器结果能够进入 Harness Evidence State。

必须区分：

```text
FOUND
NO_MATCH
UNAVAILABLE
```

必须保存：

```text
item id
path/title
revision/time
hash
purpose
claims
error
```

## Step 11：重跑同一个任务并生成 ATP 产物

目标产物：

```text
test_case_doc/etimer/etimer.md
test_case_doc/etimer/ET6801_etimer.md
```

内容和机器块必须由 ATP 活动 Rule Owner 决定，不由 Harness Handoff 重新定义。

## Step 12：完成软件 Evidence、Reflection 与 Closure

只有实际执行过的 Validation 才能 PASS。硬件未执行时必须保留 `NOT_EXECUTED`，并说明解除条件。

---

## 11. 下一阶段的验收 Gate

### Gate A：公共边界

```text
公共 main 无 ATP/eTimer 特例
项目 Provider 只存在于 ATP 项目分支
项目变化不反向污染 main
```

### Gate B：Provider 源码

```text
source file exists
manifest adapter exists
runtime provider registered
plugin tests/build PASS
```

### Gate C：冻结 Route

```text
Context Contribution Receipt exists
Task Context compiled
A/R/K/G complete
Scope/Validation/Output Contract complete
```

### Gate D：Transport

```text
current ChatGPT identity verified
request actually delivered
response actually returned
no alternate model substituted
```

### Gate E：Source Evidence

```text
all registered roots disposed
FOUND/NO_MATCH/UNAVAILABLE explicit
file-level receipts persisted
claims linked to sources
```

### Gate F：项目产物

```text
required files created
contracts structurally valid
unknown/conflict honest
software validation evidence recorded
```

### Gate G：Closure

```text
Framework—not Agent—determines completion
Reflection recorded
Knowledge candidates not auto-promoted
no unexecuted hardware PASS
exact HEAD / Run / Artifact linked
```

---

## 12. 后续禁止事项

下一轮不得：

- 从旧 feature / pilot 分支继续打补丁；
- 先做 Mailbox 再补 Provider；
- 在公共 Harness 中写 ATP / eTimer 业务逻辑；
- 新建第二套 Task Context Manager；
- 用 generated `dist` 证明源码存在；
- 让 CI 自动改产品源码并反复回推；
- 用另一个 API 模型代替当前 ChatGPT；
- 把预制 JSON 当成 Agent Response；
- 把 Connector 搜索对话当成 Harness Evidence；
- 因为公共 CI PASS 就宣布真实项目 Pilot PASS；
- 因为 Agent 输出合理就宣布 Evidence Closure；
- 对未执行的 Keil / FPGA / HIL / Hardware 写 PASS；
- 覆盖历史 Handoff；旧结论错误时应新增纠正文档；
- 忽略 exact HEAD、Run ID 和 Artifact。

---

## 13. 给下一对话的直接启动指令

新对话可直接发送：

```text
继续 ET Harness 的 ATP Current ChatGPT 真实项目测试。

先完整阅读：
1. agent_harness/progress_context/README.md
2. agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md
3. agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml
4. agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
5. agent_harness/design/records/00_INDEX.md

先核对 main、project/automated-testing-platform、旧 feature 和旧 pilot 的最新 HEAD 与 CI，不要相信旧聊天中的 PASS 叙述。

不要继续旧的 feat/atp-context-contributor-v0.1 和 pilot/atp-et6801-etimer-current-chatgpt-v0.1。先从 project/automated-testing-platform 创建干净分支，实现真实 ATP context.contribute Provider 源码、Adapter 注册和聚焦测试。Provider 合入长期项目分支且 Route/Context Gate 全绿以后，才创建新的 v0.2 Pilot 和 External Chat Transport。

冻结 Agent 仍是当前 ChatGPT 对话中的 GPT-5.6 Pro；冻结原始任务仍是：分析6801芯片etimer这个IP。不得加入人工业务提示，不得替换模型，不得伪造外部资料或硬件 Evidence。
```

---

## 14. 关键 Evidence 索引

### 设计与需求

```text
agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md
agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.yaml
agent_harness/design/records/00_INDEX.md
agent_harness/progress_context/20260826_HARNESS_CURRENT_STATE.md
agent_harness/progress_context/20260827_PUBLIC_PLUGIN_VALIDATION_AND_AUTOMATED_TESTING_PLATFORM_HANDOFF.md
```

### 公共能力

```text
main@24d7c209f3731cc3b2acd20c4428d66781f25e2d
CI Run 33141904098: SUCCESS
```

### ATP 基础 Project Plugin

```text
ATP Harness Basic Integration Run 33131570599: SUCCESS
Software Quality Gate Run 33131570607: FAILURE
```

### 失败的 ATP Provider 实验

```text
feat/atp-context-contributor-v0.1
@095948d395df5f0535514c964cae1d8e940358ba
CI Run 33143509088: FAILURE
```

### 失败的冻结 Pilot

```text
pilot/atp-et6801-etimer-current-chatgpt-v0.1
@205edeb23db70c0fcab585f33d5f7f8d91ee66a3

Route Run 33143873571: FAILURE
Mailbox Request Run 33144107143: FAILURE
Mailbox Respond Run 33144827302: FAILURE
Mailbox Verify Run 33144871424: FAILURE
```

### Route Receipt

```text
agent_harness/pilot_results/atp_current_chatgpt_route_v0_1/route-receipt.json
```

关键字段：

```text
pass=false
contextContributions=None
knowledgeIds=[]
gateIds=[]
projectTaskContextCompiled=false
externalChatAgentInvoked=false
```

---

## 15. 最终判断

本轮不是毫无进展。它完成了一个重要公共架构缺口：**项目可以通过标准、可选、受治理的能力，把自己的确定性 Task Context 贡献给公共 Harness，而无需让公共 Harness 理解项目业务。**

但 ATP 适配和真实 Agent Pilot 的工程执行没有完成。失败的核心不是需求本身不可行，而是实施过程发生了顺序和证据纪律问题：

```text
真实 Provider 源码未落地
→ Pilot 基线没有 Provider
→ Context Contribution 不存在
→ Route Gate 失败
→ Mailbox Request 不生成
→ Response / Verify 必然失败
→ 当前 ChatGPT 从未真正被 Harness 调用
```

下一阶段最重要的不是继续扩展功能，而是回到最短、最干净、可验证的路径：

```text
干净项目分支
→ 真实 Provider Source
→ Plugin Test/Build
→ 合入长期项目分支
→ 全新 Pilot
→ Route PASS
→ 真实 External Chat Transport
→ 文件级 Source Evidence
→ 同一 eTimer 任务
→ 项目产物和 Closure
```

只要严格按这一顺序推进，就不会再重复本轮弯路。
