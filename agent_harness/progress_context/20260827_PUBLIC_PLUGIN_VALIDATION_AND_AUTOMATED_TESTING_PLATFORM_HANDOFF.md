# Agent Harness 公共插件验证与 Automated_Testing_Platform 接入 Handoff

日期：2026-08-27  
仓库：`abba-labs/et-tool`  
文档性质：阶段总结、纠错说明、测试边界、下一对话入口  

> **新对话必须先读本文件。**  
> 本文件用于回答：从接手 Harness 后做了什么、修了什么、测了什么、当前能证明什么、不能证明什么，以及下一步如何把 `Automated_Testing_Platform` 正确接入公共插件体系。

---

## 0. 一页结论

### 当前 canonical 基线

```text
repo: abba-labs/et-tool
branch: main
HEAD: f37b1080ca65388fc0e32f7fa75567b512c86752
```

该基线已经包含：

- P0/P1 最小治理加固；
- 真实任务矩阵与多角度负向测试；
- Public Layer Knowledge Policy 测试对齐；
- 分级 Knowledge 检索与 Evidence 反馈闭环。

### 当前已经证明

在 **`project-et-tool` 项目插件已经接入** 的前提下，公共插件可以自动完成：

```text
Project 识别
→ Architecture / Rule / Knowledge / Gate 路由
→ 有界 Context 构建
→ Tool Preflight 与代码变更识别
→ Review Epoch / Code Gate
→ Framework-owned Evidence
→ Reflection
→ 8/8 Closure
→ Knowledge Candidate / Verification / Promotion / 再次检索
```

### 当前尚未证明

```text
公共插件可以直接治理任意一个没有 Project Plugin 的外部仓库
```

`Automated_Testing_Platform` 当前没有接入对应 Project Plugin。因此，之前直接对该仓库创建分支和 PR 的操作，**不能计入公共插件验收**。

### 下一步唯一正确方向

```text
只读分析 Automated_Testing_Platform
→ 设计最小 Project Plugin
→ 先完成项目识别、资源路由和只读闭环
→ 再做无硬件、无编译的受治理代码修改 Pilot
```

在 Project Plugin 和真实 Host/Tool Bridge 建立前，禁止再次直接通过 GitHub Tool 修改 `Automated_Testing_Platform` 来宣称公共插件已经生效。

---

## 1. 用户已经冻结的设计原则

后续工作必须继续遵守以下原则。

### 1.1 效率优先，拒绝过度设计

Harness 的目标是：

> 提高 Agent 理解项目和完成开发的效率，同时守住会导致 Agent 失控、Evidence 混乱、Knowledge 污染和状态不一致的关键边界。

只修复真实漏洞，不为了理论完备增加：

- 复杂 Permit / 签名系统；
- 多项目 Quorum；
- 百分比置信度引擎；
- 每次 Tool Error 强制生成 Knowledge；
- 额外模型调用；
- 完整零信任 Host 沙箱；
- 当前没有收益的复杂 Scope Arbiter。

### 1.2 对话简洁，详细分析进仓库

对话框只给：

- 当前结论；
- 真实问题；
- 下一步。

详细设计、失败根因、测试记录和 Handoff 继续放在：

```text
agent_harness/progress_context/
```

### 1.3 Framework 触发，Agent 做语义判断

冻结关系：

```text
Framework：触发权、校验权、阻断权、状态写入权、晋级权
Agent：语义判断、Review 结论、Knowledge/Experience 提议权
```

不能回退为：

- Agent 自己决定是否治理；
- Agent 直接写 Evidence；
- Agent 直接修改 Knowledge 验证状态；
- Host Adapter 重新实现公共 Governance 业务逻辑；
- Agent 看到 raw shell 后依靠自觉执行 Preflight。

### 1.4 Knowledge 是分级知识池，不是已验证白名单

所有相关 Knowledge 都允许 Agent 获取：

```text
FULL_VALIDATED -> VERIFIED
VALIDATED      -> SUPPORTED
CANDIDATE      -> EXPLORATORY
DEPRECATED     -> HISTORICAL
CONTRADICT     -> DISPUTED overlay
```

但使用边界必须明确：

- `EXPLORATORY`：假设、排查线索、测试目标；
- `HISTORICAL`：历史背景、反例；
- `DISPUTED`：存在冲突，禁止当成确定事实；
- `SUPPORTED / VERIFIED`：可作为主要依据，但仍受 Scope 限制。

### 1.5 当前 Pilot 边界

下一阶段暂不做：

- 真实硬件；
- 固件烧录；
- J-Link / CMSIS-DAP / CAN / UART 设备操作；
- OTP / Flash / Option / Security 写入；
- 产品编译和 Release 构建。

下一阶段只验证：

- 项目接入；
- 自动 Context / Rule / Knowledge / Gate；
- 代码错误识别；
- 受控代码修改；
- 纯软件单元测试；
- Evidence / Reflection / Closure / Knowledge 闭环。

---

## 2. 从接手以来完成的工作

## 2.1 重新评估负向治理问题，收敛 P0 / P1

最初在：

```text
pilot/adversarial-governance-negative-v0.1
```

继续分析时，曾提出较多潜在治理问题。用户明确要求避免过度设计后，重新按“是否会真实导致开发出错、Agent 绕过、Knowledge/Evidence 污染、状态不一致”评估，最终只保留 P0/P1。

### P0 修复

1. **Global Knowledge 过度晋级**
   - 单个 Project 的 `REAL_TEST` 不能把 Global Knowledge 直接升为 `FULL_VALIDATED`；
   - Project Knowledge 可以依据本项目合法 Evidence 晋级。

2. **Agent-facing Tool 必须经过 Governed Tool Gateway**
   - raw executor 在 Gateway 内注册；
   - Agent-facing API 只传 invocation；
   - `recordEvidence`、Knowledge Verification / Promotion 等 Framework mutation API 不得注册为 Agent Tool。

3. **Closure 与 Knowledge Promotion 状态一致性**
   - 8/8 Closure 成功后 Turn 固定为 `CLOSED`；
   - 后续 Promotion 失败只产生 `knowledgePromotionWarnings`；
   - 不允许出现“Kernel 已 CLOSED、调用者却认为 closeTurn 整体失败”的状态分裂。

### P1 修复

- 同步 Knowledge Validation、Scope、Source Verification 和 Runtime 文档；
- 增加 Agent 不能直接写 Evidence / Knowledge 验证状态的测试；
- 高风险错误保持 `CHECK + EVIDENCE_CHECK`，不强制每次产生 Candidate。

### 合并与验证

```text
PR: #37
merge commit: 00b4c16832a95c2bc4132227346e257e1d5d155f
focused unit tests: 68/68 PASS
Round A: 9/9 PASS
Round B: 6/6 PASS
```

该阶段明确暂缓：

- Evidence Producer 签名；
- 多项目 Quorum；
- 完整 Runtime State Store；
- 每个错误强制 Knowledge Capture。

---

## 2.2 建立真实任务矩阵，发现并修复真实绕过路径

P0/P1 合入 `main` 后创建：

```text
validation/harness-real-task-matrix-v0.1
```

### 初始结果

```text
assertions: 53
PASS: 40
FAIL: 13
```

其中 1 项是测试断言错误，其余归并为真实问题。

### 暴露的真实问题

1. 相同文件第二次修改可能复用第一次 Review Packet / Evidence；
2. Context / Task Ledger 引用持续累加，导致当前 Review 无法生成；
3. Python、Node、`GitHub.update_file` 等修改方式未被识别；
4. Tool 部分写入后报错，只被视为 Tool Error；
5. `msbuild`、`devenv`、`nmake` 没被识别为直接构建；
6. Release 路径匹配过宽，可被伪后缀、前缀目录、路径穿越绕过；
7. Windows 路径分隔符反而可能被误拒绝。

### 最小修复

- 引入 `codeChangeEpoch / reviewEpoch`；
- 每次真实修改都要求当前轮次 Packet / Evidence；
- 当前路由替换 Working Set，不再无界追加；
- Task Ledger 引用设上限；
- 补齐 Python / Node / GitHub / shell mutation 识别；
- 失败 mutator 按“可能已修改”保守处理；
- 补齐 Windows 直接构建工具识别；
- Release 入口使用 canonical 完整路径边界匹配。

### 最终结果

```text
PR: #38
merge commit: 69d04ab9273695ee362b47ca002619710f9a92c1

18/18 package builds PASS
77/77 focused unit tests PASS
3 iterations × 53 assertions = 159/159 PASS

Positive Public Governance Runtime: PASS
Round A: 9/9 PASS
Round B: 6/6 PASS
```

### 真实任务矩阵覆盖

- 只读任务与同 Task Context 复用；
- 只读任务不制造垃圾 Knowledge；
- Project Knowledge 创建、验证、晋级、下一 Turn 再次路由；
- 两次连续修改和独立 Review Epoch；
- Gate 前 Build BLOCK，Gate 后正式 Release 入口放行；
- 旧 Evidence 不能授权新代码；
- CMake / Ninja / MSBuild / Devenv / NMake 负向矩阵；
- 伪 Release 路径负向矩阵；
- Python、Node、GitHub update、部分写入失败后的修改识别；
- 多 Runtime 隔离；
- 错误 Turn、关闭后写入、未关闭完成 Task 的阻断；
- Tool Error 不生成垃圾 Knowledge；
- 非法 Knowledge Category fail-closed。

---

## 2.3 对齐 Public Layer 旧测试，不放宽生产策略

Public Layer 集成测试中发现旧 Smoke 仍假设：

```text
两个任意 SUPPORT 就能让 Global Candidate READY
```

但正式策略已经明确：

- `CODE` 只能作为 `REFERENCE`；
- `DOCUMENT / SPEC / SVD` 才计入文档验证 Quorum；
- 普通 Experience Evidence 不能自动充当 Knowledge 验证 Evidence。

因此修复的是测试数据和断言，不是生产策略。

### 合并与关键回归

```text
PR: #39
merge commit: 85f1c5153b12c5d28d7062e1ee5e19cb460a8ab2
```

已记录成功回归：

```text
Public Layer v0.2: run 32972309457 PASS
Real Task Matrix: run 32972309480 PASS
Round A: run 32972404492 PASS
Round B: run 32972432390 PASS
Windows external closed loop: run 32971777653 PASS
```

该阶段验证的是：

- Public Plugin Integration；
- Knowledge Library / Dual Scope / Source Verification / Validation Policy；
- Context Management / Context Lint；
- Experience Memory；
- Public Layer Final Integration；
- Framework Efficiency Observer；
- Windows 路径、PowerShell/CMD、Release dry-run 与退出码链路。

注意：Windows 测试不是完整 Qt 产品构建，也不是硬件测试。

---

## 2.4 将 Knowledge 改为“全状态可见 + 分级使用 + Evidence 反馈”

用户指出原设计存在闭环问题：

```text
CANDIDATE 默认隐藏
→ Agent 看不到
→ 无法把它作为测试假设
→ 无法产生 SUPPORT / CONTRADICT
→ 永远无法自然演进
```

因此完成：

### 检索变化

- 默认检索不再隐藏 `CANDIDATE / DEPRECATED`；
- Context 展示 `TrustTier / UsePolicy`；
- 可靠 Knowledge 优先；
- 探索和历史 Knowledge 低优先级、有数量预算；
- Context 字符上限不增加；
- 被裁剪项保留紧凑 Handle，可按 K-ID 继续展开。

### Evidence 反馈链

```text
Agent 获取分级 K-ID
→ 把 CANDIDATE 当作假设
→ 可信 Tool/Test 产生 Evidence
→ Reflection 提议 SUPPORT / CONTRADICT
→ Runtime 校验 K-ID、Evidence、Project Scope、Claim Fingerprint
→ 追加 Verification
→ Policy 决定是否晋级或 BLOCK
```

### 不做的事情

- 不自动改写 Fact；
- 不自动删除冲突 Knowledge；
- 不引入百分比置信度；
- 不增加第三次模型调用；
- 不强制普通错误产生 Knowledge；
- 不无限扩大 Context。

### 合并与验证

```text
PR: #40
merge commit: f37b1080ca65388fc0e32f7fa75567b512c86752
validation run: 32983203506 PASS
```

新增闭环测试验证：

- CANDIDATE 自动检索；
- Context 标记 `EXPLORATORY`；
- Agent 不能把它描述为已确认事实；
- 真实 Evidence 产生 SUPPORT；
- SUPPORT 按 Policy 晋级；
- 后续 CONTRADICT 写回同一 K-ID；
- 冲突 Knowledge 继续可见；
- 显示为 `DISPUTED / BLOCKED`；
- 整个 Task 仍能完成 Closure。

---

## 3. 当前测试体系总览

| 层级 | 核心目的 | 当前结果 |
|---|---|---|
| Package Build | 公共插件和 Runtime 可构建 | 18/18 PASS（真实任务矩阵基线） |
| Focused Unit Tests | Knowledge、Context、Rule、Runtime、Project Plugin | 77/77 PASS（真实任务矩阵基线） |
| Real Task Matrix | 模拟 Agent 的完整工作链 | 3 × 53 = 159/159 PASS；分级 Knowledge 后扩展闭环场景 |
| Positive Runtime | 正常流程能否完成 | PASS |
| Round A | 工具、构建、生命周期直接绕过 | 9/9 PASS |
| Round B | Evidence、Knowledge、旧状态、多 Agent 污染 | 6/6 PASS |
| Public Layer | 公共插件模块集成 | PASS |
| Windows External Loop | Windows 脚本、路径、退出码 | PASS |
| Online Dialogue Pilot | 当前对话充当真实语义 Agent/Reviewer | 在 `project-et-tool` 上实验性 PASS，尚未合入 main |
| External Project Portability | 不同项目插件复用公共插件 | **尚未完成** |

---

## 4. PR #42：真正经过公共插件的在线对话 Pilot

用户要求“在当前对话中拿真实代码做一次、不做硬件、不做产品编译”。正确的公共插件 Pilot 是：

```text
repo: abba-labs/et-tool
PR: #42
branch: pilot/dialogue-real-project-code-fix-v0.1
head: b8597ee49a12d8c57b6c38f783287aeb859d67ff
status: OPEN / DRAFT / NOT MERGED
successful run: 33027831563
```

### 实际任务

修复 ET-TOOL automation runner 中嵌套 `${...}` 变量展开依赖 JSON 声明顺序的问题。

### 实际验证

- 旧实现真实复现：3 个测试中 2 个失败；
- 修复后：3/3 PASS；
- 自动 Project 识别；
- 自动 Architecture / Rule / Knowledge / Gate 路由；
- 代码修改识别；
- 生成 11 个 Review Packet；
- 当前对话逐项提交 Review 结论；
- Framework 创建 Review Evidence；
- Reflection；
- 8/8 Closure；
- Task `COMPLETED`；
- 生成 Knowledge `K001.029`；
- 晋级后立即被 Knowledge Search 再次提取。

### 该 Pilot 真正证明的内容

它证明：

> 在 `project-et-tool` 已正确接入的情况下，当前在线对话可以通过 Host Bridge 参与真实语义 Review，并由公共 Runtime 自动完成治理生命周期。

### 该 Pilot 暴露的问题

1. **旧 Knowledge Batch Gate 固定要求恰好 28 条 Knowledge**
   - 新增合法 Knowledge 后旧 Gate 失败；
   - 应验证原 Batch 成员，不应禁止后续增长。

2. **Context 裁剪可能让已路由 CANDIDATE 完全不可见**
   - 分支上增加有界紧凑 Handle；
   - 不增加 Context 字符上限和模型调用。

3. **Generated / transient 文件进入 Review Snapshot**
   - `__pycache__/*.pyc`；
   - Governance 生成的 `knowledge/00_INDEX.md`；
   - 它们不是目标产品修改，却增加 Review 噪声。

4. **路由过宽**
   - 一个小型 Python helper 修改加载了多个 ET6003 hardware-validation Architecture 节点；
   - 产生 11 个 Review Packet，效率偏低。

### 当前处理原则

PR #42 目前是实验性分支，不能自动作为 canonical 基线。

下一对话必须先决定：

- 哪些修复属于公共插件真实最小改进；
- 哪些是 Pilot 脚本或测试专用改动；
- 是否拆分 PR；
- 是否补充回归后再合并。

在完成上述审查前，不直接合并 PR #42。

---

## 5. Automated_Testing_Platform 的错误测试与纠正

## 5.1 发生了什么

之前直接在：

```text
repo: Abba-shenfu/Automated_Testing_Platform
branch: et-tool-target-client-batched-event-fix
PR: #36
head: 3a68f631c4943270a633a4b40e2fbd8549893e07
status: OPEN / DRAFT / NOT MERGED
```

修改了：

```text
pc/et_test_platform/clients/target.py
pc/et_test_platform/framework_validation/unit/test_target_client.py
```

该修改识别了一个真实业务代码缺陷：同一次读取中 `RESPONSE` 后紧跟 `EVENT` 时，旧逻辑可能因提前 return 丢失后续 EVENT。

但该操作是通过 GitHub Connector 直接写入仓库，并没有经过 Automated_Testing_Platform Project Plugin，因为该插件根本尚未存在。

## 5.2 为什么不能计入公共插件测试

该操作没有自动触发 Automated_Testing_Platform 对应的：

- Project registration / resolution；
- Architecture Navigator；
- Rule Manager；
- Knowledge Manager；
- Context Builder；
- Gate Manager；
- Evidence State Manager；
- Governance Runtime；
- 8/8 Closure。

因此准确结论是：

```text
业务代码缺陷识别：可能有效
公共插件跨项目验收：无效
```

## 5.3 当前处理建议

- PR #36 不得合并；
- 可关闭并删除分支，或保留为“错误方法样本”；
- 无论是否保留，都不能在后续报告中计入 Harness 验收；
- 在 Project Plugin 接入前，不再对 Automated_Testing_Platform 做任何业务代码写入。

---

## 6. 当前能够证明什么

### 6.1 可以证明

在 Project Plugin 正确接入、Agent 通过 Governance Runtime 与 Governed Tool Bridge 工作时：

- Framework 可以自动识别项目；
- Framework 可以自动路由 Architecture / Rule / Knowledge / Gate；
- Context 能自动创建、更新和有界复用；
- 代码修改会自动刷新 Review Epoch；
- 旧 Evidence 不能授权新修改；
- 直接构建和伪 Release 路径可以被阻断；
- Agent 不能直接注册 Evidence / Knowledge mutation Tool；
- Tool Error 不会强制制造垃圾 Knowledge；
- Knowledge 所有状态可以被召回；
- CANDIDATE 可以作为测试假设；
- Evidence 可以对同一个 K-ID 追加 SUPPORT / CONTRADICT；
- Framework 可以校验 Scope、Evidence 与 Claim Fingerprint；
- Reflection 与 8/8 Closure 可以自动完成；
- Knowledge 可以创建、晋级并在后续 Turn 再次提取。

### 6.2 不能证明

当前不能声称：

- Framework 永远没有 Bug；
- 任意外部仓库无需 Project Plugin 即可自动治理；
- 当前 ChatGPT 顶层 GitHub Tool 调用天然受 Harness 约束；
- Host 完全绕开 Runtime 时仍能被拦截；
- 所有强弱模型都已真实测试；
- 进程重启后的 Runtime State 自动恢复已经完成；
- 真实 Qt 产品构建已经通过；
- 真实硬件 Evidence 全链路已经通过；
- 多项目 Global Knowledge 泛化已经完成。

---

## 7. 公共插件与 Project Plugin 的正确关系

```text
外部真实项目
    ↓
Project Plugin
    ├─ 项目标识和根目录识别
    ├─ Architecture / Rule / Knowledge / Gate 资源
    ├─ 路径分类与生成文件排除
    ├─ Tool / Build / Hardware 边界
    ├─ Evidence Source 与项目 Scope
    └─ 项目特定 Review Adapter
    ↓
Public Plugins
    ├─ Project Manager
    ├─ Architecture Navigator
    ├─ Rule Manager
    ├─ Knowledge Manager
    ├─ Context Builder
    ├─ Evidence State Manager
    ├─ Gate Manager
    ├─ Agent Governance Kernel
    ├─ Closure Adapters
    └─ Governance Runtime
```

公共插件不应该硬编码 Automated_Testing_Platform 业务知识；这些内容必须由新的 Project Plugin 提供。

---

## 8. Automated_Testing_Platform 已知初始结构

当前 `main`：

```text
repo: Abba-shenfu/Automated_Testing_Platform
HEAD: cfcd02cd9adc466cc19e196debb88cd1040db529
```

已初步看到的主要结构：

```text
firmware/
  application/
  boards/
  build/et6801/ET6801_Automated_Test.uvprojx
  chips/
  framework/
  services/
  wrap/

pc/
  et_test_platform/
    clients/
    communication/
    drivers/
    framework_validation/unit/

companion/
report/
  analysis/
  design/
  plans/
  review/
  validation/

test_case_doc/
tools/
pyproject.toml
```

Python 项目已有：

```text
pytest testpaths = pc/et_test_platform/framework_validation/unit
```

当前没有发现可直接加载的 Harness Project Plugin 注册结构，例如：

```text
agent_harness/projects/automated_testing_platform/
cordis.patch.yml
```

这些只是初步事实。下一对话必须重新完整阅读仓库，而不是直接据此开始写插件。

---

## 9. 下一阶段：Automated_Testing_Platform 接入分析

## 9.1 阶段目标

不是马上修改业务代码，而是回答：

1. 这个项目如何被稳定识别？
2. 哪些目录和文件是 Architecture、Rule、Knowledge、Gate 的权威来源？
3. 哪些文件是产品代码、测试代码、生成文件、历史报告？
4. 哪些动作是普通代码修改，哪些是编译，哪些是硬件操作？
5. 如何用最少 Context 让 Agent 快速进入正确模块？
6. 如何复用公共插件而不把项目业务逻辑写回 Public Layer？

## 9.2 推荐集成位置

第一版建议在 `abba-labs/et-tool` 中新增：

```text
agent_harness/projects/automated_testing_platform/
```

而不是先在业务仓库内复制一套 Harness Runtime。

推荐骨架：

```text
agent_harness/projects/automated_testing_platform/
  package.json
  tsconfig.json
  cordis.patch.yml
  README.md
  src/
    index.ts
    project-manifest.ts
    path-classifier.ts
    review-adapter.ts
  architecture/
    00_INDEX.md
    010_project_topology.md
    020_pc_host_framework.md
    030_firmware_framework.md
    040_protocol_transport.md
    050_validation_evidence.md
  rules/
    00_INDEX.md
    100_project_boundaries.md
    200_pc_python_rules.md
    300_firmware_rules.md
    400_test_evidence_rules.md
    500_build_hardware_boundaries.md
  knowledge/
    00_INDEX.md
    TAXONOMY.yaml
    SOURCES.yaml
    001_library.md
  gates/
    00_INDEX.md
    010_rule_review.md
    020_code_review.md
    030_contract_review.md
    040_test_evidence_review.md
  tests/
    project-registration.test.ts
    routing.test.ts
    path-classifier.test.ts
    read-only-pilot.test.ts
```

第一版不要求一次建立庞大地图，只建立完成第一条无硬件 Pilot 所需的最小资源。

## 9.3 Project 识别建议

候选稳定 Marker：

```text
pyproject.toml
pc/et_test_platform/
firmware/build/et6801/ET6801_Automated_Test.uvprojx
firmware/framework/
report/design/
```

Project Plugin 应支持环境变量或 Host 显式传入外部根目录，例如：

```text
AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT
```

不能依赖固定的个人 Windows 绝对路径。

## 9.4 第一版 Architecture 只做必要分层

建议先建立 5 个主节点：

```text
A010 Project Topology
A020 PC Host Test Framework
A030 Firmware Test Framework
A040 Protocol And Transport Boundary
A050 Validation Evidence And Reports
```

暂不展开每个 IP、芯片和硬件工具的全部细节。

第一条 Pilot 若只修改 PC Python，则主要路由：

```text
A010 + A020 + A040 + A050
```

不应自动加载全部 FPGA、Keil、DMA、CAN、J-Link 知识。

## 9.5 第一版 Rule 只守真实边界

至少需要：

1. Pilot 禁止硬件操作；
2. Pilot 禁止产品编译和固件构建；
3. 允许写入范围必须显式限定；
4. 禁止修改生成文件和缓存；
5. 无硬件测试不得表述为 hardware PASS；
6. 代码修改必须有针对性测试；
7. 协议层修改必须保持 Frame / Message Contract；
8. PC 与 Firmware 边界不能被随意耦合；
9. Evidence 必须区分纯软件、仿真、硬件；
10. `main` 不直接写入，使用 Pilot 分支或隔离 Worktree。

## 9.6 Path Classifier 与生成文件排除是 P0 效率项

下一阶段必须先分析：

### 产品代码

```text
pc/et_test_platform/**/*.py
firmware/**/*.c
firmware/**/*.h
```

### 测试代码

```text
pc/et_test_platform/framework_validation/unit/**
```

### 设计、验证与历史文档

```text
report/design/**
report/validation/**
report/review/**
report/archive/**
test_case_doc/**
```

### 可能的生成/缓存文件

```text
**/__pycache__/**
**/*.pyc
.pytest_cache/**
tmp/**
coverage/**
```

注意：不能简单排除整个 `firmware/build/**`，因为其中可能包含受版本控制的 Keil 工程文件，例如 `.uvprojx`。必须区分：

- 工程配置；
- 编译中间产物；
- 自动生成 metadata；
- 真正源文件。

## 9.7 Knowledge 初始导入原则

第一版不要把所有 `report/` 文档全文导入 Context。

只登记少量权威 Source：

- 项目 README；
- PC 分层架构设计；
- ET-Frame / Service Protocol 设计；
- 当前有效的测试规范；
- 当前有效的 Build / Hardware 运行边界；
- 已确认的关键设计决策。

Knowledge 可以是 `CANDIDATE / VALIDATED / DEPRECATED` 任意状态，但必须带：

- Scope；
- Source；
- TrustTier；
- UsePolicy；
- Evidence / Contradict 状态。

历史 `report/archive/` 默认应作为 `HISTORICAL`，不能与当前设计同级。

## 9.8 第一版 Gate 应按任务裁剪

对纯同步 Python helper 修改，合理 Gate 可能只有：

```text
Rule Review
Code Logic Review
Error/Boundary Review
Contract Review（仅修改公开协议时）
Focused Test Evidence
```

不应无条件生成：

- Hardware Gate；
- Firmware Build Gate；
- Lifecycle Gate；
- Release Gate；
- 与目标文件无关的所有芯片路线 Gate。

目标是避免 PR #42 中“小改动产生 11 个 Packet”的效率问题。

---

## 10. 正确的跨项目测试路线

## Phase A：只读分析

```text
不修改 Automated_Testing_Platform
```

输出：

- 项目结构清单；
- 权威 Source 清单；
- generated/transient 清单；
- Architecture / Rule / Gate 初稿；
- Project Plugin 最小 Contract。

验收：

- Project 能被识别；
- 只读任务能自动路由；
- Context 有界；
- 不产生垃圾 Knowledge；
- 不触发 Code Gate。

## Phase B：隔离 Snapshot 公共插件验证

在 `et-tool` CI 或临时 Worktree 中放置 Automated_Testing_Platform 的受控 Snapshot，加载新 Project Plugin。

验证：

- 公共插件不依赖 `project-et-tool`；
- 新项目能独立注册；
- Architecture / Rule / Knowledge / Gate 使用新项目资源；
- 多项目 Runtime 状态隔离；
- Project Knowledge 不污染 Global；
- 生成文件排除正确。

## Phase C：真实外部仓库只读 Pilot

GitHub Actions 或 Host 同时 checkout：

```text
et-tool Harness repo
Automated_Testing_Platform target repo
```

设置外部 Project Root，运行：

```text
openTurn
→ read-only code analysis
→ route / context
→ Reflection
→ 8/8 Closure
```

不写目标仓库。

## Phase D：真实外部仓库受治理修改

只有 A/B/C 全部通过后，才选择一个小型、无硬件、无需产品构建的真实缺陷。

完整链：

```text
当前对话提出任务
→ Project Plugin 自动识别
→ Public Runtime 自动路由
→ Governed Tool 修改隔离分支/Worktree
→ 自动识别 mutation
→ 生成当前 Review Epoch
→ 当前对话提交 Review
→ Framework Evidence
→ focused pure-software test
→ Reflection
→ 8/8 Closure
→ Knowledge 贡献与再提取
```

### 关键真实性要求

当前 ChatGPT 顶层的 `GitHub.update_file` 本身不天然受 Harness 约束。

因此跨仓库真实修改必须使用：

- External Chat Agent Bridge；或
- CI 中受 Runtime 包装的 Git / File Tool；或
- 专门的 Governed GitHub Adapter。

禁止再次：

```text
先直接调用 GitHub.update_file 修改外部仓库
再事后生成一份 Harness 报告
```

这种方式只能证明 Agent 会改代码，不能证明公共插件自动治理了 Agent。

---

## 11. Automated_Testing_Platform Project Plugin v0.1 验收标准

### 项目接入

- [ ] 项目根目录可通过 Marker 或显式 Root 稳定识别；
- [ ] 与 `project-et-tool` 并存，不冲突；
- [ ] 卸载后项目资源完全清理。

### Context 与路由

- [ ] PC Python 任务只加载相关 PC / Protocol / Test 资源；
- [ ] 不加载无关芯片和硬件路线；
- [ ] Context 不超过现有预算；
- [ ] 被裁剪 Knowledge 保留紧凑 Handle。

### Rule / Gate

- [ ] 无硬件 Pilot 自动阻断硬件动作；
- [ ] 无编译 Pilot 自动阻断编译动作；
- [ ] 只读任务不触发 Code Gate；
- [ ] 代码修改触发新 Review Epoch；
- [ ] Gate 数量与任务实际影响范围相符。

### Evidence / Knowledge

- [ ] 纯软件 Test Evidence 不被表述为 hardware PASS；
- [ ] Agent 不能直接写 Evidence；
- [ ] CANDIDATE 可以被检索和测试；
- [ ] SUPPORT / CONTRADICT 可以写回同一个 K-ID；
- [ ] Project Knowledge 不污染 Global；
- [ ] 普通失败不制造垃圾 Knowledge。

### 生命周期

- [ ] Reflection 自动触发；
- [ ] 8/8 Closure 完成；
- [ ] Task `COMPLETED`；
- [ ] 新对话可依据 Handoff 恢复。

---

## 12. 下一对话的执行顺序

下一位 Agent 不要直接改代码，按以下顺序执行：

1. 阅读本文件；
2. 阅读：
   - `20260826_HARNESS_CURRENT_STATE.md`；
   - `20260826_TEST_STRATEGY_AND_RESULTS.md`；
   - `20260826_REAL_TASK_MATRIX_AND_HARDENING.md`；
   - `20260826_KNOWLEDGE_TIERED_REFERENCE_FEEDBACK.md`；
3. 确认 canonical `main = f37b1080...`；
4. 检查 PR #42，区分可合并的公共修复与 Pilot 专用内容；
5. 将 Automated_Testing_Platform PR #36 标记为无效 Harness 验收样本，不得合并；
6. 对 Automated_Testing_Platform 做完整只读分析；
7. 输出：
   - `Automated_Testing_Platform` 接入分析；
   - 最小 Project Plugin 设计；
   - 路径分类和 generated exclusion；
   - 第一条只读 Pilot 方案；
8. 用户确认接入设计后，才创建 Project Plugin 骨架；
9. Project Plugin 通过只读和 Snapshot 测试后，才进行真实代码修改 Pilot。

---

## 13. 冻结结论

```text
公共插件核心能力：已在 project-et-tool 上通过大量正向、负向和真实任务测试
在线对话治理闭环：在 project-et-tool 上实验性通过
Knowledge 全状态检索与反馈：已合入 main
公共插件跨项目可移植性：尚未证明
Automated_Testing_Platform 直接修改：方法错误，不计入验收
下一阶段：只读分析 + 最小 Automated_Testing_Platform Project Plugin
```

最重要的边界：

> **真实项目测试不是“找一个仓库直接改代码”，而是“先让该项目接入 Project Plugin，再验证公共插件能否自动治理 Agent 完成真实任务”。**
