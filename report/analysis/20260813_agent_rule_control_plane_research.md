# Agent 规则控制面研究

时间：2026-08-13 CST
状态：研究提案，非现行规则
范围：platform-common / docs / tooling
硬件：不涉及

> 本文用于验证未来规则治理方向，不具备规则效力，不覆盖 `AGENTS.md` 或任何当前有效契约，
> 也不授权修改公共架构。只有经过用户审核、形成独立实施计划并完成迁移验证后，其中的结论
> 才能进入正式规则体系。

## 1. 研究目标

本次研究不再回答“还缺哪一条规则”，而是回答以下系统性问题：

1. 未来规则持续增加时，怎样避免每次都扩大 Agent 启动上下文？
2. 怎样保证一个任务只加载真正适用的规则，而不是让 Agent 自行翻阅全部文档？
3. 怎样区分稳定契约、执行规则、设计提案、历史结论和运行证据？
4. 怎样保证 Review 中发现的问题真正升级为长期约束，而不是下一轮再次出现？
5. 怎样在保持轻量化的前提下，让规则可验证、可替代、可追溯？
6. 怎样保证规则体系适合 Agent，而不是仅仅适合人阅读？

最终目标不是建设一个“规则文档库”，而是建设一个轻量的 **Agent 规则控制面**。

## 2. 当前问题的本质

### 2.1 当前不是缺少规则，而是缺少控制关系

现有仓库已经具备大量架构、Case、Driver、Service、Wrap、IRQ、Capability、报告和工具规则。
真正缺失的是以下关系：

```text
任务
  -> 适用规则
  -> 唯一权威来源
  -> 允许修改的边界
  -> 必须执行的门禁
  -> 产生的证据
  -> 规则冲突或缺口时的停止条件
```

当前这些关系主要依赖 Agent 阅读自然语言后自行推断。因此规则数量增加以后，会同时出现：

- 旧设计与当前规则共同留在 `design/`；
- 同一职责由多份文档重复解释；
- Checker 执行了文档中无法直接定位的隐式规则；
- Review 发现的问题没有稳定升级为 Contract、Checker 和回归测试；
- “整体冻结”后又因为局部语义仍在演进而继续重构；
- Agent 为了保险加载过多文档，真正的红线反而被稀释。

### 2.2 真实失效案例

2026-08-05 的平台 Review 已经指出：固定附件文件名会导致参数化、重复运行和并行运行
覆盖旧结果，并给出了 `case_run_id` 归档方向。该结论后来没有完整升级为：

```text
唯一权威规则
+ 机器门禁
+ 回归测试
+ 旧指导退出
```

因此后续开发再次产生同类问题。这说明当前闭环仍然是：

```text
发现问题 -> 修复当前代码
```

而应当是：

```text
发现问题
-> 判断是局部缺陷还是系统规则缺口
-> 修复代码
-> 必要时升级唯一规则
-> 更新门禁和回归场景
-> 使同类问题无法再次进入
```

### 2.3 当前加载成本已经影响可靠性

按现有规则路由粗略估算，不含 IP 分析文档：

| 任务 | 当前可能加载的规则文档 | 近似规则上下文 |
|---|---:|---:|
| 局部 PC Case 修复 | 4 | 约 1.28 万 tokens |
| 新增普通 IP 全链路 | 10 | 约 3.03 万 tokens |
| 新增 IRQ 型 IP | 11 | 约 3.49 万 tokens |
| 修改 Wire 协议 | 7 | 约 1.91 万 tokens |
| 新增芯片适配 | 7 | 约 1.99 万 tokens |
| 架构评审 | 6 | 约 2.30 万 tokens |

单个公共 IP 文档还可能增加约 1～1.6 万 tokens。问题不只是 Token 成本，而是：

- 多份文档重复描述同一边界；
- 当前规则、示例、历史和提案同时进入上下文；
- Agent 需要自行解决冲突；
- 局部修改被迫理解与任务无关的大量细节。

## 3. 适合本项目的设计原则

### 3.1 稳定的是治理机制，不是所有具体规则

未来芯片、IP、仪器和测试方法一定会变化，不能要求现在一次写完未来所有规则。

真正需要稳定的是：

```text
规则怎样被提出
规则怎样进入有效状态
规则怎样匹配任务
规则怎样被机器验证
规则怎样被替代
规则怎样退出 Agent 当前上下文
```

### 3.2 Agent 不负责自由选择权威规则

Agent 可以分析工程事实，但不应在多个互相矛盾的规则文件之间自行选择一个“看起来更新”的版本。

必须由确定性元数据给出：

- 当前有效规则；
- 适用任务和路径；
- 唯一来源；
- 替代关系；
- 对应门禁；
- 需要人工确认的风险边界。

### 3.3 规则正文仍然只有一份

机器索引只保存元数据和路由，不复制规则正文。否则很快会形成“YAML 一份、Markdown 一份、
Checker 又一份”的三套规则。

```text
规则索引 = 这条规则在哪里、何时适用、由什么验证
规则正文 = 规则本身的唯一说明
Checker   = 对可确定部分的机器执行
```

### 3.4 不能把每个缺陷都升级成新规则

只有满足下列任一条件时，才应新增或修改公共规则：

- 影响公共稳定语义或跨组件契约；
- 影响硬件安全、破坏性操作或证据可信度；
- 同类错误可能跨 IP、跨芯片或跨任务重复发生；
- 现有规则存在真实歧义、冲突或无法覆盖的边界；
- 需要新的确定性门禁才能防止回归。

单个实现 Bug、局部变量命名或一次性代码错误，应通过代码和单元测试解决，不应自动增加规则。

### 3.5 默认失败关闭

出现以下情况时，Agent 不得继续猜测：

- 两条 `active` 规则声明同一职责但内容冲突；
- 任务涉及稳定契约变化，但没有声明兼容性类别；
- Checker 报错无法定位到权威规则；
- 需要新增公共层、新抽象或改变架构责任链；
- 需要执行破坏性硬件操作但没有人工确认；
- 规则包引用已废弃、已替代或不存在的来源。

## 4. 最小规则控制面

本项目不需要 OPA、数据库、服务端规则引擎、插件系统或多 Agent 治理。最小控制面只需要六个对象。

### 4.1 Kernel：始终加载的不变量

Kernel 是精简后的 `AGENTS.md` 职责，只保留所有任务都必须知道的内容：

- 项目目标和跨芯片原则；
- 不得伪造硬件证据；
- 不得擅自改变公共架构或稳定契约；
- 文件和 Git 安全；
- 必须声明任务范围和硬件风险；
- 必须通过规则路由器取得任务规则包；
- 冲突、缺口和高风险动作的停止条件。

Kernel 不应继续承载某个 IP、某种 Case 写法或某个工具目录的详细规则。

### 4.2 Catalog：机器可读的规则索引

Catalog 只保存路由元数据，不保存规则正文。最小概念字段为：

```yaml
id: ET-RULE-PC-CASE-001
kind: contract
status: active
scope:
  tasks: [case_add, case_modify]
  layers: [pc.case]
source:
  file: report/design/pc_case_writing_rules.md
  anchor: case-owns-final-oracle
enforced_by:
  - tools/quality/check_pc_code_rules.py:ETPCxxx
  - pc/unit/test_case_rules.py
supersedes: []
```

Catalog 明确禁止：

- 复制完整规则正文；
- 编写可执行表达式 DSL；
- 保存芯片寄存器、IRQ、地址或板级事实；
- 保存当前任务状态；
- 保存测试结果和历史结论。

### 4.3 Canonical Rule：唯一规则正文

规则正文按职责只有一个 Owner。建议的规则类型只有四类：

| 类型 | 回答的问题 | 示例 |
|---|---|---|
| Invariant | 永远不能违反什么 | 公共语义不得绑定具体芯片 |
| Contract | 两个组件之间稳定承诺什么 | Wire、Case ID、Service、Wrap API |
| Policy | 哪类修改必须怎样完成 | 代码修改、硬件操作、证据和验收 |
| Procedure | 已决定的工作怎样执行 | 新增 IP、烧录、发布、报告生成 |

以下内容不是规则：

| 内容 | 正确归属 |
|---|---|
| 为什么做出架构决定 | ADR |
| 尚未批准的改造方向 | Plan / Proposal |
| 一次代码审核结论 | Review |
| 某次运行结果 | Evidence / Artifact |
| 教学示例和模板 | How-to / Template |
| 某芯片事实 | Chip Capability / Mapping |

### 4.4 Task Descriptor：本次任务的最小描述

Task Descriptor 不建设第二套项目状态。它复用 `PROJECT_STATE.json` 和 `ACTIVE.md`，只补充规则路由
必须知道、但当前状态中没有表达的字段：

```yaml
task_kind: case_modify
target: aes
layers: [pc.case]
change_class: bugfix
hardware: false
```

该描述可以由 Agent 在运行前生成到临时目录，也可以未来由 `ACTIVE.md` 的结构化字段提供。
不要求用户手工维护第二份长期配置。

### 4.5 Rule Packet：当前任务的最小规则包

Rule Packet 由确定性脚本生成，只包含：

- 本次任务适用的规则 ID；
- 每条规则的一句约束摘要；
- 精确正文路径和锚点；
- 必须执行的门禁；
- 禁止触碰的范围；
- 需要人工确认的动作；
- 发现冲突时的失败原因。

它是临时运行输入，不是新的长期规则文件。

### 4.6 Gate / Eval：证明规则执行正确

Gate 检查代码和文档是否违反规则。Eval 检查“规则控制面自己是否工作正确”。二者不能混为一谈。

```text
Checker/Gate：这次代码是否违反 ET-RULE-PC-CASE-001？
Rule Eval：case_modify 任务是否正确加载 ET-RULE-PC-CASE-001，且没有加载已替代规则？
```

## 5. 两个相互独立的状态维度

### 5.1 规则生命周期

轻量化生命周期只需要四种状态：

```text
draft -> active -> deprecated -> superseded
```

- `draft`：只用于讨论，不进入 Agent 任务规则包；
- `active`：当前唯一有效规则；
- `deprecated`：仍兼容但不允许新开发继续使用；
- `superseded`：只保留历史追溯，必须指向替代规则。

同一职责不得同时存在两条互相竞争的 `active` 规则。

### 5.2 公共契约成熟度

契约成熟度不能再用“整个公共层已冻结”表达，而应按契约单元管理：

```text
evolving
stable
```

- `evolving`：允许经过审核的兼容调整；
- `stable`：兼容扩展必须显式说明，破坏性变化必须版本化并取得用户批准。

规则生命周期回答“这条规则是否生效”；契约成熟度回答“这个公共语义允许怎样变化”。二者不能混用。

## 6. Agent 固定执行闭环

```text
1. 读取 Kernel、PROJECT_STATE、ACTIVE
2. 声明 Task Descriptor
3. Rule Resolver 生成 Rule Packet
4. 若冲突、缺失或触发高风险条件 -> 停止并请求确认
5. 只读取 Rule Packet 指向的正文锚点和目标代码
6. 实施最小变更
7. 执行 Packet 声明的 targeted gate
8. 执行适用的总门禁
9. 生成证据并确认未触碰禁止范围
10. 若发现规则缺口 -> 单独进入规则变更流程，不在功能修改中顺手补规则
```

关键限制：Agent 不能因为“当前代码不好实现”而自行新增层、Registry、Adapter、Protocol 或通用抽象。

## 7. 规则变更闭环

规则变化应与普通代码变化分开处理：

```text
问题证据
-> 分类：实现缺陷 / 规则歧义 / 规则缺失 / 契约变化
-> 形成 draft 提案
-> 影响范围和兼容性评估
-> 用规则场景 Eval 验证
-> 高风险项取得用户批准
-> 修改唯一正文与 Catalog
-> 同步 Checker / Review Gate / 回归测试
-> 旧规则标记 superseded
-> 最后才切换为 active
```

以下变化必须人工确认后才能进入实现：

- 新增或删除公共层；
- 改变 `Case -> Driver -> Service -> Wrap -> Chip Driver` 责任链；
- 改变稳定 Wire、Case ID、Service 或 Wrap API 语义；
- 改变 canonical Result / Artifact / Evidence 结构；
- 增加跨 IP 隐式编排；
- 引入新的规则框架、运行时 Registry 或插件机制；
- 执行破坏性硬件操作。

## 8. 典型任务纸面模拟

### 8.1 修改一个现有 PC Case

输入：

```yaml
task_kind: case_modify
layers: [pc.case]
change_class: bugfix
hardware: false
```

期望规则包：

```text
公共芯片中立不变量
Case Contract
目标 IP 的目标 Case 语义块
Case 代码样式门禁
目标单元测试和软件门禁
```

不应加载：Firmware Service、Wrap、IRQ、Capability 生成、架构总设计、历史 Review。

### 8.2 新增普通 IP

输入：

```yaml
task_kind: ip_add
layers: [ip.contract, pc.driver, pc.case, firmware.service, firmware.wrap]
change_class: compatible
hardware: false
```

期望规则包只包含每个责任边界的一条有效 Contract，不再加载多份模板、旧提案和最终实施记录。

若 Agent 试图修改 Scheduling、TargetClient、公共协议或 Result Core，Resolver 必须标记为超出任务范围。

### 8.3 新增 IRQ 型 IP

在普通 IP 规则包基础上增加 IRQ Contract。只有使用 DMA 时才增加 DMA/DMAMUX 相关规则。

不允许因为“中断复杂”默认加载全部硬件、报告和历史设计。

### 8.4 新增芯片适配

期望加载：

```text
公共芯片中立不变量
Chip Capability / Mapping 规则
Firmware Chip Config / Board / Build 规则
目标 IP 的公共契约摘要
```

不应默认修改公共 Case、Driver、Service、Wrap API。只有发现真实公共语义缺口时，任务升级为独立契约变更。

### 8.5 修改 Wire 协议

Resolver 必须要求声明：

```text
bugfix / backward-compatible / breaking
```

如果是 `breaking` 或无法判断，必须在编辑代码前停止并请求用户确认。PC 与 Firmware 必须同时进入影响范围。

### 8.6 修改报告或 Evidence

只加载 Result/Artifact/Evidence Contract 和报告导出规则，不自动加载全部 Case 设计。

若变化改变 canonical Result Schema，则属于稳定契约变化，不得以“展示优化”名义直接修改公共层。

### 8.7 硬件执行

规则包必须明确：目标、板卡、连接路径、命令、预期结果、恢复路径、Artifact 目录和破坏性。
破坏性动作必须停在人工确认之前。

### 8.8 架构变化

任何新增公共层、Adapter、Registry、Plugin 或依赖反转，第一轮输出只能是：

```text
问题证据
候选方案
对现有责任链的影响
兼容与迁移计划
替代方案
```

没有用户确认，不进入代码实施。

## 9. 规则控制面自身的 Eval

未来上线前至少应具备以下确定性场景测试：

| Eval | 通过条件 |
|---|---|
| 路由正确性 | 每个典型任务只得到预期规则 ID |
| 排除正确性 | Proposal、Review、superseded 规则不进入 Packet |
| 冲突检测 | 同职责多条 active 规则时失败关闭 |
| 来源完整性 | 每条 active 规则的文件与锚点真实存在 |
| 门禁可追溯 | 每个 Checker 规则码能找到规则 ID 和正文 |
| 变更分类 | 稳定 Wire/Result/API 变化能触发人工确认 |
| 芯片隔离 | 普通公共 IP 任务不加载具体芯片事实 |
| 硬件安全 | 破坏性动作无法绕过确认门禁 |
| 上下文控制 | 相比当前路由显著减少无关规则，且不漏红线 |
| 替代闭环 | superseded 规则只可追溯，不可再参与执行 |

Eval 使用固定任务描述和期望 Rule Packet，不需要调用硬件，也不需要使用 LLM 判断 PASS。

## 10. 与现有 project-control 的关系

现有轻量上下文控制面继续保留：

| 现有对象 | 回答的问题 |
|---|---|
| `PROJECT_STATE.json` | 当前仓库和里程碑事实是什么 |
| `ACTIVE.md` | 当前唯一活动任务是什么 |
| `QUEUE.md` | 后续有限候选任务是什么 |
| ADR | 为什么做出某个架构决定 |
| Evidence | 哪些结论已被证明 |
| History | 过去发生过什么 |

规则控制面只补充：

| 新职责 | 回答的问题 |
|---|---|
| Rule Catalog | 当前有哪些有效规则及其唯一来源 |
| Rule Resolver | 本任务适用哪些规则 |
| Rule Packet | Agent 本次必须遵守什么 |
| Rule Eval | 路由、替代和高风险门禁是否工作正确 |

二者之间不复制状态、历史、证据或规则正文。

## 11. 明确不引入的复杂机制

当前阶段明确排除：

- OPA/Rego 或其他通用策略 DSL；
- 数据库或常驻规则服务；
- 多 Agent 审批编排；
- 动态插件式规则加载；
- 运行时依赖注入容器；
- 自动修改规则正文的生成器；
- 为每个 IP 复制一套规则；
- 每次缺陷都创建一份新规则文档；
- 一次性大规模迁移全部文档。

建议实现形态应保持为：

```text
少量 YAML 元数据
+ 一个无第三方依赖的只读 Resolver/Validator
+ 现有 Markdown 唯一正文
+ 现有 Checker/pytest
```

## 12. 分阶段验证建议

### 阶段 A：只读 Catalog 审计

- 不移动、不改写任何现有规则；
- 为现有规则建立试验性 Catalog；
- 标记职责重复、状态不明、无门禁和已被替代的内容；
- Resolver 只输出报告，不参与正式开发。

### 阶段 B：任务路由模拟

- 使用本文件的八类场景作为 Eval；
- 对比当前加载集合与候选 Rule Packet；
- 验证没有遗漏硬件安全、芯片隔离和稳定契约红线；
- 验证上下文显著减少。

### 阶段 C：Checker 可追溯

- 不重写 Checker；
- 先为现有 Checker 规则码建立规则 ID 映射；
- 失败信息能够指向唯一规则正文；
- 发现 Checker 内部存在无正文规则时，先评审其合理性。

### 阶段 D：小范围试运行

- 选择一个局部 Case 修改和一个新增 IP 任务试运行；
- 仍保留当前 `AGENTS.md` 作为安全兜底；
- 对比遗漏率、冲突数、加载量和 Agent 返工次数；
- 数据证明有效后，再讨论正式迁移。

### 阶段 E：渐进式规则收敛

- 每次只收敛一个责任域；
- 将旧提案或重复规则标记为 superseded/archive；
- 同步 Catalog、Checker、回归测试和索引；
- 禁止一次性重写全部规则文档。

## 13. 本阶段研究判断

本项目适合建设轻量 Agent 规则控制面，但不适合立即重构全部规则文档。

当前最安全的下一步不是修改 `AGENTS.md`，而是：

```text
建立只读试验 Catalog
-> 为现有规则分配稳定 ID 和唯一 Owner
-> 用典型任务生成 Rule Packet
-> 用 Eval 验证路由和停止条件
-> 证明有效后再请求用户批准迁移
```

如果这一步失败，只删除试验元数据和脚本，不影响现有代码、规则、测试和硬件流程。

## 14. 只读原型验证结果

本轮在项目 `tmp/rule-control-plane-prototype/` 中建立了可删除原型：

```text
catalog.yaml    # 少量现有规则的实验索引
scenarios.yaml  # 典型任务与期望规则包
evaluate.py     # 无LLM判断的确定性路由与冲突检查
```

该原型不是正式工具，不进入 `tools/`、`AGENTS.md`、现有 Checker 或软件门禁。

### 14.1 第一轮发现：新增芯片路由错误

最初原型把 `chip_add` 路由到公共 PC Driver 和公共 Wrap。这虽然符合“新增芯片可能涉及适配代码”
的直觉，却违反既定边界：正常新增芯片应增加 Profile、Board、Chip Config、Capability 和芯片
Driver 事实，不应默认修改公共 Driver、Service 或 Wrap API。

场景 Eval 在代码修改前发现了该错误，随后将 `chip_add` 规则包收敛为：

```text
公共芯片中立不变量
+ Capability Contract
+ Chip Adaptation Boundary
```

### 14.2 第二轮发现：层级不能代替唯一责任域

最初冲突检查使用：

```text
rule kind + task kind + layer
```

它把公共 IP 语义 Contract 和 PC Case 责任 Contract 误判为冲突，因为二者都会作用于
`case_modify / pc.case`，但解决的是不同问题。

因此 Catalog 必须显式包含稳定 `owner`，表示“这一条规则唯一拥有的语义责任域”。冲突检查
基于 `owner`，不能根据文件名、目录或层级猜测。

该字段是规则唯一性的最低必要信息，不是新增运行框架。

### 14.3 验证结果

修正后的实验结果：

```text
synthetic active-owner conflict                PASS，失败关闭
local_case_bugfix                              PASS
add_normal_ip                                  PASS
add_irq_ip                                     PASS
add_chip                                       PASS
breaking_wire_change                           PASS，要求人工确认
report_display_change                          PASS
destructive_hardware_run                       PASS，要求人工确认
architecture_adapter_proposal                  PASS，要求人工确认
tool_pipeline_change                           PASS
```

同时确认：

- `superseded` 历史规则不会进入当前 Rule Packet；
- 局部 Case 修改不会加载 Firmware、IRQ 和历史 Evidence 提案；
- 普通 IP 与 IRQ IP 的规则包能够按真实责任增量区分；
- 新增芯片不会默认修改公共 Case、Driver、Service 和 Wrap；
- 架构新增层和破坏性 Wire/硬件操作能够在实施前停止；
- 人为加入同 `owner` 的第二条 `active` 规则时，Catalog 校验失败。

### 14.4 尚未证明的部分

本轮只证明了元模型和场景路由方向可行，尚未证明：

- 全部现有规则都能无歧义分配唯一 `owner`；
- 当前 96 个左右的 Checker 规则码都能映射到权威 Rule ID；
- Markdown 锚点变化能被可靠检测；
- 真实任务中规则包不会漏掉某条必要红线；
- 规则包的上下文减少量达到最终目标；
- 现有冲突文档能够低风险完成迁移和退出。

因此本轮不能直接批准修改 `AGENTS.md` 或启用正式 Resolver。

## 15. 外部研究参考

- OpenAI Codex Agent Loop：`AGENTS.md` 的聚合和上下文机制；
  <https://openai.com/index/unrolling-the-codex-agent-loop/>
- OpenAI Practical Guide to Agents：清晰指令、确定性 Guardrail、Eval 和高风险人工介入；
  <https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/>
- AGENTS.md：根级与路径级 Agent 指令的作用域；
  <https://agents.md/>
- Kubernetes KEP Process：提案状态、批准、替代和长期追踪；
  <https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md>
- OpenTelemetry Semantic Convention Stability：按语义组管理成熟度与废弃；
  <https://opentelemetry.io/docs/specs/semconv/general/semantic-convention-groups/>
- Semantic Versioning：必须先声明公共 API，才能判断兼容和破坏性变化；
  <https://semver.org/>

## 16. 现有规则体系完整盘点结论

本节记录的是对当前工作树的只读审计结论，不代表已经批准迁移或启用新的规则机制。
盘点原始数据与校验原型位于项目 `tmp/rule-control-plane-prototype/`。

### 16.1 当前不是“缺少规则”，而是规则对象没有分型

本轮共盘点 26 份与开发约束相关的文档：

| 文档角色 | 数量 | 当前问题 |
|---|---:|---|
| Kernel / Router | 3 | 每次启动固定加载约 1.1 万 Token，且仓库级入口同时承担不变量、路由、流程、Git 和规则治理 |
| Canonical Contract | 8 | 基本覆盖当前 PC、Case、Service、Wrap、IRQ、Wire 和 Capability，但其中 3 份没有显式生命周期状态 |
| Procedure / Template / Checklist | 4 | 与 Canonical Contract 重复描述较多，模板会随着实现变化而漂移 |
| Proposal / Reference / Implementation Record | 7 | 多份仍位于 `report/design/`，部分内容与当前架构直接冲突，却缺少明确失效标识 |
| Local Policy / Index | 3 | `tools`、`artifacts` 的局部规则有效；`report/README.md` 只是索引，不应承担规则语义 |
| Mixed Legacy | 1 | 同一文件同时保存已废弃方案、现行过程和历史测试记录，无法确定加载边界 |

26 份文档约 7.7 万 Token。即便只计算 8 份 Canonical Contract，也约 2.3 万 Token。
因此，未来不能通过“要求 Agent 多读几份完整文档”解决可靠性问题；必须让任务只加载精确 Owner、规则摘要和正文锚点。

### 16.2 已确认的三组现实冲突

1. **Case 结构化证据冲突**：当前 `pc_case_writing_rules.md` 要求 Case 记录结构化观测；
   旧 `pc_ip_test_layer_simplification_design.md` 却要求普通 Case 不再写 JSON。旧文档仍处于
   `report/design/`，Agent 仅靠路径无法判断其已失效。
2. **Artifact 位置冲突**：当前仓库规则与 `artifacts/README.md` 要求输出位于仓库内
   `artifacts/runs/`；旧 `report_repository_governance.md` 仍要求仓库外 Artifact，且文档自称已确认。
3. **Chip Adapter 冲突**：当前责任链为 `Service -> Own Wrap -> Chip Driver`；总体架构草案仍多处
   要求 SDK/Board Adapter。该旧方向已经实际诱发过错误重构，说明“读到冲突文档”不是理论风险。

这些冲突的共同根因不是正文措辞不够严，而是缺少机器可读的：

```text
document role + lifecycle + unique owner + superseded_by
```

### 16.3 Checker 已经形成第二套隐式规则系统

当前 10 个 Checker 共提取出 155 个唯一诊断码，但：

- 只有 1 个诊断码能从权威入口或契约正文直接追溯；
- 7 个 `ETCASE` 诊断码在两个 Checker 中重复使用且含义不同；
- Firmware 架构 Checker 没有稳定诊断码；
- 多个 Checker 同时跨越代码分层、注释、芯片中立、Case Schema 和文档同步等责任域。

这不意味着要立即拆分 10 个 Checker，也不意味着要为 155 个错误码创建 155 条规则。
正确的最小收敛目标是：

```text
每个诊断码唯一
-> 映射到一个稳定规则 Owner
-> 指向该 Owner 的唯一正文锚点
```

Checker 文件可以暂时保持现状；先解决“诊断不可追溯”和“编号冲突”，再根据真实维护成本决定是否拆分。

### 16.4 当前最重要的权威缺口

现状中最值得优先形成唯一 Owner 的，不是未来可能出现的所有设备，而是已经存在大量实现和门禁、
却仍依赖分散文字或 Checker 隐含语义的四个领域：

| 优先级 | 缺口 | 现在必须处理的原因 |
|---|---|---|
| P0 | Agent 规则治理元模型 | 没有 Owner、生命周期和替代关系，继续新增规则必然继续产生竞争正文 |
| P0 | Case Spec / Plan / Report Machine Schema | Schema 已被大量 Checker 强制执行，却嵌在 1360 行分析流程文档中，机器与人都无法稳定定位唯一契约 |
| P0 | Canonical Result / Observation / Evidence | `results/case_report.py`、`recorder.py`、RunContext 已经形成真实公共接口；缺少 Owner 会让“报告展示优化”反向污染结果与 Case |
| P1 | Pipeline / `run_config` / Stage 语义 | Runner、GUI、配置校验和 Artifact 生命周期已经是实质公共能力，`tools/README.md` 只适合管理目录和入口，不足以承担运行契约 |
| P1 | Checker Diagnostic Namespace | 已经发生编号碰撞和无编号诊断，影响 Agent 从错误定位到唯一规则 |

以下领域不应现在为了“完整”而提前创建空契约：

- `instruments/` 和 `programmers/` 当前基本只有包入口；
- 通用 Renode/FPGA/Hardware Backend 尚未形成稳定、统一的实际接口；
- 外部观测器、烧录器和多 Backend 的独立契约应在第一个真实实现进入前定义，而不是现在凭想象冻结。

这条区分很重要：**规则体系要允许未来增加 Owner，但不能要求现在把未来所有 Owner 都写出来。**

### 16.5 当前路由还存在一个明显孤岛

`test_case_doc/ip自动化测试分析守则.md` 承担 IP 分析流程、Case Schema、Plan Schema、Report Schema
等大量内容，但当前仓库规则的最小开发路由没有稳定、明确地把它作为独立流程 Owner 加载。
结果是：文档虽然很长，Agent 在真实任务中仍可能根本没有读到；一旦强制整份加载，又会给普通局部任务带来过量上下文。

后续不能简单地把它追加到所有启动列表。应先拆清：

```text
IP 分析 Procedure
Machine Schema Contract
示例 / 模板
历史解释
```

然后由 `ip_analysis`、`ip_add`、`case_schema_change` 等不同任务分别精确路由。

## 17. 下一阶段研究顺序

下一阶段仍不直接迁移正式规则，建议按以下顺序验证：

1. **建立只读 Owner Catalog 完整版**：为现有有效规则分配唯一 Owner，给冲突文档标注候选
   `superseded_by`，但不修改原文生效状态。
2. **建立诊断码映射表**：把 155 个诊断码归并到有限的 Owner 域，验证能否做到唯一、完整、无循环；
   不先重写 Checker。
3. **为五类现实任务做路由回放**：局部 Case 修复、新 IP、报告变更、Pipeline 配置变更、芯片适配；
   对比当前必须读取量、遗漏率和冲突数。
4. **只提出首批收敛单元**：优先选择 Machine Schema、Result/Evidence 或 Diagnostic Namespace
   中最小且证据最充分的一项，形成迁移提案和回滚方案。
5. **获得用户批准后才迁移**：一次只迁移一个 Owner；同步正文、Catalog、Checker、Eval 和索引；
   旧文档明确标记 superseded，禁止顺手重构业务代码。

当前研究结论是：正式落地时应先解决“谁是唯一 Owner、什么任务加载它、如何证明没有遗漏”，
而不是先设计更多正文、目录或工具。只有 Owner 与路由被验证后，才有资格讨论缩减 `AGENTS.md` 和归档旧文档。

## 18. 诊断码映射实验与首个迁移单元判断

本轮又增加了两个只读实验输入：

```text
diagnostic_owner_map.yaml  # 诊断命名空间到规则 Owner 的候选映射
audit_diagnostic_map.py    # 检查现有诊断码是否唯一落入一个 Owner 域
gap_scenarios.yaml         # 没有 Owner 时必须失败关闭的任务场景
```

实验结果：

```text
155 个现有诊断码均可唯一映射到一个候选 Owner 命名空间
7 个当前跨文件冲突码均有明确迁移方向
1 个 Firmware Checker 仍完全没有稳定诊断码
5 类缺少 Owner 的任务均被明确拒绝为“规则包完整”
```

候选迁移方向不是重写 Checker，而是保留其现有职责并逐步统一命名空间：

- `ETCASE` 保留给 Case/Plan/Report 机器契约；
- Case 编排 Checker 的现有 `ETCASE101/201..206` 候选迁移到 `ETORCH`；
- Firmware Checker 候选按 Service、Wrap、Chip Config 分为 `ETFW1xx/2xx/3xx`；
- 每个命名空间只映射到一个 Owner，具体错误码仍然是该 Owner 下的诊断实例。

这证明“诊断可追溯”可以用轻量映射实现，不需要引入策略引擎或重写全部门禁。但当前 Checker
尚未迁移，因此结果明确标记 `NOT_READY`，不能把实验状态误报成正式规则已经收敛。

### 18.1 首个正式迁移单元不应是 Result 或 Pipeline

虽然 Result/Evidence 和 Pipeline 都存在明显规则缺口，但它们连接真实报告、运行配置、编译、烧录、
硬件和 Artifact 生命周期，第一步就迁移它们的风险过高。

首个正式迁移单元更适合选择：

```text
Checker Diagnostic Namespace + Rule Owner Traceability
```

理由：

1. 不改变 PC、Firmware、Wire、Case、报告或硬件执行语义；
2. 可以先只增加映射与回归，不要求移动现有正文；
3. 能直接证明 Agent 遇到门禁错误时是否能找到唯一规则；
4. 为后续迁移 Machine Schema、Result/Evidence 和 Pipeline 提供统一追溯基础；
5. 回滚简单：删除实验映射即可，不影响现有 Checker 的执行结果。

正式实施仍必须单独提交迁移方案并获得用户批准。本研究阶段不修改任何现有诊断码、Checker、
`AGENTS.md`、规则正文或业务代码。

## 19. 2026-08-14 首个正式迁移单元结果

用户批准后，首个收敛单元已按研究结论正式实施：

```text
Checker Diagnostic Namespace + Rule Owner Traceability
```

实施边界保持不变：未修改 PC/Firmware 运行架构、Wire Contract、Case 语义、报告语义或硬件流程。
本次只完成以下治理闭环：

1. 建立 `agent_rule_governance.md`，明确规则角色、生命周期、Owner、诊断码和失败关闭原则；
2. 建立 `rule_owner_catalog.yaml`，把有效 Rule ID、正文锚点、诊断命名空间和 Checker 关联为机器索引；
3. 将 Case 编排诊断从冲突的 `ETCASE` 迁移到独立 `ETORCH` 命名空间；
4. 为 Firmware 架构 Checker 增加稳定 `ETFW` 诊断码，但不改变其检查逻辑；
5. 增加治理 Checker，强制诊断码全局唯一、唯一 Owner、正文锚点存在、Checker 声明一致；
6. 把治理 Checker 纳入 `tools/validate_pc.py`，并增加冲突和缺失锚点的失败关闭回归。

验证结果：

```text
Rule governance validation: PASS
Targeted governance/checker regression: PASS
Full software gate: 514 passed, 9 skipped
Formal Case collection: PASS
AES/CRC/DMA/Framework Communication/UART report export: PASS
Hardware/Keil/HIL: NOT_EXECUTED
```

这一步解决的是“规则如何被唯一定位和机器追溯”，不是把所有规则正文一次性重写。后续仍应一次只收敛
一个 Owner；任何新规则必须先证明现有 Owner 无法承载，禁止恢复为遇到问题就新增散落文档或 Checker。

## 20. 2026-08-14 第二个正式迁移单元结果

第二个收敛单元选择 `public_ip_machine_contract` Owner，仅迁移公共 IP 机器契约正文：

```text
ET_CASE_SPEC + ET_CASE_PLAN + ET_CASE_REPORT
```

迁移前，完整 Schema 混在 1300 行以上的 IP 分析流程中，Case 写法和新 IP 入口又重复部分 REPORT
规则。迁移后：

1. `public_ip_machine_contract.md` 成为 Schema、生命周期和块间绑定的唯一正文；
2. `ip自动化测试分析守则.md` 只保留何时创建 PLAN/SPEC/REPORT 的分析 Procedure；
3. `pc_case_writing_rules.md` 只保留 Case 如何产生真实 Evidence 的运行规则；
4. `new_ip_development_rules.md` 只保留开发同步链和精确路由；
5. Catalog 的 `public_ip_machine_contract` Owner 已切换到新正文；
6. 治理门禁新增 `ETGOV110`，禁止三种 Schema 模板再次复制到第二份规范正文。

未修改任何 Schema 字段、Checker 判定、公共 IP 文档机器块、Formal Case、报告生成器或运行代码。

验证结果：

```text
Formal Case document validation: PASS (5 documents)
Case plan validation: PASS (4 documents)
Case spec implementation binding: PASS
Machine contract/report targeted regression: 28 PASS
Final software gate: 515 passed, 9 skipped
Formal Case collection and five report exports: PASS
Hardware/Keil/HIL: NOT_EXECUTED
```

当前规范性设计文档和 IP 分析守则中，`et.case.v1`、`et.case-plan.v1`、
`et.case-report-note.v1` 模板各只剩唯一正文；未来复制会被机器门禁拒绝。

## 21. 2026-08-14 第三个正式迁移单元结果

第三个收敛单元选择 `canonical_result_evidence` Owner，固定当前已经实现并通过回归保护的运行事实链：

```text
pytest execution
-> RunContext + Recorder
-> session.json / cases/<case_run_id>/result.json
-> report/analyzer/web只读消费
```

本次结论和边界：

1. `canonical_result_evidence_contract.md` 成为 Canonical Result、Observation身份、Evidence完整性和
   Artifact引用关系的唯一正文；
2. 当前可写 Canonical Status 仅为 `PASS/FAIL/SKIP/EVIDENCE_MISSING`；
3. `NOT_SELECTED/NOT_EXECUTED/RUN_ERROR` 是报告根据Selection和结构化证据派生的只读展示状态，
   不得写回 `result.json`；
4. `pc_layered_architecture.md` 只保留依赖方向，IP分析守则只保留分析/归因职责，Case规则只保留
   Case如何产生真实观测；
5. Artifact根目录和运行目录布局仍由 `artifacts/README.md` 管理，不与结果契约混合；
6. 尚未实现的Event数据库、Web状态模型和自动分析语义没有被提前写成当前契约。

治理模型同时补齐一个必要边界：可静态判定的规则继续由Checker和诊断码保护；公共接口行为可以由
Catalog登记的真实回归测试保护，不得为了分配诊断码而制造空壳Checker。每个active Owner仍必须至少
拥有Checker或回归测试之一，并能从失败项反查唯一Owner。

验证结果：

```text
Rule governance validation: PASS
Result/Observation/Evidence targeted regression: 47 PASS
Final software gate: 516 passed, 9 skipped
Formal Case collection and five report exports: PASS
Hardware/Keil/HIL: NOT_EXECUTED
```

未修改PC/Firmware运行代码、Wire Contract、Case执行语义、报告实现或硬件流程。

## 22. 2026-08-14 全量规则盘点复核

本节是前三个Owner收敛完成后的只读复核。它只回答“现有规则体系还差什么”，不批准新增Owner，
也不修改任何业务实现。

### 22.1 当前覆盖情况

`rule_owner_catalog.yaml` 当前登记13个active Owner，已经覆盖：

```text
Agent规则治理
PC层职责
PC Case职责
Python样式与注释门禁
Public IP Machine Contract
Public IP实现同步
Canonical Result / Observation / Evidence
Public IP语义
公共区芯片中立
Contract/代码同步
Chip Adaptation边界
Firmware Service职责
Firmware Wrap职责
```

这些Owner已覆盖全部现有Checker诊断码，并由Checker或真实回归测试保护。前三个正式收敛单元没有
留下无归属诊断码。

### 22.2 根因仍是文档角色没有机器登记

治理契约已经定义 `kernel/contract/policy/procedure` 以及非规则的
`proposal/plan/review/evidence/artifact/template/history`，但Catalog当前只登记规则Owner，尚未登记
未成为Owner的设计文档属于哪一种角色、生命周期是什么、是否被替代。

因此 `report/design/` 中仍同时存在：

| 当前角色判断 | 代表文件 | 风险 |
|---|---|---|
| active Contract | `et_frame_v1.md`、`capability_v2_contract.md`、`interrupt_subsystem_design.md` | 有真实实现和回归，但没有Owner登记 |
| active Procedure/Router | `new_ip_development_rules.md`、`firmware_layering.md`、`pc_layered_architecture.md` | 容易被误当成第二份Contract |
| active Template/Checklist | `pc_ip_package_template.md`、`pc_firmware_architecture_review_checklist.md` | 内容重复但本质不应拥有稳定语义 |
| implemented Record | `20260809_case_driver_simplification_v2_design.md` | 应作为实施记录，不应继续承担现行规则 |
| proposal/history | `pc_ip_test_layer_simplification_design.md`、`2026-08-05-uart-feature-split-design.md` | 已与现行设计冲突或仅适用于一次迁移 |
| draft architecture | `et_ip_automated_test_platform_architecture.md` | 自称草案，却仍被当前设计索引直接列出 |
| superseded generation design | `svd_capability_generation.md` | 已声明v1不再扩展，应路由到Capability v2 |

这说明下一步不能直接继续新增Contract。必须先给所有当前设计文档建立轻量机器清单，至少记录：

```text
path
role
lifecycle
owner（仅规则正文需要）
superseded_by（仅deprecated/superseded需要）
```

该清单应扩展现有治理Catalog或与其保持单一校验入口，不能再建立平行规则系统、数据库或通用DSL。

### 22.3 已确认的四个后续Owner候选

以下领域已经存在真实公共实现和回归，不是凭未来想象创建的空契约：

| 优先级 | 候选Owner | 当前证据 | 现状 |
|---|---|---|---|
| P1 | ET-Frame / Framework Wire | PC/Firmware编解码、TargetClient、native vector与可靠性测试 | `et_frame_v1.md`已有正文，但未登记Owner |
| P1 | Capability v2 | 生成器、Profile加载器、17项定向回归 | `capability_v2_contract.md`已有正文，但未登记Owner |
| P1 | IRQ Subsystem | IRQ Manager/Wrap、多个IP Service、Firmware回归 | `interrupt_subsystem_design.md`已有正文，但未登记Owner |
| P1 | Operator Pipeline / Run Config / Artifact Run | Runner、GUI、Profile、41项Operator回归和Artifact目录测试 | 规则散落在AGENTS、README、tools/README和artifacts/README |

前三项原则上不需要新写正文，只需在角色盘点后审查现有正文是否与代码一致，再登记Owner和回归测试。
第四项存在真正的多正文问题，后续才可能需要一个最小Contract收口配置Schema、Stage语义、安全门禁和
一次运行一个Artifact目录的边界。

### 22.4 不应新增Owner的文档

下列内容应继续作为Procedure、Template、Checklist、Record或History，而不是每份文档各建Owner：

```text
pc_layered_architecture.md
firmware_layering.md
new_ip_development_rules.md
pc_ip_package_template.md
pc_firmware_architecture_review_checklist.md
20260809_case_driver_simplification_v2_design.md
2026-08-05-uart-feature-split-design.md
pc_ip_test_layer_simplification_design.md
```

它们只能路由到已有或未来唯一Contract，不得重新定义稳定接口。

### 22.5 两个已确认的当前文档错误

1. `report_repository_governance.md`仍写“外层artifacts、不提交Git”，与当前
   `artifacts/README.md`的“仓库内唯一产物目录、正式产物允许提交”直接冲突；该旧正文不能继续标记
   “已确认”。
2. `report/README.md`仍把`463 passed, 9 skipped / 228 nodes`描述为当前工作树状态，而最新统一门禁是
   `516 passed, 9 skipped`；索引不应长期手工维护易漂移的当前运行计数。

这两项属于文档角色/生命周期收敛后的直接修复目标，不应通过继续添加补充说明来掩盖。

### 22.6 修正后的剩余顺序

剩余工作不再按“再写几份文档”计算，而按以下5个收敛单元执行：

1. **Document Role/Lifecycle Inventory**：为现有设计文档登记角色、生命周期和替代关系；
2. **ET-Frame Owner登记与正文一致性审计**：不改变Wire；
3. **Capability + IRQ Owner登记与正文一致性审计**：两个独立Owner可在同一只读审计阶段准备，分别验收；
4. **Operator Pipeline / Run Config / Artifact Contract**：收回当前分散规则；
5. **最终冻结审计**：清除竞争正文路由、刷新索引、运行完整软件门禁和精确规则路由回放。

第1步是其余步骤的前置条件。若跳过它直接新增Owner，旧草案和新Contract仍会并列，系统会重新回到
“遇到问题加一份规则”的补丁模式。

## 23. 2026-08-14 Document Role/Lifecycle Inventory收敛结果

本单元没有新增第二套文档索引、DSL或数据库，而是在既有
`report/design/rule_owner_catalog.yaml`中增加`documents`清单，使规则Owner与规则载体共享同一治理入口。

### 23.1 最小元数据与约束

当前22份`report/design/*.md`均且仅登记一次，字段只保留治理所需最小集合：

```text
path
role: kernel | contract | policy | procedure | template | proposal | record | history
lifecycle: draft | active | deprecated | superseded
owners（仅active kernel/contract/policy允许）
superseded_by（deprecated/superseded必需）
```

治理Checker同时验证目录覆盖、合法角色与生命周期、Owner双向一致性、替代目标存在性。Procedure、Template、
Proposal、Record和History不能声明Owner；draft、deprecated和superseded文档不能覆盖active Contract。
这使Agent不再依赖文件名或目录位置猜测规则效力。

### 23.2 本轮形成的真实状态

- 8份现行Contract/Policy与既有Owner完成绑定；
- ET-Frame、Capability v2和IRQ正文诚实登记为draft Contract，等待后续逐项代码一致性审计后再激活；
- 其余Procedure、Template、Record、Proposal和History均明确标识，不再被误认为平台契约；
- 旧`report_repository_governance.md`登记为deprecated，替代入口为`report/README.md`和
  `artifacts/README.md`；
- `report/README.md`删除会漂移的手工测试计数，当前状态统一路由到`project-control/work/ACTIVE.md`。

### 23.3 验证结论

- 文档治理定向回归：8 PASS；
- 完整非硬件软件门禁：519 PASS、9 SKIP；
- Formal Case全量收集、五类Excel报告导出、Firmware生成工程契约均通过；
- 未执行硬件、Keil、烧录或HIL，未修改公共运行架构、协议、Case、Driver或Firmware执行语义。

本单元完成后，剩余顺序缩减为4个收敛单元：ET-Frame、Capability+IRQ、Operator Pipeline、最终冻结审计。

## 24. 2026-08-14 ET-Frame v1 Owner收敛结果

本单元逐项核对了Python Frame/Message Codec、TargetClient、Framework Driver、C Frame/Message Codec、
Firmware Protocol/Router/Framework Service、共享黄金向量和原生可靠性Harness。合法帧格式、公共命令编号、
状态码、Session、Sequence、CRC和重放行为两端一致，Wire版本继续保持v1。

收敛中修正了两类正文漂移：

1. Framework六条命令原先只写抽象描述，现按现有实现补齐准确Body布局、字符串编码、Registry Hash算法和
   `RESET_REASON_GET`的`NOT_SUPPORTED`语义；
2. 原文“所有请求超时都重试一次”与当前可靠设计不一致，现明确只有Driver声明`retry_safe`的命令才允许
   复用完全相同帧重试一次，变更型及未声明命令默认只发送一次。

新增的唯一运行保护是PC在事务边界拒绝非零Response Flags。该字段在v1本就固定为0，此检查不改变合法Wire，
只使未知扩展失败关闭。ET-Frame正文现登记为active Contract和唯一Owner，保护测试覆盖Python/C黄金向量、
TargetClient、Firmware常量一致性及原生协议可靠性。

验证结果：定向协议/治理测试通过（其中1项因本机编译器条件SKIP）；完整非硬件软件门禁520 PASS、9 SKIP，
Formal Case全量收集、五类Excel报告导出和Firmware生成工程契约均通过。未执行硬件、Keil、烧录或HIL。

## 25. 2026-08-14 Capability v2与IRQ Contract收敛结果

Capability和IRQ原先已经具有真实公共实现与回归，但治理清单仍标记为draft，IRQ正文还保留初建时的
“当前代码差距”和实施顺序。这个状态会诱导后续Agent把已完成架构再次当作待重构目标。

本单元完成以下收敛：

- Capability v2正文更新为active Contract，明确正式芯片基线位于
  `profiles/chip_capabilities/<chip>/ip/`，临时生成物、Audit候选和测试夹具不能冒充运行时基线；
- Capability Owner绑定生成器、Profile加载器、不可变查询、证据闭合和SVD生成回归；
- IRQ正文删除过时差距表和实施计划，改为当前实现边界和未来演进规则；
- IRQ重试规则与ET-Frame统一：只有Driver显式声明`retry_safe`的命令才允许自动重试，固件精确重放
  不能反向推导“所有变更命令均可自动重试”；
- IRQ Owner绑定Manager原生可靠性、Capture Fault和DMA IRQ Fault回归。

定向Capability/IRQ回归通过：40项执行，其中2项因现有本机条件SKIP；规则治理门禁通过。未执行硬件。

## 26. 2026-08-14 Operator Pipeline / Run Config / Artifact收敛结果

一键运行规则原先分散在AGENTS、根README、tools README、artifacts README和测试代码中，但公共实现已经
具备统一Runner、GUI、Profile、安全门禁和单Run目录。为避免继续在多个README中补丁式追加规则，本单元
新增一个最小active Contract作为唯一行为Owner，既有README只保留使用说明和目录细则。

契约固定：

- `run_config.yaml`是唯一生效本机配置，模板、GUI和CLI不形成第二套配置源；
- Pipeline Profile只能绑定仓库`tools/`内受控脚本，不能携带个人路径或选择Case；
- Case集合只来自正式IP/Case Registry；Case不读取Run Config；
- 非Renode硬件动作必须显式确认，`--check-only`不创建Run目录或触发动作；
- 一次Pipeline只创建一个`artifacts/runs/<run_id>/`，子阶段、测试和报告共享该目录；
- Manifest记录配置Hash、源码身份、状态和退出码，报告不重新判定PASS/FAIL。

同时删除项目入口AGENTS中的旧`TEST_READY/TEST_PASS`建议文本，统一路由到ET-Frame v1，避免两个协议
同时具有规则权威。Operator专项44项与规则治理门禁通过；未执行真实构建、烧录或HIL。

## 27. 2026-08-14 最终冻结审计

最终审计按规则Owner、文档生命周期、权威路由、实现证据和完整门禁五个方向完成：

- 所有active Kernel/Contract/Policy都有唯一Owner以及Checker或真实回归；
- Capability、IRQ和Operator已进入AGENTS最小发现路由，Procedure与README不再取得更高权威；
- 旧文本协议、旧Artifact分类和历史绝对路径只命中Archive、History、Record或Draft Proposal，未作为
  现行规则继续传播；
- 公共代码、Wire、Case、Driver、Service、Wrap和芯片硬件语义未因本轮治理收敛而改变；
- 完整非硬件软件门禁通过：520 PASS、9 SKIP；Formal Case全量收集、五类Excel报告导出、Firmware
  生成工程契约和全部规则Checker通过。

本次冻结针对“规则控制面和公共契约治理”完成，不把未执行的Keil、烧录或HIL升级为PASS。未来规则
可以增加，但必须先指定现有Owner或证明需要一个新的单一职责Owner，并同时登记生命周期与机器证据；
禁止再创建平行规则目录、第二份Schema正文或问题驱动的补充规范。
