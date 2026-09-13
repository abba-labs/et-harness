---
schema: et.rule-document.v1
number: R210
domain: pc
lifecycle: active
owners: [pc_case_responsibility, public_ip_implementation_sync]
rule_ids: [ET-RULE-PC-CASE, ET-RULE-IP-IMPLEMENTATION-SYNC]
---

# R210 Formal Case规则

## 1. 定位

本文只定义Formal Case的目录、拆分、注释、执行、断言、Evidence和公共IP契约同步。Case是测试流程和最终PASS/FAIL的唯一所有者，也必须是验证工程师可从上到下阅读的“可执行测试说明书”。

公共`test_case_doc/<ip>/<ip>.md`中已经通过人工审核的Feature、输入、6～8步测试流程、通过条件和关键Evidence，是Formal Case实现的稳定逻辑基线。Case代码可以使用更紧凑的Python表达，但不得改变、隐藏或重新解释这条测试逻辑。

代码阅读顺序应尽量等于真实硬件顺序：

```text
准备/选择输入
-> 配置
-> 激励
-> 启动/等待
-> 读取/观测
-> Expected/Golden
-> 比较/断言
-> 记录/清理
```

这不是要求代码机械拆成八个函数或八个注释块；实际Case应按R140已审核流程自然展开，让Reviewer能够把文档步骤与代码主体一一对应。

## 2. 目录与注册

```text
pc/et_test_platform/test_cases/<ip>/
├── conftest.py
├── <ip>_helpers.py          # 可选，只放纯数据辅助
├── test_<ip>_p0.py
├── test_<ip>_p1.py
├── test_<ip>_p2.py
└── test_<ip>_p3.py
```

- P0：最小可用和身份；P1：主要功能；P2：组合、异常和恢复；P3：压力、性能或当前环境不能安全执行的能力。
- 每个公开Case必须有稳定`case_id`并进入唯一Case Registry；不运行时从运行注册表移除，不删除契约定义。
- 一个P级文件优先按Feature分隔符分区；超过机器规模门禁时才按同一P级的功能域拆文件。

## 3. Case拆分

基础配置、启动、最小数据路径和终态可以组成一个“基本功能Case”。下列Feature必须独立：

- 中断源、Mask、Force、Clear与恢复；
- 不同错误路径；
- DMA、外设握手或外部仪器证据；
- 边界值、低功耗、复位恢复、性能和压力；
- 失败后能否继续工作的恢复语义。

相同流程仅参数不同使用`pytest.mark.parametrize`，不得复制Case。多实例IP默认使用Capability提供的代表实例；只有实例差异、边界或并发本身是Feature时才展开矩阵。

## 4. 函数前注释

每个`test_*`函数前必须使用中文`#`，固定三段；函数内不得用Docstring替代：

```python
# 测试 Feature：
# UART内部回环的最小收发路径。
#
# 测试方法：
# 1. 初始化目标实例并开启内部回环。
# 2. 发送确定性数据，在统一Deadline内读取结果。
#
# 通过条件：
# 1. 实际数据与期望数据逐字节一致。
# 2. 完成状态有效且没有错误事件。
def test_uart_p0_003_internal_loopback_basic(uart_dut_handle) -> None:
    ...
```

函数前注释是代码阅读摘要，不是Excel测试说明的第二份全文副本。它可以比`<ip>.md`中的6～8步更简洁，但必须保持同一Feature、关键配置/激励、主要Observation和PASS语义；不得为了短而把代码实际执行的关键测试环节描述成“执行测试”“验证功能”等抽象句。

函数内按“准备、配置、激励/发送/接收、启动/等待、观测、Expected/Golden、断言、记录、清理”的真实需要分段。每个独立配置组、非直观参数、循环范围、等待条件和清理动作前必须有一行解释目的的`#`注释；不同阶段之间留一个空行。

对于没有数学Golden的状态、IRQ、错误、恢复或仪器Case，代码应按`<ip>.md`声明的规范预期、读回值、Observer或其他Oracle展开，不得为了匹配模板人为制造Golden变量。

## 5. Case函数允许和禁止的内容

允许：

- 调用本IP、支撑IP、配测设备和仪器Driver；
- 显式编排配置、触发、观测和清理顺序；
- 使用Capability门禁和稳定参数；
- 对实际观测做强断言并记录Evidence。

禁止：

- 直接构造TargetClient、编解码Wire、发送裸Command；
- 直接访问寄存器、端口、芯片名、物理实例或板级接线；
- 在Helper、Fixture或Firmware中隐藏完整测试流程和最终断言；
- 用弱断言、扩大SKIP、延长超时或吞异常伪造覆盖；
- 复制Driver轮询、协议恢复或设备I/O实现。

如果R140已审核的某一步在Case主体中完全不可见，且Reviewer必须进入Helper/Fixture才能知道该配置、激励、等待、观测或比较实际上发生在哪里，则该实现不符合本规则。

## 6. 线性表达规则

新建Case和可读性重写过的Case必须优先使用：

```text
普通变量 + 直接Driver API + if/for + try/finally + assert
```

固定限制：

1. 设备生命周期不使用`with`、`ExitStack`、`xxx_mode()`或`xxx_on_exit()`作为新的主流程表达。`pytest.raises(...)`只表达预期异常，不属于设备生命周期禁止项。
2. 多步清理需要保证全部尝试并聚合失败时，允许使用一个最外层`case_cleanup_scope()`；它只能包围线性Case主体，不得隐藏配置、激励、观测或断言。
3. 为`case_cleanup_scope()`提供的`cleanup_actions()`只能按资源实际获得状态返回直接清理动作，不得执行Feature流程、断言、等待或构造通用Cleanup状态机。
4. 主流程嵌套原则上不超过2层；不为少写几行把完整测试流程抽进Helper。
5. 允许保留能说明边界、方向或激励差异的有意义重复；“减少行数”不是抽象理由。
6. 已存在的复杂生命周期写法是待迁移存量，不是新开发样板；只在对应Case按行为保持规则完成迁移后删除。
7. 文档中的一个测试步骤可以对应多行代码，也可以由同一线性阶段中的几个直接动作共同完成；禁止为了“看起来一一对应”把Case机械拆成无意义的小函数。
8. 反过来，一个关键配置/激励/观测若足以改变测试语义，就必须在`<ip>.md`的6～8步流程中有对应含义，不能只存在于代码里成为隐藏测试逻辑。

## 7. Helper、Fixture与Cleanup

- Helper只做确定性数据生成、纯转换和无I/O结果比较。
- Fixture只解析Capability/Bench、构造Driver并管理基础连接；不得替Case完成IP配置、启动、激励、观测或断言。第一次Feature Mutation必须在Case中可见。
- Support不得变成第二个Driver；不得把`configure/start/wait/read/compare/cleanup`串成“一键Case”。
- 单一且不会阻断其他恢复动作的清理默认使用显式`try/finally`；多步清理使用一个`case_cleanup_scope()`聚合，但动作和资源所有权必须在Case中可见。
- Cleanup失败不能覆盖Primary Error，也不能被忽略。

可读性不得降低清理可靠性。如果某个存量Case的多步清理必须依赖现有聚合机制，直接改为普通`finally`会导致“前一步失败后后续清理不执行”或丢失Primary Error，则本次不得强行迁移。必须先确认已有Driver直接动作能以等价、有界、全部尝试的方式恢复状态。

### 7.1 Case前置隔离基线

除纯只读能力/身份查询外，每个Formal Case必须在第一次Feature配置前显式建立独立基线：

```text
复位参与本Case的辅助总线主设备或支撑IP
-> 复位被测IP及参与对测的Peer IP
-> 复位Firmware Resource Pool
-> 开始本Case配置、激励和观测
```

固定规则：

1. 复位动作必须直接出现在Case主体，并以`# 隔离：`说明作用域；Fixture、Support和Helper不得隐藏该顺序。
2. 多IP Case只复位本次实际参与的IP。DMA等仍可能主动访问Resource的总线主设备先复位，目标IP和Peer随后复位，Resource Pool最后复位。
3. UART对测Case只复位测试使用的DUT/Peer实例，禁止复位PC控制UART或其他无关实例。
4. Resource Pool使用整池`reset()`建立空基线，不逐个猜测、恢复或复用前一Case的Handle。
5. 纯只读能力/身份Case允许不复位，但必须以`# 只读 Case：`明确说明没有Feature配置和前置复位。
6. 复位、恢复、持久状态本身是Feature的Case，仍先建立一次统一基线；测试步骤中的目标复位属于Feature刺激，不能被前置基线替代。
7. 缺少当前芯片的稳定CRG复位映射属于内部集成缺口，必须失败关闭；不得改用寄存器直写、隐式Fixture动作或`SKIP`绕过。
8. 前置隔离不替代Case退出清理。外部仪器、全局Route、调试会话或可能影响安全恢复的已获得资源，仍按本节既有Cleanup规则处理。

### 7.2 中断Case的状态所有权

中断、FIFO、错误和恢复Case在实现前必须明确以下五项；任一项无法回答时，不得进入HIL：

```text
Trigger Source   = 什么硬件条件产生目标中断
Clear Owner      = 哪一层通过什么稳定动作清除目标状态
Data Drain Owner = 哪一层排空会持续维持中断的数据或FIFO
Exit Condition   = PC等待什么有界状态结束
Recovery Path    = 超时或断言失败后如何恢复到下一Case可用状态
```

固定规则：

1. Case负责按已审核顺序配置、触发、等待、观测和最终断言；Driver负责单IP有界动作；Firmware ISR只执行必要的硬件维护、锁存和计数，不承担最终测试结论。
2. 清除中断控制位不等于清除中断源。FIFO非空、状态未读、W1C未清或错误条件仍存在时，Case必须通过稳定Driver动作消除真实来源。
3. 负向阈值、Mask或“预期不触发”场景也必须处理已经写入的数据。若保留数据会触发其他中断或阻止CPU响应命令，必须在同一execution内建立Capture/Drain路径。
4. 等待必须使用统一有界deadline，并保留最后硬件状态；不得用固定Sleep代替事件完成条件，也不得通过延长超时掩盖中断风暴。
5. 决定性Observation必须在Cleanup改变现场前记录。Cleanup完成后还必须证明目标中断、FIFO和会话状态不会污染下一Case。

中断Case的公共文档按R140写出上述语义，芯片IRQ号、Handler名和寄存器映射仍留在芯片适配文档，
不得写入公共Case。

### 7.3 手动诊断与Formal Case责任边界

手动测试只证明最短`Chip Driver -> Hardware`路径中的刺激和硬件现象。它不能证明PC编解码、Service状态、Resource Handle、Wrap调用或Formal Case断言正确。

同一Feature出现“手动PASS、Formal FAIL”时，必须按以下顺序定位：

```text
Case输入与调用顺序
-> Driver请求编码和响应解码
-> Service命令前置状态与Session
-> Resource Handle/Range及IRQ绑定
-> Wrap参数转换和Chip Driver调用
-> 硬件Observation返回
```

每一步只核对与手动PASS路径的输入、动作和Observation是否等价。找到第一个差异后只修对应责任层；禁止同时改Case、Driver、Service和Wrap，禁止弱化Formal断言来迁就手动结果。只有完整Formal链路重新执行并满足R140判据后，才能记录Formal PASS。

## 8. 断言与Evidence

1. 断言必须直接证明文档声明的Feature，至少覆盖输出和关键终态。
2. PASS和FAIL路径记录同一组关键Observation；报告不得只在失败时有硬件事实。
3. Case只记录真实消费的数据，不制造推导值冒充硬件读数。
4. Observer、DUT、Peer和Instrument证据必须保留来源身份。
5. 原始附件写入Canonical Artifact；人读报告只按R120模板提取有限字段。
6. R140中已经批准进入人工报告的关键Evidence，如果Case实际已经读取或计算该事实，必须在决定性断言前记录，使PASS和FAIL都能从Canonical Result/Artifact中解析同一事实。
7. 测试方法、PASS条件和报告备注必须形成证明闭环：方法声明“读取/比较”的关键事实必须有Evidence；报告展示的关键值必须能追溯到方法步骤和真实运行结果。
8. 软件Oracle、比较结果和配置事实不得标记成DUT硬件Observation；真正的DUT/Peer/Instrument状态必须保留真实source。
9. R140声明的硬件Observation必须由当前Case通过Driver/Service的稳定语义接口真实取得；Case仍禁止直接读写寄存器。Evidence必须保留能够识别该硬件来源的稳定寄存器/字段或硬件端点名称，例如`STATUS.FINISH`、`RESULT_DOUT[0..3]`、`IRQ_STATUS.COMPLETE`，不得只留下`finish=true`或`actual=...`而丢失来源语义。
10. Driver返回的typed status/result只有在其字段可以明确映射到目标硬件寄存器/字段或硬件端点时，才允许作为对应DUT硬件Observation。若只是Firmware/协议派生值，必须按软件/协议事实记录，不得标记成寄存器反馈。
11. `produced_bytes`、`parameter_id`、执行次数、PC Golden和软件比较布尔值默认不是硬件寄存器Observation；它们允许参与PASS判定和报告，但必须与真实硬件Observation分开表达。
12. Feature需要状态变化证明时，代码必须取得R140声明的关键前后状态。例如文档要求证明W1C的`1 -> 0`，实现必须实际采样Clear前和Clear后目标字段；如果当前代码只有最终状态，应暴露为Contract/Implementation Gap，禁止用文字补足。
13. Feature声明强度不得超过运行Evidence的证明范围。只记录完成后`BUSY=0`时，Case和报告都不得声称已验证运行期间`BUSY=1`。
14. 人工报告展示硬件证据时应使用寄存器/字段或硬件端点名称和真实运行值；默认不需要物理地址。目标芯片实际寄存器名由芯片映射解析，Case代码不得硬编码芯片地址。
15. **一条 `record_observation()` 只绑定一个真实设备来源端点。** 同一次判断若同时涉及 `RESULT_DOUT[0..3]`、`STATUS.FINISH`、`IRQ_RAW/STATUS`、ISR latch 或其他独立硬件事实，必须分别记录；禁止把多个值拼成字符串/字典后挂在一个 endpoint 上，再让报告误以为这些事实来自同一寄存器/Field。
16. **寄存器事实与Service事实分开。** IRQ Case 中 `IRQ_RAW.<Source>`、`IRQ_STATUS.<Source>`、Service `latched` 和 `event_count` 不得互相冒充；`event_count`、delta和其他软件/Service计数默认使用 `record_property()`，真实寄存器/硬件端点值使用 `record_observation()`。只有明确硬件端点直接提供计数时，才允许作为硬件Observation。

### 8.1 Evidence生命周期与最终闭合

Formal Case的Evidence必须满足**单调累积、不可丢失、最终可解析**。`assert`通过只说明判断执行过，不代表报告证据已经闭合。

固定规则：

1. **关键Evidence不得丢失。** 某个事实一旦用于或将用于`pass_criteria`、决定性`assert`、`failure_observations`或`ET_CASE_REPORT`，必须在决定性断言前记录，并在本次Case execution结束时仍可从Canonical Result或已绑定Artifact解析。后续记录只能增加证明事实，禁止让已经形成的关键Evidence消失。
2. **关键事实与大附件分工明确。** 少量、决定PASS/FAIL的配置、Expected、硬件状态、寄存器/字段读值和Actual优先使用`record_property()`或`record_observation()`进入Canonical Result；大量向量、长序列、完整快照或调试原始数据才放Artifact。Artifact不得被当成增量日志器。
3. **同一路径只发布一次Snapshot。** 同一个Case execution内，同一Artifact路径默认只能由Case发布一次。`write_json_result()`及其IP本地Snapshot Helper均按R130的完整Snapshot语义处理，禁止通过重复写同一路径实现“追加字段”。需要单个最终附件时，应先在内存中累计完整dict/list，再一次性发布。
4. **多阶段现场使用不同路径。** 如果确实需要独立保存多个阶段Snapshot，必须使用语义明确且不同的路径，例如`before_clear.json`和`after_clear.json`，并分别绑定到当前Canonical Result；禁止用同一路径覆盖前一阶段现场。
5. **Case结束必须完成Evidence Closure。** 对每个执行实例，Reviewer必须能够沿`Pass Criteria -> Evidence Key -> Canonical Result/Artifact -> ET_CASE_REPORT`找到最终仍存在的事实。测试动作和断言正确、但最终证据无法解析时，属于真实Contract/Implementation Gap，不得宣称Formal Case已经闭环。

错误示例：

```python
record_result(artifact_dir, "aes_p1_003", data_length_readback=readback)
assert readback == configured
...
record_result(artifact_dir, "aes_p1_003", finish=status.finish)
# 同一路径第二次Snapshot会替换第一次内容，readback不再有保存保证。
```

正确示例：

```python
record_observation(
    record_property,
    key="data_length_readback",
    value=readback,
    source="dut",
    endpoint="DATA_SIZE[1:0]",
)
assert readback == configured

artifact = {
    "data_length_readback": readback,
    "finish": status.finish,
}
write_json_result(final_path, artifact)  # 当前execution只发布一次最终Snapshot。
```

参数化Case按单个`parameter_id` execution独立满足上述规则；不同execution可以复用同一逻辑文件名，因为Canonical Result会按 Formal slot 目录`cases/<CASE_ID>/<SLOT>/`隔离同名附件。

同一稳定Case的每个参数execution还必须独立产生R120声明的公共报告Evidence。分支专属事实可以额外记录，
但不得用`None`、空结构或其他参数分支的结果补足本分支缺失的必要事实。

最小实现示例：

```python
status = aes.status_get()
record_observation(
    record_property,
    key="finish",
    value=status.finish,
    source="dut",
    endpoint="STATUS.FINISH",
)
assert status.finish is True
```

示例中的`STATUS.FINISH`是公共寄存器/字段语义名称，不是芯片地址；实际芯片寄存器名由芯片适配映射提供。代码仍通过Driver读取，不允许为了Evidence直接访问寄存器。

仅为了让报告更有“说服力”而新增未被测试逻辑使用的硬件访问、额外寄存器读取或私有探针，不属于Evidence补录，必须先回到Contract评审，禁止在Case可读性整改中顺手加入。

## 9. PASS、FAIL、SKIP与DEFERRED

- `PASS`：全部强断言通过。
- `FAIL`：环境支持执行但结果不符合预期。
- `SKIP`：只用于缺少外部物理接线、外部仪器或不可替代的外部Bench拓扑，导致Case无法安全产生刺激或独立观测；必须写明缺失条件和解除条件。
- `NOT_EXECUTED`：Case尚未运行。Driver/Service/Wrap、内部路由、Execution Mapping或Runtime能力发布缺口必须归入此状态，并在Case被选中时失败关闭，禁止改成SKIP。
- `DEFERRED`：仅用于尚未纳入当前执行计划的规划状态，不能替代已注册Case的FAIL、SKIP或NOT_EXECUTED。

SVD、设计或公共契约已经声明的Feature，即使当前FPGA/芯片行为不符合预期，也必须发布能力并执行真实断言；不得通过Capability裁剪、Runtime Feature屏蔽或`pytest.skip()`把硬件FAIL隐藏成“不支持”。

**运行配置缺失不得判为SKIP。** Case依赖的工具、仪器或调试器配置未从运行环境传入时，属内部集成缺口，夹具必须失败关闭并给出缺失的配置项；只有外部设备物理不可替代时才能SKIP。判据是“设备是否具备”，不是“配置是否传入”——把后者写成SKIP会掩盖内部缺陷，使Case被静默跳过。同理，Case产生的原始附件必须以`_result`后缀登记，绑定到当前execution；未绑定的附件会使现场无法封存。

没有分析清楚、历史代码未移植或Case难写都不是DEFERRED理由。需求与历史资料是否进入当前Case集合必须遵循R140的Source Item全量处置；有效稳定测试语义必须被当前Case覆盖，允许通过合并、拆分或更强Case替代，禁止因实现困难静默丢失。

## 10. 可读性重写的行为保持

仅做Case/Driver可读性整理时，以下内容在Before/After之间必须完全一致：

```text
Case ID、函数名、pytest marker、Fixture输入
测试参数、Driver Public API语义、Target Command和Payload
Deadline/超时、激励与观测顺序、断言和PASS条件
Evidence来源、Observation字段、Result/Artifact Schema和Cleanup终态
```

该类任务只允许改变Python表达方式、注释和局部排列。任何Public API、Protocol、Capability、Fixture架构、Target端或覆盖集合变化都必须拆成独立任务，重新编译Task Context并获得对应写入权限。

如果本次只是把已有真实事实补录为人工报告Evidence，必须证明该事实原本已经在Case执行路径中取得且不改变设备交互；否则不属于纯可读性/Evidence补录，应停止并重新评审任务边界。

## 11. Contract与实现同步

每个Formal Case必须形成唯一双向绑定：

```text
test_case_doc/<ip>/<ip>.md ET_CASE_SPEC / PLAN / REPORT
<-> 已审核Feature、输入、6～8步测试流程、硬件Observation和PASS条件
<-> Case Registry case_id
<-> 唯一真实 test_* 函数
<-> 真实Evidence字段及硬件来源语义
<-> 人工报告关键Evidence
```

新增、删除、改义或拆分Case时必须在同一变更中更新文档、Registry和实现。Case ID发布后不得静默改义；兼容迁移必须记录旧ID到新ID。

仅做人工表达优化且不改变测试语义时，可以让`<ip>.md`写得比函数前注释更详细，但代码主体必须仍能对应完整测试链。若文档优化后暴露出代码缺步骤、步骤顺序不同、Oracle不同、硬件观测点不同或关键Evidence根本没有产生，应把它作为真实Contract/Implementation Gap处理，禁止只改文字掩盖差异。

## 12. Review与验证

Reviewer必须能在5分钟内完成两层核对：

1. 只看公共`<ip>.md`，直接回答“Feature测什么、输入/配置是什么、6～8步如何执行、从哪个硬件寄存器/字段或端点观察什么、Expected/Oracle来自哪里、怎样判PASS、报告准备展示哪些关键Evidence”。
2. 打开真实Case主体后，能够沿代码从上到下把这些步骤映射到实际配置、激励、等待、硬件观测、断言和Evidence记录，并确认关键Evidence在最终Canonical Result/Artifact中没有被后续Snapshot覆盖；不得先追踪多层Helper、Fixture或Context Manager才能理解主流程。

IRQ/FIFO/Error Case还必须完成第三层核对：Reviewer无需猜测即可指出Trigger Source、Clear Owner、
Data Drain Owner、Exit Condition和Recovery Path，并确认负向场景不会把持续中断或残留数据带入下一Case。

`<ip>.md`的人审流程负责“让人知道应该怎么测、从硬件哪里证明”，Case主体负责“让人确认代码确实这样测、这样取证并最终保留下来”。两者任意一侧需要依赖猜测、抽象标签或隐藏实现才能解释时，都不符合本规则。

新Case和存量Case可读性改造可参考已审核样板：

```text
pc/et_test_platform/test_cases/uart/test_uart_p0.py
```

该文件只示范函数前中文三段注释、阶段注释、直接Driver调用、线性测试流程和最外层可靠清理边界；本规则正文仍是唯一权威，UART的Feature、参数和资源组合不得复制到其他IP。

```powershell
python tools/quality/validate_case_docs.py test_case_doc/<ip>/<ip>.md
python tools/quality/check_case_spec_implementation.py
python tools/quality/check_case_orchestration_rules.py
python -m pytest --collect-only -q pc/et_test_platform/test_cases/<ip>
```
