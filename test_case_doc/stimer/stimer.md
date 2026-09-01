# STIMER Public Test Contract

> 本文件定义 STIMER 的跨芯片稳定 Feature、Formal Case 设计、Oracle、最小充分 Evidence 与未来报告语义；已有代码链的 Case 使用 SPEC，只有尚未实现代码链的 Case 才使用 PLAN。
> 当前已实现并注册 16 个轻量 Formal Case；P2-002 已实现为真实的 Driver/Service/Bench 脉冲链路，运行时仅在目标 Capability 和 `stimer_emergency_input` Bench 绑定存在时执行。P3-001 仍受逻辑 Observer Bench 绑定门禁。
> 芯片实例、物理地址、实际寄存器名称、IRQn、SDK 类型和目标芯片已知缺口只进入同目录 `<CHIP>_stimer.md`。
> Formal Case 前置隔离统一遵循 `R210`：第一次 Feature 配置前由 Case 显式复位参与 IP；DMA Case 先复位 DMA，再复位 STIMER，最后复位 Resource Pool。本文件各 Case 不重复展开该公共前置条件。

## 0. Stable Automation Contract

### 0.1 稳定数据与动作语义

公共自动化层按以下逻辑语义设计，未来 PC Driver / Firmware Service / Wrap 必须实现等价能力，但不得把芯片 SDK 符号直接暴露为公共 Contract：

| 稳定语义 | 公共含义 | 约束 |
|---|---|---|
| `prescaler_divider` | STIMER 输入时钟的逻辑分频系数 | 合法范围由目标芯片 Capability 给出；公共 Case 不硬编码某芯片最大值 |
| `period_ticks` | 一个计数周期的逻辑 Tick 数/终止周期语义 | 目标芯片负责转换为自身寄存器编码；公共层不依赖 raw `period-1` 等写法 |
| `run_mode` | `ONE_SHOT` / `FREE_RUN` | One-Shot 到期后停止在终态；Free-Run 到期后重新进入下一周期 |
| `load_mode` | `IMMEDIATE` / `SHADOW` | Immediate 由软件加载动作决定生效时刻；Shadow 在周期边界生效，目标芯片差异由 Chip Adaptation 说明 |
| `compare_channel` | 逻辑比较通道编号 | 有效通道数由 Capability 给出 |
| `compare_ticks` | 比较门限的逻辑 Tick 值 | 主路径要求位于当前有效周期内；非法/晚加载诊断单独作为诊断语义 |
| `event_pulse_width_cycles` | Overflow/Compare 事件对外脉宽的逻辑时钟周期数 | 由目标芯片编码；必须由连续数字 Observer 测量后才可宣称脉宽正确 |
| `irq_source` | `OVERFLOW` / `COMPARE0..N` | Source 集合由 Capability 给出 |
| `dma_request_source` | Overflow 或某 Compare Event | 选择动作本身不是 DMA 成功证据；必须由真实 DMA Channel 与 Destination 闭环 |
| `debug_halt_policy` | CPU Halt 时 STIMER `PAUSE` / `RUN_FREE` | 需要真实 Debugger Halt Observer |
| `diagnostic_snapshot` | 一次原子读取 STIMER 历史/告警状态 | 目标芯片若为 read-to-clear，必须一次读取后再拆字段，禁止逐字段读取丢现场 |

未来公共 Driver / Service 至少应提供等价稳定动作：

```text
CAPABILITIES_GET
CONFIGURE(prescaler_divider, period_ticks, run_mode, load_mode)
START / STOP / PAUSE / RESUME / CLEAR_COUNT
COUNT_GET_LIVE / COUNT_LATCH
PERIOD_UPDATE(period_ticks, load_mode)
COMPARE_SET(compare_channel, compare_ticks)
EVENT_PULSE_WIDTH_SET(source, event_pulse_width_cycles)
IRQ_ENABLE / IRQ_DISABLE / IRQ_MASK / IRQ_UNMASK / IRQ_FORCE / IRQ_CLEAR / IRQ_SNAPSHOT
DMA_REQUEST_SELECT(dma_request_source)
DIAGNOSTIC_SNAPSHOT
DEBUG_HALT_POLICY_SET(debug_halt_policy)
```

这些名称只描述稳定动作，不冻结 Wire Command ID；具体实现状态以本文件的Case Contract和Gap Registry为准。
公共 `StimerDriver` 构造必须显式接收 Profile/Fixture 解析后的逻辑 `instance_id`，禁止默认选择实例0。

### 0.2 稳定 Observation Endpoint

Canonical Observation 坚持“一条 Observation = 一个来源端点 + 一个 raw value”。以下名称是公共稳定语义；实际寄存器/Field 由 `<CHIP>_stimer.md` 映射：

| 公共稳定 Endpoint | 事实类型 | 证明用途 |
|---|---|---|
| `COUNT.LIVE` | DUT 当前计数值 | 证明计数推进、暂停、恢复、清零、One-Shot/Free-Run 终态 |
| `COUNT.LATCHED` | DUT 软件锁存快照 | 证明锁存动作取得单次稳定快照 |
| `IRQ_RAW.OVERFLOW` | DUT Overflow 原始 pending | 证明 Overflow 事件真实发生，不受 Mask 解释混淆 |
| `IRQ_RAW.COMPARE[n]` | DUT Compare 原始 pending | 证明指定比较通道事件真实发生 |
| `IRQ_STATUS.OVERFLOW` | DUT Mask 后 Overflow 状态 | 证明 Enable/Mask 后的有效 IRQ 状态 |
| `IRQ_STATUS.COMPARE[n]` | DUT Mask 后 Compare 状态 | 证明指定 Source 的有效 IRQ 状态 |
| `IRQ_DELIVERY.LATCHED_SOURCE` | DUT ISR/Service 独立锁存 | 证明有效 IRQ 真正进入软件中断投递链；不得冒充 IRQ 寄存器 |
| `STATUS_HISTORY.OVERFLOW` | DUT Overflow 历史状态 | 证明历史状态产生；若目标芯片 read-to-clear，读取本身会消费现场 |
| `STATUS_DIAG.COMPARE_REPEAT[n]` | DUT Compare 重复事件诊断 | 证明脉宽扩展窗口内重复事件被检测/忽略 |
| `EVENT_PULSE.OVERFLOW` | FPGA/Instrument 数字波形 | 测量 Overflow 对外事件宽度 |
| `EVENT_PULSE.COMPARE[n]` | FPGA/Instrument 数字波形 | 测量 Compare 对外事件宽度 |
| `DMA_CHANNEL_STATUS` | Peer DMA 硬件状态 | 证明 STIMER 事件真正驱动既有 DMA Channel |
| `DMA_DESTINATION_WORD` | Peer DMA 目的端数据 | 证明真实搬运发生，不以“DMA配置成功”替代 |
| `EMERGENCY_CAPTURE.COUNT` | DUT 系统级紧急捕获寄存器 | 证明紧急触发沿锁存 STIMER 计数 |
| `REFERENCE.CYCLE_COUNT` | 独立目标侧/外部参考计数 | 作为预分频比例、周期精度或长期运行的独立时间 Oracle |

### 0.3 Evidence 分层

```text
Measurement / Oracle:
- prescaler_divider / period_ticks / compare_ticks
- 参数节点、Expected Ratio、Expected Source
- IRQ event_count / delta
- 软件派生的 count_delta / ratio
- 参考窗口参数

Hardware Observation:
- COUNT.LIVE / COUNT.LATCHED
- IRQ_RAW.* / IRQ_STATUS.*
- STATUS_HISTORY.* / STATUS_DIAG.*
- EVENT_PULSE.*
- DMA_CHANNEL_STATUS / DMA_DESTINATION_WORD
- EMERGENCY_CAPTURE.COUNT
- REFERENCE.CYCLE_COUNT
```

配置输入值只有在真实读回对应硬件端点后才能升级为 Hardware Observation。最终 Excel/报告未来只选择 1～4 个决定性字段，完整调试现场保留在 Canonical Result / bound Artifact。

## 1. Feature Catalog

| Feature ID | 稳定 Feature | 公共测试语义 | 主要 Case |
|---|---|---|---|
| STIMER_F_001 | STIMER 计数与Start/Stop | Enable/Start 后实时计数应推进；Stop 后在有界观察窗保持不变 | STIMER_P0_001, STIMER_P3_001 |
| STIMER_F_002 | STIMER 可编程预分频 | 不同 `prescaler_divider` 应按逻辑分频关系改变计数速率；精确边界由 Capability 决定 | STIMER_P1_001, STIMER_P3_001 |
| STIMER_F_003 | STIMER 可编程周期与溢出 | 配置 `period_ticks` 后应在周期终点产生 Overflow，并进入模式定义的终态 | STIMER_P0_002, STIMER_P1_002, STIMER_P1_004, STIMER_P3_001 |
| STIMER_F_004 | STIMER One-Shot/Free-Run模式 | One-Shot 只产生一次周期终止并停在终态；Free-Run 可连续产生后续周期 | STIMER_P1_002, STIMER_P3_001 |
| STIMER_F_005 | STIMER 软件清零 | 软件清零后实时计数应重新从零附近开始，且模块生命周期按规范继续 | STIMER_P1_003 |
| STIMER_F_006 | STIMER Pause/Resume | Pause 后计数冻结，Resume 后从暂停值继续推进且不发生无因重置 | STIMER_P1_003 |
| STIMER_F_007 | STIMER Immediate/Shadow周期加载 | Immediate 与 Shadow 的新周期生效时刻不同；必须通过下一次终点/计数行为证明，而不是只看配置输入 | STIMER_P1_004 |
| STIMER_F_008 | STIMER Live/Latch计数 | 实时计数连续变化；Latch 后锁存计数是该动作时刻的稳定快照，重复 Latch 应产生新快照 | STIMER_P1_005 |
| STIMER_F_009 | STIMER Compare门限与事件 | 各比较通道在目标门限前不应提前触发，到达门限后对应Compare原始事件状态应有效且来源隔离 | STIMER_P1_006 |
| STIMER_F_010 | STIMER Overflow/Compare脉宽扩展 | 配置不同逻辑脉宽后，由 FPGA/Instrument 连续数字 Observer 测得的事件脉宽应匹配 Expected | STIMER_P1_008 |
| STIMER_F_011 | STIMER IRQ使能/屏蔽/清除与RAW/STATUS | Raw/Status 必须保持来源语义；Mask 应抑制有效状态但不伪造 Raw；Clear 后目标 Source 消失且不误清其他 Source | STIMER_P1_007 |
| STIMER_F_012 | STIMER IRQ软件强制 | Force 指定 Source 后应产生对应 Raw/Status；Mask、Delivery、Clear 语义与自然事件一致 | STIMER_P1_007 |
| STIMER_F_013 | STIMER DMA请求握手 | Overflow/Compare 可作为 DMA Request Source；只有 Peer DMA 完成且 Destination 数据正确才算闭合 | STIMER_P2_001 |
| STIMER_F_014 | STIMER 溢出历史状态 | Overflow事件后历史位按目标硬件语义置位，read-to-clear端点必须使用单次原子Snapshot保存首次现场 | STIMER_P1_009 |
| STIMER_F_015 | STIMER Debug Halt行为 | Debugger 真正 Halt CPU 时，PAUSE 策略计数冻结，RUN_FREE 策略计数继续 | STIMER_P2_003 |
| STIMER_F_016 | STIMER 紧急计数捕获 | 安全紧急触发沿应把当前 STIMER 计数锁存到系统级紧急捕获端点，并有明确清理/复位语义 | STIMER_P2_002 |
| STIMER_F_017 | STIMER IRQ真实投递 | 有效Overflow或Compare IRQ必须形成真实ISR/Service投递，并由latched_source与event_count证明 | STIMER_P1_007, STIMER_P3_001 |
| STIMER_F_018 | STIMER 比较重复事件状态 | Compare脉宽扩展窗口内的同Source重复事件应置位对应诊断状态，首次现场由单次原子Snapshot保存 | STIMER_P1_010 |
| STIMER_F_019 | STIMER 暂停/溢出边界优先级 | Pause与Overflow同边界时先完成Overflow并回零，再进入Pause终态 | STIMER_P1_003 |

## 2. Case Catalog

| Case ID | P | Case 名称 | 关键输入 / 刺激 | 最小充分 Oracle / Observation | Resource |
|---|---:|---|---|---|---:|
| STIMER_P0_001 | P0 | 基本计数、Start/Stop 与实时读数测试 | 代表性合法 period/divider；Start→采样→Stop | `COUNT.LIVE` Start 后推进、Stop 后冻结 | R0 |
| STIMER_P0_002 | P0 | 周期终点与 Overflow 基本测试 | 多个短 period；One-Shot | `IRQ_RAW.OVERFLOW=1` + `COUNT.LIVE` 终态 | R0 |
| STIMER_P1_001 | P1 | 预分频比例与边界测试 | 代表性 divider + Capability 边界 | 不同divider的`COUNT.LIVE`中位速率比 | R0 |
| STIMER_P1_002 | P1 | One-Shot / Free-Run 生命周期测试 | 同一 period 下切换两种模式 | One-Shot 清 Raw 后不再重触发；Free-Run 可再次出现 Overflow | R0 |
| STIMER_P1_003 | P1 | 软件清零、Pause/Resume 与 Overflow 边界优先级测试 | CLEAR、PAUSE、RESUME；边界同步刺激 | `COUNT.LIVE` 前后状态；Full Coverage 证明 Overflow 优先后暂停 | R3 |
| STIMER_P1_004 | P1 | Immediate / Shadow 周期加载时机测试 | old/new period，分别在周期中途更新 | 下一终点与 `COUNT.LIVE`/Overflow 行为符合对应加载时机 | R0 |
| STIMER_P1_005 | P1 | 实时计数与重复锁存快照测试 | 运行中多次 Latch | `COUNT.LATCHED` 单次稳定且重复 Latch 更新；`COUNT.LIVE` 继续推进 | R0 |
| STIMER_P1_006 | P1 | 四通道 Compare 门限与来源隔离测试 | 合法 threshold 矩阵与 channel 参数 | 门限前 Raw=0；到达后仅目标 `IRQ_RAW.COMPARE[n]=1` | R0 |
| STIMER_P1_007 | P1 | IRQ 控制链、Force 与真实 Delivery 测试 | 5类 Source 的 Enable/Mask/Force/Clear | RAW/STATUS 原子寄存器事实 + ISR latch/event_count 分层闭合 | R0 |
| STIMER_P1_008 | P1 | Overflow/Compare事件脉宽测试 | Overflow/Compare宽度矩阵 | `EVENT_PULSE.*` 实测宽度与Expected一致 | R3 |
| STIMER_P1_009 | P1 | Overflow历史状态read-to-clear测试 | 自然Overflow + 两次原子状态读取 | 首次`STATUS_HISTORY.OVERFLOW=1`，再次读取为0 | R0 |
| STIMER_P1_010 | P1 | Compare重复事件诊断测试 | 扩展窗口内连续产生同Source Compare事件 | 单次`STATUS_DIAG.COMPARE_REPEAT[n]`原子Snapshot | R0 |
| STIMER_P2_001 | P2 | STIMER 事件触发真实 DMA 搬运测试 | Overflow/Compare Source + 预置 DMA Channel | `DMA_CHANNEL_STATUS` 完成 + `DMA_DESTINATION_WORD` 与 Golden 一致 | R2 |
| STIMER_P2_002 | P2 | 紧急故障触发计数捕获测试 | 安全可控紧急触发源 | 触发前 `COUNT.LIVE` 与 `EMERGENCY_CAPTURE.COUNT` 时序一致；清理规则明确 | R3 |
| STIMER_P2_003 | P2 | CPU Debug Halt 暂停/自由运行测试 | Debugger Halt 窗口 + 两种策略 | Halt 前后 `COUNT.LIVE` Delta 与真实 Halt 窗口相符 | R3 |
| STIMER_P3_001 | P3 | 长时间周期、IRQ 与计数稳定性测试 | 长时运行 + 代表性 divider/period | 独立参考频率、外部周期 Observer 与 Service IRQ累计一致，无异常状态 | R5 |

## 3. Machine-readable Case Contract

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P0_001
case_name: STIMER基本计数、Start/Stop与实时读数测试
report_feature: |-
  1. STIMER 计数与Start/Stop
p_level: P0
feature_refs:
- STIMER_F_001
method:
  inputs:
  - 基本配置：选择Capability内代表性合法prescaler_divider与足够大的period_ticks，避免观察窗内自然Overflow。
  - 观察窗口：使用两个有界采样窗口分别观察Start后的计数推进与Stop后的计数冻结。
  steps:
  - 初始准备：确认目标实例可用，清理历史IRQ/诊断状态并配置代表性divider、period和FREE_RUN。
  - 启动前采样：读取COUNT.LIVE作为start_before，确认初始值处于合法计数范围。
  - 启动计数：执行START，在有界窗口后再次读取COUNT.LIVE形成running_after。
  - 运行判定：确认running_after相对start_before发生推进，且期间无非预期错误或Overflow终态。
  - 停止计数：执行STOP并立即读取COUNT.LIVE形成stop_before。
  - 停止复核：经过第二个有界窗口后再次读取COUNT.LIVE形成stop_after。
  - 结果汇总：比较两组采样，证明Start使计数推进而Stop后计数保持不变。
  observations:
  - 启动前实时计数：读取COUNT.LIVE保存start_before；该值是后续运行增量的硬件基线。
  - 运行后实时计数：读取COUNT.LIVE保存running_after，期望与start_before不同；证明计数器真实推进。
  - 停止前后实时计数：分别读取COUNT.LIVE形成stop_before与stop_after，期望两次相同；证明Stop冻结计数。
  pass_criteria:
  - 启动计数有效：running_after与start_before不同且均在合法计数范围内。
  - 停止计数有效：stop_after严格等于stop_before。
  - 生命周期完整：Start与Stop均在统一deadline内完成且无非预期Overflow/错误状态。
timeout: 使用STIMER统一deadline；所有计数变化必须由状态/计数端点驱动，禁止固定sleep充当完成Oracle
cleanup:
- 停止本Case启动的STIMER并恢复本Case修改的运行模式、周期和分频配置。
- 清理由本Case产生的IRQ/诊断现场，保留cleanup失败Evidence。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板且无需外部仪器, bench: DUT内部计数端点即可完成Oracle}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement + COUNT.LIVE原子Observation + bound structured Artifact]
failure_observations:
- {key: running_counts, label: Start阶段COUNT.LIVE实际序列, source: dut, role: actual, format: text}
- {key: stopped_counts, label: Stop阶段COUNT.LIVE实际序列, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P0_002
case_name: STIMER周期终点与Overflow基本测试
report_feature: |-
  1. STIMER 可编程周期与溢出
p_level: P0
feature_refs:
- STIMER_F_003
method:
  inputs:
  - 周期参数：选择一个可在统一deadline内完成的代表性短period_ticks。
  - 模式条件：使用ONE_SHOT隔离单次周期终点，预先清除Overflow Raw和历史状态。
  steps:
  - 参数选择：选择本轮period_ticks并配置合法divider、ONE_SHOT和IMMEDIATE加载。
  - 状态清理：清除IRQ_RAW.OVERFLOW及可清理历史状态，确认起始Raw为0。
  - 启动周期：执行START并在统一deadline内等待目标周期终点。
  - Overflow读取：由ISR在清除前锁存IRQ_RAW.OVERFLOW，保存原始pending事实。
  - 终态读取：读取COUNT.LIVE，确认One-Shot周期结束后的计数终态。
  - 事件清除：ISR清除IRQ_RAW.OVERFLOW，PC读取回调后的运行状态作为恢复证据。
  - 结果汇总：保存period_ticks、ISR锁存Raw、终态计数与回调后状态。
  observations:
  - Overflow原始状态：读取ISR清除前锁存的IRQ_RAW.OVERFLOW，期望为1；证明真实Overflow事件发生。
  - One-Shot计数终态：读取COUNT.LIVE，期望处于One-Shot定义的零终态；不以软件延时替代终态。
  - Overflow清除状态：读取ISR清除后的运行状态，作为目标Source已被消费的恢复证据。
  pass_criteria:
  - 周期终点有效：代表性period节点在deadline内由ISR锁存IRQ_RAW.OVERFLOW=1。
  - One-Shot终态正确：Overflow后COUNT.LIVE处于定义的零终态。
  - 清除生命周期正确：ISR完成事件消费，回调后没有遗留有效运行状态。
timeout: 按最大period_ticks与divider计算有界deadline并增加统一调度裕量，禁止无界轮询
cleanup:
- 停止STIMER并清除本Case产生的Overflow IRQ状态。
- 恢复本Case修改的周期、分频、运行模式与加载模式。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT内部IRQ Raw与计数端点完成Oracle}
backend: [FPGA, Silicon]
evidence: [period_ticks Measurement + IRQ_RAW.OVERFLOW与COUNT.LIVE Observation + bound structured Artifact]
failure_observations:
- {key: event_count_delta, label: 自然Overflow ISR事件增量, source: measurement, role: actual, format: decimal}
- {key: irq_last_event, label: 自然Overflow实际锁存Source, source: dut, role: actual, format: hex32}
- {key: terminal_count, label: Overflow后COUNT.LIVE实际终态, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: STIMER_P1_001
case_name: STIMER预分频比例与边界测试
report_feature: |-
  1. STIMER 可编程预分频
p_level: P1
feature_refs:
- STIMER_F_002
method:
  inputs:
  - 分频矩阵：覆盖divider=1、代表性中间值以及Runtime Capability声明的最大合法divider。
  - 采样矩阵：每个divider在固定有界窗口内重复测量三轮，使用中位速率降低PC调度和串口往返抖动。
  steps:
  - 能力确认：读取Runtime Capability的最大divider；至少需要divider=1和一个更大合法节点，否则按能力发布缺口失败关闭。
  - 节点配置：对每个divider停止STIMER，重新配置相同的最大周期与FREE_RUN，并清零计数。
  - 计数测量：交错执行三轮divider矩阵，在固定有界窗口前后读取COUNT.LIVE，形成count_delta和actual_rate。
  - 比例计算：对每个divider取中位速率，以divider=1为基准计算actual_ratio，并以divider比例计算expected_ratio。
  - 单调复核：确认divider增大时中位速率严格下降，避免只依赖单个节点或单轮样本。
  - 结果汇总：记录全部COUNT.LIVE原始样本、中位速率、Expected Ratio和Actual Ratio。
  observations:
  - STIMER计数样本：每个divider读取COUNT.LIVE形成原始硬件样本；软件差分结果保持Measurement身份。
  - 速率结果：Actual Rate由COUNT.LIVE差分和真实采样窗口派生，中位值用于抵抗单轮调度抖动。
  - 比例结果：Actual Ratio由同一STIMER在不同divider下的中位速率计算，Expected Ratio只来自公开divider语义。
  pass_criteria:
  - 速率关系正确：各节点Actual Ratio在统一采样容差内匹配divider形成的Expected Ratio。
  - 单调关系正确：divider增大时中位Actual Rate严格下降。
  - 合法边界可执行：Runtime Capability声明的最大divider节点完成且无异常状态。
  - 配置静态性：每个divider变化均通过Stop/重新初始化完成，不在运行中热改静态分频。
timeout: 每个divider使用由参考窗口和最慢合法分频计算的统一有界deadline
cleanup:
- 停止STIMER并保留全部原始计数样本。
resources: {minimum_level: R0, full_coverage_level: R0, board: DUT板无需额外接线, bench: 无外部仪器依赖}
backend: [FPGA, Silicon]
evidence: [divider比例Measurement + COUNT.LIVE Observation + 中位速率Artifact]
failure_observations:
- {key: prescaler_rate_ratios, label: divider的Expected与Actual速率比, source: measurement, role: actual, format: text}
- {key: actual_rate_hz, label: 各divider的COUNT.LIVE中位计数速率, source: measurement, role: actual, format: float}
- {key: prescaler_measurements, label: 各轮COUNT.LIVE原始计数样本, source: dut, role: actual, format: text}
gap: [stimer_prescaler_limit_mapping_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_002
case_name: STIMER One-Shot与Free-Run生命周期测试
report_feature: |-
  1. STIMER 可编程周期与溢出
  2. STIMER One-Shot/Free-Run模式
p_level: P1
feature_refs:
- STIMER_F_003
- STIMER_F_004
method:
  inputs:
  - 模式矩阵：在相同divider与短period下分别执行ONE_SHOT和FREE_RUN。
  - 事件策略：每轮使用IRQ_RAW.OVERFLOW作为周期边界，并在首次Overflow后Clear再观察下一窗口。
  steps:
  - 初始配置：清理Overflow状态并配置ONE_SHOT、短period和合法divider。
  - One-Shot启动：执行START并等待首次IRQ_RAW.OVERFLOW=1。
  - One-Shot终态：读取COUNT.LIVE，Clear Overflow后继续观察一个完整下一周期窗口。
  - One-Shot复核：确认COUNT.LIVE保持终态且IRQ_RAW.OVERFLOW未再次置位。
  - Free-Run重建：Stop并重新初始化为FREE_RUN，保持相同period/divider后启动。
  - Free-Run首周期：等待首次Overflow，Clear对应Raw并继续观察下一周期。
  - Free-Run连续性：确认第二次IRQ_RAW.OVERFLOW重新置位且COUNT.LIVE在周期间继续推进。
  - 结果汇总：分别保存两种模式的首次/再次Overflow和计数终态。
  observations:
  - One-Shot首次Overflow：读取IRQ_RAW.OVERFLOW，期望首次周期终点为1。
  - One-Shot停止终态：首次Clear后下一完整周期窗口内COUNT.LIVE保持零终态且Raw不再出现。
  - Free-Run再次Overflow：首次Clear后下一周期IRQ_RAW.OVERFLOW再次为1；证明自动进入后续周期。
  pass_criteria:
  - One-Shot单次性：仅首次周期产生Overflow，随后观察窗内无第二次Raw且COUNT.LIVE保持终态。
  - Free-Run连续性：Clear首次Overflow后能在下一周期再次观察IRQ_RAW.OVERFLOW=1。
  - 模式隔离：两种模式每轮均重新初始化，不依赖上一轮内部状态。
timeout: 覆盖两种模式至少两个period窗口并使用有界deadline
cleanup:
- 停止STIMER并清除Overflow状态。
- 恢复本Case修改的运行模式、周期、分频与加载模式。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT内部计数与IRQ Raw即可}
backend: [FPGA, Silicon]
evidence: [run_mode Measurement + 两阶段IRQ_RAW.OVERFLOW与COUNT.LIVE Observation]
failure_observations:
- {key: one_shot_event_count_delta, label: One-Shot自然Overflow事件增量, source: measurement, role: actual, format: decimal}
- {key: free_run_event_count_delta, label: Free-Run连续Overflow事件增量, source: measurement, role: actual, format: decimal}
- {key: free_run_last_event, label: Free-Run最后实际锁存Source, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_003
case_name: STIMER软件清零与Pause/Resume测试
report_feature: |-
  1. STIMER 软件清零
  2. STIMER Pause/Resume
p_level: P1
feature_refs:
- STIMER_F_005
- STIMER_F_006
method:
  inputs:
  - 基本序列：使用长period验证运行中CLEAR_COUNT、PAUSE和RESUME，避免基本节点自然Overflow。
  steps:
  - 运行准备：配置FREE_RUN、合法divider与长period，清理历史状态后START并确认COUNT.LIVE推进。
  - 软件清零：在运行中执行CLEAR_COUNT并读取COUNT.LIVE，确认重新从零附近开始且随后继续推进。
  - 暂停动作：执行PAUSE并连续两次读取COUNT.LIVE，确认有界窗口内计数冻结。
  - 恢复动作：执行RESUME并再次读取COUNT.LIVE，确认从暂停值继续推进而不是无因重置。
  - 恢复推进复读：短间隔后再次读取COUNT.LIVE，确认恢复后的计数持续推进。
  - 结果汇总：保存运行、Pause、Clear和Resume四个阶段的COUNT.LIVE现场。
  observations:
  - 清零后计数：读取COUNT.LIVE，期望CLEAR_COUNT后回到零附近并随后重新推进。
  - 暂停前后计数：PAUSE后两次COUNT.LIVE期望相同；RESUME后后续COUNT.LIVE应变化。
  pass_criteria:
  - 软件清零正确：CLEAR_COUNT后计数回到定义起点且模块继续处于可运行生命周期。
  - 暂停恢复正确：PAUSE窗口计数冻结，RESUME后计数重新推进。
timeout: 使用统一有界状态请求与短采样窗口
cleanup:
- 取消Pause并停止STIMER，清除Overflow/Compare状态。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE分阶段Observation + bound structured Artifact]
failure_observations:
- {key: count_sequence, label: 运行、Pause、Clear与Resume阶段COUNT.LIVE序列, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_004
case_name: STIMER Immediate与Shadow周期加载时机测试
report_feature: |-
  1. STIMER 可编程周期与溢出
  2. STIMER Immediate/Shadow周期加载
p_level: P1
feature_refs:
- STIMER_F_003
- STIMER_F_007
method:
  inputs:
  - 周期组合：使用相同old_period和更长的new_period，使COUNT.LIVE越过old_period成为明确判别点。
  - 加载模式：Immediate与Shadow各自从独立Free-Run生命周期开始，只改变load_mode。
  steps:
  - Immediate基线：装载old_period并启动，在COUNT.LIVE到达中段后写new_period。
  - Immediate判别：等待COUNT.LIVE越过old_period，确认此时Overflow Event Count没有增加。
  - Immediate终点：继续等待新周期Overflow，确认新周期已作用于当前周期。
  - Shadow基线：重新装载old_period并启动，在相同计数中段写入Shadow new_period。
  - Shadow旧周期：等待第一次Overflow，确认当前old_period没有被新值提前替换。
  - Shadow新周期：在下一周期等待COUNT.LIVE越过old_period，随后等待第二次Overflow。
  - 证据汇总：保存两阶段update_count、cross_count和Overflow Event Count。
  observations:
  - Immediate更新计数：读取COUNT.LIVE，证明更新发生在旧周期中段。
  - Immediate越界计数：读取COUNT.LIVE，期望越过old_period且Event Count仍未增加。
  - Shadow更新计数：读取COUNT.LIVE，证明Shadow写入发生在旧周期中段。
  - Shadow首次事件：读取ISR Event Count，期望旧周期先产生一次Overflow。
  pass_criteria:
  - Immediate当前周期生效：COUNT.LIVE越过old_period前不得产生Overflow，之后在new_period终点产生一次Overflow。
  - Shadow当前周期保持：写入new_period后当前old_period仍产生第一次Overflow。
  - Shadow下一周期生效：下一周期可越过old_period，并在new_period终点产生第二次Overflow。
timeout: 每阶段使用统一2秒Count/IRQ deadline，禁止无界等待
cleanup:
- 停止STIMER并Disable/Clear本Case Overflow IRQ。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT内部COUNT.LIVE与ISR Event Count足够}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE Observation + Overflow event_count Measurement + bound structured Artifact]
failure_observations:
- {key: immediate_update_count, label: Immediate更新时实时计数, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.period_load}
- {key: immediate_cross_count, label: Immediate越过旧周期时实时计数, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.period_load}
- {key: immediate_cross_event_delta, label: Immediate越界时事件增量, source: measurement, role: actual, format: decimal}
- {key: shadow_first_event_delta, label: Shadow旧周期首次事件增量, source: measurement, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_005
case_name: STIMER实时计数与重复锁存快照测试
report_feature: |-
  1. STIMER Live/Latch计数
p_level: P1
feature_refs:
- STIMER_F_008
method:
  inputs:
  - 运行配置：使用FREE_RUN、长period和代表性divider，确保测试窗口内不因Overflow干扰锁存关系。
  - 锁存轮次：执行两次Latch，每次都在不同实时计数位置触发。
  steps:
  - 计数启动：配置并START STIMER，读取COUNT.LIVE确认计数正在推进。
  - 第一轮锁存：执行COUNT_LATCH后读取COUNT.LATCHED保存latched_1。
  - 第一轮稳定性：不再次Latch连续读取COUNT.LATCHED，期望保持latched_1不变。
  - 实时推进：读取COUNT.LIVE形成live_2，确认实时值已经越过第一轮锁存位置。
  - 第二轮锁存：再次执行COUNT_LATCH并读取COUNT.LATCHED形成latched_2。
  - 第二轮对照：确认latched_2更新且与邻近COUNT.LIVE处于合理先后关系。
  - 重复轮次：再执行至少一次Latch，确认控制动作可重复而非只在首轮有效。
  - 结果汇总：记录每轮Live/Latch原始样本与轮次顺序。
  observations:
  - 实时计数端点：读取COUNT.LIVE，期望运行期间随时间推进。
  - 锁存快照端点：每次Latch后读取COUNT.LATCHED，未重新Latch前期望保持稳定。
  - 重复锁存更新：第二/第三次COUNT.LATCHED应更新为新时刻快照；证明锁存控制可重复使用。
  pass_criteria:
  - 实时读数有效：运行期间COUNT.LIVE样本发生推进。
  - 单次快照稳定：同一Latch后重复读取COUNT.LATCHED保持一致。
  - 重复Latch有效：新一轮Latch后COUNT.LATCHED更新到新的计数位置。
  - 宽度语义一致：报告按公共计数宽度呈现，不把目标SDK返回类型宽度冒充硬件位宽。
timeout: 使用短有界观察窗完成三轮Latch，禁止以大延时掩盖控制脉冲问题
cleanup:
- 停止STIMER并恢复本Case配置。
- 保留每轮Live/Latch样本，清理本Case产生的状态。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT内部COUNT端点即可}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE与COUNT.LATCHED原子Observation + latch轮次Measurement]
failure_observations:
- {key: live_counts, label: 重复Latch过程COUNT.LIVE实际序列, source: dut, role: actual, format: text}
- {key: latched_counts, label: 重复Latch的COUNT.LATCHED实际序列, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_006
case_name: STIMER四通道Compare门限与来源隔离测试
report_feature: |-
  1. STIMER Compare门限与事件
p_level: P1
feature_refs:
- STIMER_F_009
method:
  inputs:
  - 门限矩阵：四个逻辑Compare通道分别配置互不相同且严格小于period_ticks的compare_ticks。
  - 来源隔离：每个参数节点只Enable目标Compare Source，测试前清除全部Compare Raw状态。
  steps:
  - 参数配置：选择channel/compare_ticks，配置长period、合法divider并装载目标Compare门限。
  - 起始清理：清除全部Compare Raw并确认目标和非目标Source均为0。
  - 门限前采样：START后在COUNT.LIVE小于compare_ticks时读取IRQ_RAW.COMPARE[n]，期望目标Source仍为0。
  - 门限到达：继续有界等待直到COUNT.LIVE越过目标门限，再读取全部Compare Raw。
  - 来源判定：确认仅目标IRQ_RAW.COMPARE[n]=1，其他Compare Source保持0。
  - 清除复核：Clear目标Source并再次读取Raw，确认目标pending消失。
  - 通道轮换：对全部Compare通道重复独立生命周期，不复用上一通道残留状态。
  - 结果汇总：保存每个channel的门限前/后Count与Raw位图。
  observations:
  - 门限前目标Raw：COUNT.LIVE小于compare_ticks时读取IRQ_RAW.COMPARE[n]，期望为0；证明没有提前触发。
  - 门限后目标Raw：达到门限后读取目标IRQ_RAW.COMPARE[n]，期望为1；证明目标比较事件发生。
  - 非目标Raw位图：同一时刻读取其他Compare Raw，期望为0；证明来源隔离。
  pass_criteria:
  - 不提前触发：每个通道在门限前目标Raw均为0。
  - 到点触发正确：每个通道在门限到达后目标Raw为1。
  - 来源隔离正确：非目标Compare Source不因当前门限事件置位。
  - 清除与覆盖完整：目标Clear后Raw为0且全部逻辑Compare通道均执行。
timeout: 每个compare_ticks使用由period/divider推导的有界deadline
cleanup:
- 停止STIMER并清除全部Compare IRQ状态。
- 恢复比较门限与事件配置，保留原始Raw位图。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT内部Count与Compare Raw足够}
backend: [FPGA, Silicon]
evidence: [compare channel/threshold Measurement + COUNT.LIVE与IRQ_RAW.COMPARE原子Observation]
failure_observations:
- {key: compare_channel, label: 本轮目标Compare通道, source: oracle, role: expected, format: decimal}
- {key: compare_threshold, label: 本轮Compare门限, source: oracle, role: expected, format: decimal}
- {key: irq_last_event, label: 自然Compare实际锁存Source, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_007
case_name: STIMER IRQ控制链、Force与真实Delivery测试
report_feature: |-
  1. STIMER IRQ使能/屏蔽/清除与RAW/STATUS
  2. STIMER IRQ软件强制
  3. STIMER IRQ真实投递
p_level: P1
feature_refs:
- STIMER_F_011
- STIMER_F_012
- STIMER_F_017
method:
  inputs:
  - Source矩阵：覆盖OVERFLOW与全部COMPARE Source；自然事件用于至少一个Overflow和一个Compare节点，其余Source允许Force补全控制矩阵。
  - Delivery观察：目标侧ISR/Service独立记录latched_source与event_count；它们与IRQ寄存器分别保存，不互相冒充。
  steps:
  - Source准备：清除目标IRQ Source，Enable并Unmask，记录event_count_before且确认RAW/STATUS起始为0。
  - 事件产生：通过自然事件或IRQ_FORCE产生目标Source，立即记录IRQ_RAW与IRQ_STATUS。
  - Delivery确认：读取ISR/Service latched_source与event_count_after，证明有效状态真实进入投递链。
  - Mask因果：Clear现场后Mask同一Source，再次Force，读取IRQ_RAW与IRQ_STATUS并记录新的event_count。
  - Mask判定：确认Raw可以存在但Status被Mask抑制，且event_count不增加。
  - Unmask恢复：解除Mask，按目标硬件pending语义观察STATUS/Delivery恢复，不重新伪造另一Source。
  - Clear生命周期：执行IRQ_CLEAR并读取RAW/STATUS，确认目标Source消失且非目标Source未被误清。
  - Source汇总：对全部IRQ Source重复独立节点并保存寄存器事实与Service事实。
  observations:
  - IRQ原始状态：读取IRQ_RAW.<Source>，期望事件/Force后为1；它只证明原始pending。
  - IRQ有效状态：读取IRQ_STATUS.<Source>，Unmask时期望1、Mask时期望0；证明Mask语义。
  - ISR真实投递：读取IRQ_DELIVERY.LATCHED_SOURCE并结合event_count delta，证明有效IRQ进入ISR；Service值不冒充寄存器。
  - 清除后状态：Clear后读取目标RAW/STATUS，期望均为0并保持非目标Source。
  pass_criteria:
  - Enable/Unmask路径闭合：目标Raw=1、Status=1且ISR event_count增加。
  - Mask抑制正确：再次Force时Raw=1、Status=0且ISR event_count不增加。
  - Clear精确：目标Clear后Raw/Status为0且非目标Source状态不被误清。
  - Source覆盖完整：OVERFLOW与全部COMPARE Source均完成控制矩阵。
timeout: 每个Source使用统一IRQ deadline；Delivery等待有界，禁止以固定sleep替代ISR事件
cleanup:
- Disable并Mask本Case使用的IRQ Source，Clear所有本Case pending。
- 注销/恢复ISR Service状态并保留最后一次寄存器与event_count现场。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板且目标固件提供STIMER IRQ Service, bench: 无外部仪器要求}
backend: [FPGA, Silicon]
evidence: [IRQ_RAW/IRQ_STATUS Observation + ISR latched Source + event_count Measurement + bound Artifact]
failure_observations:
- {key: irq_source, label: 本轮目标IRQ Source, source: oracle, role: expected, format: text}
- {key: masked_raw, label: Mask阶段IRQ_RAW实际值, source: dut, role: actual, format: hex32}
- {key: masked_status, label: Mask阶段IRQ_STATUS实际值, source: dut, role: actual, format: hex32}
- {key: delivery_delta, label: ISR event_count增量, source: measurement, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: STIMER_P1_008
case_name: STIMER Overflow/Compare事件脉宽测试
report_feature: |-
  1. STIMER Overflow/Compare脉宽扩展
p_level: P1
feature_refs:
- STIMER_F_010
method:
  inputs:
  - 脉宽矩阵：选择公共接口可表达的最小、代表性和扩展脉宽值，当前只覆盖Compare0 Source。
  steps:
  - 输出路由：通过Bench逻辑名stimer_output建立事件到数字Observer的稳定路由并确认可连接。
  - 公共配置：固定Compare0门限、周期和FREE_RUN，仅改变event_pulse_width_cycles。
  - 观测准备：每个宽度节点清除历史IRQ，Arm并启动stimer_output单次采集。
  - 事件激励：启动STIMER并等待两个真实Compare0 IRQ Delivery，确保外部波形不是空闲或软件延时。
  - 波形测量：停止Observer并读取frequency_hz、period_s和positive_width_s。
  - 比例比较：用实测positive_width_s/period_s与width_cycles/period_ticks比较，隔离未知源时钟频率。
  - 参数切换：停止当前节点并对下一脉宽重新建立完整生命周期，不复用前一节点事件。
  - 结果汇总：保存每个宽度节点的Expected比例、实测物理量、IRQ Source和波形Artifact。
  observations:
  - 外部事件脉宽：stimer_output Observer读取positive_width_s和period_s，作为真实物理观测。
  - 事件来源：STIMER IRQ Snapshot读取Compare0真实Delivery，确认波形与DUT事件同源。
  pass_criteria:
  - 脉宽测量正确：全部计划宽度节点的实测宽度/周期比例在统一量化容差内匹配Expected。
  - Source覆盖正确：每个节点均产生Compare0真实IRQ Delivery。
  - Evidence完整：每个参数节点都保留Expected、实测宽度和对应波形Artifact。
timeout: 每个脉宽节点使用事件周期与采样窗口推导的有界deadline
cleanup:
- 停止STIMER、清理本Case事件状态并恢复事件输出路由。
- 释放FPGA/Instrument采样资源并保留波形Artifact。
resources: {minimum_level: R3, full_coverage_level: R3, board: DUT Compare0事件需可路由到stimer_output逻辑信号, bench: Companion FPGA、逻辑分析仪或示波器通过Bench绑定完成连续脉宽采样}
backend: [FPGA, Silicon]
evidence: [event_pulse_width_cycles Measurement + EVENT_PULSE物理量Observation + IRQ Snapshot + waveform Artifact]
failure_observations:
- {key: expected_width_cycles, label: 目标事件Expected脉宽周期数, source: oracle, role: expected, format: decimal}
- {key: actual_width_s, label: stimer_output实测事件正脉宽, source: observer, role: actual, format: float, semantic_ref: stimer.feature.event_pulse_width}
- {key: actual_period_s, label: stimer_output实测事件周期, source: observer, role: actual, format: float, semantic_ref: stimer.feature.event_pulse_width}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_009
case_name: STIMER Overflow历史状态read-to-clear测试
report_feature: |-
  1. STIMER 溢出历史状态
p_level: P1
feature_refs:
- STIMER_F_014
method:
  inputs:
  - Overflow输入：使用短周期One-Shot自然产生一次Overflow，不使用IRQ Force替代硬件周期终点。
  steps:
  - 能力确认：确认目标实例提供Period、Runtime Status与自然Overflow IRQ能力。
  - 基线清理：停止STIMER并单次读取Runtime Status，消费前序read-to-clear诊断现场。
  - 功能配置：配置短周期One-Shot，清零计数并建立Overflow IRQ投递。
  - 自然激励：启动STIMER并在统一deadline内等待一次真实Overflow ISR事件。
  - 首次快照：只读取一次Runtime Status，原子保存STATUS_HISTORY.OVERFLOW首次现场。
  - 生命周期复核：再次读取Runtime Status，观察相同历史位是否已按read-to-clear语义清除。
  - 结果判定：关联自然Overflow ISR、首次历史位与第二次清除后状态形成完整证明链。
  observations:
  - Overflow投递：读取IRQ_DELIVERY.LATCHED_SOURCE与event_count，期望OVERFLOW被真实投递且计数增加一次。
  - 首次历史状态：第一次原子读取STATUS_HISTORY.OVERFLOW，期望为1；证明自然Overflow被诊断端点记录。
  - 清除后状态：第二次原子读取STATUS_HISTORY.OVERFLOW，期望为0；证明第一次读取已完成read-to-clear。
  pass_criteria:
  - 自然事件成立：Overflow ISR event_count精确增加一次且Last Event包含OVERFLOW。
  - 历史位有效：首次Runtime Status Snapshot包含STATUS_HISTORY.OVERFLOW。
  - 生命周期正确：紧随其后的第二次Snapshot不再包含STATUS_HISTORY.OVERFLOW。
timeout: 使用统一IRQ deadline等待自然Overflow；所有状态读取均为有界同步命令
cleanup:
- 停止STIMER，Disable并Clear本Case的Overflow IRQ Source。
- 读取并消费本Case可能残留的read-to-clear诊断状态。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板且目标固件提供原子Runtime Status读取, bench: 无外部仪器要求}
backend: [FPGA, Silicon]
evidence: [Overflow ISR event_count + STATUS_HISTORY.OVERFLOW首次/清除后Observation + bound Artifact]
failure_observations:
- {key: overflow_history_status, label: Overflow历史状态序列, source: dut, role: actual, format: text, semantic_ref: stimer.feature.overflow_history}
- {key: overflow_delivery_delta, label: Overflow ISR事件增量, source: measurement, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P1_010
case_name: STIMER Compare重复事件诊断测试
report_feature: |-
  1. STIMER 比较重复事件状态
p_level: P1
feature_refs:
- STIMER_F_018
method:
  inputs:
  - Compare输入：选择一个Capability支持的Compare Source，事件脉宽设置为256个STIMER时钟周期。
  - 重复刺激：配置短周期Free-Run，使同Source Compare自然周期小于事件扩展窗口。
  steps:
  - 能力确认：确认Compare、Free-Run、事件脉宽、IRQ控制与原子Runtime Status读取均已映射。
  - 基线清理：停止STIMER并单次读取Runtime Status，消费前序read-to-clear诊断现场。
  - Compare配置：设置短Free-Run周期、目标Compare门限和长于周期的事件脉宽。
  - Raw观测配置：Enable并Mask目标Source，使硬件Raw可见而CPU IRQ不被高频事件持续投递。
  - 重复事件激励：启动STIMER，连续等待并清除两次目标Raw，证明同Source Compare自然重复发生。
  - 诊断快照：只读取一次Runtime Status，保存STATUS_DIAG.COMPARE_REPEAT[n]首次现场。
  - 生命周期复核：再次读取Runtime Status，确认目标重复诊断位按read-to-clear语义清除。
  - 结果判定：关联两次目标Compare事件、首次诊断位和清除后状态形成证明链。
  observations:
  - Compare Raw序列：连续两次读取IRQ_RAW.COMPARE[n]均为1，且两次之间执行目标Source Clear。
  - CPU投递计数：Mask期间event_count保持不变，证明高频刺激未进入CPU IRQ投递链。
  - 首次重复诊断：原子读取STATUS_DIAG.COMPARE_REPEAT[n]，期望为1；证明硬件检测到重复事件。
  - 清除后诊断：第二次原子读取同一字段，期望为0；证明read-to-clear生命周期正确。
  pass_criteria:
  - 重复刺激成立：两次目标Compare Raw均有效，且Mask期间CPU Delivery计数不增加。
  - 重复诊断有效：首次Snapshot包含目标STATUS_DIAG.COMPARE_REPEAT[n]且不误置其他通道。
  - 生命周期正确：第二次Snapshot中目标重复诊断位清除。
timeout: 使用统一IRQ Raw deadline等待两次自然Compare；所有状态读取均为有界同步命令
cleanup:
- 停止STIMER，把目标事件恢复为不扩展脉宽并清理目标IRQ Source。
- 读取并消费本Case可能残留的read-to-clear诊断状态。
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板且目标固件提供事件脉宽配置与原子状态读取, bench: 无外部仪器要求}
backend: [FPGA, Silicon]
evidence: [Compare Raw序列 + CPU Delivery增量 + STATUS_DIAG.COMPARE_REPEAT首次/清除后Observation + bound Artifact]
failure_observations:
- {key: compare_raw_sequence, label: Compare Raw状态序列, source: dut, role: actual, format: text, semantic_ref: stimer.feature.compare_repeat}
- {key: masked_delivery_delta, label: Mask期间CPU投递增量, source: measurement, role: actual, format: decimal}
- {key: compare_repeat_status, label: Compare重复诊断状态序列, source: dut, role: actual, format: text, semantic_ref: stimer.feature.compare_repeat}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: STIMER_P2_001
case_name: STIMER事件触发真实DMA搬运测试
report_feature: |-
  1. STIMER DMA请求握手
p_level: P2
feature_refs:
- STIMER_F_013
method:
  inputs:
  - Request矩阵：覆盖OVERFLOW与各逻辑COMPARE Source；每个节点使用确定性Destination初值与独立Expected Word。
  - DMA配置：预先创建可观察的Peer DMA Channel，Destination必须位于可读目标内存且初值与Expected不同。
  steps:
  - DMA准备：配置Peer DMA Channel、Source/Destination和传输宽度，保持Channel已就绪但尚未完成。
  - STIMER配置：选择当前dma_request_source，配置能确定产生该事件的period/compare参数并清理历史状态。
  - 启动顺序：先Arm DMA Channel，再START STIMER，禁止事件先于DMA就绪。
  - 事件确认：使能目标自然Source，由ISR在清除前保存last_raw、last_event和event_count，证明STIMER事件真实产生。
  - DMA完成等待：在统一deadline内读取DMA_CHANNEL_STATUS直到原Channel进入完成终态且无Error。
  - 目的端读取：读取DMA_DESTINATION_WORD形成Actual，禁止用DMA配置值代替搬运结果。
  - Golden比较：将Destination Actual与独立Expected Word比较，并确认不是初始化哨兵值。
  - Source汇总：对全部计划Request Source重复独立生命周期。
  observations:
  - STIMER触发事件：读取ISR保存的last_raw、last_event和event_count增量；证明Request源事件存在且已真实投递。
  - DMA硬件终态：读取DMA_CHANNEL_STATUS，期望原Channel完成且无Error。
  - DMA目的端数据：读取DMA_DESTINATION_WORD，期望与独立Expected一致且不等于初始化哨兵。
  pass_criteria:
  - Request Source有效：每个计划Overflow/Compare Source均真实产生对应事件。
  - DMA完成正确：原DMA Channel在deadline内完成且无Error，不允许重启Channel掩盖请求丢失。
  - 数据搬运正确：Destination Actual精确等于Expected且哨兵被替换。
  - Source覆盖完整：全部Capability声明的STIMER DMA Source均形成独立结果。
timeout: 由最慢STIMER事件周期与DMA统一deadline共同限制，禁止无界等待Channel
cleanup:
- 停止STIMER并清理本Case事件状态。
- 按资源owner逆序Disable/释放DMA Channel并恢复Destination测试Buffer。
resources: {minimum_level: R2, full_coverage_level: R2, board: DUT板需具备STIMER到DMA的Execution Mapping, bench: DUT内部DMA Peer即可}
backend: [FPGA, Silicon]
evidence: [STIMER事件Observation + DMA_CHANNEL_STATUS + DMA_DESTINATION_WORD + Expected Measurement]
failure_observations:
- {key: trigger_latched_source, label: STIMER目标事件ISR锁存Source, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.dma_request}
- {key: dma_interrupt_status, label: DMA Channel实际中断状态, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.dma_request}
- {key: dma_actual_word, label: DMA目的端实际数据, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.dma_request}
- {key: dma_expected_word, label: DMA目的端Expected数据, source: oracle, role: expected, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: STIMER_P2_002
case_name: STIMER紧急故障触发计数捕获测试
report_feature: |-
  1. STIMER 紧急计数捕获
p_level: P2
feature_refs:
- STIMER_F_016
method:
  inputs:
  - 逻辑触发源：使用Runtime Capability声明的第一个逻辑Source和Trigger Group，不向Case暴露芯片XBAR mask。
  - 外部激励：通过Bench逻辑名`stimer_emergency_input`获取单次PulseStimulus，脉宽由Case给出，物理设备和通道由Bench绑定。
  - 捕获窗口：配置Capability允许的长period，使用触发前后COUNT.LIVE建立无符号32-bit计数窗口。
  steps:
  - Runtime门禁：确认目标Service声明EMERGENCY_CAPTURE、PERIOD、FREE_RUN和START_STOP；缺少能力时按运行时事实skip。
  - STIMER配置：停止旧会话，禁用旧紧急路由，配置长period Free-Run并清零COUNT.LIVE。
  - 路由准备：配置公开逻辑Source/Trigger Group，打开`stimer_emergency_input`对应的Bench激励器。
  - 触发前采样：START后读取COUNT.LIVE形成count_before。
  - 紧急刺激：通过PulseStimulus发出一次有界脉冲，并记录真实主机执行时间窗。
  - 捕获读取：读取EMERGENCY_CAPTURE.COUNT和触发后的COUNT.LIVE，禁止用软件保存的count_before冒充捕获寄存器。
  - 结果清理：在断言后停止STIMER、禁用紧急路由并关闭激励器；只读捕获值由下一次有效触发覆盖。
  observations:
  - 紧急捕获值：读取EMERGENCY_CAPTURE.COUNT形成captured_count，格式为hex32。
  - 实时计数窗口：读取触发前后COUNT.LIVE和无符号32-bit推进跨度。
  - 外部激励事件：记录`stimer_emergency_input` PulseStimulus的真实执行时间窗和设备身份。
  pass_criteria:
  - 能力与命令：Runtime能力已真实发布且配置、读取命令成功返回。
  - 激励与计数：PulseStimulus返回真实执行时间窗，COUNT.LIVE在触发前后推进。
  - 捕获窗口：captured_count落在本次触发前后COUNT.LIVE的无符号32-bit计数窗口内。
  - 清理结果：Case结束时STIMER停止、紧急路由禁用、外部激励输出关闭。
timeout: 单次配置、脉冲和捕获读取使用统一有界请求deadline；禁止无界等待
cleanup:
- 停止STIMER并解除紧急触发路由。
- 关闭`stimer_emergency_input`激励输出；只读捕获值不写入伪造的清零值。
resources: {minimum_level: R3, full_coverage_level: R3, board: DUT需提供安全紧急触发路由, bench: 逻辑名stimer_emergency_input的PulseStimulus绑定}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE窗口 + EMERGENCY_CAPTURE.COUNT + PulseStimulus时间窗 Artifact]
failure_observations:
- {key: emergency_capture_count, label: EMERGENCY_CAPTURE.COUNT实际值, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.emergency_capture}
- {key: live_count_samples, label: 紧急触发前后COUNT.LIVE原始值, source: dut, role: actual, format: text, semantic_ref: stimer.feature.emergency_capture}
- {key: pulse_event, label: 外部PulseStimulus实际时间窗, source: instrument, role: actual, format: text, semantic_ref: stimer.feature.emergency_capture}
gap: [stimer_emergency_trigger_mapping_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: STIMER_P2_003
case_name: STIMER CPU Debug Halt暂停与自由运行测试
report_feature: |-
  1. STIMER Debug Halt行为
p_level: P2
feature_refs:
- STIMER_F_015
method:
  inputs:
  - 策略矩阵：分别执行debug_halt_policy=PAUSE与RUN_FREE，使用相同长period/divider避免Halt期间Overflow。
  - Halt窗口：由Debugger控制固定有界Halt时长并记录独立halt_duration，不以目标CPU软件延时模拟Halt。
  steps:
  - Debugger准备：建立可脚本化的Halt/Resume控制并确认可在CPU Halt状态读取或恢复后读取STIMER计数。
  - PAUSE配置：配置STIMER PAUSE策略、长period后START，读取COUNT.LIVE保存pause_before。
  - PAUSE Halt：Debugger真实Halt CPU并保持目标窗口，记录halt_duration后Resume。
  - PAUSE读回：读取COUNT.LIVE保存pause_after，确认Halt窗口内计数未按正常速率推进。
  - RUN_FREE重建：Stop并重新配置RUN_FREE策略，START后读取COUNT.LIVE保存run_before。
  - RUN_FREE Halt：以相同Debugger流程再次Halt/Resume并记录第二个halt_duration。
  - RUN_FREE读回：读取COUNT.LIVE保存run_after，确认计数在Halt窗口内继续推进。
  - 结果汇总：比较两种策略的Count Delta与独立Halt窗口，保留Debugger Session Artifact。
  observations:
  - PAUSE前后计数：读取COUNT.LIVE形成pause_before/pause_after，期望Halt窗口内Delta处于冻结量化范围。
  - RUN_FREE前后计数：读取COUNT.LIVE形成run_before/run_after，期望Halt窗口内出现与divider一致的正向Delta。
  - Debugger Halt窗口：由Instrument/Debugger记录实际halt_duration，作为独立刺激事实而非STIMER寄存器。
  pass_criteria:
  - PAUSE策略正确：真实Halt窗口内STIMER计数冻结在Observer量化上界内。
  - RUN_FREE策略正确：真实Halt窗口内STIMER计数继续推进且Delta明显大于PAUSE节点。
  - 策略隔离：两节点均从独立生命周期开始且不因Overflow/Reset混淆结果。
timeout: 每个Debugger节点限定Halt、Resume和读回deadline；Debugger失联立即失败关闭
cleanup:
- 确保CPU已Resume并停止STIMER，恢复默认debug_halt_policy。
- 关闭Debugger自动化Session并保存Halt/Resume时间线。
resources: {minimum_level: R3, full_coverage_level: R3, board: DUT需支持受控Debug Halt且不触发额外Reset, bench: JTAG或SWD Debugger自动化控制}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE前后Observation + Debugger halt_duration Measurement + Debug Session Artifact]
failure_observations:
- {key: pause_delta, label: PAUSE策略Halt窗口计数增量, source: measurement, role: actual, format: decimal}
- {key: run_free_delta, label: RUN_FREE策略Halt窗口计数增量, source: measurement, role: actual, format: decimal}
- {key: debugger_pause_window_s, label: PAUSE策略Debugger实际Halt时长, source: instrument, role: stimulus, format: float, semantic_ref: stimer.feature.debug_halt}
- {key: debugger_run_free_window_s, label: RUN_FREE策略Debugger实际Halt时长, source: instrument, role: stimulus, format: float, semantic_ref: stimer.feature.debug_halt}
gap: [stimer_debugger_bench_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: STIMER_P3_001
case_name: STIMER长时间周期、IRQ与计数稳定性测试
report_feature: |-
  1. STIMER 计数与Start/Stop
  2. STIMER 可编程预分频
  3. STIMER 可编程周期与溢出
  4. STIMER One-Shot/Free-Run模式
  5. STIMER IRQ真实投递
p_level: P3
feature_refs:
- STIMER_F_001
- STIMER_F_002
- STIMER_F_003
- STIMER_F_004
- STIMER_F_017
method:
  inputs:
  - 长时矩阵：由Runtime Capability和独立参考频率生成两个divider/period组合，窗口固定为有界时长。
  - 逻辑观测：使用stimer_reference获取独立频率，使用stimer_output读取Overflow外部周期；物理通道由Bench绑定。
  steps:
  - 参考准备：打开stimer_reference逻辑Observer并读取参考频率，作为Expected周期计算的独立时基。
  - 参数准备：按参考频率、divider和period上限生成两个合法参数节点。
  - 基线采样：每个节点START前记录COUNT.LIVE和IRQ event_count，清除前序Raw/Status。
  - 长时运行：Arm stimer_output后START并运行有界窗口，Service只累计Overflow事件。
  - 中途健康检查：窗口中按预定点读取一次Status，单独保存read-to-clear诊断现场。
  - 结束采样：STOP并停止Observer，读取COUNT.LIVE、IRQ event_count、外部周期和最终Status。
  - 数学核对：按参考频率、divider和period计算Expected输出频率/Overflow数量，交叉比较Observer和Service事实。
  - 结果汇总：保存参数、原始计数、IRQ快照、状态和Observer身份，形成可回溯长时Artifact。
  observations:
  - 独立参考频率：读取stimer_reference频率，作为长期Expected计算Oracle。
  - 外部Overflow周期：读取stimer_output频率、周期和正脉宽，形成独立周期事实。
  - STIMER计数：读取COUNT.LIVE前后值，确认窗口内真实推进。
  - IRQ投递累计：读取IRQ_SNAPSHOT.event_count和last_event，确认Overflow没有丢失或重复。
  - 诊断快照：保存中途和最终Status原始值，允许Overflow历史位但禁止Compare错误/重复位。
  pass_criteria:
  - 周期一致：外部stimer_output频率与独立参考计算值处于有界量化容差内。
  - IRQ无丢失重复：Service event_count增量与Expected Overflow数量处于有界误差内，last_event包含Overflow。
  - 计数推进：每个节点COUNT.LIVE增量大于零。
  - 长时健康稳定：中途和最终Status不包含Compare错误或重复事件位，所有参数节点均完成。
timeout: 每个节点使用固定长时窗口和Driver deadline；禁止无界长期循环
cleanup:
- 停止STIMER、Disable并清除Overflow IRQ，恢复本Case修改的脉宽配置。
- 停止并关闭stimer_reference/stimer_output逻辑Observer，保存完整长时Artifact。
resources: {minimum_level: R5, full_coverage_level: R5, board: 可靠性DUT板与稳定时钟条件, bench: 长时Companion FPGA或等价独立Reference/Event Counter}
backend: [FPGA, Silicon]
evidence: [stimer_reference频率 + stimer_output周期 + COUNT.LIVE + IRQ event_count + diagnostic Artifact]
failure_observations:
- {key: expected_overflow_count, label: 独立参考计算Expected Overflow总数, source: oracle, role: expected, format: decimal}
- {key: output_frequency, label: stimer_output实际Overflow频率, source: observer, role: actual, format: float, semantic_ref: stimer.feature.long_run}
- {key: irq_latched_source, label: Service实际Overflow锁存Source, source: dut, role: actual, format: hex32, semantic_ref: stimer.feature.irq_delivery}
- {key: count_samples, label: 长时COUNT.LIVE起止原始值, source: dut, role: actual, format: text, semantic_ref: stimer.feature.long_run}
gap: [stimer_long_run_reference_bench_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  STIMER_P0_001:
    summary: "STIMER Start后实时计数推进，Stop后实时计数保持稳定。"
    fields:
      - {source: observation, path: running_counts, label: Start阶段COUNT.LIVE, format: text, aggregate: distinct}
      - {source: observation, path: stopped_counts, label: Stop阶段COUNT.LIVE, format: text, aggregate: distinct}
  STIMER_P0_002:
    summary: "STIMER One-Shot短周期自然产生Overflow，ISR投递与终态计数可观测。"
    fields:
      - {source: measurement, path: event_count_delta, label: Overflow事件增量, format: decimal, aggregate: same}
      - {source: observation, path: irq_last_event, label: Overflow锁存Source, format: hex32, aggregate: same}
      - {source: observation, path: irq_raw_at_delivery, label: ISR锁存Overflow Raw, format: hex32, aggregate: same}
      - {source: observation, path: terminal_count, label: Overflow后COUNT.LIVE, format: hex32, aggregate: same}
  STIMER_P1_001:
    summary: "STIMER不同预分频节点的COUNT.LIVE中位计数速率按divider比例下降。"
    fields:
      - {source: measurement, path: prescaler_measurements, label: 各divider的COUNT.LIVE与速率样本, format: text, aggregate: distinct}
      - {source: measurement, path: prescaler_rate_ratios, label: divider的Expected与Actual速率比, format: text, aggregate: distinct}
  STIMER_P1_002:
    summary: "STIMER One-Shot只结束一次，Free-Run可连续产生多个Overflow周期。"
    fields:
      - {source: measurement, path: one_shot_event_count_delta, label: One-Shot事件增量, format: decimal, aggregate: same}
      - {source: measurement, path: free_run_event_count_delta, label: Free-Run事件增量, format: decimal, aggregate: same}
      - {source: observation, path: free_run_last_event, label: Free-Run锁存Source, format: hex32, aggregate: same}
  STIMER_P1_003:
    summary: "STIMER Pause期间计数冻结，Clear后计数归零，Resume后恢复推进。"
    fields:
      - {source: observation, path: count_sequence, label: Clear/Pause/Resume计数序列, format: text, aggregate: distinct}
  STIMER_P1_004:
    summary: "STIMER Immediate更新作用于当前周期，Shadow更新从下一周期开始生效。"
    fields:
      - {source: observation, path: immediate_update_count, label: Immediate更新时实时计数, format: hex32, aggregate: range}
      - {source: observation, path: immediate_cross_count, label: Immediate越过旧周期时计数, format: hex32, aggregate: range}
      - {source: measurement, path: immediate_cross_event_delta, label: Immediate越界时事件增量, format: decimal, aggregate: same}
      - {source: measurement, path: shadow_first_event_delta, label: Shadow首次事件增量, format: decimal, aggregate: same}
  STIMER_P1_005:
    summary: "STIMER Live计数持续推进，重复Latch每次保存当前计数快照。"
    fields:
      - {source: observation, path: live_counts, label: COUNT.LIVE序列, format: text, aggregate: distinct}
      - {source: observation, path: latched_counts, label: COUNT.LATCHED序列, format: text, aggregate: distinct}
  STIMER_P1_006:
    summary: "STIMER四路Compare分别在配置门限产生目标Source事件。"
    fields:
      - {source: measurement, path: compare_channel, label: Compare通道, format: decimal, aggregate: distinct}
      - {source: measurement, path: compare_threshold, label: Compare门限, format: decimal, aggregate: distinct}
      - {source: observation, path: irq_last_event, label: 实际Compare Source, format: hex32, aggregate: distinct}
  STIMER_P1_007:
    summary: "STIMER五类IRQ Source的Mask、Unmask、Force、Disable和CPU投递语义分层正确。"
    fields:
      - {source: measurement, path: irq_source, label: 目标IRQ Source, format: text, aggregate: distinct}
      - {source: observation, path: masked_raw, label: Mask阶段IRQ_RAW, format: hex32, aggregate: distinct}
      - {source: observation, path: masked_status, label: Mask阶段IRQ_STATUS, format: hex32, aggregate: distinct}
      - {source: measurement, path: delivery_delta, label: Unmask投递增量, format: decimal, aggregate: same}
  STIMER_P1_008:
    summary: "STIMER Compare0事件的配置脉宽与外部stimer_output实测正脉宽比例一致。"
    fields:
      - {source: measurement, path: event_pulse_width_cycles, label: 事件脉宽配置矩阵, format: text, aggregate: distinct}
      - {source: observation, path: actual_width_s, label: 各脉宽节点实测正脉宽, format: float, aggregate: distinct}
      - {source: observation, path: actual_period_s, label: 各脉宽节点实测周期, format: float, aggregate: distinct}
  STIMER_P1_009:
    summary: "STIMER自然Overflow会置位历史状态，首次原子读取后该状态按read-to-clear语义清除。"
    fields:
      - {source: observation, path: overflow_history_status, label: Overflow历史状态序列, format: text, aggregate: distinct}
      - {source: measurement, path: overflow_delivery_delta, label: Overflow ISR事件增量, format: decimal, aggregate: same}
  STIMER_P1_010:
    summary: "STIMER短周期Compare会在事件脉宽扩展窗口内形成重复诊断，首次读取后该状态按read-to-clear清除。"
    fields:
      - {source: observation, path: compare_raw_sequence, label: Compare Raw状态序列, format: text, aggregate: distinct}
      - {source: measurement, path: masked_delivery_delta, label: Mask期间CPU投递增量, format: decimal, aggregate: same}
      - {source: observation, path: compare_repeat_status, label: Compare重复诊断状态序列, format: text, aggregate: distinct}
  STIMER_P2_001:
    summary: "STIMER五类自然事件分别触发一次DMA P2M搬运，目标内存数据与Period硬件编码一致。"
    fields:
      - {source: observation, path: trigger_latched_source, label: STIMER目标事件ISR锁存Source, format: hex32, aggregate: distinct}
      - {source: observation, path: dma_interrupt_status, label: DMA Channel中断状态, format: hex32, aggregate: same}
      - {source: observation, path: dma_actual_word, label: DMA目标内存实际值, format: hex32, aggregate: distinct}
      - {source: measurement, path: dma_expected_word, label: DMA目标内存Expected值, format: hex32, aggregate: same}
  STIMER_P2_002:
    summary: "STIMER外部紧急脉冲触发系统级捕获，EMERGENCY_CAPTURE.COUNT落在本次COUNT.LIVE推进窗口。"
    fields:
      - {source: observation, path: emergency_capture_count, label: EMERGENCY_CAPTURE.COUNT实际值, format: hex32, aggregate: distinct}
      - {source: observation, path: live_count_samples, label: 紧急触发前后COUNT.LIVE原始值, format: text, aggregate: distinct}
      - {source: observation, path: pulse_event, label: 外部PulseStimulus实际时间窗, format: text, aggregate: distinct}
  STIMER_P2_003:
    summary: "STIMER真实Debugger Halt下PAUSE策略冻结计数，RUN_FREE策略继续计数。"
    fields:
      - {source: observation, path: pause_count_samples, label: PAUSE策略Halt前后COUNT.LIVE, format: text, aggregate: same}
      - {source: observation, path: run_free_count_samples, label: RUN_FREE策略Halt前后COUNT.LIVE, format: text, aggregate: same}
      - {source: observation, path: debugger_pause_window_s, label: PAUSE策略Debugger Halt窗口, format: float, aggregate: distinct}
      - {source: observation, path: debugger_run_free_window_s, label: RUN_FREE策略Debugger Halt窗口, format: float, aggregate: distinct}
  STIMER_P3_001:
    summary: "STIMER长时Free-Run的外部Overflow周期与Service IRQ累计保持一致。"
    fields:
      - {source: observation, path: reference_frequency_hz, label: 独立参考频率, format: float, aggregate: same}
      - {source: observation, path: output_frequency, label: stimer_output实际Overflow频率, format: float, aggregate: distinct}
      - {source: observation, path: irq_latched_source, label: Overflow锁存Source, format: hex32, aggregate: distinct}
      - {source: observation, path: count_samples, label: 长时COUNT.LIVE前后值, format: text, aggregate: distinct}
```
<!-- ET_CASE_REPORT_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Mapping | Case Adaptation | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | ADAPTED=17; MAPPING_GAP=2 | ADAPTED=13; BENCH_GAP=3 | 早期全量Working-tree FPGA HIL为22 PASS / 5 SKIP；复核后P1_001改为内部速率比并等待重跑，P2_003为FAIL，仅P1_008/P2_002/P3_001保留外部物理Bench SKIP | `ET6801_stimer.md` |

`SUPPORTED` 或“硬件已确认”不等于HIL PASS。已实现Case必须经过本轮HIL后才能写入执行结论；若运行资源尚未绑定，使用 `BENCH_GAP` 或 Runtime Capability 门禁，不把已实现代码链降级为 PLAN。

## 5. Common Gap / Evolution

### 5.1 当前公共 Gap Registry

| Gap ID | 当前状态 | 解除条件 |
|---|---|---|
| `stimer_case_implementation_gap` | CLOSED | 16个Case已建立Registry、实现、证据和报告绑定；P2-002的运行门禁由Runtime Capability与Bench逻辑绑定负责 |
| `stimer_prescaler_limit_mapping_gap` | OPEN | 目标Chip Capability给出已验证逻辑divider上下界；冲突时不得用历史芯片范围覆盖目标SVD |
| `stimer_reference_observer_gap` | OPEN | 只服务P3长时绝对周期/漂移；P1预分频比例使用内部COUNT.LIVE速率比，不依赖外部Reference |
| `stimer_pause_overflow_boundary_bench_gap` | OPEN | 建立可重复的Pause/Overflow同边界刺激并可证明事件先后，不以概率性软件延时替代 |
| `stimer_immediate_load_edge_semantic_gap` | OPEN | 目标Chip确认重复Immediate Load控制脉冲/上升沿生命周期，Driver重复调用不会因残留位失效 |
| `stimer_control_pulse_repeatability_gap` | OPEN | 对Clear/Latch/Compare Load等脉冲型控制验证重复操作可产生新硬件动作 |
| `stimer_compare_driver_gap` | CLOSED | 隔离的Driver Test Extension按32-bit Compare门限寄存器写入，公共Wrap不直接访问寄存器 |
| `stimer_irq_service_gap` | CLOSED | Firmware Service已提供Source级IRQ latch/event_count，并保持与RAW/STATUS分层的Canonical Evidence |
| `stimer_atomic_status_snapshot_gap` | CLOSED | Chip Driver Test Extension对read-to-clear状态执行一次读取，公共Wrap只解析该原子Snapshot |
| `stimer_compare_repeat_execution_mapping_gap` | CLOSED | 公共脉宽配置、短周期Free-Run、两次自然Raw边界与原子read-to-clear状态形成完整证明链 |
| `stimer_event_route_bench_gap` | OPEN | 建立Overflow/Compare事件到FPGA/Instrument数字Observer的稳定路由与采样率约束 |
| `stimer_dma_execution_mapping_gap` | CLOSED | 公共Resolver隔离芯片Request/地址事实，Case闭合STIMER Source、DMAMUX、DMA Channel和Destination数据链 |
| `stimer_emergency_trigger_mapping_gap` | OPEN | 明确安全紧急触发Source、路由和允许的外部/FPGA刺激方式 |
| `stimer_emergency_capture_cleanup_gap` | OPEN | 明确紧急捕获寄存器的软件清除/Reset生命周期，避免Case猜测不可逆恢复动作 |
| `stimer_debugger_bench_gap` | OPEN | 建立可脚本化Debugger Halt/Resume并可记录真实Halt窗口 |
| `stimer_long_run_reference_bench_gap` | OPEN | 建立P3长时独立Reference/Event Counter、稳定供电时钟和Artifact留存链 |

### 5.2 设计原则

1. **先冻结 Contract，再写 Case。** 已实现Case遵循本文件的输入、流程、Observation与Oracle；其余PLAN在实现前必须先完成同等审核。
2. **不机械继承历史测试。** 历史 `stimer.json`、UnitTest、FPGA Test 只作为 Source Item；其中热改静态分频、单一IRQ布尔标志、依赖延时、调试测试方法等旧做法必须由当前 Contract 取代。
3. **不把配置写值当硬件事实。** `prescaler_divider`、`period_ticks`、`compare_ticks` 是 Measurement；只有真实 `COUNT/IRQ/STATUS/Observer` 读取才是 Observation。
4. **中断寄存器与ISR分层。** `IRQ_RAW/STATUS`、`IRQ_DELIVERY.LATCHED_SOURCE`、`event_count` 是三类来源事实，报告不得合并成一个“中断正常”字段。
5. **诊断Snapshot优先保现场。** read-to-clear 目标必须先原子读取并记录，再断言；禁止逐字段读取导致第一项检查消费后续现场。
6. **Feature强度不超过Observer。** 没有连续数字采样就不能声称脉宽正确；没有真实Debugger Halt就不能声称CPU Halt策略通过；没有独立Reference就不能声称长期无漂移。

### 5.3 Feature完整覆盖环境矩阵

| Feature | 最小环境/执行映射 | 当前结论 |
|---|---|---|
| F001、F003～F009、F011～F012、F017 | DUT + 当前STIMER Service/Wrap/Driver；IRQ项需要目标CPU真实ISR | 不需要外部仪器；当前Case已覆盖主体路径 |
| F002 | DUT + 片内独立Reference Counter或经校准的数字Observer | 需要独立时基，不能用PC串口往返时间作为精度判据 |
| F010 | DUT事件输出路由 + Companion FPGA/逻辑分析仪/示波器数字采样 | 需要连续数字波形Observer以证明脉宽 |
| F013 | DUT + DMA Peer + STIMER Request/Channel/Destination映射 | 需要片内DMA配测，不需要外部仪器 |
| F014 | DUT + 当前STIMER Service/Wrap/Driver的单次原子Runtime Status读取 | 不需要外部仪器；基线读取清前序状态，自然Overflow后读取首次现场并复核read-to-clear |
| F018 | DUT + 脉宽配置 + 目标侧原子重复Compare刺激 + 单次原子Runtime Status读取 | 属于软件执行映射缺口，不需要外部仪器 |
| F015 | DUT + 可脚本化Debugger Halt/Resume | 需要真实CPU Halt控制，不可用STIMER Pause命令代替 |
| F016 | DUT + 安全紧急触发源/路由 + 紧急捕获清理Owner | 需要板级或片内安全触发映射 |
| F019 | DUT + 目标侧Pause/Overflow同边界原子触发入口 | 需要确定性目标侧执行映射，不可用PC延时制造竞态 |

当前已接入的示波器可承担F002、F010及部分F019长时观测，但执行前必须由Bench/Profile提供
逻辑信号、物理探头通道、触发电平、探头倍率和安全幅值范围。电源与万用表不能证明STIMER数字
计数、事件脉宽或IRQ语义，因此不作为这些Case的强制资源。
