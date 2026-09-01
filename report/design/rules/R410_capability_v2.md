---
schema: et.rule-document.v1
number: R410
domain: capability
lifecycle: active
owners: [capability_v2]
rule_ids: [ET-RULE-CAPABILITY-V2]
---

# R410 Capability v2 契约

## 1. 定位

`et-ip-capability/v2`是PC测试用例查询芯片IP语义能力的稳定接口。它不是寄存器
清单，也不描述测试覆盖率。每颗芯片的每个IP仍使用一个`<ip>.yaml`。

本契约已经由事实IR、保守语义归一、审计输出、不可变运行时查询和`explain`
链路共同落实。Schema契约使用`et_contract_test`隔离验证；正式芯片能力分别存放在
`profiles/chip_capabilities/<chip>/ip/`，只有通过加载、证据闭合和质量门禁的文件才是
运行时基线。临时生成物、Audit候选和测试夹具均不得冒充正式芯片能力。

项目的Capability工具必须独立实现。`RegGen`、芯片SDK工具目录和厂内生成脚本只能
作为设计参考，不能成为运行依赖或隐式输入。

## 2. 单一工具链边界

正式流程只有一个CLI入口：

```text
generate_capabilities.py --svd <input.svd> \
  --semantic-output-dir <chip>/ip --audit-output-dir <chip>/audit
```

CLI内部允许拆分成可测试的解析、事实IR、语义归一、输出和校验模块，但不得按芯片
或IP建立不同生成脚本。输入SVD由调用侧显式选择；输出必须记录输入文件名、SHA256
和生成器版本。

### 2.1 SVD事实层

语义归一前必须先产生`et-svd-facts/v1`规范JSON。该文件是机器审计产物，不由
pytest读取，也不允许人工修改。它保留后续Capability推导所需的事实：

- device、peripheral、cluster、register、field、标准枚举和interrupt描述；
- `derivedFrom`来源、基地址、偏移、绝对地址、访问属性、复位值和复位掩码；
- register/cluster数组的原始名称、展开索引和完整逻辑路径；
- 标准`enumeratedValue`的值、说明和`isDefault`；
- description内`Values:`的原始文本及确定性解析结果；
- IRQ名称、IRQn、输入文件名和输入字节SHA256。

这里的“无损”指Capability推导边界内的事实不得被静默丢弃，不表示能够从JSON反向
还原原始XML排版。暂不支持的`derivedFrom`层级或无法无歧义表示的路径必须失败，
不得猜测。同名寄存器若偏移不同，路径追加固定偏移限定符，例如
`DAC0.TDAT@0x00000004`；同名且同偏移仍报错。同地址但名称不同的合法别名完整保留。

生成和确定性检查：

```powershell
python tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --facts-output <facts.json> `
  --facts-only

python tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --facts-output <facts.json> `
  --facts-only `
  --check
```

语义归一阶段只能消费该IR，不得重新扫描SVD；这样事实解析只有一个实现。

### 2.2 语义归一层

`svd_semantics.py`是唯一通用语义归一器。它不允许出现芯片名、IP名、外设地址、
实例数量或按IP选择的规则文件。当前只输出能够由SVD直接证明的语义：

- peripheral基地址直接生成`identity.base_address`；
- 非负IRQ直接生成结构化`interrupt`，实例前缀被稳定去除；
- 仅1 bit且字段名明确以`EN/ENABLE/ENABLED`结尾时生成Feature；
- 仅标准`enumeratedValue`或description内明确`Values:`生成Option；
- 全部Option都是显式数字时，才允许生成其最大值Limit；
- 只读且寄存器明确标记为Component Parameter时，可从复位选中枚举生成实现参数；
  当前仅接受字段首段明确为`CHn/channelN`的通道级参数；
- 只读ID、TYPE、VERSION类字段可由复位值生成Identity；
- 未命中、歧义或不支持的事实全部进入Audit，不得猜测。

语义名称稳定性规则：

- 原字段名已经是稳定自然语义时，禁止使用description改名；
- 仅当缩写占名称token的一半及以上时，才允许尝试description展开；
- 展开来源只允许字段description的首个英文名词短语，或全部枚举description中
  一致的`<subject> is ...`主语；
- 候选必须为2到8个英文token，不能以动作词开头，并且必须保留原名中已有的完整词；
- 展开后仍以缩写为主、包含歧义、混合语言或无法证明时，不生成运行时Capability，
  原事实进入Audit；
- 纯数字IRQ后缀统一为`line_<n>`，`COMBINT`统一为`combined`；两者是全局中断
  词汇，不是GPIO专用规则；
- 禁止芯片/IP映射表、人工别名字典和按文件名选择规则。

任何语义规则变化必须提升`source.generator_version`。相同SVD和相同生成器版本
不得产生不同Capability接口。

生成、检查和解释命令：

```powershell
python tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --semantic-output-dir <chip>\ip `
  --audit-output-dir <chip>\audit

python tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --semantic-output-dir <chip>\ip `
  --audit-output-dir <chip>\audit `
  --check `
  --explain dma.interrupt.transfer_done
```

`--explain`返回Capability当前值及其全部Evidence，供审核者直接追溯，不要求人工
重新搜索SVD。

### 2.3 质量审核层

`capability_quality.py`只消费本次内存中的Fact IR、Profile和Audit，不修改语义
结果。Fact IR与Profile的SVD SHA256或IP集合不一致时立即失败。它输出确定性的
`et-capability-quality/v1` JSON，包含：

- Profile、实例、能力定义、实例能力值和Evidence数量；
- 去重后的已分类事实、未分类事实及语义事实比例；
- 每个IP是否只有Identity而没有可测试语义能力，并区分“存在显式候选但命名/归一
  尚未解决”和“没有通用显式候选”；
- 对Identity-only IP进一步标记`read_only`、`writable`或`mixed`寄存器面，只陈述
  访问结构，不推断字段语义；
- 每个IP的Audit原因计数，以及尚未归类的Feature、Option、Limit、Interrupt显式
  候选；
- 每个IP的完整Capability ID索引，使重命名也必然改变质量报告；
- 过短缩写、过于泛化名称、跨类别同名等审核提示；
- 已分类组件参数的完整枚举域一致性；参数生成后也不能遮蔽源SVD中的通道枚举差异；
- 调用方通过`--require-capability`指定的关键自然查询及其Evidence数量。

命名提示和Identity-only只产生warning；事实同时出现在Profile与Audit、或必需查询
缺失属于error并使CLI失败。比例只用于比较和审核，当前不设置武断的全局通过阈值。

显式候选不是运行时能力。候选必须来自生成器已经认可的通用SVD形状：标准一位
`EN/ENABLE`字段、标准/内联枚举、显式数值枚举或声明的IRQ。候选按去数字化的相对
字段路径、规则、原因和值集合聚合，报告出现次数、实例、源字段名和最多3条示例
路径；完整逐事实路径仍保留在Audit。这样既避免按IP猜测，又避免审核重复通道字段。

```powershell
python tools\capabilities\generate_capabilities.py `
  --svd <input.svd> `
  --semantic-output-dir <chip>\ip `
  --audit-output-dir <chip>\audit `
  --quality-output <chip>\quality.json `
  --require-capability dma.interrupt.transfer_done `
  --check
```

## 3. 运行时Profile

根节点固定为：

```yaml
schema: et-ip-capability/v2
chip: et_contract_test
ip: dma
source:
  file: contract_test.svd
  sha256: <64 hex digits>
  generator_version: 6
instances:
  dma0: {svd_name: DMA0}
capabilities:
  features: {}
  limits: {}
  options: {}
  parameters: {}
  interrupts: {}
  identities: {}
evidence: {}
```

六类能力的值固定为：

| 类别 | YAML值 | 查询返回值 |
|---|---|---|
| `features` | 支持实例列表 | `bool` |
| `limits` | 实例到数字的映射 | `int/float` |
| `options` | 实例到非空标量列表的映射 | `tuple` |
| `parameters` | 实例到成员、成员到标量的两级映射 | 标量或不可变成员映射 |
| `interrupts` | 实例到`{svd_name, irqn}`的映射 | `InterruptCapability` |
| `identities` | 实例到字符串或整数的映射 | `str/int` |

能力名称使用小写英文、数字、下划线和可选点分段。名称表达稳定语义，例如：

```text
linked_list
max_block_transfers
transfer_types
transfer_done
base_address
fifo_depth
```

能力名称不得包含芯片名、实例名、寄存器地址或测试用例名称。

## 4. Evidence

每项语义能力必须有同名完整能力ID的证据：

```yaml
evidence:
  dma.feature.linked_list:
    - instance: dma0
      kind: field
      path: DMA0.CH0_CTL.LLP_SRC_EN
      rule: field_presence
  dma.parameter.fifo_depth:
    - instance: dma0
      member: channel_0
      kind: field
      path: DMA0.DMA_COMP_PARAMS_CH0.CH0_FIFO_DEPTH
      rule: readonly_component_parameter
```

证据项字段固定为：

- `instance`：该证据支持的逻辑实例；
- `member`：仅成员级Parameter必填，例如`channel_0`；其他能力不得依赖它；
- `kind`：`peripheral/register/field/interrupt`之一；
- `path`：SVD内的逻辑路径，不是磁盘路径；
- `rule`：稳定的推导规则标识，例如`direct`、`field_presence`、
  `inline_values`或`bit_width_pow2_minus_1`。

每个Capability值涉及的所有实例都必须至少有一条证据。缺证、证据引用未知实例、
证据引用未知Capability或重复证据均立即报错。

`rule`只记录当前Capability已经证明的确定性推导关系。当前规则标识包括`direct`、
`boolean_enable_field`、`enumerated_values`、`inline_values`、
`explicit_numeric_options_max`、`readonly_component_parameter`和
`readonly_reset_identity`。仅有相同位宽或相似描述不能成为证据。

## 5. Unclassified审计产物

未能可靠翻译成语义能力的SVD事实不得塞入运行时Profile，也不得静默丢弃。生成器
应在独立审计目录输出：

```yaml
schema: et-capability-audit/v1
chip: et_contract_test
ip: dma
source:
  file: contract_test.svd
  sha256: <64 hex digits>
  generator_version: 6
unclassified:
  - instance: dma0
    kind: field
    path: DMA0.TEST.TEST_MODE
    reason: no_semantic_mapping
```

审计产物不由pytest运行时加载，只用于生成门禁和人工审核。`reason`使用稳定标识，
例如`no_semantic_mapping`、`ambiguous_semantics`或`unsupported_encoding`。

## 6. 上游查询接口

Test Case只使用自然语义接口：

```python
capabilities.has_feature("dma", "linked_list", instance="dma0")
capabilities.limit("dma", "max_block_transfers", instance="dma0")
capabilities.options("dma", "transfer_types", instance="dma0")
capabilities.parameter("dma", "fifo_depth", instance="dma0", member="channel_0")
capabilities.parameter_members("dma", "fifo_depth", instance="dma0")
capabilities.interrupt("dma", "transfer_done", instance="dma0")
capabilities.identity("dma", "base_address", instance="dma0")
capabilities.evidence("dma", "feature", "linked_list", instance="dma0")
capabilities.evidence(
    "dma", "parameter", "fifo_depth", instance="dma0", member="channel_0"
)
```

查询通过加载时构建的不可变索引完成，不扫描YAML、不遍历寄存器，也不读取SVD。

## 7. v1迁移边界

字段级生成器仍可通过旧`--output-dir`输出`et-ip-capability/v1`，加载器暂时同时接受
v1和v2，避免中断已有验证。v1只作为迁移兼容，不再扩展新语义接口；新能力只能
进入v2语义链路。

正式ET芯片Capability在推导器完成且审计通过前不得落基线。

## 8. 测试套件能力需求清单

测试套件通过独立的`et-test-capability-requirements/v1` YAML声明自己真正消费的
Capability。该清单不是芯片Profile，不得写芯片名、寄存器名、地址或驱动覆盖状态：

```yaml
schema: et-test-capability-requirements/v1
suite: dma_p0
required_capabilities:
  - dma.interrupt.transfer_done
  - dma.option.transfer_type_and_flow_control
  - dma.parameter.max_block_size
```

规则固定如下：

- 一个测试等级一个清单；`suite`是跨芯片稳定名称；
- `required_capabilities`必须非空、无重复并使用完整语义Capability ID；
- 清单只冻结Case运行前必须查询的能力，不宣称芯片全部语义已经归类；
- 多个清单可以合并，但重复`suite`立即失败；
- `--requirements-file`把清单接入现有质量门禁；能力不存在或缺少Evidence时失败；
- 框架通信等不消费芯片IP能力的测试不建立空清单。

直接使用`--require-capability`仍用于临时诊断；正式测试套件使用版本化YAML，避免
命令行漏项或不同执行者使用不同清单。
