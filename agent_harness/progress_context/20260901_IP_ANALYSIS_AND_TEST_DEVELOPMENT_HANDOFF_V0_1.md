# ET Harness / ATP — IP 分析与测试开发生产模式交接 V0.1

**状态**：PRODUCTION HANDOFF / NEXT-CONVERSATION ENTRYPOINT  
**日期**：2026-09-01  
**目的**：下一对话立即继续真实芯片 IP 分析与测试代码开发。ET Harness 继续作为项目治理、导航、规则、知识、Context、Evidence 的基础设施，但本阶段的主目标不再是“测试框架本身”。

---

## 0. 下一对话先看这里

下一对话的第一目标不是继续研究 ET Harness 架构，也不是继续修 Round 3 暴露出的 Framework Bug。

当前业务优先级已经切换为：

```text
真实芯片 IP 分析
    ↓
建立公共 IP 语义 / Feature / Case 契约
    ↓
建立 ET6801 芯片适配事实
    ↓
设计测试计划
    ↓
撰写测试代码 / Driver / Service / Wrap / Case
    ↓
运行可执行的静态 / 单元 / FPGA / HIL 验证
    ↓
持续形成 Evidence / Context / Knowledge
```

ET Harness 的角色：

> **用现有 Project Plugin、项目地图、Rules、Knowledge、Context、Source Registry 和 Evidence 规则约束 Agent 的分析与开发过程；不要因为 Web Runtime 尚未完全可用而停止真实 IP 工作。**

本阶段原则：

> **Framework 作为治理基础设施使用；IP 分析与测试开发作为生产任务推进。**

---

# 1. 当前仓库与基线

## 1.1 ET Harness

Repository:

```text
abba-labs/et-harness
```

当前 Codex 已推进的实验分支：

```text
codex/fast-track-pure-mcp-atp-v0.1
```

最近观察 HEAD：

```text
1301fa36395a7bb1ea06ae307936ac2339d922e5
```

Round 3 已证明部分 Runtime / Project Plugin / Task Context / Knowledge / Gateway 能力可以运行，但最终结论是：

```text
ROUND3_CLOSED_LOOP_FAIL
```

因此：

- 不得声称 ET Harness 全生命周期已经 PASS；
- 也不应因为 Round 3 FAIL 而暂停芯片项目开发；
- Framework Bug 另列 backlog，生产任务继续。

## 1.2 ATP 真实项目

原始项目：

```text
Abba-shenfu/Automated_Testing_Platform
branch: review_code
revision: a45dee76c2eefab1e69c14003ac3def01f2a7c89
```

ET Harness 仓库已经包含 ATP 项目导入快照与 Project Plugin：

```text
agent_harness/projects/automated_testing_platform/
```

导入来源记录：

```text
agent_harness/projects/automated_testing_platform/IMPORT_SOURCE.json
```

其中记录的 ATP source revision：

```text
a45dee76c2eefab1e69c14003ac3def01f2a7c89
```

---

# 2. 当前已经具备、可以直接利用的治理能力

即使 ChatGPT Web 当前没有一个稳定可重复启动的完整 Runtime，下面这些项目能力已经可以用于生产任务，而且应该继续使用。

## 2.1 Project Governance Navigation

项目入口：

```text
AGENTS.md
project-governance/system-map.yaml
project-governance/modules/*.yaml
report/design/rule_owner_catalog.yaml
```

IP 分析任务对应：

```text
module = ip-package
change = analysis
ip = <target_ip>
chip = et6801
```

权威 Module Profile：

```text
project-governance/modules/ip-package.yaml
```

## 2.2 IP Source Registry

IP 分析资料入口：

```text
project-governance/ip-analysis-sources.yaml
```

它负责把 IP 分析导航到注册的真实来源，包括：

- SVD / Register Description；
- CMSIS / SDK Driver；
- UnitTest；
- FunctionalTest；
- FPGA 历史资料；
- 其他项目登记 Source。

下一对话不要只搜源码后直接下结论，必须沿 Source Registry 完成多源交叉验证。

## 2.3 Task Context Compiler

已有工具：

```text
tools/governance/compile_task_context.py
```

标准 IP 分析 Context：

```text
compile
--module ip-package
--change analysis
--ip <ip>
--chip et6801
```

真实 XBAR Task Context 已在独立 GitHub Runner 实验中机械验证过以下属性：

```text
module = ip-package
change = analysis
ip = xbar
chip = et6801
write_scope.allowed = test_case_doc/xbar/**
```

同时正确路由到：

- `project-governance/ip-analysis-sources.yaml`
- `public_ip_semantics`
- `public_chip_neutrality`
- `contract_document_sync`
- `ip_analysis_workflow`
- `public_ip_machine_contract`
- `canonical_result_evidence`

在 Web Host 无法直接执行 Compiler 时，必须按照同一 Module Profile / Rule Owner / Source Registry 语义工作；这属于 Soft-Governed Host 模式，但不能假装已获得 Runtime Closure。

## 2.4 ATP Project Plugin

Project Plugin 已存在：

```text
agent_harness/projects/automated_testing_platform/
```

包含：

```text
project.yaml
architecture/
rules/
knowledge/
gates/
src/context-contributor.ts
src/gate-evidence-provider.ts
```

不要重新设计或重新开发 ATP Project Plugin。

---

# 3. 当前不要等待的事情

下面这些 ET Harness 问题已经被真实测试暴露，但本阶段全部进入 Framework Backlog，不得阻塞 IP 生产任务。

## 3.1 Portable ChatGPT Runtime

目标仍然成立：未来需要给 ChatGPT Web 提供可移植的 Linux Runtime，使 Web Host 能独立运行 ET Harness。

但当前不要等待它完成再开始 IP 工作。

## 3.2 Round 3 Framework Gaps

当前已知但暂缓处理：

```text
PRELIGHT / protected-scope enforcement gap
SUPERVISION / obligation ledger gap
CLOSURE gap
CONTEXT persistence / rehydration gap
LIVE MCP wrapper activation gap
reproducible clean-runtime assembly gap
```

这些问题单独记录，除非它们直接阻塞具体 IP 任务，否则不要在本轮生产开发中扩展 Framework。

## 3.3 不要再次做的事情

- 不要重新证明 Project Plugin 是否存在；它已经存在。
- 不要重新尝试 Web → localhost / local tunnel。
- 不要把 GitHub Actions 当 ChatGPT Web Runtime。
- 不要因为 Harness 没有完整 Closure 就停止分析真实 IP。
- 不要为“让框架看起来 PASS”而修改项目规则。
- 不要把历史 FPGA PASS 当当前 SHA PASS。

---

# 4. 生产模式下的 IP 分析标准流程

对后续每个 IP，都使用同一条工作链。

```text
USER TASK
  ↓
识别 chip / ip / task type
  ↓
ip-package / analysis
  ↓
Project Map + Module Profile
  ↓
Rule Owners
  ↓
Source Registry
  ↓
SVD / CMSIS / SDK / Tests / FPGA / Docs
  ↓
Claim → Evidence → Conflict
  ↓
Feature Catalog
  ↓
Case Plan
  ↓
Public IP Contract
  ↓
Chip Overlay
  ↓
Test Implementation
  ↓
Verification / Evidence
```

## 4.1 Step A — 定义任务身份

每次开始先固定：

```text
Project
Target chip
Target IP
Repository / branch / SHA
Task type
Evidence time boundary
```

例如 XBAR：

```text
Project: Automated_Testing_Platform
Chip: ET6801
IP: XBAR
Task: ip-package/analysis
ATP revision: a45dee76c2eefab1e69c14003ac3def01f2a7c89
```

## 4.2 Step B — 读取规则和导航，不盲搜

优先读取：

```text
AGENTS.md
project-governance/system-map.yaml
project-governance/modules/ip-package.yaml
project-governance/ip-analysis-sources.yaml
相关 Rule Owner 正文
```

目的不是增加文档阅读量，而是确定：

- 应该读哪些 Source；
- 什么是公共 IP 语义；
- 什么是芯片私有事实；
- Evidence 怎么分级；
- 可以写哪些路径；
- 需要哪些验证。

## 4.3 Step C — 多源分析

每个 IP 至少检查：

```text
1. Register / SVD
2. CMSIS / Device Header
3. SDK Driver
4. UnitTest
5. FunctionalTest
6. FPGA / silicon 历史资料（如有）
7. ATP 当前平台适配
```

如果 Source Registry 中登记了资料但无法访问，必须记录：

```text
FOUND
NO_MATCH
UNAVAILABLE
```

不能静默忽略。

## 4.4 Step D — Evidence 分层

必须区分：

```text
CURRENT_SHA_DIRECT
CURRENT_SHA_STATIC
HISTORICAL_ONLY
HANDOFF_INHERITED
INFERENCE
NOT_RUN
UNAVAILABLE
```

核心纪律：

> 静态代码缺陷 ≠ 当前硅片运行失败。

> 历史 FPGA PASS ≠ 当前 SHA PASS。

> Agent 推理 ≠ Evidence。

## 4.5 Step E — 建立 Feature Catalog

分析完成后先生成 Feature，而不是马上写随机测试。

建议结构：

```text
Feature ID
Feature name
Semantics
Configuration / inputs
Expected observable result
Source basis
Chip dependency
Testability
Known conflict
```

## 4.6 Step F — 建立 Case Plan

从 Feature 系统性生成测试：

```text
正常功能
边界
非法参数
Reset / default
Enable / disable
状态迁移
多通道 / 多实例
错误处理
资源冲突
回归缺陷
```

每个 Case 必须能回溯：

```text
Feature → Case → Source → Evidence
```

不要凭 Driver API 数量机械生成 Case。

## 4.7 Step G — 先契约，再写实现

首次正式接入 IP：

```text
test_case_doc/<ip>/<ip>.md
```

用于公共 IP Feature / Case / Driver 语义。

芯片适配文档：

```text
test_case_doc/<ip>/ET6801_<ip>.md
```

用于：

- ET6801 寄存器 / channel / capability 事实；
- SDK / CMSIS 差异；
- 当前测试状态；
- 芯片特有冲突 / limitation。

完成基本契约后再进入：

```text
PC Driver
Formal Case
Firmware Service
Firmware Wrap
Chip Capability / Execution Mapping
```

---

# 5. 当前第一生产任务：ET6801 XBAR

下一对话优先继续 XBAR，不要重新从零分析。

## 5.1 当前已确认 Source

当前已找到：

```text
XBAR SVD
ET6801 CMSIS Header
ET6x XBAR SDK Driver
XBAR UnitTest
XBAR FunctionalTest
FPGA / historical materials
```

ATP 公共自动化层当前未发现正式 XBAR：

```text
test_case_doc/xbar
PC Driver
Firmware Service
Common Wrap
```

因此：

> XBAR 已有底层 IP / SDK / 历史测试资料，但 ATP 正式平台适配仍未完成。

## 5.2 当前最重要技术发现

当前 ET6801 CMSIS 类型：

```text
ETXB_GRP[12]
OPXB_GRP[12]
CBXB_GRP[8]
COXB_GRP[8]
```

当前 Driver 逻辑使用：

```text
MAX_ETXB_OUTPUT_CH = 14
MAX_OPXB_OUTPUT_CH = 14
MAX_CBXB_OUTPUT_CH = 14
MAX_COXB_OUTPUT_CH = 14
```

并使用这些 MAX 对对应 CMSIS 数组进行循环 / API 边界控制。

因此当前源码类型层可以确认：

```text
ETXB: channel 12-13 存在数组越界路径
OPXB: channel 12-13 存在数组越界路径
CBXB: channel 8-13 存在数组越界路径
COXB: channel 8-13 存在数组越界路径
```

当前分类：

```text
CONFIRMED_STATIC_C_BOUND_DEFECT
```

但不能说：

```text
CONFIRMED_SILICON_FAILURE
```

因为当前 SHA build / FPGA / silicon 运行尚未执行。

## 5.3 上游 Spec 冲突

XBAR SVD 结构字段与 CMSIS 一致：

```text
ETXB = 12
OPXB = 12
CBXB = 8
COXB = 8
```

但 ETXB 的 SVD 描述文字中观察到：

```text
0~11
与
0~13
```

存在冲突。

所以 XBAR 当前完整分类应保留为：

```text
CONFIRMED_STATIC_C_BOUND_DEFECT
+
UPSTREAM_SPEC_CONFLICT
```

需要后续继续对更上游 Register Spec / RTL / FPGA 实现确认“硬件权威通道数”。

## 5.4 历史 Test 结论

历史 XBAR test log 曾记录：

```text
48 checks
48 PASS
0 FAIL
```

但现有测试主要覆盖正常通道，未系统覆盖：

```text
ETXB/OPXB 非法 12-13
CBXB/COXB 非法 8-13
```

因此历史 48/48 PASS 不否定当前边界缺陷。

历史结果只能标记：

```text
HISTORICAL_ONLY
```

---

# 6. XBAR 下一步不要再只“分析”，要开始形成正式交付物

下一对话应按下面顺序推进。

## Phase X1 — 收口技术事实

补齐尚未完全确定的：

```text
1. ETXB / OPXB / CBXB / COXB 权威 HW 通道数
2. 各 XBAR 输入 / 输出 mux 语义
3. Enable / disable 语义
4. Reset / default 状态
5. invalid channel 预期行为
6. channel → register → bitfield 映射
7. FunctionalTest / UnitTest 实际覆盖矩阵
8. FPGA 历史验证与当前 SHA 的关系
```

输出：一个 Evidence Ledger。

## Phase X2 — 建立 XBAR Feature Catalog

初始 Feature 方向：

```text
XBAR-F001 ETXB routing
XBAR-F002 OPXB routing
XBAR-F003 CBXB routing
XBAR-F004 COXB routing
XBAR-F005 output enable / disable
XBAR-F006 mux selection
XBAR-F007 reset / default configuration
XBAR-F008 output-channel boundary validation
XBAR-F009 invalid-channel protection
XBAR-F010 functional routing verification
```

这些 ID 可以调整，但必须保证 Feature → Evidence 可追踪。

## Phase X3 — 建立正式 XBAR 文档

目标：

```text
test_case_doc/xbar/xbar.md
test_case_doc/xbar/ET6801_xbar.md
```

先完成可验证的基础版本，不追求一次性写完所有细节。

## Phase X4 — 设计测试矩阵

优先 Case：

```text
正常最小 channel
正常最大合法 channel
非法 channel = legal_max + 1
Driver MAX 与 CMSIS array boundary 回归
enable / disable
mux select
reset/default
每组 XBAR 独立测试
历史 FPGA 关键链路复现
```

特别增加边界回归：

```text
ETXB 11 / 12 / 13
OPXB 11 / 12 / 13
CBXB 7 / 8 / 13
COXB 7 / 8 / 13
```

目的：明确证明：

- 合法边界是否工作；
- 非法边界是否被拒绝；
- Driver 是否存在 OOB；
- Fix 后是否有 regression coverage。

## Phase X5 — 开始 ATP 测试实现

在文档与 Case Plan 基础上逐层实现：

```text
PC Driver
  ↓
Formal Case
  ↓
Firmware Service
  ↓
Common Wrap
  ↓
ET6801 capability / mapping
```

不要一次同时实现所有层。

建议第一个最小闭环：

```text
XBAR boundary / channel configuration test
```

它最能验证：

- public contract；
- chip adaptation；
- PC/Firmware boundary；
- 当前 Driver defect；
- regression test architecture。

---

# 7. 测试代码开发原则

## 7.1 测试来源必须明确

测试不是“想到了什么测什么”。

必须来自：

```text
Hardware semantics
Driver semantics
Feature Catalog
Known defect
Boundary / error model
```

## 7.2 公共与芯片私有分离

公共 XBAR Case 定义：

```text
what behavior should be tested
```

ET6801 Capability / Mapping 定义：

```text
ET6801 实际有多少 channel / register / feature
```

不要把 ET6801 channel 数硬编码到公共 Case 语义里。

## 7.3 测试应能生成 Evidence

每个 Formal Case 最终至少产生：

```text
Case ID
Target
Configuration
Observation
Expected
Actual
Evidence Ref
Result
```

## 7.4 优先写能抓住真实 Bug 的测试

本阶段不追求 Case 数量。

优先级：

```text
真实边界缺陷
真实平台缺口
真实历史未覆盖区域
真实跨层契约
```

不是“先写 100 个看起来完整的测试”。

---

# 8. Web ChatGPT 下一对话的工作模式

在 Portable Runtime 未就绪前，下一对话采用：

```text
SOFT-GOVERNED PRODUCTION MODE
```

具体含义：

```text
1. 读取项目真实导航 / Rules / Source Registry
2. 按 Project Plugin 语义执行任务
3. 使用 GitHub / Google Drive 真实 Source
4. 区分 Evidence / Inference / Historical
5. 只在允许的项目路径生成正式交付物
6. 不依赖 Framework Runtime 完整可用才开始工作
7. 不由 Agent 自己声明正式 Framework PASS/CLOSE
```

如果下一对话能够访问 Runtime：

```text
harness_begin
→ Context
→ WORK
→ observe/status/preflight/complete
```

则使用 Runtime。

如果 Runtime 不可用：

> 继续生产任务，但明确标识为 Web Soft-Governed execution；不能伪造 Runtime receipt。

---

# 9. 下一对话第一轮执行指令

下一对话读完本文后，直接执行：

```text
任务：继续完成 ET6801 XBAR IP 正式分析，并准备进入 ATP 测试开发。

第一步：
不要重新分析 Harness 架构，不要重新验证 Project Plugin 是否存在。

第二步：
根据 ip-package/analysis 路由，重新确认当前 XBAR Evidence Ledger，重点补齐：
- 权威硬件 channel 数；
- SVD 描述冲突；
- UnitTest / FunctionalTest 覆盖边界；
- FPGA 历史资料；
- ATP 当前适配缺口。

第三步：
生成/完善：
- XBAR Feature Catalog
- XBAR Case Plan

第四步：
开始起草正式文件：
- test_case_doc/xbar/xbar.md
- test_case_doc/xbar/ET6801_xbar.md

第五步：
以 boundary/channel validation 为第一个最小自动化测试闭环，确定 PC Driver / Firmware Service / Wrap / Formal Case 的最小实现顺序。
```

不要一次写完全部平台代码。每完成一个最小层，都回到 Feature / Case / Evidence 检查是否一致。

---

# 10. 下一批 IP 的复用方法

XBAR 完成后，其他 IP 不重新发明分析流程。

统一复用：

```text
ip-package / analysis
→ Source Registry
→ Evidence Ledger
→ Feature Catalog
→ Case Plan
→ public doc
→ chip overlay
→ driver/service/wrap/case implementation
→ verification
```

因此 XBAR 不只是一个 IP 工作，也是后续所有 ET6801 IP 的 production template。

需要在 XBAR 完成后总结：

```text
哪些 Source 最有用
哪些规则真正影响分析
哪些 Evidence 格式最有效
哪些 Feature/Case 模板可复用
哪些自动化层是每个 IP 的固定骨架
```

然后固化成后续 IP 快速接入流程。

---

# 11. Framework Backlog（先记录，不阻塞生产）

以下问题留给之后专门的 ET Harness 工程轮次：

```text
F-001 ChatGPT Portable Runtime
F-002 reproducible Runtime assembly / Cordis dependency consistency
F-003 protected-scope preflight enforcement
F-004 supervision obligation progression
F-005 valid Reflection / Closure path
F-006 Context persistence / next-task rehydration
F-007 live Gateway wrapper activation
```

除非某项直接阻塞 IP 测试开发，否则下一对话不要进入这些 Framework Bug。

---

# 12. 最终工作原则

本阶段最重要的判断标准已经改变。

以前：

```text
这个真实 IP 能不能暴露 Harness 问题？
```

现在：

```text
Harness 能不能帮助 Agent 更快、更准、更受约束地完成真实 IP 分析和测试开发？
```

业务优先级：

```text
IP 分析正确性
    > 测试设计质量
    > 测试代码可执行性
    > Evidence 可追踪性
    > Framework 完整性测试
```

Framework 的价值必须体现在真实工程产出上，而不是让真实工程等待 Framework 完美。

**下一对话从 ET6801 XBAR 正式分析与测试开发继续，不等待 Portable Runtime。**
