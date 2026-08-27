---
schema: et.rule-document.v1
number: R120
domain: public-ip
lifecycle: active
owners: [public_ip_machine_contract]
rule_ids: [ET-RULE-IP-MACHINE-CONTRACT]
---

# R120 Public IP Machine Contract

## 1. 定位与边界

本文是公共 IP 文档中以下机器块的唯一规则正文：

```text
ET_CASE_SPEC
ET_CASE_PLAN
ET_CASE_REPORT
```

本文定义稳定 Schema、生命周期、块间一致性，以及能够可靠静态判定的公共 Human Review 行语法。它不定义：

- IP Feature和Case如何分析，以及面向人工审核的Feature/Case语义质量；由`R140_ip_analysis_workflow.md`负责；
- Formal Case如何调用Driver、断言、记录Evidence，以及如何把已审核Case流程映射为可读代码；由`R210_pc_case_responsibility.md`负责；
- 芯片能力、寄存器、实例和适配事实；由 `<CHIP>_<ip>.md` 负责；
- Excel 布局或报告生成器实现；由 Result/Report 实现契约负责。

`report_feature`、`method.*`、`pass_criteria`和`ET_CASE_REPORT`的字段结构由本文冻结。`method.inputs`、`method.steps`、`method.observations`、`method.pass_criteria`中每一条人审字符串的统一“摘要：正文”行语法也由本文冻结；摘要应该写到什么具体程度、测试逻辑和Oracle是否充分，仍由R140统一规定，Formal Case实现必须按R210保持同一测试语义。

其他文档只能链接本文或描述自己的执行步骤，不得复制、扩展或重新解释以下 Schema 与公共行语法；不得为单个IP发明另一套Case方法格式。

## 2. Case 生命周期

```text
ET_CASE_SPEC
= 已实现 + 已注册 + 存在唯一真实 test_* 的 Formal Case

ET_CASE_PLAN
= 稳定设计已经完成，但尚未进入 Registry 或尚无真实 test_*
```

固定约束：

- 同一 Case ID 不得同时存在于 SPEC 和 PLAN；
- PLAN 不计入 implemented coverage；
- PLAN 转为 SPEC 时必须在同一逻辑变更中完成 Registry、真实 `test_*` 和报告契约绑定；
- 已发布 Case ID 绑定稳定语义，不得因芯片或后端变化静默改义。

### 2.1 Case Resource Level

`resources.minimum_level`和`resources.full_coverage_level`只允许：

| Level | 稳定含义 |
|---|---|
| `R0` | DUT内部数字自检、状态或独立数学参考 |
| `R1` | IP内部Loopback |
| `R2` | 片内Peer或固定板级Passive Loop |
| `R3` | Companion FPGA主动刺激或捕获 |
| `R4` | 外部仪器或电气测量 |
| `R5` | 环境、长稳或高成本条件 |

- `minimum_level`表示形成该Case有效核心Oracle所需的最低资源等级。
- `full_coverage_level`表示达到文档声明完整覆盖所需的资源等级，必须大于等于`minimum_level`。
- Resource Level只描述资源强度，不代表P等级、执行状态或PASS等级。

## 3. ET_CASE_SPEC

每个已实现 Formal Case 使用一个带 `ET_CASE_SPEC_BEGIN/END` 标记的 YAML 块：

```yaml
schema: et.case.v1
case_id: <IP>_P1_001
case_name: 具体中文Case名称
report_feature: |-
  1. DMA Channel Enable/Disable
  2. DMA Channel FREE状态
  3. DMA M2M传输
p_level: P1
feature_refs:
  - DMA_F_003
  - DMA_F_005
  - DMA_F_007
method:
  inputs:
    - 参数矩阵：说明逻辑DUT、稳定输入和关键配置，不写具体芯片实例。
  steps:
    - 能力确认：确认执行本Case所需的Runtime能力和资源条件。
    - 测试准备：建立输入、Expected和必要的初始状态。
    - 功能配置：按当前参数配置公共Driver可表达的稳定语义。
    - 激励启动：触发本Case真实硬件行为或数据路径。
    - 完成等待：在统一有界deadline内等待目标状态或事件。
    - 结果读取：读取决定性硬件Observation和必要Measurement。
    - 结果比较：把Actual与Expected或独立Oracle进行比较。
    - 结果汇总：汇总参数实例并保留决定性Evidence。
  observations:
    - 硬件实际状态：记录能够支撑本Case结论的稳定硬件事实。
  pass_criteria:
    - 功能正确性：使用强Oracle明确说明本Case何时通过。
timeout: 明确的PC侧执行边界
cleanup:
  - 明确的本Case资源清理语义
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
  - FPGA
  - Silicon
evidence:
  - canonical result/evidence
failure_observations:
  - key: expected_value
    label: 期望值
    source: oracle
    role: expected
    format: hex32
  - key: actual_value
    label: 硬件实际值
    source: dut
    role: actual
    format: hex32
    semantic_ref: <ip>.feature.<semantic-name>
gap: []
```

公共 SPEC 不得包含具体芯片 ID、固定物理实例、IRQ/Handler、Base Address、Register Offset、
Chip SDK 类型或 `if chip == ...` 分支。内部 Feature ID 只写入 `feature_refs`。

`report_feature`、`method.inputs`、`method.steps`、`method.pass_criteria`虽然属于机器字段，但同时是人工报告的稳定来源；其人审内容必须按R140形成具体、可顺序复原的测试设计，禁止把机器字段存在性当成人工可审核性的替代。

`failure_observations` 的每项必须声明稳定 `key`、中文 `label`、具体 `source`、`role` 和 `format`。
可映射到 Capability 中寄存器、字段、IRQ 或信号的硬件事实应使用芯片中立 `semantic_ref`。

### 3.1 `report_feature` 确定性生成与格式

`report_feature` 是 Excel“测试 Feature”列的稳定展示字符串，不是 Case 目标的自由总结。
它必须按以下步骤由同一 Case 的 `feature_refs` 确定性生成：

```text
1. 按 feature_refs 声明顺序逐项取出 Feature ID。
2. 在本 IP Feature Catalog 中查找该 ID 的“报告名称”。
3. 按 1. / 2. / 3. 连续编号，每行只展示一个 Feature。
4. 把全部编号行作为一个 YAML block scalar 写入 report_feature。
```

固定格式：

```yaml
report_feature: |-
  1. DMA Channel Enable/Disable
  2. DMA Channel FREE状态
  3. DMA M2M传输
feature_refs:
  - DMA_F_003
  - DMA_F_005
  - DMA_F_007
```

即使只引用一个 Feature，也必须使用 `1. <报告名称>`。编号必须从1开始且连续；
行数、顺序和文本必须与 `feature_refs` 及 Feature Catalog“报告名称”完全一致。
禁止在 Case 中重新改写、合并或补充 Feature；禁止把多个 Feature 压成一句长文，
也禁止写 Case 步骤、PASS结论、软件实现或芯片专属事实。Feature Catalog“报告名称”的
硬件语义和命名质量由R140唯一负责。

### 3.2 Human Review统一行语法

所有IP、所有`ET_CASE_SPEC`与`ET_CASE_PLAN`的以下四个列表统一使用同一种行语法：

```text
method.inputs[]
method.steps[]
method.observations[]
method.pass_criteria[]

<摘要>：<正文>
```

这是公共机器契约，不是某个IP的写作风格。固定结构红线如下：

1. 每一项必须是单行字符串，并使用中文全角冒号`：`作为第一个结构分隔符；ASCII冒号`:`不能替代该分隔符。
2. Checker以第一个`：`切分`摘要`和`正文`；两侧`strip()`后都必须非空。正文内部允许继续出现`：`或其他正常工程标点。
3. 摘要只承担Reviewer扫描导航，不绑定固定IP词表，但必须能够说明本条的角色或阶段；禁止`输入1/步骤1/观测1/判据1`及其数字变体，也禁止`测试过程/功能验证/数据处理/其他`等空泛摘要。
4. `inputs`摘要回答“这组输入/配置是什么”；`steps`摘要回答“这一步主要做什么”；`observations`摘要回答“从什么观测点看什么”；`pass_criteria`摘要回答“这一条判定什么”。具体命名质量和语义充分性由R140人工审核，不由Checker猜测。
5. `method.steps`必须包含6～8条真实测试动作；不得用拆标题、重复摘要或无实际动作的占位行凑数量。
6. SPEC与PLAN使用完全相同的行语法和步骤数量要求；不得因为PLAN尚未实现而退化为占位描述。
7. 机器Gate只判断上述确定性结构红线，不做LLM评分、关键词质量打分或IP私有格式推断；语义是否具体、Observation/Oracle是否充分继续由R140 Human Review Gate负责。

对应失败关闭诊断固定为：

| 对象 | 诊断 | 含义 |
|---|---|---|
| SPEC | `ETCASE430` | `method.*`存在不符合`<摘要>：<正文>`统一行语法的条目 |
| SPEC | `ETCASE431` | `method.steps`不是6～8条真实动作 |
| PLAN | `ETPLAN223` | `method.*`存在不符合`<摘要>：<正文>`统一行语法的条目 |
| PLAN | `ETPLAN224` | `method.steps`不是6～8条真实动作 |

## 4. ET_CASE_PLAN

每个仅完成设计的 Case 使用一个带 `ET_CASE_PLAN_BEGIN/END` 标记的 YAML 块：

```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: <IP>_P2_001
case_name: 具体中文Case名称
report_feature: |-
  1. DMA Channel Enable/Disable
  2. DMA Channel FREE状态
  3. DMA M2M传输
p_level: P2
feature_refs:
  - DMA_F_003
  - DMA_F_005
  - DMA_F_007
method:
  inputs:
    - 测试输入：说明计划使用的稳定输入、参数或资源条件。
  steps:
    - 能力确认：确认计划Case所需能力和前置条件。
    - 测试准备：建立输入、Expected和初始状态。
    - 功能配置：配置计划验证的稳定语义。
    - 激励启动：触发计划验证的真实行为。
    - 完成等待：等待目标状态、事件或外部Observer结果。
    - 结果读取：读取计划中的关键Observation。
    - 结果比较：按独立Oracle比较Actual与Expected。
    - 结果汇总：汇总计划Evidence和Gap。
  observations:
    - 关键观测：说明计划从哪个稳定观测点取得什么事实。
  pass_criteria:
    - 通过判据：说明计划Case必须满足的强Oracle。
timeout: 明确边界
cleanup:
  - 清理
resources:
  minimum_level: R0
  full_coverage_level: R2
  board: 具体需求或无额外要求
  bench: 具体需求或无额外要求
backend:
  - FPGA
  - Silicon
evidence:
  - 计划Evidence
failure_observations:
  - key: expected_value
    label: 期望值
    source: oracle
    role: expected
    format: text
  - key: actual_value
    label: DUT实际值
    source: dut
    role: actual
    format: text
gap:
  - case_implementation_gap
```

只有带成对标记和合法 fenced YAML 的 PLAN 进入机器解析。不得用 PLAN、注释或历史源码冒充已实现覆盖。PLAN 的人审字段与 SPEC 使用同一 R140 质量要求和本文3.2节统一行语法，不能因为尚未实现就使用抽象占位描述。

## 5. ET_CASE_REPORT

存在 ET_CASE_SPEC 的公共 `<ip>.md` 必须在全部 SPEC 后声明唯一一个
`ET_CASE_REPORT_BEGIN/END` YAML 块：

```yaml
schema: et.case-report-note.v1
cases:
  <CASE_ID>:
    summary: 一句中文硬件结论。
    fields:
      - {source: artifact, path: transfer.data_match, label: 数据一致, format: bool, aggregate: same}
```

固定约束：

- `cases` 必须与本文档全部 ET_CASE_SPEC Case ID 完全一致；
- `summary` 只描述稳定 Feature 结论，不硬编码运行值；
- 每个 Case 只展示 1～4 个支撑结论的关键字段；完整证据继续保留在 Artifact；
- `source` 只允许 `artifact`、`measurement`、`observation`；
- `path` 只能指向 canonical result 或已绑定结构化附件中的真实路径；
- `format` 只负责展示，原始值不得被替换；
- 参数化 Case 使用明确的 `same`、`range`、`distinct` 或 `all` 聚合语义；
- PASS 与 FAIL 使用同一模板，不得按结果状态切换字段；
- 声明字段无法解析时报告生成必须失败，不得静默省略或回退为任意 JSON 展开；
- 公共报告契约不得包含芯片名、基址、IRQ 或寄存器偏移；
- `source: observation` 的每个报告字段必须对应一个原子的 Canonical Observation `key`。一个字段不能把多个独立硬件端点、不同Evidence Source或Service计数拼成一个值后再挂到单一寄存器/Field标签下；一个结论需要多个端点时，在1～4个字段额度内分别选择原子字段；
- 公共 `path/label` 保持芯片中立。目标芯片实际寄存器/Field名称可以由报告层根据本次 `chip_id` 和 `<CHIP>_<ip>.md` 的稳定语义映射进行展示增强，但不得反向修改 Canonical Observation 的 `endpoint/source/value`，也不得把芯片名写回公共Schema；映射缺失时保留稳定语义，不得猜测实际寄存器名。

`ET_CASE_REPORT`选择的字段必须服务于R140定义的人审证明链，并由R210要求的真实Evidence支撑；报告摘要不得只重复“验证完成”，也不得选择与测试方法和PASS条件无关的运行值来制造“看起来有证据”的备注。

### 5.1 参数化Case的报告闭合

同一稳定Case ID下的每个`parameter_id`都是独立execution。`ET_CASE_REPORT`虽然按稳定Case ID声明，
但其中每个字段必须在该Case所有实际参数分支上都具有相同、明确且可解析的语义。

固定规则：

1. 报告公共字段必须由每个参数分支真实产生；只在部分分支存在的字段不得声明为该Case的公共必选字段。
2. 参数分支的差异允许保存在Artifact或Canonical Result中，但进入报告的字段应选择各分支共有的Feature证据，例如当前模式、实际输出、关键终态和比较结果。
3. 同一语义在不同分支拥有不同细节时，应使用一个稳定公共字段承载带模式身份的结构化结果；不得在报告层根据参数名猜测应该读取哪个私有字段。
4. `null`只表示本次execution没有该值，不能代替支撑PASS/FAIL的必要Evidence，也不能用于掩盖字段只适用于部分分支。
5. 只有测试流程、Oracle、资源或恢复语义发生稳定变化时才按R140拆分Case；不得仅为规避报告字段不一致而复制Case。
6. 聚合前必须先逐execution完成字段解析和Evidence完整性检查；任一实际执行分支缺少公共必选字段时，报告必须失败关闭，不能由其他参数分支补足。

推荐结构：

```yaml
cases:
  DMA_P2_012:
    summary: 不同握手模式下传输均正确完成。
    fields:
      - {source: artifact, path: handshake_mode, label: 握手模式, format: text, aggregate: all}
      - {source: artifact, path: data_match, label: 数据一致, format: bool, aggregate: same}
      - {source: artifact, path: channel_free, label: 通道释放, format: bool, aggregate: same}
```

软件模式专属的请求次数可以继续保存在Artifact中，但不能成为硬件模式execution也必须提供的报告字段。

## 6. 跨层绑定

机器契约必须保持以下稳定关联：

```text
ET_CASE_SPEC Case ID
<-> Registry ID
<-> unique test_* function
<-> Case leading comments
<-> declared structured observations
<-> ET_CASE_REPORT Case ID and field whitelist
<-> canonical result/report
```

本节只规定必须关联，不重新定义 Case 执行细节。结构化事实如何在 decisive assert 前记录、
如何绑定 Artifact、以及 `record_property` 与 `record_observation` 的边界，以
`R210_pc_case_responsibility.md`的“断言与Evidence”为Case写法正文；Canonical Result字段、
Observation身份和Evidence完整性以`R130_canonical_result_evidence.md`为唯一正文。

## 7. Machine Gate

统一使用公共门禁，不允许IP私有格式Checker：

```powershell
python tools/quality/validate_case_docs.py
python tools/quality/validate_case_plans.py
python tools/quality/validate_case_method_contract.py
python tools/quality/check_case_spec_implementation.py
python tools/validate_pc.py
```

`ETCASE*` 诊断归属本 Contract 的 SPEC/REPORT 文档约束；`ETPLAN*` 诊断归属 PLAN 文档约束；
实现记录与断言同步使用`ETSPEC*`，由`R210_pc_case_responsibility.md`负责。

`validate_case_method_contract.py`只复用`validate_case_docs.py`与`validate_case_plans.py`的现有SPEC/PLAN解析结果来检查本文3.2节行语法和步骤数量，不建立第二套YAML Schema解释器。任何IP都必须经过同一Checker。

进入HIL前，公共机器契约还必须完成以下无硬件闭合：

```text
SPEC / PLAN / REPORT解析
-> Registry与全部参数execution收集
-> 每个execution的公共报告字段可解析性检查
-> 代表性Canonical Result的JSON往返
-> 人工报告模型与Excel导出
```

该预检只证明契约和报告软件链能够闭合，不产生任何FPGA、Silicon或仪器PASS证据。参数分支、
Evidence类型或报告字段发生变化时，必须同步更新对应回归；禁止只用一个无参数的理想样本代表全部execution。

人工可审核性中能够可靠静态判定的结构红线必须在对应 Checker 中失败关闭；不能可靠静态判断的“是否具体、逻辑是否完整”由R140的人工审核Gate负责，禁止引入LLM评分、关键词打分或第二套Schema解释器。

## 8. 变更规则

修改 Schema、字段语义、生命周期、块间绑定或本文3.2节机器可判定的人审行语法时，必须在同一逻辑变更中：

1. 修改本文唯一正文；
2. 更新对应 Checker 和失败关闭回归；
3. 验证现有全部公共 IP 文档；
4. 验证 Registry、Formal Case 收集和报告导出；
5. 迁移全部受影响的公共 `<ip>.md`，不得通过IP私有例外、历史白名单或降级Gate保留旧格式；
6. 保持R140只负责人审语义质量、开发入口和Case规则只作路由，不复制Schema或机器行语法正文。

仅调整R140/R210中无法可靠静态判断的人审语义说明、且不改变本文件Schema、字段含义、运行行为或3.2节机器行语法时，不构成Schema/格式迁移；一旦把人审要求转为新的字段约束或诊断，仍必须按上述完整闭环同步迁移。

禁止为单个 IP、芯片、后端或报告样式增加私有 Schema 或私有Method格式分支。
