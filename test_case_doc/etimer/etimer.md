# ETIMER Public Test Contract

> 本文件只定义跨芯片稳定 ETIMER 语义和尚未实现的 Formal Case 计划。芯片实例、寄存器名、IRQ、引脚与 SDK 符号只进入同目录芯片文档。当前所有 Case 均为 PLAN；未执行软件、FPGA 或 HIL，不声明 PASS。

## 0. Stable IP Contract

### 0.1 稳定配置与动作

| 稳定语义 | 公共含义 |
|---|---|
| `channel` | 逻辑 ETIMER 通道；数量由 Capability 给出 |
| `prescaler_divider` | 时基分频系数；范围由 Capability 给出 |
| `period_ticks` / `phase_ticks` | 逻辑周期和相位 Tick |
| `compare_a_ticks` / `compare_b_ticks` | 两个比较门限 |
| `compare_mode` | `COMPARE_A` / `COMPARE_A_AND_B` |
| `capture_event` | `EVENT0..EVENT3` |
| `capture_edge` | `RISING` / `FALLING` |
| `timestamp_mode` | `ABSOLUTE` / `RELATIVE` |
| `capture_mode` | 指定 Event 后 `ONE_SHOT` / `CONTINUOUS` |
| `fault_mode` | `ONE_SHOT` / `CYCLE_BY_CYCLE` |
| `load_mode` | `IMMEDIATE` / `SHADOW` |

后续公共 Driver / Service 至少需要等价动作：`CONFIGURE_TIMEBASE`、`CONFIGURE_COMPARE`、`START/STOP`、`COUNT_GET/LATCH/CLEAR`、`PWM_ENABLE/DISABLE`、`CAPTURE_CONFIGURE/REARM`、`FAULT_CONFIGURE/FORCE/CLEAR`、`IRQ_ENABLE/DISABLE/MASK/UNMASK/FORCE/CLEAR/SNAPSHOT`、`EVENT_CONFIGURE`、`SYNC_CONFIGURE`、`DMA_REQUEST_SELECT`。Timeout 由 PC 统一 deadline 拥有；Cleanup 必须停止本 Case 通道并清理本 Case 产生的 IRQ/Fault/路由状态。

### 0.2 稳定 Observation Endpoint

| Endpoint | 事实与用途 |
|---|---|
| `COUNT.LIVE` / `COUNT.LATCHED` | 计数推进、锁存、清零和终态 |
| `PWM_OUTPUT[channel]` | FPGA/Instrument 测得的周期、占空比、相位与极性 |
| `DEADTIME.A_RISE/B_FALL` | 互补输出边沿间隔 |
| `CAPTURE.EVENT[0..3]` | 捕获计数值；每个事件独立记录 |
| `IRQ_RAW[source]` / `IRQ_STATUS[source]` | Mask 前后中断事实 |
| `IRQ_DELIVERY.LATCHED_SOURCE` | ISR/Service 独立锁存来源，不冒充寄存器 |
| `FAULT.OUTPUT` | Fault 前后硬件输出电平/波形 |
| `SYNC.OUTPUT` | ETIMER/Peer/Observer 看到的同步事件 |
| `DMA_CHANNEL_STATUS` / `DMA_DESTINATION_WORD` | Peer DMA 完成和真实搬运结果 |

## 1. Feature Catalog

| Feature ID | 报告名称 | 公共测试语义 | 主要 Case |
|---|---|---|---|
| ETIMER_F_001 | ETIMER 计数与Latch/Clear | 计数可推进、锁存为稳定快照并可软件清零 | ETIMER_P0_001 |
| ETIMER_F_002 | ETIMER PWM周期/分频/相位 | 分频、周期和相位按配置形成可观测波形 | ETIMER_P1_001, ETIMER_P1_005 |
| ETIMER_F_003 | ETIMER Compare A/B PWM | A或A+B比较模式形成对应占空比/边沿 | ETIMER_P1_001, ETIMER_P1_005 |
| ETIMER_F_004 | ETIMER互补输出与Dead-time | A/B互补输出具有配置的边沿延迟 | ETIMER_P1_002 |
| ETIMER_F_005 | ETIMER四事件Capture | Event0..3按边沿和时间戳模式捕获计数 | ETIMER_P1_003 |
| ETIMER_F_006 | ETIMER Capture Filter/One-shot/Continuous | Filter和触发模式改变可接受事件与停止/回卷行为 | ETIMER_P1_003 |
| ETIMER_F_007 | ETIMER Fault One-shot/CBC | 软件或外部Fault按模式和极性控制输出并可恢复 | ETIMER_P1_002 |
| ETIMER_F_008 | ETIMER IRQ控制与真实投递 | Enable/Mask/Force/Clear保持RAW/STATUS/Delivery来源分层 | ETIMER_P1_004 |
| ETIMER_F_009 | ETIMER Event/Sync跨模块路由 | 周期/比较/事件值可输出到ETIMER或片内Peer | ETIMER_P2_001 |
| ETIMER_F_010 | ETIMER Capture DMA请求 | Capture事件选择DMA请求并形成真实Peer搬运 | ETIMER_P2_002 |

## 2. Case Catalog

| Case ID | P | Case 名称 | 最小充分 Oracle | Resource |
|---|---:|---|---|---:|
| ETIMER_P0_001 | P0 | 计数、Latch与Clear测试 | `COUNT.LIVE`推进，`COUNT.LATCHED`稳定，Clear后归零附近 | R0 |
| ETIMER_P1_001 | P1 | PWM周期、分频、相位与Compare矩阵测试 | 外部`PWM_OUTPUT`周期/占空比/相位匹配独立计算 | R4 |
| ETIMER_P1_002 | P1 | 互补Dead-time与Fault模式测试 | A/B边沿间隔及Fault前后输出满足模式/极性 | R4 |
| ETIMER_P1_003 | P1 | 四事件Capture、Filter与触发模式测试 | Capture值匹配独立刺激时序，One-shot/Continuous行为正确 | R2 |
| ETIMER_P1_004 | P1 | IRQ Enable/Mask/Force/Clear与Delivery测试 | RAW、STATUS和ISR锁存来源分别闭合 | R0 |
| ETIMER_P1_005 | P1 | Immediate/Shadow周期与Compare加载测试 | 外部波形证明新值的实际生效边界 | R4 |
| ETIMER_P2_001 | P2 | Event/Sync跨模块路由测试 | Peer或数字Observer确认正确来源和时刻 | R2 |
| ETIMER_P2_002 | P2 | Capture事件触发DMA搬运测试 | DMA完成且Destination等于捕获Golden | R2 |

## 3. Machine-readable Case Contract

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P0_001
case_name: ETIMER计数、Latch与Clear测试
report_feature: |-
  1. ETIMER 计数与Latch/Clear
p_level: P0
feature_refs: [ETIMER_F_001]
method:
  inputs:
    - 时基配置：选择Capability内合法divider和足够长period，避免观察窗内自然回卷。
  steps:
    - 初始清理：停止目标逻辑通道并清除历史IRQ、Fault和计数状态。
    - 时基配置：配置合法divider和period后启动计数。
    - 推进采样：在两个有界时刻读取COUNT.LIVE形成before和after。
    - 计数锁存：执行Latch并读取COUNT.LATCHED，再次读取确认快照稳定。
    - 计数清零：执行Clear并读取COUNT.LIVE确认回到零附近。
    - 结果比较：比较推进Delta、锁存稳定性和Clear终态。
    - 结果汇总：保存原始计数Observation和动作时间Measurement。
  observations:
    - 实时计数：读取COUNT.LIVE，期望启动后after大于before；证明计数推进。
    - 锁存计数：读取COUNT.LATCHED两次值相同；证明单次Latch快照稳定。
    - 清零终态：Clear后读取COUNT.LIVE接近零且随后继续推进；证明Clear生效。
  pass_criteria:
    - 计数推进：after严格大于before且未发生非预期回卷。
    - 锁存稳定：同一次Latch后的两次COUNT.LATCHED严格相等。
    - 清零有效：Clear后COUNT.LIVE位于统一容差并重新推进。
timeout: 使用ETIMER统一有界deadline，禁止无界轮询
cleanup: [停止目标通道并清除本Case产生的IRQ和计数状态。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 通用DUT板, bench: DUT计数端点}
backend: [FPGA, Silicon]
evidence: [COUNT.LIVE与COUNT.LATCHED原子Observation和Canonical Result]
failure_observations:
  - {key: live_counts, label: 实时计数序列, source: dut, role: actual, format: text, semantic_ref: etimer.feature.counter}
  - {key: latched_count, label: 锁存计数, source: dut, role: actual, format: hex32, semantic_ref: etimer.feature.counter}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P1_001
case_name: ETIMER PWM周期、分频、相位与Compare矩阵测试
report_feature: |-
  1. ETIMER PWM周期/分频/相位
  2. ETIMER Compare A/B PWM
p_level: P1
feature_refs: [ETIMER_F_002, ETIMER_F_003]
method:
  inputs:
    - 参数矩阵：覆盖代表性divider、period、phase、COMPARE_A和COMPARE_A_AND_B节点。
    - 独立预期：由输入时钟和逻辑参数计算Expected周期、占空比与相位差。
  steps:
    - 资源准备：绑定可测量目标PWM输出的Instrument并确认采样率充足。
    - 参数配置：停止通道后配置当前divider、period、phase和compare参数。
    - 波形启动：使能PWM、计数器和目标逻辑通道并等待稳定窗口。
    - 波形采集：由Instrument采集多个完整周期的边沿时间戳。
    - 预期计算：按逻辑时钟和配置计算周期、占空比与相位Expected。
    - 单点比较：比较当前参数节点的Actual与Expected并记录容差来源。
    - 矩阵汇总：全部参数节点执行后汇总覆盖和决定性Evidence。
  observations:
    - PWM输出波形：读取PWM_OUTPUT[channel]边沿时间戳，期望周期和占空比匹配独立计算；证明PWM数据路径。
    - PWM相位关系：比较参考与目标通道边沿差，期望匹配phase_ticks；证明相位配置。
  pass_criteria:
    - 矩阵完整：计划参数节点全部执行且无缺失。
    - 周期正确：每个节点实测周期在声明容差内等于Expected。
    - 占空比正确：A和A+B模式实测边沿关系分别匹配compare配置。
    - 相位正确：多通道相位差在声明容差内匹配phase_ticks。
timeout: 每个节点至少采集三个完整周期并受统一deadline约束
cleanup: [停止全部参与通道并释放Instrument路由。]
resources: {minimum_level: R4, full_coverage_level: R4, board: 暴露目标PWM输出, bench: 逻辑分析仪或等价数字Instrument}
backend: [FPGA, Silicon]
evidence: [参数Measurement、PWM_OUTPUT原子Observation和绑定波形Artifact]
failure_observations:
  - {key: measured_period, label: 实测PWM周期, source: instrument, role: actual, format: decimal, semantic_ref: etimer.feature.pwm}
  - {key: measured_duty, label: 实测PWM占空比, source: instrument, role: actual, format: decimal, semantic_ref: etimer.feature.pwm}
gap: [case_implementation_gap, instrument_bench_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P1_002
case_name: ETIMER互补Dead-time与Fault模式测试
report_feature: |-
  1. ETIMER互补输出与Dead-time
  2. ETIMER Fault One-shot/CBC
p_level: P1
feature_refs: [ETIMER_F_004, ETIMER_F_007]
method:
  inputs:
    - 输出配置：选择互补A/B、代表性上升/下降延迟、Fault极性及ONE_SHOT/CYCLE_BY_CYCLE模式。
  steps:
    - 资源准备：绑定A/B双路数字Instrument和安全可控Fault刺激源。
    - PWM配置：配置基础PWM、互补选择和A/B边沿延迟后启动输出。
    - Dead-time采集：采集A/B多个边沿并测量非重叠间隔。
    - Fault施加：分别在两种Fault模式下施加一次安全刺激。
    - Fault观测：采集Fault期间输出电平、恢复时刻和相关状态。
    - 结果比较：比较Dead-time与配置，并比较两种Fault生命周期。
    - 结果汇总：保存刺激身份、波形Artifact和模式判定。
  observations:
    - 互补边沿间隔：测量DEADTIME.A_RISE/B_FALL，期望匹配配置且A/B无重叠导通。
    - Fault输出波形：采集FAULT.OUTPUT，期望极性和ONE_SHOT/CBC恢复行为符合模式。
  pass_criteria:
    - Dead-time正确：两个方向实测非重叠间隔均在声明容差内。
    - Fault极性正确：Fault有效期间输出保持配置的安全电平。
    - Fault模式正确：ONE_SHOT需显式Clear恢复，CBC按周期条件恢复。
timeout: 每种Fault模式均受统一deadline和安全刺激窗口约束
cleanup: [撤销Fault刺激，清Fault状态，停止PWM并恢复输出路由。]
resources: {minimum_level: R4, full_coverage_level: R4, board: 暴露互补输出与Fault输入, bench: 双路数字Instrument和安全Fault刺激}
backend: [FPGA, Silicon]
evidence: [Dead-time/Fault波形Observation和绑定Artifact]
failure_observations:
  - {key: deadtime_edges, label: 互补边沿间隔, source: instrument, role: actual, format: text, semantic_ref: etimer.feature.deadtime}
  - {key: fault_output, label: Fault期间输出, source: instrument, role: actual, format: text, semantic_ref: etimer.feature.fault}
gap: [case_implementation_gap, fault_bench_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P1_003
case_name: ETIMER四事件Capture、Filter与触发模式测试
report_feature: |-
  1. ETIMER四事件Capture
  2. ETIMER Capture Filter/One-shot/Continuous
p_level: P1
feature_refs: [ETIMER_F_005, ETIMER_F_006]
method:
  inputs:
    - 刺激矩阵：由片内Peer产生已知周期/脉宽和可控毛刺，覆盖四事件边沿、相对/绝对时间戳和两种模式。
  steps:
    - Peer准备：配置独立片内波形源并计算各事件Expected tick。
    - Capture配置：配置输入源、prescaler、四事件边沿、timestamp、filter和模式。
    - 状态清理：清Capture和IRQ历史状态后使能Capture与Timer。
    - 刺激启动：启动Peer并等待指定事件或One-shot终态。
    - Capture读取：逐项读取CAPTURE.EVENT[0..3]和对应IRQ来源。
    - Filter复核：加入低于/高于阈值的毛刺并比较接受结果。
    - 模式复核：比较One-shot停止与Continuous后续事件更新行为。
    - 结果汇总：保存全部事件原始值、Expected和来源身份。
  observations:
    - 四事件计数：分别读取CAPTURE.EVENT[0..3]，期望与Peer时序换算值一致；证明边沿捕获。
    - Capture投递：读取对应IRQ_RAW及ISR锁存Source，期望事件来源一致。
  pass_criteria:
    - Capture数值正确：四个事件值均在时钟量化容差内匹配Expected。
    - Filter行为正确：阈值内毛刺被拒绝而有效脉冲被接受。
    - 模式行为正确：One-shot在目标事件后停止，Continuous继续更新后续事件。
timeout: 按Peer最长周期和事件数计算统一有界deadline
cleanup: [停止Peer和Capture，清除Capture/IRQ状态并恢复路由。]
resources: {minimum_level: R2, full_coverage_level: R2, board: 无额外外部接线, bench: 片内独立Peer波形源}
backend: [FPGA, Silicon]
evidence: [Peer参数Measurement、四事件Observation和IRQ来源Evidence]
failure_observations:
  - {key: capture_events, label: 四事件捕获值, source: dut, role: actual, format: text, semantic_ref: etimer.feature.capture}
gap: [case_implementation_gap, capture_peer_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P1_004
case_name: ETIMER IRQ Enable、Mask、Force、Clear与Delivery测试
report_feature: |-
  1. ETIMER IRQ控制与真实投递
p_level: P1
feature_refs: [ETIMER_F_008]
method:
  inputs:
    - 中断矩阵：遍历Fault、CompareA/B、Period、Overflow和Capture Event等Capability声明来源。
  steps:
    - 初始清理：禁用并清除全部目标Source，重置ISR latch和event_count。
    - Enable验证：Enable目标Source并以Force或自然事件触发。
    - RAW读取：在Clear前读取IRQ_RAW[source]并保存原始pending。
    - STATUS读取：分别在Unmask和Mask条件读取IRQ_STATUS[source]。
    - Delivery读取：读取ISR锁存Source和event_count，保持与寄存器事实分层。
    - Clear验证：Clear目标Source并复核RAW/STATUS消失且其他Source不受影响。
    - Disable验证：Disable后重新刺激并确认无有效Delivery。
    - 矩阵汇总：逐Source保存全部状态转换和决定性Evidence。
  observations:
    - IRQ原始状态：读取IRQ_RAW[source]，期望刺激后为1且Clear后为0。
    - IRQ有效状态：读取IRQ_STATUS[source]，期望Unmask有效而Mask抑制。
    - IRQ真实投递：读取IRQ_DELIVERY.LATCHED_SOURCE和event_count，期望来源与目标一致。
  pass_criteria:
    - Source隔离：仅目标Source发生预期状态转换。
    - Mask语义正确：Mask不伪造RAW且抑制STATUS/Delivery。
    - Clear语义正确：目标Source清除且不误清其他Source。
    - Delivery真实：Unmask+Enable时形成真实ISR锁存，Disable后不投递。
timeout: 每个Source使用统一IRQ deadline
cleanup: [Disable并Clear全部本Case中断Source，恢复NVIC/Service状态。]
resources: {minimum_level: R0, full_coverage_level: R2, board: 通用DUT板, bench: 自然事件Source可由片内Peer补充}
backend: [FPGA, Silicon]
evidence: [IRQ_RAW/STATUS原子Observation、ISR latch和event_count Measurement]
failure_observations:
  - {key: irq_snapshot, label: IRQ RAW与STATUS快照, source: dut, role: actual, format: text, semantic_ref: etimer.feature.irq}
gap: [case_implementation_gap, irq_service_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P1_005
case_name: ETIMER Immediate与Shadow周期/Compare加载测试
report_feature: |-
  1. ETIMER PWM周期/分频/相位
  2. ETIMER Compare A/B PWM
p_level: P1
feature_refs: [ETIMER_F_002, ETIMER_F_003]
method:
  inputs:
    - 加载矩阵：使用old/new period和compare，分别覆盖IMMEDIATE与SHADOW更新。
  steps:
    - 波形准备：配置old参数并启动稳定PWM输出。
    - 基线采集：采集更新前至少两个完整周期作为old波形基线。
    - 新值写入：在周期中部写入new period/compare并选择当前加载模式。
    - 生效触发：IMMEDIATE执行加载动作，SHADOW等待定义的更新边界。
    - 连续采集：跨越更新点连续采集完整边沿序列。
    - 边界定位：从波形确定首个new参数周期及其前一完整周期。
    - 模式比较：比较Actual生效点与各模式定义的Expected边界。
    - 结果汇总：保存更新命令身份、边沿和模式结论。
  observations:
    - 更新边界波形：读取PWM_OUTPUT[channel]连续边沿，期望IMMEDIATE与SHADOW在各自边界生效。
  pass_criteria:
    - 旧周期完整：更新前最后一个old周期没有被非预期截断。
    - Immediate正确：新值在定义的立即加载边界开始影响输出。
    - Shadow正确：新值仅在定义的Shadow边界开始影响输出。
timeout: 覆盖更新前后各至少两个周期并受统一deadline约束
cleanup: [停止PWM并恢复period、compare和load模式。]
resources: {minimum_level: R4, full_coverage_level: R4, board: 暴露PWM输出, bench: 连续数字Instrument}
backend: [FPGA, Silicon]
evidence: [连续波形Artifact和更新边界Observation]
failure_observations:
  - {key: update_edges, label: 加载前后PWM边沿, source: instrument, role: actual, format: text, semantic_ref: etimer.feature.shadow_load}
gap: [case_implementation_gap, instrument_bench_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P2_001
case_name: ETIMER Event与Sync跨模块路由测试
report_feature: |-
  1. ETIMER Event/Sync跨模块路由
p_level: P2
feature_refs: [ETIMER_F_009]
method:
  inputs:
    - 路由矩阵：覆盖Period、Zero、CompareA/B和EventCount到ETIMER及可用片内Peer的路由。
  steps:
    - Capability确认：解析目标支持的Source、Destination和安全Peer组合。
    - Source配置：配置短周期、compare或event值并使能目标事件输出。
    - Peer准备：配置目标Peer或数字Observer等待指定Source。
    - 路由启动：启动ETIMER并在统一deadline内等待目标事件。
    - Source观测：读取ETIMER事件相关状态或输出端点。
    - Destination观测：读取Peer硬件终态或Observer时间戳。
    - 来源隔离：切换另一个Source并确认Destination只响应所选来源。
    - 结果汇总：保存Source/Destination身份和时序Evidence。
  observations:
    - 同步输出事件：观察SYNC.OUTPUT的Source和时间戳，期望与配置事件一致。
    - Peer响应终态：读取Peer独立硬件端点，期望只响应所选ETIMER Source。
  pass_criteria:
    - 路由正确：每个矩阵节点的Source与Destination身份匹配配置。
    - 时刻正确：Peer响应发生在选定Period/Compare/Event边界。
    - 来源隔离：未选择的Source不产生目标Peer响应。
timeout: 按最大ETIMER周期和Peer响应时间计算统一deadline
cleanup: [停止ETIMER并撤销本Case创建的Event/Sync/Peer路由。]
resources: {minimum_level: R2, full_coverage_level: R3, board: 目标Peer可用, bench: 片内Peer；全覆盖可用FPGA数字Observer}
backend: [FPGA, Silicon]
evidence: [Source状态、Peer端点Observation和路由配置Measurement]
failure_observations:
  - {key: sync_route, label: Event与Peer响应, source: observer, role: actual, format: text, semantic_ref: etimer.feature.sync}
gap: [case_implementation_gap, peer_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIMER_P2_002
case_name: ETIMER Capture事件触发DMA搬运测试
report_feature: |-
  1. ETIMER Capture DMA请求
p_level: P2
feature_refs: [ETIMER_F_010]
method:
  inputs:
    - DMA矩阵：选择代表性Capture Event和已知Peer波形，预置独立DMA Destination哨兵值。
  steps:
    - 资源准备：配置Peer波形、空闲DMA Channel和隔离Destination缓冲区。
    - Capture配置：配置目标Event并计算Expected capture tick。
    - DMA配置：选择对应ETIMER请求源，配置Source、Destination和单次搬运长度。
    - 哨兵确认：读取Destination确认尚未被修改后使能DMA和Capture。
    - 刺激启动：启动Peer并等待DMA硬件完成或错误终态。
    - 结果读取：读取DMA_CHANNEL_STATUS、Destination和Capture寄存器值。
    - 结果比较：比较Destination、Capture Actual与独立Expected。
    - 结果汇总：保存请求Source、DMA终态和搬运Evidence。
  observations:
    - DMA硬件终态：读取DMA_CHANNEL_STATUS，期望完成且无错误；证明Peer DMA真实执行。
    - DMA目标数据：读取DMA_DESTINATION_WORD，期望等于同次Capture值和独立Golden。
  pass_criteria:
    - 请求闭合：目标Capture Event在deadline内驱动DMA完成。
    - 搬运正确：Destination不再是哨兵且严格等于Capture Actual。
    - 数值正确：Capture Actual在时钟量化容差内匹配Peer Expected。
timeout: 按Peer最长周期与DMA统一deadline执行
cleanup: [停止DMA和Capture，清除请求/IRQ状态并释放Destination。]
resources: {minimum_level: R2, full_coverage_level: R2, board: 通用DUT板, bench: 片内Peer波形源和DMA资源}
backend: [FPGA, Silicon]
evidence: [DMA状态、Destination、Capture Observation和Canonical Result]
failure_observations:
  - {key: dma_status, label: DMA通道终态, source: peer, role: actual, format: text, semantic_ref: etimer.feature.dma_request}
  - {key: dma_destination, label: DMA目标数据, source: peer, role: actual, format: hex32, semantic_ref: etimer.feature.dma_request}
gap: [case_implementation_gap, dma_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Adaptation | Case Adaptation | 结论 | Chip Document |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=9; MAPPING_GAP=1 | IMPLEMENTATION_GAP=4; MAPPING_GAP=2; BENCH_GAP=2 | 硬件/SDK/历史测试存在，但 ATP Driver/Service/Case/Capability/Bench 尚未接入 | `ET6801_etimer.md` |

## 5. Common Gap / Evolution

- 当前 8 个 Case 全部为 `ET_CASE_PLAN`，不存在 ATP Formal Case、Registry、PC Driver 或 Firmware Service 实现。
- 外部波形、Fault、Event/Sync 与 DMA Case 必须先完成 Capability、Bench 与 Execution Mapping，未执行不得写成 PASS。
- 历史 SDK 测试只提供设计输入，不能替代当前 SHA 的 Canonical Evidence。
