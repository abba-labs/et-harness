---
schema: et.rule-document.v1
number: R110
domain: public-ip
lifecycle: active
owners: [contract_document_sync]
rule_ids: [ET-RULE-CONTRACT-SYNC]
---

# R110 IP Contract 与代码同步规则

## 1. 定位与边界

本文只规定公共IP契约、芯片适配契约和实现代码必须如何保持双向一致。它不重新定义Feature、Case、Driver、Service或Wrap的具体语义。

## 2. 公共语义变更

以下变化属于公共语义变化，必须在同一逻辑变更中更新`test_case_doc/<ip>/<ip>.md`：

- Feature含义；
- Case测试方法、Oracle、清理、Evidence和报告字段；
- 公共Driver行为；
- Wire命令语义；
- Firmware Service行为；
- Common Wrap公共接口或稳定语义。

## 3. 芯片适配变更

以下变化属于芯片适配变化，必须更新`test_case_doc/<ip>/<CHIP>_<ip>.md`及对应机器事实：

- 支持的Feature、选项、范围和实例数量；
- 实例、IRQ、基址、引脚、执行映射；
- 芯片SDK Driver行为和Test Driver Extension；
- 芯片专属限制、Known Issue和验证证据。

当适配状态会影响公共支持摘要时，还必须同步公共`<ip>.md`的适配摘要，但不得把芯片事实写入公共Feature/Case定义。

## 4. Formal Case双向绑定

```text
ET_CASE_SPEC
  <-> ET_CASE_REPORT字段白名单和人工摘要
  <-> 稳定Case ID / Registry
  <-> 真实test_*函数
  <-> Case前置Feature/测试方法/通过条件注释
  <-> 决定性断言前记录的状态中立Observation
  <-> Canonical Result / Report
```

任一侧不一致时，变更未完成。代码发现契约错误时，应先修正或在同一逻辑变更中修正契约，不得让实现静默覆盖契约。

## 5. 禁止项

- 只改代码、不改受影响契约；
- 只改契约、不提供对应实现或明确状态；
- 为通过门禁删除Case、弱化断言或把失败改成SKIP；
- 在公共契约中写入一个芯片的寄存器、IRQ、基址或SDK类型；
- 把Proposal、Review或历史记录当作当前契约。

## 6. HIL 前后闭环

### 6.1 HIL 前的执行资格

Chip Case Adaptation必须直接约束运行资格：

- `ADAPTED`表示当前目标已经具备执行该公共Case核心Oracle所需的机器映射、Runtime能力和资源；
- 只有缺少外部物理接线、外部仪器或不可替代的外部Bench拓扑，导致Case无法安全产生刺激或独立观测时，才允许在第一次硬件Mutation前明确SKIP；
- `MAPPING_GAP`、Driver/Service/Wrap缺口、Runtime能力未发布、内部路由缺失或未分析清楚，均属于实现或集成缺口，不得记为SKIP。Case被选中时应失败关闭；尚未执行时记为`NOT_EXECUTED`并写明缺口；
- SVD、设计或公共契约已经声明的Feature，即使当前FPGA/芯片实测不符合预期，也不得通过删除Capability、关闭Runtime Feature或扩大SKIP隐藏，必须保留真实FAIL；
- 如果缺口只影响更强Feature覆盖、但不影响当前Case已经声明的输入、步骤和Oracle，应把Case标为`ADAPTED`，把剩余缺口保留在Feature Mapping或Common Gap中；不得让“可完整执行的Case”长期保持Gap，也不得让“核心映射未闭合的Case”直接产生PASS。

HIL前必须逐项核对：`Case Adaptation -> Runtime Gate -> Case主体第一次Mutation`。文档状态、运行Gate和代码路径不一致时，不得开始批量HIL。

### 6.2 HIL 后的证据回写

每次用于关闭问题、更新适配状态或形成正式报告的HIL结束后，必须在同一逻辑变更中更新对应`<CHIP>_<ip>.md`：

- 目标芯片和Lane；
- Firmware Build ID、Registry Hash及能够取得的Source身份；
- 逻辑Case数量与参数化Execution数量，二者禁止混写；
- PASS、SKIP、FAIL数量；
- 每个非PASS Case的稳定Case ID、原因和对应Gap；
- 证据目录或Evidence索引；
- 本次运行是否能够证明Exact committed SHA。

芯片文档必须使用唯一的`ET_CHIP_TEST_STATUS`区域保存当前测试状态。该区域记录当前结论，当前事实与报告按R500固定保留，长期经验提炼为Case知识；旧`artifacts/runs/`与既有正式HIL报告保持只读历史。禁止累积每轮原始日志。

```markdown
<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-24 18:40 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-24 18:30 CST` | `0123456789abcdef...` | `false` | `artifacts/records/<CHIP>/UART/current/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 33 | 33 | 30 | 0 | 3 | 0 | 41 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `UART_P1_008` | FPGA | SKIP | `UART_F_xxx` / Framing Error IRQ | 未产生Framing Error状态 | 当前连接不能稳定制造错误帧 | 接入可控帧格式激励后重测 | `artifacts/records/<CHIP>/UART/current/...` |
<!-- ET_CHIP_TEST_STATUS_END -->
```

固定规则：

1. `状态更新时间`是本区域最后一次人工同步时间，必须使用`YYYY-MM-DD HH:mm CST`；每次修改状态区域都必须更新。
2. `测试时间`是对应Evidence中的实际执行时间，不能用文档编辑时间替代。每个Lane只保留最新一次权威运行。
3. `注册Case`、`已执行Case`、`PASS/FAIL/SKIP/NOT_EXECUTED`均按稳定逻辑Case ID统计；参数化节点总数只写入`Executions`。
4. 必须满足`已执行Case = PASS + FAIL + SKIP`、`注册Case = 已执行Case + NOT_EXECUTED`。
5. 参数化Case只要存在FAIL Execution，逻辑Case记为FAIL；无FAIL但存在SKIP时记为SKIP；全部Execution通过才记为PASS。
6. 非PASS表记录当前FAIL、SKIP和仍需闭环的NOT_EXECUTED。没有这些状态时保留表头并写一行`— / NONE`，不得把未执行写成SKIP。
7. FAIL必须记录实际硬件现象、原因分析和复测条件；SKIP必须记录缺失的外部物理条件、已观察现象和解除条件；NOT_EXECUTED必须记录尚未执行的原因与实现缺口。
8. 公共`<ip>.md`禁止保存芯片实测状态；状态只进入对应`<CHIP>_<ip>.md`。
9. 同一Lane的新权威运行替换当前状态；旧原始事实按R500在知识整理确认后回收。可覆盖Evidence必须核对Run ID/版本，不能把后一次current当成先前结论的原始证明；既有历史与正式HIL报告不自动删除。

Runner的`PASS`只表示当前Execution中的断言通过，不会自动把`MAPPING_GAP`或`NEEDS_VERIFICATION`升级为`ADAPTED`。如果一个Gap Case产生PASS，必须先裁决：

1. 映射已经由当前直接证据闭合，但文档陈旧：更新映射、适配状态和证据；
2. Case声明范围比Feature更窄且核心Oracle完整：Case可改为`ADAPTED`，剩余Feature缺口继续保留；
3. Case绕过了未闭合映射或使用未经审核的常量：本次PASS不得用于关闭Feature/Case，必须修正Gate或实现后重测。

运行目录来自dirty工作树，或Session没有记录`source_revision`时，只能写成`Working-tree HIL`；不得写成`Current-SHA PASS`或`Exact-SHA PASS`。确切提交版本的结论必须由记录了相同Source Revision且`source_dirty=false`的运行证据支持。

### 6.3 文档收口条件

HIL任务只有同时满足以下条件才算完成：

```text
Case方法与代码主体一致
-> Case Adaptation与Runtime Gate一致
-> 运行结果与Artifact一致
-> Chip文档记录逻辑Case/Execution结果和非PASS原因
-> 公共适配摘要同步
-> 文档和代码门禁通过
```

只生成Artifact或Excel、但芯片文档仍写`HIL_PENDING`或`NOT_EXECUTED`，属于未完成；只修改文字掩盖代码Gate或Oracle缺口同样属于未完成。

## 7. 验证与追溯

```powershell
python tools/quality/check_ip_change_rules.py --all-chip-neutral
python tools/quality/check_case_spec_implementation.py
python tools/quality/validate_case_docs.py
python tools/quality/validate_chip_ip_docs.py
```
