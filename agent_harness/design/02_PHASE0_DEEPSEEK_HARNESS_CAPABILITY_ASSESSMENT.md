# Phase 0：DeepSeek Harness / Cordis 基座能力盘点与技术决策

> 阶段：Phase 0 基座能力盘点 v0.1  
> 架构基线：`00_AGENT_HARNESS_SYSTEM_ARCHITECTURE.md` v0.3  
> 实施路线图：`01_SYSTEM_IMPLEMENTATION_ROADMAP.md`  
> 调研基座：DeepSeek Harness `0.1.0-rc.8`（2026-08-20 调研时 `master`）  
> 第一试点项目：ET-TOOL  
> 本文性质：**事实盘点与技术取舍文档，不是具体治理规则，不修改 DeepSeek Harness Core。**

---

# 1. Phase 0 结论

本轮调研后的核心结论如下：

```text
DeepSeek Harness / Cordis
负责：插件运行、生命周期、Service、Event、Session、Tool、Agent、Subagent 等执行底座

我们的治理系统
负责：能力治理、插件准入、插件推荐、项目规则、记忆治理、测试知识、证据状态、进化闭环

ET-TOOL
负责：第一个项目级治理插件与真实工程试点
```

因此第一阶段**不重新开发 Harness Core，不重新开发 Cordis，不重新制造内部插件总线**。

技术路线冻结为：

```text
DeepSeek Harness / Cordis
        ↓
治理能力抽象层
        ↓
治理插件体系
        ↓
ET-TOOL 项目插件
```

同时从第一版设计开始保留：

```text
MCP Gateway
Codex App Server Adapter
其他 Harness Adapter
```

但跨 Harness 接口在 Phase 0 不实现。

---

# 2. DeepSeek Harness 当前基座状态

调研时 DeepSeek Harness 根版本为：

```text
0.1.0-rc.8
```

项目仍处于快速迭代阶段，因此：

- 不能直接依赖内部私有实现；
- 优先使用公开 Cordis Service / Event / Bundle / Profile 扩展面；
- 需要建立 DSH 版本兼容层；
- 社区插件必须记录验证过的 DSH / Cordis 版本；
- 后续升级必须经过兼容性测试，不能默认向前兼容。

---

# 3. Cordis 可直接复用的核心能力

Cordis 已经解决了我们早期架构中大量“Bus / Plugin Runtime”问题。

## 3.1 插件生命周期

Cordis Fiber 已有完整生命周期：

```text
PENDING
  ↓
LOADING
  ↓
ACTIVE
  ↓
UNLOADING
  ↓
DISPOSED
```

异常可进入：

```text
FAILED
```

结论：**直接复用。**

我们不再自行实现插件生命周期状态机。

---

## 3.2 依赖注入

Cordis `inject` 支持：

```text
插件声明所需 Service
        ↓
依赖未准备
        ↓
插件保持 PENDING
        ↓
依赖就绪
        ↓
自动加载
```

当依赖 Service 消失时，消费者也会自动卸载并在依赖恢复后重新加载。

结论：**直接复用。**

这已经满足插件之间松耦合依赖的底层需要。

---

## 3.3 Service / Provider

DeepSeek Harness 大量能力已经以：

```text
Service Definition
Service Provider
Consumer
```

形式存在。

例如：

```text
ctx.llm
ctx.tools
ctx.sessions
ctx.storage
ctx.credentials
ctx.approval
ctx.fs
ctx.shell
ctx.subagents
ctx.jobs
ctx.skills
ctx.agentTeams
ctx.workflowEngine
```

结论：**直接复用这种能力缝隙设计。**

我们的治理能力也应优先形成新的 Cordis Service seam，而不是插件之间互相 import 实现类。

---

## 3.4 Typed Event

Cordis 已支持多种事件分发语义：

```text
emit
waterfall
parallel
serial
```

结论：**直接复用。**

我们的治理事件，例如：

```text
governance/task-classified
governance/plugin-candidates
governance/admission-checked
governance/evidence-created
governance/learning-event
```

后续直接建立在 Typed Event 机制上。

---

## 3.5 Effect / 自动清理

Cordis `ctx.effect()` 和注册机制可以自动跟随 Fiber 生命周期撤销：

```text
事件监听
工具注册
LLM Adapter
Service 注册
自定义资源
```

结论：**直接复用。**

我们的插件不得绕开 Fiber 生命周期建立无法追踪的永久全局状态。

---

## 3.6 子插件 / 递归插件

Cordis `ctx.plugin()` 原生支持子 Fiber。

结论：**直接复用。**

因此：

```text
ET-TOOL Project Plugin
  ├── Rule
  ├── Memory
  ├── Test
  └── Evidence
```

这种递归插件结构可以直接建立在 Cordis 上，不需要重新设计嵌套插件运行时。

---

# 4. DeepSeek Harness 官方能力复用矩阵

| 能力 | DSH 当前能力 | 我们的策略 |
|---|---|---|
| 插件加载与生命周期 | Cordis Fiber / Plugin | **直接复用** |
| 插件依赖 | `inject` | **直接复用** |
| 插件通信 | Service + Typed Event | **直接复用** |
| 插件组合 | Bundle / Profile / Patch | **直接复用** |
| 热替换 | Cordis HMR / Effect 清理 | **直接复用** |
| Session | `ctx.sessions` + Session Event | **直接复用** |
| Session 持久化 | persistence seam | **直接复用 / 配置 Provider** |
| Session 查询 | session query / projection | **直接复用** |
| Prompt 组装 | `ctx.systemPrompt` | **直接复用** |
| Tool 注册与执行 | `ctx.tools` | **直接复用** |
| Skill | `ctx.skills` | **直接复用** |
| Storage | `ctx.storage` / storage domain | **直接复用** |
| Credentials | `ctx.credentials` | **直接复用** |
| Approval | `ctx.approval` | **直接复用并叠加治理策略** |
| Sandbox | `ctx.sandbox` | **直接复用** |
| Filesystem | `ctx.fs` Provider seam | **直接复用** |
| Shell / Subprocess | `ctx.shell` / `ctx.subprocess` | **直接复用** |
| Background Jobs | `ctx.jobs` | **直接复用** |
| Subagent | `ctx.subagents` | **直接复用** |
| Codex Subagent | 官方 Codex Provider | **直接复用** |
| Claude Code Subagent | 官方 Claude Code Provider | **直接复用** |
| Agent Teams | `ctx.agentTeams`，实验性 | **试点复用，不作为唯一关键依赖** |
| Workflow Engine | `ctx.workflowEngine` | **直接复用基础执行能力** |
| Runtime Invariants | `ctx.invariants` | **重点复用** |
| Client Plugin | DSH Client Plugin 图 | **需要 UI 时复用** |
| Plugin Package | `dsh.bundle` + `cordis.patch.yml` | **直接复用** |
| Profile | `dsh.profile` | **直接复用** |
| LLM Adapter | `ctx.llm` | **直接复用** |

结论：

> 我们没有必要自行重新开发通用 Plugin Runtime、Service Registry、Event Bus、Session Runtime、Subagent Runtime、Job Runtime。

---

# 5. DeepSeek Harness 已经具备的跨模型能力

DeepSeek Harness 已经实现具名 Subagent Provider。

当前官方实现包括：

```text
Codex Provider
Claude Code Provider
```

上层统一通过：

```text
ctx.subagents
```

委派任务。

这意味着第一阶段即可形成：

```text
DeepSeek Harness 作为治理主机
        │
        ├── DeepSeek Agent
        ├── Codex Agent
        └── Claude Code Agent
```

因此 Phase 1～4 的多模型能力无需等待 MCP。

MCP / Codex App Server 外部 Gateway 的意义主要是：

> 当未来用户从 Codex、Cursor、Claude Code 等外部 Harness 主动工作时，也能访问同一治理能力。

---

# 6. 社区插件调研与复用判断

社区插件不直接成为项目硬依赖。

统一使用以下状态：

```text
DIRECT        可直接使用
ADAPT         建议通过能力契约薄适配
WRAP         需要二次治理封装
REFERENCE     只借鉴设计
REJECT        当前不建议进入正式链路
```

---

## 6.1 Graph Memory

当前能力：

```text
跨 Session 记忆
TASK / SKILL / EVENT 图谱
SQLite / FTS5
可选向量检索
PageRank
Community Detection
局部子图召回
来源追踪
```

其架构本身已经采用：

```text
宿主无关 Memory Core
      +
DSH Cordis Adapter
```

调研版本：`1.6.0-beta.1`。

项目声明已完成 DSH 原生适配，并完成 107 项自动测试。

复用判断：

```text
状态：ADAPT
```

理由：

- 非常适合作为第一版 Memory Provider；
- 已有跨会话和图谱能力；
- 但我们的 Memory 不应直接绑定其内部 API；
- 需要先定义 `memory.*` 治理能力契约；
- ET-TOOL 的 Current State / Change Event / Rule 等结构化知识不能完全由自由记忆抽取代替。

建议：

```text
Governance Memory Contract
        ↓
Graph Memory Provider Adapter
```

---

## 6.2 DSH Workflow

当前社区实现已经覆盖：

```text
Workflow Capsule
多 Agent
任务 DAG
parallel / pipeline
pause / resume
rerun / resume-run
Artifact
Evidence
Budget
持久 Run Graph
Governance
```

并明确通过 Cordis / Subagent / Session / Jobs 等公开 seam 实现，零 DSH Core Patch。

复用判断：

```text
状态：ADAPT / WRAP
```

理由：

- 很适合作为复杂多 Agent Workflow Provider；
- 不需要我们重新开发 Agent Runtime；
- 但我们的项目任务治理、权限边界、Rule / Test / Evidence 责任不能交给通用 Workflow 自己定义；
- 需要在上层增加 Project Governance Policy。

建议：

```text
Governance Workflow Contract
        ↓
DSH Workflow Provider
```

---

## 6.3 dsh-market

当前能力：

```text
社区插件市场
搜索
安装
升级
卸载
热禁用 / 启用
版本检查
插件配置
加载顺序诊断
基础安全提示
```

其目录当前 README 声称覆盖 1550+ 社区插件。

复用判断：

```text
状态：DIRECT / REFERENCE
```

用途：

- 可作为用户安装社区插件的现成市场；
- 可以借用它的插件目录数据；
- 不替代我们的 Governance Capability Catalog；
- 不替代治理准入。

关键区别：

```text
Market：插件在哪里，怎么安装
Governance Catalog：插件能做什么，什么风险，什么任务允许使用，可信等级如何
```

---

## 6.4 dsh-find-plugin

当前能力：

```text
自然语言需求
→ GitHub dsh-plugin topic 搜索
→ 按 Stars 重新排序
→ 返回插件候选和安装命令
```

复用判断：

```text
状态：REFERENCE
```

原因：

其插件发现机制适合“找插件”，但距离我们的 Plugin Recommender 仍有明显差距。

我们的推荐器还需要考虑：

```text
Project Scope
Task Type
Risk
Governance Policy
Capability Graph
插件可信等级
权限
历史成功率
当前健康状态
强制组合
禁止组合
```

因此不能直接把 dsh-find-plugin 当作正式治理推荐器。

---

## 6.5 dsh-plugin-audit

当前能力：

```text
第三方插件静态扫描
文件读写行为
子进程
网络主机
环境变量
凭据路径
动态代码执行
注入 Service
运行时 tools/pre-execute Sentinel
```

复用判断：

```text
状态：WRAP
```

非常适合作为未来 Plugin Admission 的一个检测 Provider。

但它自己也明确：

> Audit 是证据辅助，不是“安全证明”。

因此未来治理准入应类似：

```text
Manifest Validation
+ Static Audit
+ Dependency / Supply Chain Check
+ Permission Contract
+ Conformance Test
+ Governance Policy
```

不能只看静态扫描结果。

---

## 6.6 dsh-ci-doctor

当前能力：

```text
GitHub Actions Failure Watch
CI 日志诊断
错误签名
失败分类
疑似文件
历史失败 Ledger
Background Job
```

并通过公开 Cordis seam 使用：

```text
tools
jobs
shell
storageDomain
```

复用判断：

```text
状态：ADAPT
```

它适合作为：

```text
CI Diagnosis Provider
```

但它不是我们需要的完整 Test Knowledge / Required Test Resolver。

它解决：

> CI 为什么失败？

我们仍需要解决：

> 这次改动应该跑什么测试？

两者不能混为一层。

---

## 6.7 代码评审类社区插件

当前社区已有多种：

```text
文件评审
Git Diff Review
Reviewer Bot
Web Review
```

Phase 0 结论：

```text
不选择唯一 Provider
```

理由：

- 评审能力高度依赖项目规则和任务类型；
- 后续应该先定义 `review.*` Capability Contract；
- 再通过真实 ET-TOOL Pilot 比较多个 Provider。

当前只记录为候选生态，不形成硬依赖。

---

# 7. 社区插件总体风险判断

社区生态规模很大，但当前“可安装”不能等价为：

```text
安全
可信
适用于企业开发
适用于不可逆硬件任务
符合 ET-TOOL 规则
```

DeepSeek Harness 社区目录本身也明确提示：第三方插件运行的是本机代码，目录收录并不是安全审计。

因此正式治理系统必须增加自己的：

```text
Governance Admission
```

任何社区插件必须先进入：

```text
候选区
```

通过治理后才能进入：

```text
正式能力目录
```

---

# 8. 我们必须自行建设的能力

经过盘点，以下能力当前没有被 DeepSeek Harness / 社区插件完整覆盖，属于我们的核心工作。

## 8.1 Governance Capability Catalog

必须自行建设。

负责：

```text
能力定义
能力层级
Provider
项目范围
风险等级
可信等级
权限
适用任务
依赖能力
强制组合
禁止组合
健康状态
历史表现
```

它不是 Cordis Service Registry 的重复实现。

Cordis 回答：

> 现在运行着什么 Service？

Governance Catalog 回答：

> 这个能力是否适合当前治理任务？

---

## 8.2 Governance Manifest

必须自行建设。

这是叠加在标准 DSH Bundle / Cordis Plugin 之上的治理元数据。

它至少需要描述：

```text
插件治理身份
能力
任务范围
权限
风险
可信等级
输入输出契约
Evidence 要求
项目兼容范围
支持的 DSH / Cordis 版本
跨 Harness 可移植等级
```

---

## 8.3 Plugin Admission Gate

必须自行建设，但可复用：

```text
DSH package checks
Cordis Invariants
dsh-plugin-audit
```

形成更高层的治理门禁。

---

## 8.4 Plugin Recommender

必须自行建设。

社区已有“插件搜索”，但没有满足我们要求的项目级、风险感知、治理感知推荐系统。

---

## 8.5 Project Plugin Contract

必须自行建设。

ET-TOOL 是第一套实现。

负责定义一个项目怎样向治理系统暴露：

```text
项目身份
知识入口
规则入口
Source Map
Memory
Test Knowledge
CI
Evidence
Open Gap
项目治理策略
```

---

## 8.6 Rule Governance

必须自行建设。

DeepSeek Harness 没有 ET-TOOL 这种长期 Living Rules + Rule Map + Rule Evolution 体系。

---

## 8.7 Test Knowledge / Test Resolver

必须自行建设。

现有 CI 插件主要解决执行或失败诊断，并不解决：

```text
Change
→ Rule
→ Required Tests
```

这个能力是我们工程治理体系的重要差异化模块。

---

## 8.8 Evidence / Completion State

必须自行建设。

尤其 ET-TOOL 需要区分：

```text
CODE IMPLEMENTED
UNIT VALIDATED
NO-HW VALIDATED
HW CANDIDATE PASS
PRODUCT HW PASS
PROFILE PROMOTED
RELEASE ENABLED
CUSTOMER PACKAGE VERIFIED
```

通用 Harness 不可能替我们定义这些产品状态。

---

## 8.9 Governance Learning / Evolution

必须自行建设。

目标不是让 LLM 自由修改系统，而是：

```text
任务结果
→ Learning Event
→ 找到治理缺陷
→ 对应治理插件按自己的规则更新
→ 验证
→ 生效
```

---

# 9. 能力抽象与 Provider 原则

为了避免未来被某个 DSH 社区插件锁死，核心治理逻辑只依赖 Capability Contract。

例如：

```text
memory.context
        ↓
Graph Memory Provider
```

而不是：

```text
ET-TOOL → Graph Memory 内部 API
```

同理：

```text
workflow.run
  ↓
DSH Workflow Provider

ci.diagnose
  ↓
dsh-ci-doctor Provider

plugin.audit
  ↓
dsh-plugin-audit Provider
```

Provider 可替换。

---

# 10. 可移植等级

从 Phase 1 开始，每个治理能力必须标记可移植等级。

建议：

```text
P0 — 项目核心资产
     数据和契约不得绑定 DSH

P1 — 可替换 Provider
     第一实现可以是 DSH 插件，但必须有稳定能力契约

P2 — DSH 原生增强
     缺失不会破坏核心治理闭环
```

例如：

| 能力 | 等级 |
|---|---|
| ET-TOOL Rule 数据 | P0 |
| ET-TOOL Test Knowledge | P0 |
| Evidence / State | P0 |
| Governance Capability Contract | P0 |
| Graph Memory Provider | P1 |
| DSH Workflow Provider | P1 |
| dsh-ci-doctor | P1/P2 |
| dsh-market UI | P2 |
| DSH Web UI 增强 | P2 |

---

# 11. Phase 0 技术冻结决策

本轮正式冻结以下技术方向。

## D-001

```text
DeepSeek Harness 是第一运行基座。
```

## D-002

```text
Cordis 是第一阶段内部插件运行时和通信骨架。
不自行重新开发内部 Bus。
```

## D-003

```text
默认零 DeepSeek Harness Core Patch。
```

## D-004

```text
官方 Service / Event / Session / Tool / Subagent / Job 能力优先直接复用。
```

## D-005

```text
社区插件优先复用，但不得直接成为 Project Plugin 的内部硬编码依赖。
```

## D-006

```text
所有关键社区能力必须通过 Capability Contract / Provider Adapter 接入。
```

## D-007

```text
插件安装成功 ≠ 治理准入成功。
```

## D-008

```text
治理插件需要第二层 Governance Manifest 和 Admission Gate。
```

## D-009

```text
多 Agent 第一阶段优先使用 Subagent / Jobs / Agent Teams / Workflow。
```

## D-010

```text
Codex / Claude Code 第一阶段可以直接作为 DSH Subagent Provider 使用。
```

## D-011

```text
MCP / Codex App Server 为未来外部 Harness Gateway，Phase 1 不实现，但 Capability Contract 不得阻塞其后续实现。
```

## D-012

```text
项目核心数据、规则、测试知识、Evidence 必须保持 P0 可移植性。
```

---

# 12. Phase 0 仍需持续跟踪的风险

Phase 0 不要求解决，但必须登记：

```text
RISK-001 DeepSeek Harness 仍在快速 RC 迭代，可能产生 Breaking Change
RISK-002 Cordis API 尚未完全稳定
RISK-003 Agent Teams 当前仍属于 Experimental
RISK-004 社区插件质量、维护水平、安全水平差异巨大
RISK-005 社区插件对特定 DSH Snapshot 的兼容性可能快速失效
RISK-006 安装时第三方 build script 可以在 Agent Sandbox 外执行
RISK-007 不同插件可能重复认领相似治理语义
RISK-008 关键治理数据不得被社区插件私有格式锁定
```

这些风险后续由兼容层、准入门禁、版本锁定和能力契约逐步解决。

---

# 13. Phase 0 输出矩阵

| 原计划能力 | 结论 |
|---|---|
| Cordis Context / Service / Inject | 直接复用 |
| Typed Event / Effect / 生命周期 | 直接复用 |
| Bundle / Profile | 直接复用 |
| Session / Prompt / Tool / Skill | 直接复用 |
| Storage / Credentials / Approval / Sandbox | 直接复用 |
| Jobs / Subagent | 直接复用 |
| Agent Teams | 试点复用，保留替代路径 |
| Workflow | 官方基础能力 + 社区 DSH Workflow Provider |
| Invariants | 直接复用并用于治理门禁 |
| Memory | 建 Capability Contract，优先适配 Graph Memory |
| CI Diagnose | 适配 dsh-ci-doctor |
| Plugin Security Audit | 封装 dsh-plugin-audit 为准入证据之一 |
| Plugin Market | 直接使用 dsh-market，不能替代治理目录 |
| Plugin Discovery | 借鉴 dsh-find-plugin，不作为正式推荐器 |
| Governance Capability Catalog | 自研 |
| Governance Manifest | 自研 |
| Plugin Admission | 自研治理层，复用现有检测能力 |
| Plugin Recommender | 自研 |
| Project Plugin Contract | 自研 |
| Rule Governance | 自研 |
| Test Knowledge / Resolver | 自研 |
| Evidence / Completion State | 自研 |
| Evolution Loop | 自研 |
| MCP / Codex 外部 Gateway | 后续 Phase 6 |

---

# 14. Phase 0 验收结论

路线图要求对计划开发能力回答：

```text
直接复用？
薄适配？
二次封装？
自行开发？
```

当前已经能够明确分类。

因此：

```text
PHASE 0 BASELINE CAPABILITY ASSESSMENT = READY
```

下一阶段可以进入：

```text
Phase 1 — 治理层最小骨架
```

但 Phase 1 开始前，应先完成第一批核心能力契约设计，至少包括：

```text
governance.project
governance.capability
rule.resolve
memory.context
test.resolve
evidence.record
state.read
state.update
```

第一版只设计稳定边界，不追求一次定义全部未来能力。
