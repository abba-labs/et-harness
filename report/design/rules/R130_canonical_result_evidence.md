---
schema: et.rule-document.v1
number: R130
domain: result-evidence
lifecycle: active
owners: [canonical_result_evidence]
rule_ids: [ET-RULE-CANONICAL-RESULT-EVIDENCE]
---

# R130 Canonical Result / Observation / Evidence Contract

## 1. 定位与边界

本文是平台当前公共结果事实、Observation 身份和 Evidence 完整性的唯一规则正文。

本文只固化已经由以下实现和回归证明的公共行为：

```text
pytest_plugin.py
-> scheduling/run_context.py
-> results/recorder.py
-> session.json / cases/<case_run_id>/result.json
-> results/case_report.py（只读派生）
```

本文不定义：

- Case的Feature、方法和报告字段白名单；由`R120_public_ip_machine_contract.md`负责；
- Case内具体断言、Cleanup和Driver调用；由`R210_pc_case_responsibility.md`负责；
- Artifact根目录和运行目录布局；由`R500_operator_pipeline.md`负责；
- Excel 列宽、颜色和排版；属于报告导出实现；
- 尚未实现的 Event、数据库、Web 或自动分析模型。

报告、Analyzer 和 Web 都只能消费 Canonical Result，不得反向修改 Case 状态或原始事实。

## 2. 唯一事实链

```text
pytest真实阶段结果
+ Registry稳定Case身份
+ Target/Bench/Source元数据
+ Case显式记录的Measurement/Observation/Artifact
+ Required/Actual Evidence
-> Canonical session.json / result.json
-> 人读报告或后续派生分析
```

固定约束：

- `RunContext` 拥有 `run_id` 和 `case_run_id`，调用方传入的旧身份必须被覆盖；
- 一个 Case execution 只生成一个 Canonical Result；参数化 execution 通过稳定 `parameter_id` 区分；
- 报告层不得重新执行设备操作、调用 Test Case、改变原始状态或覆盖原始值；
- 自由文本、traceback、文件名和目录扫描不得冒充结构化 DUT Evidence。

## 3. Canonical Session

一次显式启用 Artifact 输出的 pytest Session 生成唯一 `session.json`。当前稳定事实包括：

```text
schema_version
run_id
platform_version
started_at / finished_at / exitstatus
status_counts
selection（selected_case_ids / selected_executions）
chip_id / firmware_build_id / registry_hash
target_id / transport_identity
bench_path / bench_sha256 / config_hash
bitstream_id / device_identity
source_revision / source_dirty / spec_sha256
```

无法取得的身份必须保留 `null`，不得猜测。Session 只采用第一次真实取得的目标元数据，后续 Case
不得静默改写本次运行身份。未提供 `--et-artifact-dir` 时，插件不得创建 Canonical Result 文件。

## 4. Canonical Case Result

每个 execution 的 `result.json` 当前稳定字段包括：

```text
schema_version / run_id / case_run_id
case_id / ip_id / parameter_id
status / duration_s / error
platform / target / chip / firmware / registry / bench / transport identity
measurements
observations
artifacts
required_evidence_sources
evidence_sources
evidence_complete
missing_evidence_sources
```

当前写入层直接产生的 Canonical Status 只有：

```text
PASS
FAIL
SKIP
EVIDENCE_MISSING
```

- pytest setup/call/teardown 任一失败会保留对应阶段错误，Canonical Result 写为 `FAIL`；
- 明确 pytest skip 写为 `SKIP`；
- 原本可 PASS、但缺少声明的必要 Evidence 时必须降级为 `EVIDENCE_MISSING`，并使最终 pytest/JUnit 失败；
- 已有 FAIL 不因 Evidence 缺失被改成 PASS；错误中同时保留 Evidence 缺失事实。

`NOT_SELECTED`、`NOT_EXECUTED` 和 `RUN_ERROR` 是报告层结合 Selection、Session完整性和结构化
硬件失败证据派生的展示状态，不是当前 `result.json` 可写入的 Canonical Status。Agent 不得把
派生状态伪装成一次真实 Case execution 结果。

## 5. Measurement、Observation 与 Artifact

三类事实职责固定：

```text
Measurement
= record_property登记的配置、激励、纯软件期望或简单测量值

Observation
= record_observation登记的真实设备事实

Artifact
= write_json_result等生成、并由当前Case Result显式登记路径的结构化附件
```

Observation 当前稳定字段为：

```text
key
value（原始JSON值）
source
device_id
endpoint
artifacts（run-relative路径）
```

固定要求：

- `source` 使用平台支持的稳定来源；当前支持 `dut/peer/fpga/instrument/observer`；
- 非 DUT Observation 必须提供稳定 `device_id`；DUT 缺省身份归一为 `dut`；
- `endpoint` 必须描述实际观测端点，不得为空；
- **一条 Observation 只表达一个原子设备事实**：一个 `source + device_id + endpoint` 对应一个原始 `value`。如果同一次判定同时涉及多个寄存器/Field、硬件输出、ISR锁存或其他设备端点，必须拆成多条 Observation；禁止把多个独立来源拼成字符串/对象后挂在单一 endpoint 下制造来源错觉；
- Service/Firmware 派生事实与硬件寄存器事实必须保持来源边界。例如 IRQ `RAW/STATUS`、Service `latched` 和 `event_count` 是不同事实；`event_count`、协议计数或软件差值默认记录为 Measurement，除非确有明确硬件端点直接提供该值；
- Canonical `endpoint` 应保存公共稳定硬件语义或明确设备端点，例如 `STATUS.FINISH`、`RESULT_DOUT[0..3]`、`IRQ_STATUS.COMPLETE`。目标芯片实际寄存器/Field 名可以在报告展示时由芯片映射解析，但不得反向覆盖 Canonical `endpoint/source/value`；
- Artifact 路径必须相对当前 Run，禁止绝对路径和 `..`；
- 数值保存原始值，十六进制、单位、精度等属于 Contract/报告显示元数据；
- PASS 与 FAIL 使用同一种 Observation 结构，结果状态不得改变事实字段；
- 孤立文件未进入 Canonical Result 的 `artifacts` 或 Observation `artifacts`，不能声称已绑定 Evidence；
- 报告兼容读取已绑定结构化 JSON 附件时，只能读取 Result 已登记且仍位于当前 Run 内的文件，禁止扫描目录猜测。

### 5.1 Artifact Snapshot 语义

`write_json_result()`发布的是**当前完整Snapshot**，不是Merge、Append或增量日志接口。同一路径再次写入时，当前实现会原子替换旧文件；旧字段不会自动保留。

因此：

- Case不得假设多次写同一路径会累积Evidence；Case层的允许写法由R210约束；
- 需要最终单文件附件时，调用方必须先在内存中组装完整结构，再一次性发布完整Snapshot；
- 需要保留多个阶段现场时，应发布语义不同的独立Artifact路径，而不是反复改写同一路径；
- 决定PASS/FAIL的少量关键事实优先进入Canonical Measurement/Observation，不能只依赖一个可能在后续被替换的中间Artifact。

最小反例：

```python
write_json_result(path, {"before": 1})
write_json_result(path, {"after": 0})
# 最终 path 只保证包含第二次Snapshot；不能把 before 当成仍然存在。
```

### 5.2 Canonical JSON值边界

进入Canonical Result或结构化Artifact的值必须能够完成无歧义JSON往返。稳定允许类型只有：

```text
null / bool / int / finite float / str
list[JSON value]
dict[str, JSON value]
```

固定规则：

- `bytes`、`bytearray`和`memoryview`必须在Canonical写入边界统一归一为`0..255`整数列表；Case和报告层不得各自选择Hex字符串、Python表示或其他私有编码。
- 映射键必须是字符串；`NaN`、正负无穷、集合、自定义对象、异常对象和开放文件句柄不得进入Canonical JSON。
- 不支持类型必须在写入边界失败关闭，禁止使用`str(value)`静默降级，也禁止生成`b'...'`等Python专属表示。
- 类型归一只改变存储表示，不得改变原始测试含义。需要表达摘要、Hash、单位或格式时，Case必须将其作为独立、命名清楚的稳定事实记录。
- 参数化Case的每个execution分别满足本节；某一参数分支可序列化不能证明其他分支也可序列化。

该类型边界属于Canonical Result公共能力。新增IP不得复制序列化器，也不得在Case、Driver或
`<ip>.md`中声明另一套JSON兼容规则。

## 6. Evidence完整性

```text
require_evidence(...)
= 声明本Case形成可信结论必须消费的来源

record_evidence(...)
= 登记本次执行确实消费的来源

record_observation(...)
= 登记真实设备事实，并自动登记对应Evidence来源
```

Fixture 名称、Bench 配置、Capability 声明和设备已连接都不能证明 Case 实际消费了 Evidence。

```text
missing = required_evidence_sources - evidence_sources
evidence_complete = missing为空
```

Case 声称使用 Peer、FPGA 或仪器时，必须真实产生对应来源的 Evidence/Observation；不得靠测试作者
文字说明或报告模板补足。未知 Evidence Source 必须被公共接口拒绝。

## 7. 报告只读派生边界

报告层必须失败关闭校验：

- Session 与 Result 的 `run_id` 一致；
- `case_run_id` 唯一；
- Case ID 存在于公共机器契约；
- Result 属于 Session 记录的实际 Selection；
- Canonical Status 属于当前允许集合；
- 同一参数 execution 不重复；
- 声明的 Observation 和报告字段真实可解析。

报告可以将没有可信硬件失败Observation的原始 FAIL 显示为 `RUN_ERROR`，也可以把缺少结构化
Observation 的执行显示为 `EVIDENCE_MISSING`；但不得回写 `result.json`，也不得把软件异常显示为
DUT FAIL。

报告为了人工可读性，可以基于当前 Session `chip_id` 和已审核 `<CHIP>_<ip>.md` 映射，把稳定 Observation endpoint 的展示标签补充为目标芯片实际寄存器/Field名称。这属于**只读显示增强**：必须保留原始 Canonical key/value/source/endpoint，不得重新解释值、改变状态、执行新设备读取或在映射缺失时猜测芯片寄存器名。

人工报告的展示还必须满足：

- 结构化字典和列表使用统一的人读格式器展示有限字段，不得直接输出原始JSON或Python `repr`；
- `count`格式允许消费已经计算好的非负整数或可计数集合，其他类型必须失败关闭；
- 展示转换不得覆盖Canonical原始值，也不得通过自由文本重新计算PASS/FAIL；
- 声明字段缺失、格式与值类型不兼容或结构无法确定性展示时，报告生成失败，不得静默留空冒充完整报告。

## 8. 存储与原子性

Canonical JSON 使用同目录临时文件写入后原子替换，避免正常中断留下半个 JSON。原子替换只保证单次Snapshot完整，不提供跨多次写入的字段合并。具体运行目录由`R500_operator_pipeline.md`唯一管理；本文只要求：

```text
one Session -> one session.json
one execution -> cases/<case_run_id>/result.json
large/raw evidence -> independent file + canonical relative reference
```

不得把数据库、Web事件流或未来Analyzer设计提前写成当前稳定Contract。

### 8.1 当次事实与长期Case知识

- 当次Canonical Session、Result及绑定附件仍是执行事实；事实摘要和Excel只读派生，不修改状态、值、时间、Lane、版本或未知身份。
- 长期Case Markdown是Agent提炼的工程知识，不是结果数据库、最新PASS列表或每轮日志。它独立于原始JSON/ZIP即可读懂，但不声称替代可重新计算的原始测试证据。
- Agent测试前读取目标Case知识、公共方法和未关闭问题；测试后对照本次Selection、全部参数execution、版本和实际观测，决定补充新知识、修正已有知识或确认没有新知识。
- 测试过程中可以增量提炼已确认知识。Agent每轮结束必须完成核对再显式review。当前原始事实按R500覆盖，不以保留每轮原始目录替代知识整理。进行中的Session不允许提前review。
- 人可以不调用`review`；该轮原始现场可能在下一轮被覆盖。
- Agent每一轮结束后必须review；不得把「人可不」读成Agent也可跳过。
- 人覆盖`current/`后，已有`cases/<CASE_ID>.md`保留。Agent不得虚构已丢失轮次，也不得把旧Markdown当成已对照消失的`current/`确认。
- 有效知识包括：实际测试方法及与公共方法的差异、关键现象与少量决定性值、适用基线、根因及其置信程度、排查方法、修复动作、复测结论和未关闭问题。没有内容的章节不强制填写。
- 首次整理必须形成最小可用方法与适用范围；重复PASS且没有新知识时不修改正文、不累加执行次数、不追加流水账。
- 失败原因未知时明确标记待确认，不能从错误摘要自动推断根因；后续PASS只代表该次执行结果，不自动关闭问题，也不扩大到其他参数、Lane或版本。
- 已选但未执行的参数仍是派生的NOT_EXECUTED；SKIP、FAIL、EVIDENCE_MISSING和未知身份保持边界。不同版本的最近观测不能拼成同版本完整回归。
- 事实提取工具默认只输出Case/参数状态、错误摘要与身份，按Case列出可查询键，按精确键读取原始值。同一Observation键下的多条观测按原顺序完整返回，各自保留source/device/endpoint/value，不覆盖或合并设备事实。摘要截断必须显式标识；禁止整份JSON/ZIP灌入正文或自动撰写分析。
- 每份知识标注芯片、Lane、源码/方法/固件等已知适用基线及未知项；版本变化后由Agent判断知识适用性和复测范围，工具不猜测影响。
- 脚本只提取事实、检查Markdown结构/链接、刷新IP索引并登记显式整理确认，不改Case正文、不推断修复、不生成长期结构化快照。静态检查PASS不代表分析正确或问题关闭。
- 原始现场的保留、显式整理确认、复用回执、必要附件和历史迁移由R500规定。

## 9. 回归与变更规则

当前Owner由现有行为回归保护：

```powershell
pytest pc/et_test_platform/framework_validation/unit/scheduling/test_run_context.py
pytest pc/et_test_platform/framework_validation/unit/core/test_result_integrity_gate.py
pytest pc/et_test_platform/framework_validation/unit/results/test_case_report.py
python tools/validate_pc.py
```

修改 Canonical字段、Status优先级、Evidence完整性、Observation身份、Artifact绑定或报告只读边界时，
必须先更新本文，再同步最小运行代码与上述回归。禁止通过报告层猜测、Case私有格式、放宽Evidence门禁
或增加第二套结果状态系统来兼容局部需求。

新IP或既有IP改变Evidence结构时，进入HIL前必须使用接近真实Case形状的代表性数据完成：

```text
Canonical Result写入
-> JSON重新读取
-> ET_CASE_REPORT字段解析
-> 人工报告模型
-> Excel导出
```

代表性数据必须覆盖该IP实际使用的嵌套结构、参数聚合和边界类型；只测试简单标量不能证明报告链闭合。
模拟数据只能作为软件契约回归，禁止记录为真实硬件Evidence。
