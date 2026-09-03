# IPCM Stable IP Contract

> 本文件定义 IPCM 的芯片中立 Feature、Case、Oracle、Observation、资源和稳定自动化动作。
> 芯片实例、Core 数量、Mailbox/Channel 数量、寄存器、IRQn、SDK API 和部署地址只进入同目录 `<CHIP>_ipcm.md`。
> 更新：2026-09-03。当前 13 个 Case 均为 `ET_CASE_PLAN / PLANNED`，不是已注册的 Formal Case；文档完成不等于代码实现或硬件 PASS。

## 0. Stable IP Contract

### 0.1 稳定对象与配置语义

| 稳定对象 | 公共语义 | 约束 |
|---|---|---|
| `mailbox_id` | 独立 IPCM Mailbox 资源编号 | 合法范围由 `mailbox_count` 决定，公共 Case 不写死最大编号。 |
| `source_endpoint` | 消息发起执行实体及其 ACK 事件通道 | 由 Capability/Execution Mapping 映射到目标 Core 和硬件 Channel。 |
| `destination_endpoints` | 一个或多个消息接收执行实体及事件通道 | 使用逻辑 Endpoint 集合表达，不暴露目标 Channel 位图。 |
| `ack_mode` | `MANUAL` / `AUTO` | `MANUAL` 由接收端显式发送 ACK；`AUTO` 允许释放目标路由触发 ACK，也可在能力支持时显式发送 ACK。两种触发动作分开测试。 |
| `link_mode` | `SINGLE` / `LINKED` | `LINKED` 使用连续 Mailbox 组成一条消息链，合法长度由 Capability 给出。 |
| `irq_delivery` | `IRQ` / `POLLING` | `IRQ` 观察 Raw、Masked 和回调计数；`POLLING` 只允许 Raw 置位，不得投递 IRQ。 |
| `payload` | 不透明二进制字节序列 | 单 Mailbox 和 Linked 最大字节数由 Capability 发布；公共层禁止静默截断。 |
| `peer_role` | `INITIATOR` / `RESPONDER` | 逻辑角色与 Core 编号解耦；双向 Case 可交换角色。 |

### 0.2 稳定 Observation 与 Measurement

| Endpoint | 来源 | 原子事实 |
|---|---|---|
| `CAPABILITY.MAILBOX_COUNT` | `dut` | 当前 IPCM 实现的 Mailbox 数量。 |
| `CAPABILITY.CHANNEL_COUNT` | `dut` | 当前 IPCM 实现的事件通道数量。 |
| `CAPABILITY.DATA_WORD_COUNT` | `dut` | 单 Mailbox 数据寄存器字数。 |
| `MAILBOX.SOURCE_ENDPOINTS` | `dut` | 当前 Mailbox 已配置的 Source Endpoint 集合。 |
| `MAILBOX.DESTINATION_ENDPOINTS` | `dut` | 当前 Mailbox 尚未释放的 Destination Endpoint 集合。 |
| `MAILBOX.ACK_MODE` | `dut` | 当前 Manual/Auto ACK 配置。 |
| `MAILBOX.LINK_MODE` | `dut` | 当前 Single/Linked 配置。 |
| `MAILBOX.IRQ_ENABLED_ENDPOINTS` | `dut` | 当前启用中断投递的 Endpoint 集合；硬件命名为 Mask 时仍发布 Enable 语义。 |
| `CHANNEL.RAW_PENDING_MAILBOXES` | `dut` | 指定逻辑事件通道的 Raw Pending Mailbox 位集合。 |
| `CHANNEL.MASKED_PENDING_MAILBOXES` | `dut` | 指定逻辑事件通道经过 Enable/Mask 后的 Pending Mailbox 位集合。 |
| `MESSAGE.RECEIVED_PAYLOAD` | `peer` | Peer 实际收到的 Payload。 |
| `ACK.RECEIVED_PAYLOAD` | `dut` | Initiator 实际收到的 ACK Payload。 |

`IRQ.CALLBACK_COUNT`、`PEER_JOB.STATE`、`PEER_JOB.EVENT_COUNT`以及`MESSAGE/ACK.RECEIVED_LENGTH`是软件回报，记录为Measurement，不代表硬件长度或计数寄存器；Payload是从数据端口读取的硬件Observation。Raw/Masked按实际读取端归属`dut`或`peer`，Peer必须提供device_id，不能把两端快照合成一个硬件值。

### 0.3 稳定自动化动作

| 稳定动作 | 请求语义 | 约束 |
|---|---|---|
| `capabilities_get` | 获取 Mailbox、Channel、Data Word、模式、Linked 和 Multi-destination 能力 | 只发布目标硬件事实，不发布测试实现程度。 |
| `mailbox_configure` | 配置 Source、Destination、ACK、Link 和 IRQ Delivery | 输入使用逻辑 Endpoint；目标映射由 Chip Profile 完成。 |
| `mailbox_release` | 释放指定 Mailbox 或连续 Mailbox 链 | 释放后必须通过硬件快照确认配置和 Pending 状态恢复。 |
| `mailbox_snapshot_get` | 获取 Mailbox 稳定配置和路由状态 | 返回稳定逻辑值，不暴露芯片寄存器类型。 |
| `channel_pending_snapshot_get` | 获取指定 Endpoint 当前的 Raw/Masked Pending Mailbox 位集合 | 返回完整位集合；这是即时读回，不可冒充已被清除的历史事件。 |
| `event_snapshot_get` | 取回接收或IRQ入口保存的Raw/Masked和Payload快照 | 快照须标识Mailbox、Endpoint和消息/ACK阶段；读取不得重新触发硬件动作。 |
| `message_send` | 从 Initiator 向 Destination 发送一条有界消息 | 超过容量必须返回明确错误，禁止静默截断。 |
| `message_receive` | 读取指定 Mailbox 的有效 Payload | 长度由 Case/Peer Job 明确传入并原样回报。 |
| `ack_send` | 显式发送ACK，可选择原样返回或替换ACK Payload | 用于MANUAL；能力`explicit_ack_in_auto`支持时也用于AUTO，不得擅自改为MANUAL或先释放Destination。 |
| `destination_release` | 清除指定 Destination Endpoint | `AUTO` 模式下用于触发 Auto ACK；多目标时逐个释放并观测。 |
| `interrupt_clear` | 只清除当前消息/ACK Pending | 不得隐式释放 Destination 或触发未请求的 Auto ACK。 |
| `peer_job_start/status/result/abort` | 在片内 Peer 上异步执行接收、ACK、双向、Linked 或多目标动作 | PC 控制通道保持响应；Job 必须有 ACK、deadline 和可终止语义。 |

### 0.4 Oracle、Timeout 与隔离

- 每个Case在第一次配置前停止上一Peer Job并关闭其IPCM事件处理，再由PC调用CRG Driver复位IPCM实例，随后清除两端IPCM Service状态并复位Resource Pool；任何一步失败立即终止。IPCM Wrap不得调用CRG Driver，Mailbox释放不能代替IP硬件复位。
- IPCM 功能 Case 必须使用真实片内 Peer；同一 Core 内两个 Channel 的自发自收只能用于诊断，不能证明 Core 间通信。
- 所有等待由 PC 持有统一 Case deadline；Firmware 同步命令只做一次原子动作，Peer 接收和多阶段 ACK 放入异步 Job。
- 不能以API返回成功或固定sleep代替硬件证据；按Case Oracle记录Pending、Payload和对应事件。纯Polling或无ACK场景不得要求不存在的回调或ACK。
- `POLLING` 的通过条件是 Raw Pending 置位、Masked Pending 为 0、IRQ Callback 不增加且数据可读。
- `AUTO`的自动触发必须同时验证正反条件：未调用显式ACK时，释放Destination产生ACK，只清消息中断不产生ACK。AUTO下显式ACK另由P1_008验证。
- Linked Case区分N次Destination消息与1次Source链尾ACK：前N-1次接收端ACK动作只推进下一Mailbox，最后一次才向Source投递ACK；禁止要求Source收到N次ACK，也禁止只看链尾而不核对所有片段。
- Multi-destination Case 必须确认每个 Destination 独立收到消息；只释放一个 Destination 时其他 Destination 状态必须保持。
- Formal Case只调用IPCM Driver、用于基线的CRG Driver、Capability/Resource Fixture和Canonical Evidence；不直接访问Codec、Transport或寄存器。
- Firmware Service 只校验当前命令、调用 IPCM Wrap 并编码原始事实，不实现 Case 流程或通过判定。
- Cleanup 只需 Abort Peer Job、释放测试 Mailbox、复位 IPCM 实例和 Resource Pool；下一 Case 仍重新建立完整基线。
- 参数矩阵中的每个Payload长度或Mailbox ID必须形成独立且稳定的`parameter_id`；不得把多个参数分支隐藏在Case内部循环后只输出一份不可定位的结果。
- Raw Pending、Masked Pending、Mailbox配置、Payload和Service回调计数是不同事实，必须分别记录；Service回调计数属于Measurement，不得标成硬件寄存器Observation。
- 人读报告每个Case只选择1～4项最小充分事实。完整Payload、全Mailbox矩阵和全链成员明细进入绑定Artifact，不得直接展开到Excel备注。
- 长Payload的人读字段只保留实际长度、数据一致性、首个错误偏移和必要摘要；完整字节序列始终保留在Canonical Result或Artifact中。

### 0.5 固定输入与事件采样时序

- `C`为单Mailbox字节容量，`N`为本Case链成员数；`P(n,s)[i]=(s+37*i)&0xff`，`0<=i<n`。短Payload长度`L=min(7,C)`，选择的长度须在Capability范围内。案例中的种子用于区分方向或轮次，不是芯片配置。
- 未单列配置的消息Case使用SINGLE、MANUAL和IRQ；Source/Destination各一个逻辑Endpoint，两个不同Core执行。每轮只由一个端配置共享Mailbox，Peer Ready后才允许发送；Peer不重复初始化同一Mailbox。
- IRQ入口先保存Raw、Masked、Mailbox身份和有效Payload，再按PC指定的原子动作清中断、显式ACK或释放Destination。需要PC分步确认时先暂停该Endpoint的IRQ投递、保留快照，防止同一level Pending重复计数；不能先清状态再补读。Payload比较和PASS判定只在PC。
- Source ACK入口同样先保存Raw/Masked和ACK Payload，再清ACK。后续PC读取`event_snapshot_get`得到事件发生时快照，`channel_pending_snapshot_get`得到清除后的即时终态；两种证据的阶段和key不能混用。
- Polling不进入ISR；Peer按PC指令在clear/ack/release之前保存完整Raw/Masked和Payload。多Pending场景待PC明确允许后才开始消费，不用固定延时“碰运气”。
- 未发生ACK的反向观测窗口为PC单调时钟100 ms，计入Case总deadline；结束后核对Source即时Raw/Masked及回调增量均为0。窗口不能用来宣称永久不会ACK。
- 多目标路由使用MANUAL：两个Destination先独立收包，再分别释放，最后显式ACK。未确认的多目标AUTO聚合触发条件不混入这条Case的Oracle；在芯片文档列为待确认语义，不宣称已覆盖。

### 0.6 IPCM V1原子命令与事件接口

Service ID=`0x0109`，API Version=`1`。只新增IPCM命令体，外层ET-Frame及其他IP命令不变。所有整数Little Endian，保留字段必须为0；`u16/u32`表示位宽，`bytes`表示原始数据。

| 命令 | ID | 请求 | 响应 |
|---|---|---|---|
| CAPABILITIES_GET | 0x0001 | 空 | 8个u16：API版本、结构长度、Mailbox数、Channel数、Data Word数、每Mailbox字节数、Capture Slot数、每Slot字节上限 |
| CONFIGURE | 0x0002 | first/count:u16，source/destination/irq_enabled逻辑Endpoint集合:u32，ack/link:u8，reserved:u16 | 空 |
| MAILBOX_RELEASE | 0x0003 | first/count:u16 | 空 |
| MAILBOX_SNAPSHOT_GET | 0x0004 | mailbox:u16 | source/destination/irq_enabled逻辑集合:u32，ack/link:u8，reserved:u16 |
| PENDING_SNAPSHOT_GET | 0x0005 | endpoint:u16 | raw/masked:u32，完整Mailbox位集合 |
| PAYLOAD_WRITE | 0x0006 | first/count/length:u16 + length个bytes | 空；只准备数据，不SEND |
| PAYLOAD_READ | 0x0007 | mailbox/length:u16 | length个bytes；不ACK、不清除 |
| MESSAGE_SEND | 0x0008 | mailbox:u16 | 空 |
| ACK_SEND | 0x0009 | mailbox:u16 | 空；显式ACK，不改ACK模式、不隐式释放Destination |
| INTERRUPT_CLEAR | 0x000A | mailbox:u16 | 空；不ACK |
| DESTINATION_RELEASE | 0x000B | mailbox/endpoint:u16 | 空；AUTO ACK是否产生由硬件决定 |
| CAPTURE_ARM | 0x0010 | slot/endpoint/mailbox/length:u16，irq/stage:u8 | 空；一次有界采样会话，irq=0 Polling / 1 IRQ，stage=0 MESSAGE / 1 ACK |
| CAPTURE_GET | 0x0011 | slot:u16 | 下述42字节事件头 + 有效Payload |
| CAPTURE_ABORT | 0x0012 | slot:u16 | 空；关闭本IP投递并解绑，不清Mailbox、不ACK |
| STATE_RESET | 0x0013 | 空 | 空；Abort所有Slot后清Service观测，不复位IP、不清资源池 |

事件头依次为`generation/raw_status/masked_status/latched_events/event_count/unexpected_count/overflow_count/fault_flags:u32`和`endpoint/mailbox/length/state/stage:u16`。`state=0 IDLE / 1 WAITING / 2 READY / 3 FAULT`。只有READY携带有效Payload；未完成或FAULT返回length=0，不冒充有效观测。`event_count`只计真实IRQ回调，Polling为0。`stage`由PC显式标注，不能当作硬件状态。

`ACK MANUAL=0/AUTO=1`、`LINK SINGLE=0/LINKED=1`；集合bit n代表逻辑Endpoint n，不是物理Channel n，物理映射仅由Chip Config提供。`count`始终包括首Mailbox，参数不满足容量或实际链结构时失败，禁止截断。

Capture的4个Slot、每Slot128字节是Service软件预算，不是芯片Feature；PC必须分别核对硬件容量和服务执行上限。IRQ入口先保存Raw/Masked及Payload，再暂停本Endpoint的投递以保留Raw，随后由PC单独执行ACK、Clear或Release。GET不会重读硬件覆盖旧事件；下一次ARM递增generation，STATE_RESET保留代次以识别旧数据。IRQ会话只由Service经IRQ Manager注册。Polling仅在显式ARM后做一次非阻塞采样，不擅自消费其他Pending。

当前这些为本核原子执行接口；跨核Peer提交/结果接口尚未接入，不得据此把同核双Channel诊断宣称为真实双核Case。13条PLAN仍保持PLANNED，待Peer、Capability、PC和Smoke闭环后按同一语义落实SPEC。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联 Case |
|---|---|---|---|
| IPCM_F_001 | IPCM Mailbox、Channel与Payload容量 | 硬件可报告 Mailbox、事件 Channel 和单 Mailbox Data Word 数量。 | `IPCM_P0_001`, `IPCM_P1_004` |
| IPCM_F_002 | IPCM Source与Destination路由 | Mailbox 可将 Source ACK 和消息分别路由到配置的逻辑 Endpoint。 | `IPCM_P0_001`, `IPCM_P0_002`, `IPCM_P1_004`, `IPCM_P1_005` |
| IPCM_F_003 | IPCM单Mailbox变长Payload | 单 Mailbox 可传输目标声明容量内的二进制 Payload。 | `IPCM_P0_002`, `IPCM_P2_003` |
| IPCM_F_004 | IPCM消息与ACK中断状态 | 消息和 ACK 到达时产生对应 Raw/Masked Pending 和 IRQ 回调。 | `IPCM_P0_002`, `IPCM_P1_003` |
| IPCM_F_005 | IPCM IRQ与Polling模式 | 同一事件可选择 IRQ 投递或仅通过 Raw Pending 轮询处理。 | `IPCM_P1_003` |
| IPCM_F_006 | IPCM Manual ACK原Payload返回 | Responder 可显式 ACK，Initiator 收到原 Payload。 | `IPCM_P0_002` |
| IPCM_F_007 | IPCM Manual ACK Payload更新 | Responder 可在 ACK 前替换 Payload，Initiator 收到更新值。 | `IPCM_P1_001` |
| IPCM_F_008 | IPCM Auto ACK触发条件 | 不调用显式ACK时，Destination释放触发Auto ACK，单纯清消息中断不触发。 | `IPCM_P1_002` |
| IPCM_F_009 | IPCM双向Core间消息 | 两个片内执行实体可通过两个独立 Mailbox 双向交换消息。 | `IPCM_P1_005` |
| IPCM_F_010 | IPCM多Mailbox独立Pending | 多个 Mailbox 可同时 Pending，完整位集合可被识别并逐个处理。 | `IPCM_P1_006` |
| IPCM_F_011 | IPCM Mailbox释放与复用 | Mailbox 释放后配置和 Pending 恢复，可重新配置并再次传输。 | `IPCM_P0_001`, `IPCM_P1_004` |
| IPCM_F_012 | IPCM Auto Link连续Mailbox传输 | 连续 Mailbox 可在 Manual ACK 策略下组成一条 Linked 消息。 | `IPCM_P2_001` |
| IPCM_F_013 | IPCM Auto ACK Link传输 | 连续 Mailbox 可同时使用 Auto Link 与 Auto ACK。 | `IPCM_P2_002` |
| IPCM_F_014 | IPCM Multi-destination路由 | 一条消息可路由到多个 Destination Endpoint，并由各端独立释放。 | `IPCM_P1_007` |
| IPCM_F_015 | IPCM同Mailbox连续分段传输 | 同一 Mailbox 可在多轮 ACK 后连续复用并重组长消息。 | `IPCM_P2_003` |
| IPCM_F_016 | IPCM Auto ACK模式显式ACK | AUTO配置保持不变，Responder不释放Destination，直接发送显式ACK。 | `IPCM_P1_008` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---:|---|---|---|---:|---|
| IPCM_P0_001 | P0 | IPCM能力与Mailbox配置读回测试 | 容量、路由、释放 | CFG能力值与Mailbox配置逐项一致，释放后恢复 | R0 | PLANNED |
| IPCM_P0_002 | P0 | IPCM双Core Manual ACK变长Payload测试 | 路由、Payload、IRQ、Manual ACK | 请求与ACK Payload逐字节一致，双端Pending和回调正确 | R2 | PLANNED |
| IPCM_P1_001 | P1 | IPCM Manual ACK Payload更新测试 | ACK Payload更新 | Responder收到请求，Initiator收到指定更新Payload | R2 | PLANNED |
| IPCM_P1_002 | P1 | IPCM Auto ACK触发条件测试 | Auto ACK | 只清中断不ACK，释放Destination后恰好ACK一次 | R2 | PLANNED |
| IPCM_P1_003 | P1 | IPCM IRQ与Polling状态测试 | IRQ、Polling | Polling仅Raw置位；IRQ模式Raw/Masked/Callback均有效 | R2 | PLANNED |
| IPCM_P1_004 | P1 | IPCM全Mailbox释放与复用测试 | 容量、释放复用 | Capability发布的每个Mailbox均可配置、传输、释放、复用 | R2 | PLANNED |
| IPCM_P1_005 | P1 | IPCM双向双Mailbox通信测试 | 双向Core消息 | 两个方向Payload、Mailbox和事件通道均准确且互不串扰 | R2 | PLANNED |
| IPCM_P1_006 | P1 | IPCM多Mailbox同时Pending测试 | 多Mailbox Pending | IRQ关闭时Raw同时含两个Mailbox，Masked=0；逐项清除不影响另一位 | R2 | PLANNED |
| IPCM_P1_007 | P1 | IPCM Multi-destination独立释放测试 | 多目标路由 | 两个Destination均收包，逐个释放时状态独立 | R2 | PLANNED |
| IPCM_P1_008 | P1 | IPCM Auto ACK模式显式ACK测试 | AUTO下显式ACK | 不改AUTO配置、不释放Destination，显式ACK返回原Payload且仅一次 | R2 | PLANNED |
| IPCM_P2_001 | P2 | IPCM Auto Link Manual ACK长Payload测试 | Auto Link | 全链Payload和逐Mailbox事件完整，最终ACK正确 | R2 | PLANNED |
| IPCM_P2_002 | P2 | IPCM Auto ACK Link长Payload测试 | Auto ACK Link | N个Destination顺序收包，Source仅收到一次链尾ACK | R2 | PLANNED |
| IPCM_P2_003 | P2 | IPCM同Mailbox连续分段传输测试 | 连续复用 | 多轮分段无丢失、重复或串包，重组结果一致 | R2 | PLANNED |

## 3. Machine-readable Case Contract

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P0_001
case_name: IPCM能力与Mailbox配置读回测试
report_feature: |-
  1. IPCM Mailbox、Channel与Payload容量
  2. IPCM Source与Destination路由
  3. IPCM Mailbox释放与复用
p_level: P0
feature_refs: [IPCM_F_001, IPCM_F_002, IPCM_F_011]
method:
  inputs:
    - 目标能力：Capability发布的mailbox_count、channel_count和data_word_count。
    - 代表配置：一个合法mailbox_id、不同的Source/Destination Endpoint、MANUAL与SINGLE模式。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool。
    - 能力读取：读取三个硬件配置计数并与Capability比较。
    - Mailbox配置：配置代表Mailbox的Source、Destination、ACK、Link和IRQ Delivery。
    - 配置观测：读取Mailbox硬件快照并逐项比较稳定语义。
    - 释放观测：释放Mailbox并确认Source、Destination、IRQ Enable和Pending均恢复为空。
    - 结果汇总：汇总能力比较、配置比较和释放终态，生成互相独立的Canonical事实。
  observations:
    - 容量寄存器：分别记录CAPABILITY.MAILBOX_COUNT、CAPABILITY.CHANNEL_COUNT和CAPABILITY.DATA_WORD_COUNT，并与Capability期望值逐项比较。
    - 配置字段：分别记录MAILBOX.SOURCE_ENDPOINTS、MAILBOX.DESTINATION_ENDPOINTS、MAILBOX.ACK_MODE、MAILBOX.LINK_MODE和MAILBOX.IRQ_ENABLED_ENDPOINTS。
    - 释放终态：分别记录释放后的Source、Destination、IRQ Enable、Raw Pending和Masked Pending，期望值均为空集合。
  pass_criteria:
    - 能力一致：硬件配置计数与Capability完全一致且均大于0。
    - 配置一致：Mailbox稳定字段与输入逐项一致。
    - 释放完整：释放后配置和Pending均回到空闲基线。
timeout: 5 s
cleanup: [Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [三个容量计数逐项一致, Mailbox配置逐项一致, Mailbox释放终态为空]
failure_observations:
  - {key: actual_mailbox_count, label: CAPABILITY.MAILBOX_COUNT实际值, source: dut, role: actual, format: decimal, semantic_ref: ipcm.limit.mailbox_count}
  - {key: actual_channel_count, label: CAPABILITY.CHANNEL_COUNT实际值, source: dut, role: actual, format: decimal, semantic_ref: ipcm.limit.channel_count}
  - {key: actual_data_word_count, label: CAPABILITY.DATA_WORD_COUNT实际值, source: dut, role: actual, format: decimal, semantic_ref: ipcm.limit.data_word_count}
  - {key: configured_source_endpoints, label: MAILBOX.SOURCE_ENDPOINTS配置值, source: dut, role: actual, format: hex32}
  - {key: configured_destination_endpoints, label: MAILBOX.DESTINATION_ENDPOINTS配置值, source: dut, role: actual, format: hex32}
  - {key: released_source_endpoints, label: 释放后MAILBOX.SOURCE_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: released_destination_endpoints, label: 释放后MAILBOX.DESTINATION_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: released_raw_pending, label: 释放后CHANNEL.RAW_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: released_masked_pending, label: 释放后CHANNEL.MASKED_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, capability_semantic_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P0_002
case_name: IPCM双Core Manual ACK变长Payload测试
report_feature: |-
  1. IPCM Source与Destination路由
  2. IPCM单Mailbox变长Payload
  3. IPCM消息与ACK中断状态
  4. IPCM Manual ACK原Payload返回
p_level: P0
feature_refs: [IPCM_F_002, IPCM_F_003, IPCM_F_004, IPCM_F_006]
method:
  inputs:
    - Payload长度矩阵：1、3、4、单Mailbox容量减1和单Mailbox容量；分别使用length_1、length_3、length_4、length_max_minus_1和length_max作为parameter_id。
    - Payload内容：当前长度n使用P(n,0x11)，按0.5节公式逐字节生成；只保留合法且去重后的长度。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - Peer准备：启动Responder Job，配置目标Mailbox并等待READY。
    - 消息发送：Initiator发送当前parameter_id对应长度的Payload。
    - Responder处理：Peer先锁存消息Raw/Masked和Payload，再显式发送原Payload的Manual ACK。
    - 双端观测：Source先锁存ACK Raw/Masked和Payload再清ACK；PC读取两端事件快照、回调增量及清除后的即时Pending。
    - 结果判定：逐字节比较请求与ACK，并确认每轮事件恰好处理一次。
  observations:
    - 请求数据：分别记录MESSAGE.RECEIVED_LENGTH、MESSAGE.RECEIVED_PAYLOAD和请求数据一致性。
    - Destination事件：分别记录CHANNEL.RAW_PENDING_MAILBOXES、CHANNEL.MASKED_PENDING_MAILBOXES和Service回调增量。
    - ACK数据：分别记录ACK.RECEIVED_LENGTH、ACK.RECEIVED_PAYLOAD和ACK数据一致性。
    - Source事件：分别记录Source通道Raw Pending、Masked Pending和Service回调增量。
  pass_criteria:
    - 数据完整：所有长度的请求与ACK均逐字节一致。
    - 路由正确：消息只到Destination Endpoint，ACK只到Source Endpoint。
    - 中断正确：每轮两端Raw/Masked Pending和回调计数符合一次消息与一次ACK。
timeout: 10 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [当前Payload长度, 请求数据一致, ACK数据一致, 双端事件次数正确]
failure_observations:
  - {key: payload_length, label: 当前Payload长度, source: dut_config, role: config, format: decimal}
  - {key: destination_raw_pending, label: Destination CHANNEL.RAW_PENDING_MAILBOXES, source: peer, role: actual, format: hex32}
  - {key: destination_masked_pending, label: Destination CHANNEL.MASKED_PENDING_MAILBOXES, source: peer, role: actual, format: hex32}
  - {key: source_raw_pending, label: Source CHANNEL.RAW_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: source_masked_pending, label: Source CHANNEL.MASKED_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: received_payload, label: Responder实际Payload, source: peer, role: actual, format: bytes_hex}
  - {key: ack_payload, label: Initiator实际ACK Payload, source: dut, role: actual, format: bytes_hex}
  - {key: request_data_match, label: 请求Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: ack_data_match, label: ACK Payload逐字节一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_001
case_name: IPCM Manual ACK Payload更新测试
report_feature: |-
  1. IPCM Manual ACK Payload更新
p_level: P1
feature_refs: [IPCM_F_007]
method:
  inputs:
    - 请求Payload：A=P(L,0x21)，L和Pattern公式见0.5节。
    - ACK Payload：B=P(L,0xA1)，长度与A相同、内容不同。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - Peer准备：启动Manual ACK Update Job并提交Pattern B。
    - 请求发送：Initiator发送Pattern A。
    - Peer处理：Responder锁存消息快照和Pattern A，再用预先下发的Pattern B覆盖Data并发送Manual ACK，不在固件比较Expected。
    - ACK观测：Initiator锁存ACK Pending和Payload后清ACK，PC读取快照并比较两端Payload、回调计数和长度。
    - 终态确认：清除ACK并确认双端Pending恢复为0。
  observations:
    - 请求数据：记录MESSAGE.RECEIVED_LENGTH和MESSAGE.RECEIVED_PAYLOAD，并比较Pattern A。
    - ACK数据：记录ACK.RECEIVED_LENGTH和ACK.RECEIVED_PAYLOAD，并比较Pattern B。
    - Source事件：分别记录ACK到达时的Raw Pending、Masked Pending和Service回调增量。
  pass_criteria:
    - 请求正确：Responder收到Pattern A且长度一致。
    - 更新正确：Initiator收到Pattern B，不得仍为Pattern A或混合数据。
    - 事件唯一：消息和ACK各处理一次。
timeout: 5 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [请求数据一致, ACK数据一致, ACK事件次数正确]
failure_observations:
  - {key: request_payload, label: Responder收到的请求Payload, source: peer, role: actual, format: bytes_hex}
  - {key: expected_ack_payload, label: 期望更新ACK Payload, source: oracle, role: expected, format: bytes_hex}
  - {key: actual_ack_payload, label: Initiator实际ACK Payload, source: dut, role: actual, format: bytes_hex}
  - {key: ack_raw_pending, label: ACK CHANNEL.RAW_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: ack_masked_pending, label: ACK CHANNEL.MASKED_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: ack_callback_delta, label: ACK Service回调增量, source: dut, role: actual, format: decimal}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_002
case_name: IPCM Auto ACK触发条件测试
report_feature: |-
  1. IPCM Auto ACK触发条件
p_level: P1
feature_refs: [IPCM_F_008]
method:
  inputs:
    - Payload矩阵：clear_only使用P(L,0x31)，release使用P(L,0xB1)；两个动作分别形成parameter_id。
    - Responder动作矩阵：AUTO模式；clear_only只清消息中断，release只释放Destination；均不调用ack_send。
  steps:
    - 基线建立：为当前parameter_id复位IPCM实例、两端Service状态和Resource Pool，确认片内Peer Ready。
    - AUTO配置：配置单Destination和AUTO ACK，PC下发本参数的Payload与唯一Responder动作。
    - 消息发送：发送Payload，Peer先保存消息Pending和数据，再执行clear_only或release并回报动作完成。
    - Source观测：clear_only分支在动作完成后的100 ms内核对无ACK；release分支等待一次ACK并在清ACK前锁存Source快照。
    - 结果比较：PC核对Peer数据；clear_only应保留Destination且Source Raw/Masked与回调增量均为0，release应清空Destination且原Payload ACK仅一次。
    - 终态确认：读取当前分支终态；只清中断分支不补做release冒充正向结果，随后执行统一Cleanup。
  observations:
    - 动作前后：两个参数均记录动作前后MAILBOX.DESTINATION_ENDPOINTS及Peer收到的Payload。
    - Source事件：两个参数均记录Source Raw/Masked和ACK回调增量；release取清ACK前锁存值，clear_only取无ACK窗口末即时值，阶段身份进入Artifact。
    - ACK数据：仅release参数记录实际ACK Payload并与请求比较，clear_only无ACK，不伪造空Payload或数据一致结果。
  pass_criteria:
    - 反向成立：只清消息中断不产生ACK。
    - 正向成立：释放Destination后产生一次ACK且Payload保持原值。
timeout: 8 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [当前Responder动作, 动作后Destination状态, Source Raw与Masked快照, 当前分支ACK计数符合期望]
failure_observations:
  - {key: responder_action, label: 当前Responder动作, source: dut_config, role: config, format: text}
  - {key: destination_before_action, label: 动作前MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: destination_after_action, label: 动作后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: source_raw_pending, label: 当前分支Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: source_masked_pending, label: 当前分支Source Masked Pending, source: dut, role: actual, format: hex32}
  - {key: ack_callback_delta, label: 当前分支ACK回调增量, source: dut, role: actual, format: decimal}
  - {key: received_payload, label: Peer实际消息Payload, source: peer, role: actual, format: bytes_hex}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_003
case_name: IPCM IRQ与Polling状态测试
report_feature: |-
  1. IPCM消息与ACK中断状态
  2. IPCM IRQ与Polling模式
p_level: P1
feature_refs: [IPCM_F_004, IPCM_F_005]
method:
  inputs:
    - Payload矩阵：polling使用P(L,0x41)，irq使用P(L,0xC1)。
    - Delivery矩阵：POLLING与IRQ，分别使用polling和irq作为parameter_id；MANUAL模式只收消息并清中断，不发ACK。
  steps:
    - 基线建立：为当前parameter_id复位IPCM实例、两端Service状态和Resource Pool，确认片内Peer Ready。
    - Delivery配置：配置MANUAL单Mailbox，按参数关闭或启用Destination的IRQ投递，记录回调计数基线。
    - 消息发送：Peer Ready后由Initiator发送本参数Payload。
    - 事件采样：polling由Peer轮询、irq由ISR在清除前锁存Raw/Masked和Payload，再只清消息中断。
    - 结果比较：PC比较Payload；Raw应仅含目标Mailbox，polling的Masked及回调增量为0，irq的Masked含目标Mailbox且回调增量为1。
    - 终态确认：读取清除后Raw/Masked为0的即时状态，确认无重复回调，不等待本Case未请求的ACK。
  observations:
    - Polling硬件状态：分别记录CHANNEL.RAW_PENDING_MAILBOXES和CHANNEL.MASKED_PENDING_MAILBOXES。
    - Polling软件状态：记录Service回调增量和Payload数据一致性。
    - IRQ硬件状态：分别记录CHANNEL.RAW_PENDING_MAILBOXES和CHANNEL.MASKED_PENDING_MAILBOXES。
    - IRQ软件状态：记录Service回调增量和Payload数据一致性。
  pass_criteria:
    - Polling正确：仅Raw Pending置位，无IRQ回调，数据完整。
    - IRQ正确：Raw/Masked均置位且回调恰好一次，数据完整。
timeout: 8 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [当前Delivery模式, 清除前Raw与Masked状态, 回调增量, Payload数据一致]
failure_observations:
  - {key: delivery_mode, label: 当前Delivery模式, source: dut_config, role: config, format: text}
  - {key: event_raw_pending, label: 清除前Raw Pending, source: peer, role: actual, format: hex32}
  - {key: event_masked_pending, label: 清除前Masked Pending, source: peer, role: actual, format: hex32}
  - {key: callback_delta, label: 当前模式回调增量, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: Payload逐字节一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_004
case_name: IPCM全Mailbox释放与复用测试
report_feature: |-
  1. IPCM Mailbox、Channel与Payload容量
  2. IPCM Source与Destination路由
  3. IPCM Mailbox释放与复用
p_level: P1
feature_refs: [IPCM_F_001, IPCM_F_002, IPCM_F_011]
method:
  inputs:
    - Mailbox矩阵：Capability发布的全部合法mailbox_id；每个ID使用mailbox_<id>作为独立parameter_id。
    - Payload编码：首轮P(L,mailbox_id)，复用轮P(L,mailbox_id+0x80)；当前ID另记为Measurement，不以Payload推算ID。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 首轮传输：配置当前parameter_id对应Mailbox，完成双Core消息与ACK并核对当前ID对应的Payload。
    - 首轮释放：释放当前Mailbox，分别读取配置、Destination、Raw Pending和Masked Pending终态。
    - 复用传输：重新配置同一Mailbox，再次完成一轮内容不同的消息与ACK。
    - 复用释放：再次释放当前Mailbox并读取相同终态字段。
    - 参数判定：确认当前Mailbox两轮数据一致、事件唯一且两次释放均恢复为空闲基线。
  observations:
    - 参数身份：记录当前parameter_id和mailbox_id。
    - 传输结果：分别记录首轮和复用轮的数据一致性及事件次数。
    - 释放配置：分别记录释放后的Source、Destination和IRQ Enable集合。
    - 释放事件：分别记录释放后的Raw Pending和Masked Pending位集合。
  pass_criteria:
    - 全域覆盖：每个Capability Mailbox恰好完成两轮。
    - 独立正确：每轮只出现当前Mailbox Pending且Payload携带正确ID。
    - 释放完整：释放后配置和Pending恢复，后续复用成功。
timeout: 20 s
cleanup: [Abort Peer Job, Release all test Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [当前Mailbox ID, 首轮数据一致, 复用轮数据一致, 两次释放终态为空]
failure_observations:
  - {key: mailbox_id, label: 当前Mailbox ID, source: dut_config, role: config, format: decimal}
  - {key: first_data_match, label: 首轮Payload一致, source: oracle, role: actual, format: bool}
  - {key: reuse_data_match, label: 复用轮Payload一致, source: oracle, role: actual, format: bool}
  - {key: released_source_endpoints, label: 释放后MAILBOX.SOURCE_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: released_destination_endpoints, label: 释放后MAILBOX.DESTINATION_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: released_irq_enabled_endpoints, label: 释放后MAILBOX.IRQ_ENABLED_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: released_raw_pending, label: 释放后CHANNEL.RAW_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
  - {key: released_masked_pending, label: 释放后CHANNEL.MASKED_PENDING_MAILBOXES, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, capability_semantic_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_005
case_name: IPCM双向双Mailbox通信测试
report_feature: |-
  1. IPCM Source与Destination路由
  2. IPCM双向Core间消息
p_level: P1
feature_refs: [IPCM_F_002, IPCM_F_009]
method:
  inputs:
    - 正向Mailbox和反向Mailbox：从Capability选择两个不同Mailbox。
    - 正向Payload A与反向Payload B：A=P(L,0x51)，B=P(L,0xD1)；两方向均MANUAL，只清消息中断、不发ACK。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 双向配置：配置Initiator到Responder的正向Mailbox和Responder到Initiator的反向Mailbox。
    - 正向发送：Initiator发送Payload A，Responder锁存消息快照和数据后清消息中断；PC核对A。
    - 反向发送：Responder在正向接收完成后通过另一Mailbox发送Payload B。
    - 终态观测：Initiator锁存Payload B及反向Pending后清中断；PC比较两方向事件快照中的Mailbox、Endpoint、Payload和回调。
    - 终态清除：处理两个方向Pending并确认两个Mailbox状态互不残留。
  observations:
    - 正向路由：分别记录正向Mailbox ID、Source Endpoint和Destination Endpoint。
    - 正向数据：记录Responder收到的Payload和数据一致性。
    - 反向路由：分别记录反向Mailbox ID、Source Endpoint和Destination Endpoint。
    - 反向数据：记录Initiator收到的Payload和数据一致性。
    - 终态事件：分别记录两个方向的Raw Pending、Masked Pending和Service回调增量。
  pass_criteria:
    - 正向正确：Responder只在正向Mailbox收到Payload A。
    - 反向正确：Initiator只在反向Mailbox收到Payload B。
    - 无串扰：两个方向的Pending和回调不落到错误Mailbox或Endpoint。
timeout: 8 s
cleanup: [Abort Peer Job, Release both Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [双向路由一致, 正向数据一致, 反向数据一致, 双向终态无Pending]
failure_observations:
  - {key: forward_mailbox_id, label: 正向Mailbox ID, source: peer, role: actual, format: decimal}
  - {key: forward_source_endpoints, label: 正向MAILBOX.SOURCE_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: forward_destination_endpoints, label: 正向MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: forward_payload, label: Responder实际正向Payload, source: peer, role: actual, format: bytes_hex}
  - {key: forward_data_match, label: 正向Payload一致, source: oracle, role: actual, format: bool}
  - {key: reverse_mailbox_id, label: 反向Mailbox ID, source: dut, role: actual, format: decimal}
  - {key: reverse_source_endpoints, label: 反向MAILBOX.SOURCE_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: reverse_destination_endpoints, label: 反向MAILBOX.DESTINATION_ENDPOINTS, source: dut, role: actual, format: hex32}
  - {key: reverse_payload, label: Initiator实际反向Payload, source: dut, role: actual, format: bytes_hex}
  - {key: reverse_data_match, label: 反向Payload一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_006
case_name: IPCM多Mailbox同时Pending测试
report_feature: |-
  1. IPCM多Mailbox独立Pending
p_level: P1
feature_refs: [IPCM_F_010]
method:
  inputs:
    - Mailbox与Payload：从Capability选择两个不同Mailbox，分别使用P(L,0x61)和P(L,0xE1)。
    - Delivery策略：两个Mailbox使用同一个Destination Endpoint，并先以Polling阻止自动回调处理。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 双Mailbox配置：两个Mailbox指向同一Destination Endpoint并关闭IRQ投递。
    - 连续发送：Initiator在Peer处理前依次发送两条消息。
    - Pending观测：Peer一次读取Raw Pending位集合，确认两个Mailbox位同时存在。
    - 逐项处理：Peer按位集合逐个读取Payload并清除对应Mailbox。
    - 清除观测：每次处理后读取位集合，确认只清目标位，最终为0。
  observations:
    - Pending变化：分别记录处理前、清除首个Mailbox后和全部清除后的Raw Pending位集合。
    - Masked状态：记录IRQ关闭条件下的Masked Pending位集合，期望始终为0。
    - Payload对应：分别记录两个Mailbox的实际Payload及数据一致性。
  pass_criteria:
    - 同时Pending：初始Raw位集合恰好包含两个目标Mailbox，所有阶段Masked均为0且IRQ回调不增加。
    - 独立清除：第一次清除后仅剩另一个Mailbox位。
    - 数据正确：两个Payload与各自Mailbox一一对应，最终Pending为0。
timeout: 8 s
cleanup: [Abort Peer Job, Release both Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [处理前Raw Pending集合, 首次清除后Raw Pending集合, 全部清除后Raw Pending集合, 双Mailbox数据一致]
failure_observations:
  - {key: pending_before, label: 处理前Raw Pending位集合, source: peer, role: actual, format: hex32}
  - {key: pending_after_first, label: 首个Mailbox清除后Raw Pending位集合, source: peer, role: actual, format: hex32}
  - {key: pending_after_all, label: 全部处理后Raw Pending位集合, source: peer, role: actual, format: hex32}
  - {key: masked_pending, label: IRQ关闭时Masked Pending位集合, source: peer, role: actual, format: hex32}
  - {key: mailbox_a_payload, label: Mailbox A实际Payload, source: peer, role: actual, format: bytes_hex}
  - {key: mailbox_b_payload, label: Mailbox B实际Payload, source: peer, role: actual, format: bytes_hex}
  - {key: payloads_match, label: 双Mailbox Payload分别一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_007
case_name: IPCM Multi-destination独立释放测试
report_feature: |-
  1. IPCM Multi-destination路由
p_level: P1
feature_refs: [IPCM_F_014]
method:
  inputs:
    - Endpoint集合：一个Source Endpoint和两个不同Destination Endpoint。
    - 消息配置：P(L,0x71)，使用MANUAL与POLLING；两个Destination由同一片内Peer分别轮询，Source位于另一个Core。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 多目标配置：同一Mailbox配置两个Destination Endpoint并读取Destination快照。
    - 消息发送：Initiator发送一次Payload，Peer在任何清除动作前分别保存两个Endpoint的Raw/Masked和Payload，不调用全Mailbox interrupt_clear。
    - 首目标释放：只释放第一个Destination，读取MAILBOX.DESTINATION_ENDPOINTS集合，确认仍含第二个Destination且Source Raw Pending为0。
    - 次目标释放：只释放第二个Destination，确认Destination为空且Source Raw Pending仍为0；两端Payload由PC独立比较。
    - 显式ACK：Peer最后调用ack_send；Source轮询锁存链路ACK后清除，确认原Payload正确、无重复Pending，保存终态。
  observations:
    - 多目标投递：分别记录两个Destination的原始Raw/Masked、Payload和接收次数Measurement；Polling模式所有IRQ回调增量为0。
    - 首次释放：记录首个释放后的MAILBOX.DESTINATION_ENDPOINTS、两个Destination Raw Pending和Source Raw Pending。
    - 最终释放：记录第二个释放后的MAILBOX.DESTINATION_ENDPOINTS及显式ACK前Source Raw Pending。
    - 显式ACK：记录Source ACK Raw Pending、Payload及清除后的即时Pending，接收次数单独记Measurement。
  pass_criteria:
    - 多目标投递：两个Destination均恰好收到一次相同Payload。
    - 独立释放：首个释放只清自己的Destination位，第二个仍有效；两个释放动作均不在MANUAL下产生ACK。
    - 显式ACK：最后的ack_send使Source收到原Payload ACK，清除后无Pending；不推断多目标AUTO聚合行为。
timeout: 8 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer支持两个逻辑事件Endpoint, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [两个Destination均收到数据, 两次释放后Destination集合, 显式ACK前Source Raw为0, 显式ACK数据一致]
failure_observations:
  - {key: destination_a_event_count, label: Destination A事件次数, source: peer, role: actual, format: decimal}
  - {key: destination_b_event_count, label: Destination B事件次数, source: peer, role: actual, format: decimal}
  - {key: destination_payload_match, label: 两个Destination Payload一致, source: oracle, role: actual, format: bool}
  - {key: status_after_first_release, label: 首次释放后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: source_raw_after_first_release, label: 首个释放后的Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: status_after_final_release, label: 最终释放后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: source_raw_before_ack, label: 全部释放后显式ACK前Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: source_raw_on_ack, label: 显式ACK到达时Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: final_ack_data_match, label: 最终显式ACK Payload一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, multi_destination_driver_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P1_008
case_name: IPCM Auto ACK模式显式ACK测试
report_feature: |-
  1. IPCM Auto ACK模式显式ACK
p_level: P1
feature_refs: [IPCM_F_016]
method:
  inputs:
    - 消息配置：一个合法Mailbox、两个不同Core的Source和Destination，AUTO与SINGLE模式，启用两端IRQ。
    - 请求Payload：P(L,0x81)，保持原数据返回，不调用destination_release。
  steps:
    - 基线建立：复位IPCM实例、两端Service状态和Resource Pool，确认片内Peer Ready及explicit_ack_in_auto能力。
    - AUTO配置：配置Mailbox并读回MAILBOX.ACK_MODE=AUTO，Peer只接受本次显式ACK动作。
    - 消息发送：Initiator发送Payload，Peer在ISR入口保存Raw/Masked、Payload和Destination集合，暂停该事件IRQ投递但不释放Destination。
    - 显式ACK：Peer读回AUTO配置和仍存在的Destination后直接ack_send，禁止切换MANUAL或先调用destination_release。
    - Source观测：Source先锁存ACK Raw/Masked与原Payload再清ACK；PC取回双方事件快照并比较数据。
    - 重复检查：PC在100 ms窗口内确认ACK回调增量保持1、Source即时Raw/Masked为0，记录AUTO模式仍未改变。
  observations:
    - ACK前配置：分别记录MAILBOX.ACK_MODE和MAILBOX.DESTINATION_ENDPOINTS，证明未通过切模式或释放来触发ACK。
    - 事件数据：分别记录Peer收到的Payload、Source收到的ACK Payload及两端清除前Raw/Masked。
    - ACK次数：记录Source回调增量Measurement及清除后Source即时Pending。
  pass_criteria:
    - 触发正确：配置始终为AUTO，显式ACK前Destination仍存在，未执行destination_release。
    - 数据正确：Peer请求与Source ACK均逐字节等于原Payload，长度为L。
    - 事件唯一：两端事件快照命中目标Mailbox，Source ACK回调仅增加1，检查窗口内不重复。
timeout: 5 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [显式ACK前AUTO模式, ACK前Destination集合, 请求与ACK数据一致, Source ACK次数为1]
failure_observations:
  - {key: mode_before_ack, label: ACK前MAILBOX.ACK_MODE, source: peer, role: actual, format: text}
  - {key: destination_before_ack, label: ACK前MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: destination_raw_pending, label: 消息到达时Destination Raw Pending, source: peer, role: actual, format: hex32}
  - {key: destination_masked_pending, label: 消息到达时Destination Masked Pending, source: peer, role: actual, format: hex32}
  - {key: source_raw_pending, label: ACK到达时Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: source_masked_pending, label: ACK到达时Source Masked Pending, source: dut, role: actual, format: hex32}
  - {key: received_payload, label: Peer实际请求Payload, source: peer, role: actual, format: bytes_hex}
  - {key: ack_payload, label: Source实际ACK Payload, source: dut, role: actual, format: bytes_hex}
  - {key: ack_callback_delta, label: Source ACK回调增量, source: dut, role: actual, format: decimal}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P2_001
case_name: IPCM Auto Link Manual ACK长Payload测试
report_feature: |-
  1. IPCM Auto Link连续Mailbox传输
p_level: P2
feature_refs: [IPCM_F_012]
method:
  inputs:
    - Linked链：从Capability选择可容纳最大链长的连续Mailbox范围。
    - Payload：P(N*C-3,0x91)，最后Mailbox只读取C-3个有效字节，不把填充字节计入总长度。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 链配置：按MANUAL ACK和LINKED配置连续Mailbox，核对每个链成员快照及末项Link终止。
    - Linked发送：Initiator一次提交完整Payload。
    - Peer处理：Responder每次先保存当前Mailbox消息Pending及有效Payload再ack_send，前N-1次推进下一Mailbox，末项产生Source ACK。
    - 重组判定：PC核对N次Destination事件的Mailbox顺序和重组数据；Source仅接受一次链尾ACK，先锁存Mailbox身份与Raw/Masked再清除。
    - 终态确认：读取全链配置和Pending，确认处理后没有遗留事件。
  observations:
    - 链配置：完整记录每个链成员的Mailbox ID、MAILBOX.LINK_MODE和末项终止状态到绑定Artifact。
    - 链事件：逐个保存Destination清除前Raw/Masked，单独记录Source链尾ACK快照与回调次数Measurement；不把N次Peer ACK动作当作N次Source事件。
    - 重组摘要：记录实际总长度、数据一致性和首个错误偏移；完整Payload只进入绑定Artifact。
  pass_criteria:
    - 链配置正确：连续成员和末项Link终止准确。
    - 片段完整：每个成员只处理一次，顺序和有效长度正确。
    - 总体正确：重组Payload逐字节一致，Source只出现一次链尾ACK，不能出现中间Mailbox的Source ACK。
timeout: 15 s
cleanup: [Abort Peer Job, Release linked Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Linked链范围, 重组数据一致, N次Destination事件顺序, Source仅一次链尾ACK]
failure_observations:
  - {key: linked_range, label: Linked Mailbox范围, source: dut_config, role: config, format: text}
  - {key: reconstructed_length, label: Responder重组Payload长度, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: 重组Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: first_mismatch_offset, label: 首个Payload错误偏移, source: oracle, role: actual, format: decimal}
  - {key: pending_sequence_match, label: 逐Mailbox Pending顺序一致, source: oracle, role: actual, format: bool}
  - {key: source_ack_mailbox, label: Source ACK实际Mailbox, source: dut, role: actual, format: decimal}
  - {key: source_ack_raw_pending, label: 链尾ACK Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: source_ack_masked_pending, label: 链尾ACK Source Masked Pending, source: dut, role: actual, format: hex32}
  - {key: source_ack_count, label: Source ACK回调次数, source: dut, role: actual, format: decimal}
gap: [case_implementation_gap, linked_range_driver_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P2_002
case_name: IPCM Auto ACK Link长Payload测试
report_feature: |-
  1. IPCM Auto ACK Link传输
p_level: P2
feature_refs: [IPCM_F_013]
method:
  inputs:
    - Linked链：从Capability选择可容纳最大链长的连续Mailbox范围。
    - Payload：P(N*C-3,0xA1)，最后Mailbox只读取C-3个有效字节。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 链配置：按AUTO ACK和LINKED配置连续Mailbox并核对链成员。
    - Linked发送：Initiator一次提交完整Payload。
    - Peer处理：Responder每次先锁存Raw/Masked及有效片段，再destination_release；前N-1次推进下一Mailbox，末项产生Source ACK。
    - 重组判定：PC比较N个有序片段与完整Payload，核对每个Destination释放状态；Source锁存唯一链尾ACK快照后清除。
    - 终态确认：读取全链Destination、Raw和Masked Pending，确认均清零。
  observations:
    - 链配置：完整记录每个链成员的MAILBOX.LINK_MODE和MAILBOX.ACK_MODE到绑定Artifact。
    - 释放事件：记录逐Mailbox清除前Raw/Masked和释放后Destination，单独记录Source唯一链尾ACK快照及次数Measurement。
    - 重组摘要：记录实际总长度、数据一致性和首个错误偏移；完整Payload只进入绑定Artifact。
    - 终态硬件：分别记录全链Destination、Raw Pending和Masked Pending是否清零。
  pass_criteria:
    - 链数据完整：所有片段按顺序重组且逐字节一致。
    - Auto ACK正确：N个Destination消息依序到达，Source只出现一次链尾ACK，不出现中间Mailbox ACK。
    - 终态干净：全部链成员Destination和Pending均清零。
timeout: 15 s
cleanup: [Abort Peer Job, Release linked Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [重组总长度, 重组数据一致, N次Destination释放顺序, Source仅一次链尾ACK]
failure_observations:
  - {key: reconstructed_length, label: Responder重组Payload长度, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: 重组Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: first_mismatch_offset, label: 首个Payload错误偏移, source: oracle, role: actual, format: decimal}
  - {key: destination_release_sequence_match, label: Destination释放顺序一致, source: oracle, role: actual, format: bool}
  - {key: source_ack_mailbox, label: Source ACK实际Mailbox, source: dut, role: actual, format: decimal}
  - {key: source_ack_raw_pending, label: 链尾ACK Source Raw Pending, source: dut, role: actual, format: hex32}
  - {key: source_ack_masked_pending, label: 链尾ACK Source Masked Pending, source: dut, role: actual, format: hex32}
  - {key: source_ack_count, label: Source ACK回调次数, source: dut, role: actual, format: decimal}
  - {key: final_pending_clear, label: 全链Raw与Masked Pending清零, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, linked_range_driver_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: IPCM_P2_003
case_name: IPCM同Mailbox连续分段传输测试
report_feature: |-
  1. IPCM单Mailbox变长Payload
  2. IPCM同Mailbox连续分段传输
p_level: P2
feature_refs: [IPCM_F_003, IPCM_F_015]
method:
  inputs:
    - 总Payload：P(3*C+3,0xB1)，共4段，前三段各C字节、尾段3字节；C至少为4。
    - 分段策略：每段携带实际长度和段序号，ACK处理完才发送下一段；最后短消息P(L,0xC1)单独验证再次发送。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 单Mailbox配置：配置MANUAL ACK模式并启动连续接收Peer Job。
    - 分段循环：Initiator发送当前分段；Peer在ACK前锁存长度、数据和Pending，Source在清ACK前锁存ACK；PC确认当前段完成才允许下一段，不重新复位IP。
    - Peer重组：Peer只回报各段原始数据，PC按段序号重组并逐段比较；末段只读写3个有效字节，不按容量追加越界数据。
    - 终态判定：比较段数、总长度、完整Payload和Mailbox最终Pending状态。
    - 复用确认：完成全部分段后再发送一个短Payload，确认同一Mailbox仍可使用。
  observations:
    - 分段事件：完整记录每段序号、有效长度、请求/ACK Pending和Service回调增量到绑定Artifact。
    - 分段顺序：生成段数、序号连续性和每段数据一致性Measurement。
    - 重组摘要：记录重组总长度、数据一致性和首个错误偏移；完整Payload只进入绑定Artifact。
    - 复用终态：分别记录短Payload复用结果及最终Raw/Masked Pending。
  pass_criteria:
    - 分段完整：每段恰好处理一次，长度和内容正确。
    - 顺序正确：分段序号连续，无丢失、重复或串包。
    - 恢复正确：重组Payload一致且Mailbox最终可再次使用。
timeout: 12 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 片内Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [实际分段数量, 重组总长度, 重组数据一致, 同Mailbox复用成功]
failure_observations:
  - {key: actual_segment_count, label: 实际完成分段数量, source: peer, role: actual, format: decimal}
  - {key: segment_sequence_match, label: 分段序号连续且无重复, source: oracle, role: actual, format: bool}
  - {key: reconstructed_length, label: Responder重组Payload长度, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: 重组Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: first_mismatch_offset, label: 首个Payload错误偏移, source: oracle, role: actual, format: decimal}
  - {key: reuse_data_match, label: 同Mailbox短Payload复用一致, source: oracle, role: actual, format: bool}
  - {key: final_raw_pending, label: 连续传输后Raw Pending, source: dut, role: actual, format: hex32}
  - {key: final_masked_pending, label: 连续传输后Masked Pending, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, dualcore_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=16 | IMPLEMENTATION_GAP=1; MAPPING_GAP=12 | 13个PLAN覆盖已找到的IPCM_0~9测试思想；尚未编码或HIL。释放硬件语义与压力测试缺失正文仍须闭环 | `ET6801_ipcm.md` |

## 5. Common Gap / Evolution

- `case_implementation_gap`：已增加本核IPCM Wrap、Service及注册；PC Driver、Core1 Peer执行入口和13条Formal Case仍待完成，不以底层代码存在冒充Case实现。
- `capability_semantic_gap`：需要由芯片能力声明Mailbox、Channel、Data Word、模式、Linked、Multi-destination及AUTO下显式ACK；当前适配缺口见芯片文档。
- `dualcore_execution_mapping_gap`：必须建立逻辑Initiator/Responder、事件Endpoint和Core1 Peer部署映射；公共Case不得硬编码Core或IRQ编号。
- `linked_range_driver_gap`、`multi_destination_driver_gap`、`driver_api_gap`：底层测试扩展已补齐，等待双核Case集成及真实硬件确认；不改变历史SDK API。
- `ip_reset_mapping_gap`：已补IPCM公共CRG类别及芯片映射；全IP复位与单Mailbox释放仍是不同动作，IPCM Wrap不跨IP调用。
- `mailbox_release_semantic_gap`：释放清除哪些配置必须由目标证据确定；不得在Wrap中悄悄复位整个IP替代单Mailbox释放。
- `source_item_body_gap`：历史压力入口只有调用和声明，未找到实现；待获取正文后提取其有效测试点，不能宣称未知正文已被当前Case覆盖。
- 多目标AUTO聚合ACK触发条件尚未证实；P1_007先独立覆盖多目标路由与MANUAL释放，不把推断作为通过条件，也不宣称覆盖了该组合。
- `CORE2CORE`独立门铃中断不属于IPCM Mailbox Feature，必须由Dual-Core/CPU独立Contract承接，不能混入本IP。
- 3101和6003为单核目标，本轮没有读取、映射或继承其资料；未来若某芯片无片内Peer，应由Capability明确不支持，而不是删除公共Feature。
