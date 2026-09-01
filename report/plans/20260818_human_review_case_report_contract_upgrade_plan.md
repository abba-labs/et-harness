# Human Review Case / Report Contract 最小改造计划

> 状态：计划草案（非现行规则，不具备规则权威）
>
> 目标：在不重构现有测试架构、不改变已验证测试行为的前提下，把 `test_case_doc/<ip>/<ip>.md` 与最终 Excel 报告收敛为稳定的人类审核接口，使 Reviewer 无需逐行阅读 PC Case / Firmware Case 实现，即可判断“测什么、怎么测、实际得到什么、为什么 PASS/FAIL”。

## 1. 背景与核心问题

当前 Formal Case 的机器契约已经能够驱动报告生成，但部分 IP 的人读信息存在明显失真：

- `report_feature` 使用“矩阵、语义、生命周期、路径”等工程标签，Reviewer 无法直接知道具体验证能力。
- `method.inputs` 与 `method.steps` 过度压缩，甚至输入和步骤内容相同，无法还原测试逻辑。
- `pass_criteria` 使用“符合预期、结果正确”等抽象表述，缺少可核对的具体条件。
- `ET_CASE_REPORT` 虽然能够从真实 Artifact / Measurement / Observation 中提取字段，但当前备注更像结果标签，不足以证明“本次确实执行过并取得关键硬件证据”。
- 参数化 Case 的多个相关字段如果分别使用 `distinct` 聚合，可能破坏 `parameter -> expected -> actual` 的对应关系。

本计划不以“写得更长”为目标，而以“人能审核”为目标。

最终人审主链固定为：

```text
Feature
-> 输入 / 配置
-> 6~8 条测试步骤
-> 通过条件
-> 本次执行关键证据备注
-> PASS / FAIL
```

## 2. 权威顺序与变更原则

本次改造严格遵守仓库现有权威顺序：

```text
AGENTS.md
> Rxxx 活动规则
> test_case_doc/<ip>/<ip>.md
> 当前实现代码
> report/plans（本计划，仅用于实施导航）
```

固定原则：

1. 先修改现有规则 Owner 的唯一正文，不先改 IP 文档或代码。
2. 不新增平行规则体系；现有 Owner 能表达的职责必须扩展现有规则。
3. 规则稳定后，再逐 IP 审核和优化 `<ip>.md`。
4. `<ip>.md` 明确后，再检查代码是否已经满足文档；只有确实缺少关键 Evidence 时才最小补码。
5. 测试行为、Driver API、Firmware Service、Wire、Capability 默认不变。
6. 若仅为人读表达优化，不得顺手重构测试流程。
7. 若发现真实“文档与实现语义不一致”，停止可读性迁移，单独报告为语义缺口，不在本任务中猜测修复。

## 3. 第一阶段：规则层收敛

### 3.1 规则治理入口

规则修改前必须编译 `governance / rule` Task Context，并读取：

- `AGENTS.md`
- `R001_agent_rule_governance.md`
- `rule_owner_catalog.yaml`
- 目标 Rxxx 正文
- 对应 Checker / Regression

本次原则上不新增新的 `Rxxx` 文档。

### 3.2 R120：主要规则修改点

`R120_public_ip_machine_contract.md` 是本次最主要的规则 Owner，应增加“Human Review Contract”约束，至少明确：

#### Feature

- `report_feature` 必须直接说明“验证什么能力”。
- 必须能看出关键模式、条件或对象；不能只写内部工程标签。
- 禁止仅以“矩阵、语义、生命周期、路径、能力、正确性”等抽象名词作为完整 Feature 描述。
- Feature 不要求展开实现细节、寄存器或 Driver API。

推荐目标形式：

```text
验证 <硬件能力> 在 <关键模式/配置> 下的 <可观测行为> 是否满足 <稳定预期>
```

#### Inputs

- 面向 Excel 的输入说明保持简洁，通常 1~3 条。
- 必须说明真正影响 Case 构造和判断的测试数据、参数矩阵、配置条件及必要的 Expected 来源。
- 参数化 Case 必须能看出“为什么有这些参数组合”。
- 不写 Buffer 分配、Python 对象、内部 Handle、Cleanup owner 等实现细节，除非它本身就是待验证 Feature。

#### Steps

Formal `ET_CASE_SPEC` / `ET_CASE_PLAN` 的 `method.steps` 固定为 **6~8 条**。

6~8 条步骤必须按真实执行顺序覆盖以下逻辑链：

```text
准备输入
-> 配置 DUT
-> 施加激励
-> 启动 / 等待硬件完成
-> 读取关键输出 / 状态
-> 获取 Expected / Golden
-> 比较与判定
-> 参数化 Case 必要时汇总
```

允许合并相邻动作，但不得压缩成一句概括，也不得扩展到代码实现级别。

#### Pass Criteria

- 通常 2~5 条。
- 必须可直接核对，不得只写“符合预期”“结果正确”“状态正常”。
- 稳定值明确时直接写具体条件，例如 `produced_bytes = 16`、`FINISH = true`。
- 参数化 Case 必须明确完整执行条件，例如 `12/12`。
- 每个关键 PASS 判据必须能追溯到真实 Observation / Measurement / Artifact 或明确的独立 Oracle。

#### Report Remark / ET_CASE_REPORT

继续复用现有 `ET_CASE_REPORT`，优先不新增 Schema。

人读备注目标为 **3~6 行**：

```text
执行覆盖 / PASS-FAIL 数量        # 报告公共层自动生成
稳定摘要                          # summary
1~4 个关键 Evidence              # fields
```

关键字段优先选择：

- 硬件完成/状态；
- 实际输出长度/计数；
- 关键硬件实际值；
- Expected/Actual 比较事实；
- 中断/请求/状态位；
- DMA/UART/ADC 等 Feature 的决定性硬件证据。

禁止把固定文本“验证完成”当作唯一备注证据。

参数化 Case 中，存在对应关系的字段不得通过独立聚合破坏关系。主备注优先使用可安全汇总的字段；FAIL 时必须能够定位失败 `parameter_id`，并使用同一字段白名单展示失败执行的关键值。

### 3.3 R140：IP 分析与 Case 规划规则

R140 负责让 Agent 从源头就产出可审核的 Feature / Case，而不是等到报告阶段再补文字。

建议增加：

- Feature Admission 除稳定语义外，还必须形成具体的人读 Feature 描述。
- Case Closure 完成时，必须先形成“输入 / 6~8 步 / Pass Criteria / 关键 Evidence”再视为 Implementation Ready。
- 完成 Gate 增加 Human Review Gate：
  - Reviewer 不读代码即可知道测什么；
  - 能顺序复原测试逻辑；
  - 能知道关键输出和 Oracle；
  - 能知道哪些运行证据将进入报告。
- 分析文档可以保留机器/Agent 所需的简洁字段，但人审字段不得为了省 Token 压缩语义。

### 3.4 R210：Formal Case 实现规则

R210 只做最小澄清，不把 Excel 文本复制进代码：

- PC Case 代码仍要求线性、可读、真实硬件顺序可见。
- 函数前注释可以比 `ip.md` 简洁，不要求复制完整 6~8 条报告步骤。
- 但代码实际流程、关键断言、Evidence 必须与 `ET_CASE_SPEC / ET_CASE_REPORT` 一致。
- 报告要求展示的关键硬件 Evidence 若已在 Case 中取得，必须在 decisive assert 前记录。
- 不得为了报告增加假的“硬件值”；软件比较结果只能作为软件/Oracle事实，不得伪装成 DUT Observation。

### 3.5 R110 / R130 / R001

默认不修改，先复用现有规则：

- R001：已经规定“优先扩展现有 Owner、规则变更顺序、同步 Checker/Regression”。
- R110：已经规定 IP Contract 与实现必须双向一致。
- R130：已经规定 Canonical Result / Observation / Evidence 与报告只读派生边界。

只有后续设计确实改变这些 Owner 的稳定语义时才修改，避免“顺手补规则”。

### 3.6 规则层机器门禁

优先增加可确定性检查，不使用 LLM 参与 PASS/FAIL。

建议最小新增 Checker 条件：

- `method.steps` 必须为 6~8 条。
- `inputs` 与 `steps` 不得是同一内容或明显整段重复。
- `pass_criteria` 必须达到最小条目数。
- `ET_CASE_REPORT` 参数关联字段不得使用已证明会破坏关系的组合方式。
- SPEC 与 PLAN 规则一致时，分别由现有 `validate_case_docs.py` / `validate_case_plans.py` 检查。

“Feature 是否足够具体”存在语义判断成分：规则正文负责约束 Agent，Checker 只检查可靠的结构性红线，不建立脆弱的 NLP/关键词评分系统。

若增加新的 `ETCASExxx / ETPLANxxx` 诊断：

- 进入现有 `public_ip_machine_contract` Owner；
- 更新 `rule_owner_catalog.yaml` 诊断范围；
- 同步 Checker Regression；
- 不新建 Owner / 命名空间，除非现有 Owner 无法表达。

## 4. 第二阶段：逐 IP 审核和优化 `<ip>.md`

规则层通过后，按 IP 独立处理，不进行全仓一次性批改。

建议顺序：

```text
AES（已知问题，作为 Pilot）
-> CRC
-> DMA
-> UART
-> Framework Communication / 其他已实现 Formal IP
```

每个 IP 先只做“合同审核”，将所有 Case 分类：

| 分类 | 含义 | 默认动作 |
|---|---|---|
| A：纯描述问题 | 测试行为正确，只是 Feature/Method/Pass Criteria 抽象 | 只改 `<ip>.md` |
| B：报告字段已有 | 想展示的关键 Evidence 已经由 Case 记录 | 只改 `<ip>.md` 的 ET_CASE_REPORT |
| C：Evidence 未记录 | PC 已经读取/断言该值，但没有留进 Result/Artifact | PC Case 最小增加记录 |
| D：公共报告缺口 | 执行覆盖、失败参数、聚合方式属于所有 IP 的共同问题 | 只改一次公共 report model |
| E：真实语义不一致 | 文档描述与实际 Case 行为不一致 | 停止本 Case 迁移，单独评审 |

每个 Case 的人审目标固定检查：

```text
Feature具体吗？
输入/配置清楚吗？
6~8步是否完整形成逻辑链？
通过条件是否具体、可核对？
备注准备展示哪些关键证据？
这些证据当前代码真的产生了吗？
```

### 4.1 重要顺序

“先梳理 `ip.md`，再优化代码”指设计顺序，而不是允许长期留下 Contract/Code 不一致。

最终可合入的同一逻辑变更必须满足 R110：

```text
规则已稳定
-> 人先审核 ip.md 目标表达
-> 对照当前代码做 Gap 分析
-> 只补必要 Evidence / 公共报告缺口
-> 文档与代码同时闭环
```

若 `ip.md` 只是文字展开、没有改变测试语义或报告字段，允许没有代码修改。

若 `ET_CASE_REPORT` 新增了代码当前没有记录的字段，则该 IP 的最终变更必须同时补齐对应 Evidence。

## 5. 第三阶段：公共报告层最小改造

只有 AES Pilot 的 `ip.md` 审核完成后，才确定公共报告层最终改动，防止先设计通用框架。

当前优先方案：**不新增报告 Schema，不改变 Excel 主表结构。**

现有 Excel 主表已经具备：

```text
测试Feature
测试方法（含通过条件）
测试Case ID
测试结果
备注
```

因此默认不修改 `tools/reporting/generate_case_report.py` 的列结构。

公共 `case_report.py` 仅考虑以下最小能力：

1. 自动在备注增加执行覆盖：
   - 实际执行 / 期望执行；
   - PASS / FAIL / SKIP 等必要数量。
2. 继续使用 `ET_CASE_REPORT` 的 `summary + 1~4 fields`。
3. FAIL 时自动显示失败 `parameter_id`。
4. FAIL 的关键值仍只使用该 Case 已声明的同一字段白名单，不直接展开任意 JSON。
5. 参数化主备注不再通过独立 `distinct` 展示需要保持一一对应的多列数据。
6. 完整原始 Evidence 仍保存在 Canonical Result / Artifact；人读主表只显示关键证据。

只有上述方案无法满足真实 IP Case 时，才评审是否需要 Schema 扩展。禁止为了 AES 单个 Case 新增 AES 私有报告格式。

## 6. 第四阶段：PC Case Evidence 最小补齐

代码修改遵循“记录现有事实，不改测试行为”。

允许的典型改动：

```text
原来：
读取 FINISH
assert FINISH

改为：
读取 FINISH
记录 FINISH
assert FINISH
```

或：

```text
原来：
actual / expected 已经取得
assert actual == expected

改为：
记录 expected / actual / 比较结果
assert actual == expected
```

禁止的默认改动：

- 改 Driver Public API；
- 改 Firmware Service / Wire；
- 改 Hardware 配置顺序；
- 改 Timeout；
- 改断言强度；
- 改 pytest 参数矩阵；
- 改 Case ID；
- 重构 Fixture / Helper；
- 为报告增加新的硬件访问。

若报告希望展示的硬件状态当前 PC 根本取不到：

```text
STOP
-> 记录“观测能力缺口”
-> 单独评审是否需要 Driver/Firmware/Wrap 扩展
```

不得在“报告可读性”任务中顺手向下扩架构。

## 7. AES Pilot 预期最小改动示例

以 `AES_P0_002` 为例，目标不是马上照此修改，而是作为 Pilot 审核模板。

### 文档层

`report_feature`：

```text
AES ECB/CBC/CTR × AES-128/256 × Encrypt/Decrypt 固定参考向量运算正确性
```

`inputs`：1~3 条，说明 12 组参数组合、Key/Input、CBC IV、CTR Counter、独立 Golden。

`steps`：固定 6~8 条，覆盖：

```text
选择向量
-> 配置 AES
-> 输入并启动
-> 等待完成
-> 读取 Actual / produced_bytes / FINISH
-> 计算 Golden
-> 比较并汇总
```

`pass_criteria`：明确：

```text
12/12执行
Actual逐Byte等于Golden
produced_bytes=16
FINISH=true
```

`ET_CASE_REPORT`：优先选择可安全汇总的 3~4 个关键 Evidence，而不是长串所有 Actual。

### 代码层 Gap 预估

当前 Case 已记录：

```text
vector_id
expected
actual
produced_bytes
```

当前 Case 已读取并 Assert、但未记录：

```text
FINISH
```

因此若审核决定备注必须显示 FINISH，原则上只需增加该 Evidence 记录，不改变 AES 测试行为。

## 8. Task Context 拆分

本次不要使用一个超大 Task Context 修改所有层。

建议按责任域重新编译：

### 8.1 规则阶段

```text
module = governance
change = rule
```

只允许规则正文、Catalog、Checker及其规则回归。

### 8.2 单 IP Contract / Case 阶段

```text
module = ip-package
change = case
ip = <ip>
```

用于已存在 Formal IP 的 `<ip>.md` 与对应 PC Case 同步。

如果审核发现不是可读性问题，而是 Feature / Case 语义本身需要重新分析，再扩围为：

```text
module = ip-package
change = analysis
ip = <ip>
chip = <chip>
```

不得在 Case 可读性任务中直接重新扫描所有原始资料。

### 8.3 公共报告模型阶段

```text
module = operator-pipeline
change = report
```

只修改公共报告模型、Excel转换及对应 Unit Test。

任务扩围前先执行前一 Task Context 的 `scope-check`。

## 9. 验证计划

### 9.1 规则阶段

```powershell
python tools/quality/validate_rule_governance.py
python tools/quality/validate_case_docs.py
python tools/quality/validate_case_plans.py
python tools/validate_pc.py
git diff --check
git status --short
```

### 9.2 每个 IP

```powershell
python tools/quality/validate_case_docs.py test_case_doc/<ip>/<ip>.md
python tools/quality/check_case_spec_implementation.py
python tools/quality/check_pc_code_rules.py --root . pc/et_test_platform/test_cases/<ip>
python tools/quality/check_case_orchestration_rules.py --root . pc/et_test_platform/test_cases/<ip>
python -m pytest --collect-only -q pc/et_test_platform/test_cases/<ip>
python tools/validate_pc.py
```

纯文档变更时只运行适用的最小门禁，但最终合入前仍运行仓库总软件门禁。

### 9.3 公共报告层

```powershell
python -m pytest -q pc/et_test_platform/framework_validation/unit/results/test_case_report.py
python tools/validate_pc.py
```

增加至少以下 Regression：

- 备注自动显示 execution coverage。
- PASS/FAIL 使用同一字段白名单。
- 参数化 Case 的失败 `parameter_id` 可定位。
- 关联字段不会因独立 `distinct` 造成错误的人读对应关系。
- ET_CASE_REPORT 引用不存在字段时继续失败关闭。
- 报告不扫描目录、不重新执行设备、不修改 Canonical Status。

### 9.4 最终代表性 HIL

完成软件层后，以 AES Pilot 生成一次真实 Excel：

人工检查：

```text
Feature是否一眼能看懂
测试方法是否6~8步且逻辑完整
通过条件是否具体
备注是否能证明本次真实执行
失败/参数信息是否可定位
Excel是否保持简洁
```

未执行真实硬件时必须明确 `NOT_EXECUTED`，软件门禁不能替代 HIL。

## 10. 变更文件预估

### 规则层（预计）

```text
report/design/rules/R120_public_ip_machine_contract.md      # 必改
report/design/rules/R140_ip_analysis_workflow.md             # 建议改
report/design/rules/R210_pc_case_responsibility.md           # 小幅澄清
report/design/rule_owner_catalog.yaml                         # 仅新增诊断码时改
tools/quality/validate_case_docs.py                           # 增加可机械验证的红线
tools/quality/validate_case_plans.py                          # 与 SPEC 对齐
对应 Checker / Rule Governance regression                    # 按现有位置最小增加
```

默认不改：

```text
R001
R110
R130
AGENTS.md
```

除非实施过程中证明现有正文无法表达新的稳定职责。

### 公共报告层（预计）

```text
pc/et_test_platform/results/case_report.py
pc/et_test_platform/framework_validation/unit/results/test_case_report.py
```

默认不改：

```text
tools/reporting/generate_case_report.py
```

因为现有 Excel 主表字段已经满足人工 Review 结构。

### 单 IP（按审核结果）

```text
test_case_doc/<ip>/<ip>.md
pc/et_test_platform/test_cases/<ip>/test_<ip>_p*.py   # 只有缺 Evidence 时改
```

默认不改：

```text
PC Driver
Firmware Service
Firmware Wrap
Chip Driver
Wire
Capability
```

## 11. 停止条件

出现以下任意情况时停止“可读性最小改动”，不得继续扩围：

1. 需要改变 Case 测试语义或参数矩阵。
2. 需要新增/修改 Driver Public API。
3. 需要新增 Wire Command。
4. 需要修改 Firmware Service/Wrap 才能取得新硬件事实。
5. 需要改变 Timeout、Cleanup、断言或设备操作顺序。
6. 发现 `ip.md` 与代码真实行为冲突，无法仅通过文字澄清解决。
7. 为满足某个 IP 必须新增私有报告 Schema 或私有公共框架。

这些情况必须单独形成问题证据和新的 Task Context，经评审后再处理。

## 12. 最终完成标准

本次迁移只有同时满足以下条件才算完成：

```text
规则层：
Human Review Contract 已进入现有 Owner 正文
+ 可机械验证部分已有 Checker

IP 文档层：
Feature具体
+ 输入清楚
+ 6~8步测试逻辑完整
+ 通过条件具体
+ 关键报告 Evidence 已定义

代码层：
真实实现与 ip.md 一致
+ 报告需要的关键事实真实记录
+ 无无关架构/行为变化

报告层：
主 Excel 一眼可判断测什么、怎么测、为什么 PASS/FAIL
+ 备注有关键真实硬件证据
+ 参数化失败可定位
+ 原始 Evidence 可追溯

验证：
专项门禁 PASS
+ 总软件门禁 PASS
+ 代表性真实 HIL Excel 人工 Review 通过
```

---

## 建议执行顺序

```text
Phase 1  规则 Owner / Checker
   ↓ 人工审核规则
Phase 2  AES ip.md Pilot
   ↓ 人工审核 Feature / Method / Criteria / Remark design
Phase 3  AES 最小 Evidence + 公共 Report gap
   ↓ 生成 Excel 人工审核
Phase 4  CRC / DMA / UART / 其他 Formal IP 逐个迁移
   ↓
Phase 5  全量软件门禁 + 代表性 HIL + 最终 Review
```

本计划本身不具备规则权威。实施时如与 `AGENTS.md` 或活动 Rxxx 冲突，以活动规则为准。
