---
schema: et.rule-document.v1
number: R140
domain: ip-analysis
lifecycle: active
owners: [ip_analysis_workflow]
rule_ids: [ET-RULE-IP-ANALYSIS]
---

# R140 IP分析与Case规划规则

## 1. 定位

本文只定义新IP如何从开放资料输入收敛为稳定Feature、Case规划和公共自动化语义。公共/芯片边界遵循R100，文档同步遵循R110，Case机器块及可机器判定的人审行语法遵循R120，运行Result/Evidence遵循R130，Capability机器Profile遵循R410。

分析阶段只写`test_case_doc/<ip>/`，不实现Driver、Case、Service、Wrap、Capability或Chip Driver。

公共`<ip>.md`同时是后续Agent实现和人工审核的稳定设计入口。给机器读取的字段可以简洁，但最终进入人工审核和Excel的Feature、输入、测试步骤、硬件观测、通过条件和关键Evidence必须具体、清楚、可顺序复原，禁止为了节省Token压缩掉测试逻辑。

## 2. 分析输入与资料导航

- 首次分析必须同时指定`ip`和`chip`。
- 必须读取`project-governance/ip-analysis-sources.yaml`；该文件只负责资料定位和分类，不定义Evidence用途或权威级别。
- 用户新增的手册、RTL、需求、日志、代码或其他资料允许直接加入本次Evidence Set，不要求先登记Source Map。
- Agent必须使用当前执行环境可访问的Locator；已登记资料无法访问时记`UNAVAILABLE`，不得用同名文件、历史记忆或其他芯片资料静默替代。
- 必须同时形成`<ip>.md`和`<CHIP>_<ip>.md`。
- 新芯片接入已有IP时先映射已有Feature/Case；只有新增跨芯片稳定语义才改公共定义。

### 2.1 最小读取协议

对Source Map中登记的每个资料根，只搜索与目标IP相关的文件、符号、测试入口和段落；禁止默认全文读取整个SDK或所有IP。

每个资料根必须记录一种搜索状态：

```text
FOUND       = 找到目标IP相关资料
NO_MATCH    = 已搜索，未发现目标IP相关内容
UNAVAILABLE = 当前Agent无法访问
```

出现新能力、语义冲突、历史测试意图不清或平台断点时允许定向扩大读取；问题解决后停止扩散。

## 3. Evidence与Source Coverage

资料类别不限制用途。同一资料可以支撑多个Claim，不同资料可以互相补充或暴露冲突。

每个关键Claim必须记录`来源路径 + 符号/寄存器/Case/章节 + 可证明事实`，并使用以下状态：

| 状态 | 含义 |
|---|---|
| `VERIFIED` | 有直接适用证据支持 |
| `UNKNOWN` | 当前Evidence Set无法定案 |
| `CONFLICT` | 两个可信来源对同一Claim直接矛盾 |
| `INFERRED` | 仅用于继续搜索，不得发布为确定事实 |

固定规则：

- 目标芯片/Revision的直接证据优先用于目标芯片结论；其他芯片可以提供继承线索和稳定语义证据，但不能单独证明目标芯片`SUPPORTED`。
- Driver/API、Capability、历史Case或某个字段缺失，均不能单独推出Hardware=`UNSUPPORTED`。
- 当前代码存在不等于Stable Contract成立；旧日志或其他SHA的PASS不等于当前执行PASS。
- 冲突无法由适用范围、Revision或更直接证据消解时，必须保留`CONFLICT/UNKNOWN`和解除条件。

`<CHIP>_<ip>.md`必须能追溯每个资料根的搜索状态。存在`UNAVAILABLE`时不得宣称资料全集已完成。

## 4. 固定分析顺序

```text
1. Source coverage：定位并搜索全部登记资料根和用户新增资料
2. Claim extraction：提取需求、能力、测试意图、冲突和未知
3. IP facts：Hardware / Register / Driver / IRQ / DMA /限制/错误/恢复
4. Source item trace：逐项处置Requirement、Test Point和其他有效测试语义
5. Feature admission：Source Item -> Public Feature / Capability / Gap
6. Case closure：复用、参数化、合并、拆分或新增Case
7. Automation contract：稳定数据、动作、观测、Oracle和PC/Firmware接口语义
8. Platform mapping：Capability、Bench、Execution Mapping和适配状态
9. Coverage gate：检查Source、Feature、Case、Gap和Unknown是否闭合
```

“源码存在”“入口调用”“日志PASS”必须分开记录；无正确性断言的代码不计功能覆盖。

## 5. Source Item全量处置

Source Item包括与目标IP有关的需求条目、Test Point、历史Case、硬件行为、Driver能力、错误/IRQ/DMA路径、边界、性能、压力和其他具有测试意义的输入。

每个有效Source Item必须进入Trace，不得静默丢失。新分析统一使用：

| 处置 | 含义 |
|---|---|
| `MAPPED` | 已由当前Feature/Case/Capability/Gap表达 |
| `MERGED` | 与其他Item合并到同一稳定语义 |
| `SPLIT` | 一个Item拆为多个独立Feature/Case |
| `SUPERSEDED` | 被更强Case或更强Oracle完整覆盖 |
| `REJECTED` | 测试未定义行为、逻辑错误或无有效测试语义 |
| `NOT_APPLICABLE` | 对当前公共语义或目标芯片不适用 |
| `DEFERRED` | 稳定语义成立，但当前缺安全刺激、独立观测或必要资源 |
| `UNKNOWN` | 证据不足 |
| `CONFLICT` | 可信输入互相矛盾且尚未消解 |

`MERGED/SPLIT/SUPERSEDED/REJECTED/NOT_APPLICABLE`必须记录目标Case或理由。

Source Map中`requirements`下的每个需求条目必须逐项处置；有效需求必须被当前Case集合覆盖，或明确落入`NOT_APPLICABLE/DEFERRED/UNKNOWN/CONFLICT`并写原因和解除条件。不得因实现困难、开发时间或历史代码未移植而删除需求。

全集指**测试语义全集**，不要求保持历史函数数量或旧Case数量。

## 6. Feature准入

新Feature必须同时满足：

1. 有适用于目标芯片的明确证据；
2. 语义芯片中立；
3. 有直接可观测终态、独立Oracle或错误/恢复判据；
4. 有独立自动化测试价值；
5. 无需芯片分支才能解释。

否则不得发布新Feature ID。

| 处置 | 条件 |
|---|---|
| `EXISTING_FEATURE` | 与已有Feature语义相同 |
| `COMPATIBLE_EXTENSION` | 语义不变，仅范围/选项/数量变化 |
| `NEW_FEATURE` | 新稳定语义或新Oracle |
| `CAPABILITY_ONLY` | 仅范围、选项、数量、实例、IRQ等机器事实 |
| `NOT_PUBLIC_FEATURE` | 寄存器/SDK细节、重复状态或无独立测试价值 |
| `UNSUPPORTED` | 权威硬件证据明确不存在 |
| `UNKNOWN` | 证据不足 |

### 6.1 人工可审核 Feature 描述

Feature Catalog“报告名称”是 `report_feature` 每一行的唯一文本来源。
`report_feature` 的编号和生成由R120唯一规定；本节只约束单个“报告名称”的硬件语义。

固定要求：

1. 一个名称只表达一个IP硬件功能、模式、配置、状态、事件或数据通路；不把多个Feature压缩成复合长句。
2. 名称使用“`<IP/硬件对象> + <模式/动作/状态>`”的短工程词组，只回答“测哪个硬件功能点”。
3. `M2M/M2P/P2M/P2P、FIFO、LLI、IRQ、TX/RX、RAW/STATUS、Mask/Unmask、Force/Clear`等业界通用专有名词保持原文，不强行翻译为生硬中文。
4. 禁止使用“生命周期、门禁、能力闭合、语义、Runtime、Service、Driver、测试正确性”等软件、流程或抽象词作为硬件Feature。
5. 禁止写测试步骤、PASS/FAIL结论、寄存器物理地址、Python函数、Driver API、Buffer/Handle或芯片专属实现。
6. 如果所谓Feature实际只是软件参数校验、运行时映射、测试资源管理或报告行为，它不应进入IP Feature Catalog。

正反例：

| 推荐报告名称 | 不允许的表达 | 问题 |
|---|---|---|
| `DMA M2M传输` | `DMA存储器到存储器数据路径正确性` | 专有名词被生硬翻译，且写成测试结论 |
| `DMA Channel Enable/Disable` | `DMA Channel基础生命周期` | “生命周期”无法直接对应硬件行为 |
| `DMA Channel FREE状态` | `DMA通道可恢复能力` | 抽象词隐藏了真实硬件状态 |
| `DMA TRANSFER_DONE IRQ` | `DMA中断路径语义正确` | 没有指出具体IRQ事件 |
| `AES ECB/CBC/CTR工作模式` | `AES模式矩阵能力` | 无法说明实际硬件模式 |

Reviewer只阅读“报告名称”时，必须能直接识别所属IP和具体硬件功能点；否则人工审核Gate必须失败。

## 7. Case收敛与P等级

新增Case前必须比较已有Case的：

```text
Precondition / Data Path / Stimulus / Observation / Oracle / Resource / Cleanup
```

- 只有参数、Option、长度或边界值不同，且路径、Oracle、Resource、Cleanup相同时，必须参数化已有Case。
- 测试路径、独立Observer、Oracle、资源等级或恢复语义发生稳定变化时才新增Case。
- 多个Source Item可以`MERGED`到一个Case；一个Source Item可以`SPLIT`为多个Case。
- Case必须使用最短可证明路径；“调用成功”“结果非零”或DUT自证不能替代可证明Feature的强Oracle。

| 等级 | 定义 |
|---|---|
| `P0` | 身份、基础配置、最小可用性、最小数据路径 |
| `P1` | 主要功能、标准配置矩阵、独立IRQ/错误、常规边界 |
| `P2` | 跨IP组合、DMA、复杂路径、异常恢复、高级配测 |
| `P3` | 压力、长稳、性能、特殊环境 |

Case机器字段和Resource Level按R120填写。尚无Registry/真实`test_*`的Case只能写`ET_CASE_PLAN`；不得提前写`ET_CASE_SPEC`。

### 7.1 人工可审核 Case 流程

`method.inputs`、`method.steps`、`method.observations`和`method.pass_criteria`不是给机器占位的摘要，而是后续代码开发和最终Excel人工审核共同使用的稳定测试设计。Reviewer只看`<ip>.md`时，必须能够顺序复原“输入什么、怎么配置、怎么触发、从哪个硬件观测点读到什么、Expected从哪里来、最后怎么判断”。

#### 可扫描摘要格式

`method.inputs`、`method.steps`、`method.observations`和`method.pass_criteria`中的每一条人审内容，必须使用R120冻结的唯一公共行语法：

```text
<类别/阶段/观测/判据摘要>：<具体测试内容>
```

该行语法对所有IP、SPEC和PLAN完全一致，中文全角冒号`：`是机器可判定的结构分隔符；任何IP不得发明私有格式。R120及其Checker负责“是否满足统一语法、摘要/正文是否存在、steps是否6～8条”等确定性结构红线，R140只继续负责摘要和正文是否真正表达清楚测试语义。

摘要用于让Reviewer快速扫描主线，冒号后的正文才是完整Contract。固定要求：

1. 摘要应是能独立表达该条主要作用的短语，通常为4～12个中文字符或一个简短工程短语；长度不是机械门禁，清楚优先于凑字数。
2. `inputs`的摘要回答“这组输入/配置是什么”，例如“参数覆盖矩阵”“输入与密钥”“模式参数与Golden”。
3. `steps`的摘要回答“这一步主要在做什么”，例如“资源与AES初始化”“初始状态确认”“IRQ会话启动”“传输状态轮询”“输出结果校验”。
4. `observations`的摘要回答“从哪个硬件观测点看什么”，例如“运算完成状态”“硬件输出结果”“中断触发状态”“清除后状态”。
5. `pass_criteria`的摘要回答“这一条在判定什么”，例如“覆盖完整性”“数据正确性”“输出长度正确性”“硬件完成状态”。
6. 摘要必须依据当前Case真实语义自由命名；不建立IP私有格式，也不要求所有IP机械复用同一组标题。IRQ、DMA、状态、错误、性能或仪器Case应使用符合各自流程的阶段名称。
7. 禁止使用“输入1、步骤1、观测1、判据1、测试过程、功能验证、数据处理、其他”等不能帮助理解主线的空泛摘要。
8. Reviewer只阅读冒号前的摘要时，应能大致看出该Case的输入构成、执行主线、关键硬件反馈和判定维度；需要精确参数和条件时再阅读冒号后的具体描述。
9. 摘要只是人读导航，不得增加、删除、调换或重新解释测试语义；`steps`的6～8条数量要求仍按真实测试动作计数，不能通过拆标题或合并标题规避。
10. R120机器Gate通过只证明公共行语法和数量结构正确；如果摘要空泛、步骤逻辑不完整、Observation不足以支撑Feature或Pass Criteria缺乏真实Oracle，R140人工审核仍必须失败关闭。

最小示例：

```yaml
method:
  inputs:
    - 参数覆盖矩阵：覆盖 ECB/CBC/CTR × AES-128/AES-256 × Encrypt/Decrypt。
    - 输入与密钥：每组使用16-byte输入及对应长度Key。
  steps:
    - AES基础初始化：Enable AES并配置当前Mode、Key Size和Direction。
    - 运算启动：写入当前输入并启动一次有界PROCESS。
    - 硬件状态读取：读取STATUS.FINISH和RESULT_DOUT[0..3]对应的硬件结果。
    - Golden结果计算：使用相同参数计算独立PC Golden。
    - 结果比较：逐Byte比较硬件输出与Golden并检查完成状态。
    - 结果汇总：参数化Case汇总全部执行实例。
  observations:
    - 运算完成状态：读取STATUS.FINISH，期望FINISH=1；用于证明本次AES运算进入完成终态。
    - 硬件输出结果：读取RESULT_DOUT[0..3]形成Actual Output，期望与独立PC Golden一致；用于证明AES运算结果正确。
  pass_criteria:
    - 覆盖完整性：计划参数必须全部执行完成。
    - 数据正确性：RESULT_DOUT[0..3]形成的Actual必须与独立Golden完全一致。
    - 硬件完成状态：STATUS.FINISH必须为1。
```

示例只说明表达形式和寄存器/字段级观测粒度，不定义AES或其他IP的固定寄存器名；真实Case仍必须满足下述输入、步骤、硬件观测和通过条件规则。

#### 输入与配置

- `method.inputs`通常使用1～3条，每条按“输入类别摘要：具体说明”表达，说明决定Case构造的测试数据、参数组合、关键配置条件和必要的Expected/Golden来源。
- 参数化Case必须让人看出组合如何构造、覆盖哪些维度以及为什么形成这些执行实例。
- 输入描述不得退化成“固定向量、标准配置、典型数据、合法输入”等无法复原测试含义的抽象词；可以不展开全部Hex原始数据，但必须能追溯到稳定向量/参数来源。
- 不写Buffer申请、内部Handle、Python对象、Fixture名字等实现细节，除非该细节本身就是Feature。

#### 测试步骤

每个正式Case的`method.steps`固定写成**6～8条**，每条按“测试阶段摘要：具体动作”表达，并按真实测试执行顺序形成完整逻辑链。它的目标不是机械套八个固定标题，而是让人一眼看懂“代码会怎样一步一步测试”。

步骤必须覆盖当前Case实际需要的以下逻辑：

```text
准备/选择本轮输入
-> 配置DUT关键模式和参数
-> 施加测试数据、事件或外部激励
-> 启动动作并等待明确的完成/状态条件
-> 读取决定结论的硬件输出、状态或Observer结果
-> 获取独立Expected/Golden/规范预期
-> 比较Actual与Expected并检查关键终态
-> 参数化Case必要时汇总覆盖与总判定
```

固定规则：

1. 上述链路是逻辑要求，不要求每条步骤机械对应一个固定标题；可以根据真实Case把相邻动作合理合并或拆分，但总数必须保持6～8条且不能丢失关键因果关系。
2. 配置类Case、状态清除Case、IRQ/Error Case、DMA/Peer/Instrument Case可以使用各自真实流程；没有数学Golden时，应明确规范状态、读回值、独立Observer或其他稳定Oracle是什么，不能为了套模板虚构Golden。
3. 每一步必须描述“做什么以及为什么能进入下一步”，阶段摘要只负责快速定位，不能用摘要替代后面的具体动作；禁止把输入列表原样复制成步骤，也禁止用“执行测试”“验证功能”“完成矩阵”等一句话替代完整流程。
4. 必须写出与Feature直接相关的关键配置和数据方向，例如Mode、Direction、Length、Source/Destination、Mask/Force/Clear、Start/Wait/Readback等稳定语义；允许在观测动作中引用7.1定义的稳定寄存器/字段语义名称，但禁止写物理地址和芯片专属SDK调用。
5. 参数化Case必须说明单个参数实例如何执行，以及全部实例如何形成Case总结果；不得只列参数名而省略执行流程。
6. 该6～8条流程经人工审核后就是后续PC Case实现的逻辑基线。实现Agent不得自行省略、调换、隐藏或新增会改变测试语义的关键步骤；发现实现需要偏离时必须先回到Contract重新评审。

#### 硬件观测与最小充分证明

`method.observations`必须定义能够直接支撑当前Feature结论的**最小充分硬件观测**。目标是让Reviewer知道“从硬件哪里看、正常应该看到什么、为什么这个现象足以支撑PASS”，不是把所有可读寄存器都采集一遍。

固定规则：

1. 每条关键硬件Observation必须同时说明：**观测对象**、**期望现象**和**证明含义**。观测对象必须具体到稳定寄存器/字段语义或明确硬件端点，禁止只写“状态”“Actual”“硬件反馈”“结果值”等无法定位来源的抽象名。
2. 公共`<ip>.md`使用不带物理地址的稳定寄存器/字段语义名称，例如`STATUS.FINISH`、`RESULT_DOUT[0..3]`、`IRQ_STATUS.COMPLETE`、`DMA_CHANNEL_STATUS`。禁止在公共Case中写寄存器地址、基址或芯片专属地址常量。
3. 目标芯片实际寄存器名与公共语义名称不同时，`<CHIP>_<ip>.md`必须记录映射，例如`STATUS.FINISH -> RPT_AES_STS.FINISH`。人工报告允许展示解析后的实际寄存器/字段名称，但默认不需要展示物理地址。
4. Feature声明的强度不得超过Observation实际能够证明的强度。只观测到运算完成后的`BUSY=0`，只能证明“完成后BUSY为0”，不得写成已验证“运行期间BUSY先拉高再拉低”；只有实际采样到对应状态变化时才能发布更强结论。
5. 状态变化本身是Feature时，必须观测决定语义的前后状态。例如W1C清除应看到目标字段清除前有效、执行Clear、清除后无效；只看到最终无效状态不能证明清除语义。
6. 算法/数据路径Feature通常至少需要“硬件完成状态或等价终态 + 硬件输出端点 + 独立Oracle”；IRQ Feature优先观察目标IRQ寄存器/字段或真实ISR锁存事实；DMA Feature优先观察Channel硬件状态和Destination数据。不同Feature按其真实语义选择最少必要观测，不机械套固定清单。
7. `produced_bytes`、`parameter_id`、执行次数、PC Golden、软件比较结果等允许作为协议/软件/Oracle事实支撑报告，但除非能直接证明它们来自具体硬件寄存器或硬件端点，否则禁止把它们描述为“硬件寄存器反馈”。
8. 不得为了让报告显得更充分而无条件增加额外寄存器读取。若当前Feature的最小充分证明需要新的硬件观测动作，必须把它作为真实Contract/Implementation Gap评审后再进入实现阶段。

推荐表达：

```yaml
observations:
  - 运算完成状态：读取STATUS.FINISH，期望FINISH=1；该字段证明本次硬件运算已经进入完成终态。
  - 硬件输出结果：读取RESULT_DOUT[0..3]形成128-bit Actual，期望与独立Golden一致；该输出证明目标数据路径的运算结果正确。
```

状态型Feature示例：

```yaml
observations:
  - 清除前状态：读取STATUS.FINISH，期望Clear前FINISH=1；证明目标状态位已经真实置位。
  - 清除后状态：执行Clear后再次读取STATUS.FINISH，期望FINISH=0；通过1->0变化证明W1C清除行为成立。
```

#### 通过条件

- `method.pass_criteria`通常使用2～5条，每条按“判定维度摘要：精确条件”表达，并必须写成可直接核对的条件。
- 禁止只写“结果正确、符合预期、状态正常、调用成功”。稳定值明确时应写出具体硬件字段或输出端点，例如`STATUS.FINISH=1`、`RESULT_DOUT[0..3]逐Byte等于Golden`；软件派生事实需要参与判定时必须明确其非寄存器来源。
- 参数化Case必须明确完整执行条件，例如`12/12`全部执行并满足单实例判据。
- 每个关键通过条件必须有对应Observation/Measurement/Artifact或独立Oracle来源；没有真实观测就不得声称验证了该条件。
- 判据摘要应区分不同判断维度，使Reviewer先看摘要即可知道Case从哪些方面决定PASS；不得把所有条件都写成“结果校验”。

#### 报告Evidence设计

分析阶段必须同时决定最终人工报告需要看到哪些关键执行事实，用来证明“测试确实按上述方法执行并得到结论”。关键Evidence应直接对应测试步骤、硬件Observation和通过条件。

硬件Evidence面向Reviewer时必须保留可识别的寄存器/字段或硬件端点名称，并展示真实运行值；有明确规范Expected时同时展示Expected或状态变化关系。禁止把`FINISH=true`、`Actual=...`这类没有硬件来源名称的孤立值作为完整硬件反馈说明。

人读报告只保留能够证明结论的少量关键字段，完整原始数据继续保留在Canonical Result/Artifact。`ET_CASE_REPORT`具体Schema由R120负责，运行Evidence身份由R130负责。

## 8. Stable Automation Contract

公共`<ip>.md`的`## 0. Stable IP Contract`必须足以指导后续PC Case、PC Driver、Firmware Service和Common Wrap实现，至少明确：

- 公共数据表示、单位、Enum和Config语义；
- Case需要的稳定直接动作、状态与观测；
- Runtime Service、Capability、Bench、Peer/FPGA/Instrument的事实边界；
- 独立Oracle来源；
- 异步操作需要的Start/Status/Result/Abort语义；
- Timeout和Cleanup所有权；
- 需要新增Wire时的稳定Request/Response语义。

其中，Case需要的稳定动作/状态/Oracle必须足以实现7.1已审核的6～8步测试逻辑和最小充分硬件观测。分析完成后，代码Agent应能直接根据公共Contract实现流程，而不需要再次猜测“应该怎么测、从硬件哪里证明”。

公共Contract禁止芯片地址、基址、IRQn、SDK结构体或固定实例；允许为Case Observation定义不带地址的稳定寄存器/字段语义名称。Chip Driver/Test Driver Extension缺口和目标芯片实际寄存器名映射只写入`<CHIP>_<ip>.md`。

分析完成后，后续开发Agent不得为了重新理解稳定Feature、Case或Automation语义而再次扫描历史测试资料；若仍必须回到原始资料才能决定公共接口或Case语义，分析未完成。Chip Driver实现读取目标SDK不受此限制。

## 9. Deferred、SKIP与Gap

- `DEFERRED`：Feature/Case已分析清楚，但缺安全刺激、独立观测或必要RTL/板级资源；必须写阻塞事实和解除条件。
- `SKIP`：已实现Formal Case在运行时因Capability或台架映射明确不支持而跳过。
- Driver/Service/Wrap/Case未实现属于`IMPLEMENTATION_GAP`，不是Deferred。
- Mapping未闭合属于`MAPPING_GAP`；分析不清属于`UNKNOWN/NEEDS_VERIFICATION`。
- 开发时间不足、Case难写、历史代码未移植均不是Deferred理由。

## 10. 文档输出

公共`test_case_doc/<ip>/<ip>.md`固定章节：

```text
## 0. Stable IP Contract
## 1. Feature Catalog
## 2. Case Catalog
## 3. Machine-readable Case Contract
## 4. Chip Adaptation Summary
## 5. Common Gap / Evolution
```

Section 3只使用R120定义的机器块和统一人审行语法；其中面向人工报告的Feature、输入、步骤、硬件Observation、通过条件和报告Evidence必须满足6.1和7.1，不得用机器占位文本替代人审设计。

目标芯片`<CHIP>_<ip>.md`必须包含：

- Source Coverage：每个登记资料根的`FOUND/NO_MATCH/UNAVAILABLE`；
- Source Item Trace：`Source Item -> Feature/Case/Capability/Gap -> Disposition`；
- Evidence、Conflict和Unknown的可追溯事实；
- 公共硬件Observation到目标芯片实际寄存器/字段名称的映射；
- R100定义的`第五章 Chip -> Public Feature Mapping`和`第六章 Chip -> Public Case Adaptation`。

除R100固定的第五/六章标题外，芯片文档其他章节可按IP复杂度组织。公共文档禁止芯片地址、IRQn、实例名和SDK符号，但允许7.1定义的稳定寄存器/字段语义名称；芯片文档禁止重新定义公共Feature/Case ID或放置`ET_CASE_SPEC/PLAN`。

## 11. 停止读取条件

同时满足以下条件后停止继续扩展资料：

- 每个登记资料根已有`FOUND`或`NO_MATCH`；
- 每个有效Source Item已有明确处置；
- 每个关键Claim已`VERIFIED`或明确为`UNKNOWN/CONFLICT`；
- Feature/Case是否新增已经可以确定；
- 所有Gap均已定位并有解除条件。

“可能还能找到更多资料”不是继续扫描的理由。存在核心资料`UNAVAILABLE`时可以形成Gap，但不得通过完成Gate。

## 12. 完成Gate

分析完成必须满足：

- `ip + chip`明确，Source Map和用户新增资料已纳入分析；
- 所有登记资料根已搜索，无`UNAVAILABLE`核心资料；
- `requirements`全部逐项处置，所有有效Source Item无静默遗漏；
- Hardware/Register/Driver/Test等Claim已核对，Conflict/Unknown均有解除条件；
- 新Feature全部通过准入条件，并具有6.1要求的具体人审描述；
- 当前Case集合覆盖全部有效稳定测试语义，并完成复用/参数化/合并/拆分判断；
- 每个Case有明确Oracle、Resource、Evidence、Cleanup和合法P等级；
- 每个Case的输入、6～8步测试逻辑、最小充分硬件Observation、通过条件和关键报告Evidence已经完整定义，Reviewer无需读实现代码即可复原测试方法与硬件证明链；
- 每个关键硬件Observation都有明确寄存器/字段或硬件端点名称、Expected和证明含义，且Feature声明强度不超过Observation可证明范围；
- 测试步骤能够直接指导后续实现，且不依赖抽象标签、隐藏Helper或未声明的实现假设才能解释；
- 未实现Case均为合法`ET_CASE_PLAN`；
- Stable Automation Contract达到Implementation Ready；
- 公共/芯片文档和R100 Mapping完整；
- 未执行的软件、Keil、FPGA或HIL不得写成PASS。

人工审核未通过6.1/7.1时，即使Schema有效、Feature/Case ID完整，也不得宣称IP分析完成或Implementation Ready。

```powershell
python tools/quality/check_public_ip_contracts.py
python tools/quality/validate_case_plans.py test_case_doc/<ip>/<ip>.md
python tools/quality/validate_case_method_contract.py test_case_doc/<ip>/<ip>.md
python tools/quality/validate_chip_ip_docs.py
```

`validate_case_docs.py`和`check_case_spec_implementation.py`只在Case实现阶段执行。
