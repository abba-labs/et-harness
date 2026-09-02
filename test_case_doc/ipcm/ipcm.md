# IPCM Stable IP Contract

> 本文件定义 IPCM 的芯片中立 Feature、Case、Oracle、Observation、资源和稳定自动化动作。
> 芯片实例、Core 数量、Mailbox/Channel 数量、寄存器、IRQn、SDK API 和部署地址只进入同目录 `<CHIP>_ipcm.md`。
> 当前 12 个 Formal Case 均为 `PLANNED`；文档完成不等于代码实现或硬件 PASS。

## 0. Stable IP Contract

### 0.1 稳定对象与配置语义

| 稳定对象 | 公共语义 | 约束 |
|---|---|---|
| `mailbox_id` | 独立 IPCM Mailbox 资源编号 | 合法范围由 `mailbox_count` 决定，公共 Case 不写死最大编号。 |
| `source_endpoint` | 消息发起执行实体及其 ACK 事件通道 | 由 Capability/Execution Mapping 映射到目标 Core 和硬件 Channel。 |
| `destination_endpoints` | 一个或多个消息接收执行实体及事件通道 | 使用逻辑 Endpoint 集合表达，不暴露目标 Channel 位图。 |
| `ack_mode` | `MANUAL` / `AUTO` | `MANUAL` 由接收端显式发送 ACK；`AUTO` 由接收端释放目标路由后触发 ACK。 |
| `link_mode` | `SINGLE` / `LINKED` | `LINKED` 使用连续 Mailbox 组成一条消息链，合法长度由 Capability 给出。 |
| `irq_delivery` | `IRQ` / `POLLING` | `IRQ` 观察 Raw、Masked 和回调计数；`POLLING` 只允许 Raw 置位，不得投递 IRQ。 |
| `payload` | 不透明二进制字节序列 | 单 Mailbox 和 Linked 最大字节数由 Capability 发布；公共层禁止静默截断。 |
| `peer_role` | `INITIATOR` / `RESPONDER` | 逻辑角色与 Core 编号解耦；双向 Case 可交换角色。 |

### 0.2 稳定 Observation Endpoint

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
| `IRQ.CALLBACK_COUNT` | `dut` | 指定逻辑事件通道对应 Service 回调累计次数。 |
| `MESSAGE.RECEIVED_LENGTH` | `peer` | Peer 实际收到的有效 Payload 字节数。 |
| `MESSAGE.RECEIVED_PAYLOAD` | `peer` | Peer 实际收到的 Payload。 |
| `ACK.RECEIVED_LENGTH` | `dut` | Initiator 实际收到的 ACK Payload 字节数。 |
| `ACK.RECEIVED_PAYLOAD` | `dut` | Initiator 实际收到的 ACK Payload。 |
| `PEER_JOB.STATE` | `peer` | 异步 Peer Job 的 `READY/RUNNING/WAITING/DONE/FAILED/ABORTED` 状态。 |
| `PEER_JOB.EVENT_COUNT` | `peer` | Peer 已处理的目标消息或 ACK 事件数。 |

### 0.3 稳定自动化动作

| 稳定动作 | 请求语义 | 约束 |
|---|---|---|
| `capabilities_get` | 获取 Mailbox、Channel、Data Word、模式、Linked 和 Multi-destination 能力 | 只发布目标硬件事实，不发布测试实现程度。 |
| `mailbox_configure` | 配置 Source、Destination、ACK、Link 和 IRQ Delivery | 输入使用逻辑 Endpoint；目标映射由 Chip Profile 完成。 |
| `mailbox_release` | 释放指定 Mailbox 或连续 Mailbox 链 | 释放后必须通过硬件快照确认配置和 Pending 状态恢复。 |
| `mailbox_snapshot_get` | 获取 Mailbox 稳定配置和路由状态 | 返回稳定逻辑值，不暴露芯片寄存器类型。 |
| `channel_pending_snapshot_get` | 获取指定 Endpoint 的 Raw/Masked Pending Mailbox 位集合 | 必须一次返回完整位集合，不能只返回单个 Mailbox ID。 |
| `message_send` | 从 Initiator 向 Destination 发送一条有界消息 | 超过容量必须返回明确错误，禁止静默截断。 |
| `message_receive` | 读取指定 Mailbox 的有效 Payload | 长度由 Case/Peer Job 明确传入并原样回报。 |
| `ack_send` | Manual ACK，可选择原样返回或替换 ACK Payload | 只能用于 `MANUAL` 模式。 |
| `destination_release` | 清除指定 Destination Endpoint | `AUTO` 模式下用于触发 Auto ACK；多目标时逐个释放并观测。 |
| `interrupt_clear` | 只清除当前消息/ACK Pending | 不得隐式释放 Destination 或触发未请求的 Auto ACK。 |
| `peer_job_start/status/result/abort` | 在片内 Peer 上异步执行接收、ACK、双向、Linked 或多目标动作 | PC 控制通道保持响应；Job 必须有 ACK、deadline 和可终止语义。 |

### 0.4 Oracle、Timeout 与隔离

- 每个 Case 在第一次配置前执行 `Reset IPCM instance -> Service State Reset -> Resource Pool Reset`；任何一步失败立即终止 Case。
- IPCM 功能 Case 必须使用真实片内 Peer；同一 Core 内两个 Channel 的自发自收只能用于诊断，不能证明 Core 间通信。
- 所有等待由 PC 持有统一 Case deadline；Firmware 同步命令只做一次原子动作，Peer 接收和多阶段 ACK 放入异步 Job。
- 不能以 API 返回成功或固定 sleep 代替硬件证据；必须同时记录 Pending 位集合、回调计数、Payload 和 ACK。
- `POLLING` 的通过条件是 Raw Pending 置位、Masked Pending 为 0、IRQ Callback 不增加且数据可读。
- `AUTO` ACK 必须同时验证正向条件和反向条件：释放 Destination 才产生 ACK，只清消息中断不得产生 ACK。
- Linked Case 必须校验每个链成员、总长度、最终 Payload 和最终 ACK；禁止只看最后一个中断。
- Multi-destination Case 必须确认每个 Destination 独立收到消息；只释放一个 Destination 时其他 Destination 状态必须保持。
- Formal Case 只调用 IPCM Driver、Capability/Resource Fixture 和 Canonical Evidence；不直接访问 Codec、Transport 或寄存器。
- Firmware Service 只校验当前命令、调用 IPCM Wrap 并编码原始事实，不实现 Case 流程或通过判定。
- Cleanup 只需 Abort Peer Job、释放测试 Mailbox、复位 IPCM 实例和 Resource Pool；下一 Case 仍重新建立完整基线。
- 参数矩阵中的每个Payload长度或Mailbox ID必须形成独立且稳定的`parameter_id`；不得把多个参数分支隐藏在Case内部循环后只输出一份不可定位的结果。
- Raw Pending、Masked Pending、Mailbox配置、Payload和Service回调计数是不同事实，必须分别记录；Service回调计数属于Measurement，不得标成硬件寄存器Observation。
- 人读报告每个Case只选择1～4项最小充分事实。完整Payload、全Mailbox矩阵和全链成员明细进入绑定Artifact，不得直接展开到Excel备注。
- 长Payload的人读字段只保留实际长度、数据一致性、首个错误偏移和必要摘要；完整字节序列始终保留在Canonical Result或Artifact中。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联 Case |
|---|---|---|---|
| IPCM_F_001 | IPCM Mailbox、Channel与Payload容量 | 硬件可报告 Mailbox、事件 Channel 和单 Mailbox Data Word 数量。 | `IPCM_P0_001`, `IPCM_P1_004` |
| IPCM_F_002 | IPCM Source与Destination路由 | Mailbox 可将 Source ACK 和消息分别路由到配置的逻辑 Endpoint。 | `IPCM_P0_001`, `IPCM_P0_002`, `IPCM_P1_005` |
| IPCM_F_003 | IPCM单Mailbox变长Payload | 单 Mailbox 可传输目标声明容量内的二进制 Payload。 | `IPCM_P0_002`, `IPCM_P2_003` |
| IPCM_F_004 | IPCM消息与ACK中断状态 | 消息和 ACK 到达时产生对应 Raw/Masked Pending 和 IRQ 回调。 | `IPCM_P0_002`, `IPCM_P1_003` |
| IPCM_F_005 | IPCM IRQ与Polling模式 | 同一事件可选择 IRQ 投递或仅通过 Raw Pending 轮询处理。 | `IPCM_P1_003` |
| IPCM_F_006 | IPCM Manual ACK原Payload返回 | Responder 可显式 ACK，Initiator 收到原 Payload。 | `IPCM_P0_002` |
| IPCM_F_007 | IPCM Manual ACK Payload更新 | Responder 可在 ACK 前替换 Payload，Initiator 收到更新值。 | `IPCM_P1_001` |
| IPCM_F_008 | IPCM Auto ACK触发条件 | Auto ACK 只在 Destination 释放时触发，单纯清消息中断不触发。 | `IPCM_P1_002` |
| IPCM_F_009 | IPCM双向Core间消息 | 两个片内执行实体可通过两个独立 Mailbox 双向交换消息。 | `IPCM_P1_005` |
| IPCM_F_010 | IPCM多Mailbox独立Pending | 多个 Mailbox 可同时 Pending，完整位集合可被识别并逐个处理。 | `IPCM_P1_006` |
| IPCM_F_011 | IPCM Mailbox释放与复用 | Mailbox 释放后配置和 Pending 恢复，可重新配置并再次传输。 | `IPCM_P1_004`, `IPCM_P2_003` |
| IPCM_F_012 | IPCM Auto Link连续Mailbox传输 | 连续 Mailbox 可在 Manual ACK 策略下组成一条 Linked 消息。 | `IPCM_P2_001` |
| IPCM_F_013 | IPCM Auto ACK Link传输 | 连续 Mailbox 可同时使用 Auto Link 与 Auto ACK。 | `IPCM_P2_002` |
| IPCM_F_014 | IPCM Multi-destination路由 | 一条消息可路由到多个 Destination Endpoint，并由各端独立释放。 | `IPCM_P1_007` |
| IPCM_F_015 | IPCM同Mailbox连续分段传输 | 同一 Mailbox 可在多轮 ACK 后连续复用并重组长消息。 | `IPCM_P2_003` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---:|---|---|---|---:|---|
| IPCM_P0_001 | P0 | IPCM能力与Mailbox配置读回测试 | 容量、路由 | CFG能力值与Mailbox配置逐项一致，释放后恢复 | R0 | PLANNED |
| IPCM_P0_002 | P0 | IPCM双Core Manual ACK变长Payload测试 | 路由、Payload、IRQ、Manual ACK | 请求与ACK Payload逐字节一致，双端Pending和回调正确 | R2 | PLANNED |
| IPCM_P1_001 | P1 | IPCM Manual ACK Payload更新测试 | ACK Payload更新 | Responder收到请求，Initiator收到指定更新Payload | R2 | PLANNED |
| IPCM_P1_002 | P1 | IPCM Auto ACK触发条件测试 | Auto ACK | 只清中断不ACK，释放Destination后恰好ACK一次 | R2 | PLANNED |
| IPCM_P1_003 | P1 | IPCM IRQ与Polling状态测试 | IRQ、Polling | Polling仅Raw置位；IRQ模式Raw/Masked/Callback均有效 | R2 | PLANNED |
| IPCM_P1_004 | P1 | IPCM全Mailbox释放与复用测试 | 容量、释放复用 | Capability发布的每个Mailbox均可配置、传输、释放、复用 | R2 | PLANNED |
| IPCM_P1_005 | P1 | IPCM双向双Mailbox通信测试 | 双向Core消息 | 两个方向Payload、Mailbox和事件通道均准确且互不串扰 | R2 | PLANNED |
| IPCM_P1_006 | P1 | IPCM多Mailbox同时Pending测试 | 多Mailbox Pending | Raw/Masked位集合同时包含两个Mailbox并可逐个清除 | R2 | PLANNED |
| IPCM_P1_007 | P1 | IPCM Multi-destination独立释放测试 | 多目标路由 | 两个Destination均收包，逐个释放时状态独立 | R2 | PLANNED |
| IPCM_P2_001 | P2 | IPCM Auto Link Manual ACK长Payload测试 | Auto Link | 全链Payload和逐Mailbox事件完整，最终ACK正确 | R2 | PLANNED |
| IPCM_P2_002 | P2 | IPCM Auto ACK Link长Payload测试 | Auto ACK Link | 全链Payload完整，每个Destination释放驱动正确ACK链 | R2 | PLANNED |
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
p_level: P0
feature_refs: [IPCM_F_001, IPCM_F_002]
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
    - Payload内容：每个长度使用可复现且互不相同的二进制Pattern。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - Peer准备：启动Responder Job，配置目标Mailbox并等待READY。
    - 消息发送：Initiator发送当前parameter_id对应长度的Payload。
    - Responder处理：Peer读取Payload并显式发送不修改Payload的Manual ACK。
    - 双端观测：每轮读取Destination和Source的Raw/Masked Pending、回调计数及Payload。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
    - 请求Payload：固定长度的可复现二进制Pattern A。
    - ACK Payload：相同长度且内容不同的Pattern B。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - Peer准备：启动Manual ACK Update Job并提交Pattern B。
    - 请求发送：Initiator发送Pattern A。
    - Peer处理：Responder确认Pattern A后用Pattern B覆盖Data并发送Manual ACK。
    - ACK观测：Initiator读取ACK Pending、回调计数、长度和Payload。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
    - Payload矩阵：两轮使用相同长度、不同内容的Payload。
    - Responder动作矩阵：只清消息中断、释放Destination。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 反向场景：配置AUTO ACK，Responder收到第一条消息后只执行interrupt_clear。
    - 反向观测：确认Source ACK Pending和Callback在有界窗口内均不增加。
    - 正向场景：重新建立基线，Responder收到第二条消息后执行destination_release。
    - 正向观测：确认Source收到原Payload ACK且ACK事件恰好一次。
    - 终态确认：清除ACK并确认Source与Destination Pending均恢复为0。
  observations:
    - 只清中断：分别记录清除后的MAILBOX.DESTINATION_ENDPOINTS、Source Raw Pending、Source Masked Pending和ACK Service回调增量。
    - 释放前后：分别记录destination_release前后的MAILBOX.DESTINATION_ENDPOINTS。
    - Auto ACK：分别记录ACK.RECEIVED_PAYLOAD、Source Raw Pending、Source Masked Pending和ACK Service回调增量。
  pass_criteria:
    - 反向成立：只清消息中断不产生ACK。
    - 正向成立：释放Destination后产生一次ACK且Payload保持原值。
timeout: 8 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [只清中断后的ACK次数为0, 释放后的ACK次数为1, Destination释放状态, ACK数据一致]
failure_observations:
  - {key: clear_only_ack_count, label: 只清中断后的ACK回调计数, source: dut, role: actual, format: decimal}
  - {key: destination_before_release, label: 释放前MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: destination_after_release, label: 释放后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: release_ack_count, label: 释放Destination后的ACK回调计数, source: dut, role: actual, format: decimal}
  - {key: ack_payload, label: Auto ACK实际Payload, source: dut, role: actual, format: bytes_hex}
  - {key: ack_data_match, label: Auto ACK Payload一致, source: oracle, role: actual, format: bool}
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
    - Payload矩阵：两轮使用相同长度、不同内容的Payload。
    - Delivery矩阵：POLLING与IRQ。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - Polling配置：关闭Destination事件投递后发送第一条消息。
    - Polling观测：确认Raw Pending包含目标Mailbox、Masked Pending为0、Callback不增加，Peer轮询读取成功。
    - IRQ配置：重新建立基线并启用Destination事件投递，发送第二条消息。
    - IRQ观测：确认Raw和Masked Pending均包含目标Mailbox，Callback增加且Peer读取成功。
    - 终态确认：分别处理两轮消息并确认对应Raw与Masked Pending最终为0。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Polling Raw与Masked状态, Polling回调增量, IRQ Raw与Masked状态, IRQ回调增量]
failure_observations:
  - {key: polling_raw_pending, label: Polling模式Raw Pending, source: peer, role: actual, format: hex32}
  - {key: polling_masked_pending, label: Polling模式Masked Pending, source: peer, role: actual, format: hex32}
  - {key: polling_callback_count, label: Polling模式回调计数, source: peer, role: actual, format: decimal}
  - {key: polling_data_match, label: Polling模式Payload一致, source: oracle, role: actual, format: bool}
  - {key: irq_raw_pending, label: IRQ模式Raw Pending, source: peer, role: actual, format: hex32}
  - {key: irq_masked_pending, label: IRQ模式Masked Pending, source: peer, role: actual, format: hex32}
  - {key: irq_callback_count, label: IRQ模式回调计数, source: peer, role: actual, format: decimal}
  - {key: irq_data_match, label: IRQ模式Payload一致, source: oracle, role: actual, format: bool}
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
    - Payload编码：每个Mailbox使用包含mailbox_id的短Payload。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 首轮传输：配置当前parameter_id对应Mailbox，完成双Core消息与ACK并核对Payload中的mailbox_id。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
    - 正向Payload A与反向Payload B：长度相同、内容不同。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 双向配置：配置Initiator到Responder的正向Mailbox和Responder到Initiator的反向Mailbox。
    - 正向发送：Initiator发送Payload A，Responder接收并核对。
    - 反向发送：Responder在正向接收完成后通过另一Mailbox发送Payload B。
    - 终态观测：Initiator接收Payload B，比较两个方向的Mailbox、Endpoint、Pending和回调。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
    - Mailbox与Payload：选择两个不同Mailbox和两个可区分Payload。
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
    - 同时Pending：初始Raw位集合同时包含两个目标Mailbox。
    - 独立清除：第一次清除后仅剩另一个Mailbox位。
    - 数据正确：两个Payload与各自Mailbox一一对应，最终Pending为0。
timeout: 8 s
cleanup: [Abort Peer Job, Release both Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
    - 消息配置：一个固定短Payload，使用AUTO ACK模式。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 多目标配置：同一Mailbox配置两个Destination Endpoint并读取Destination快照。
    - 消息发送：Initiator发送一次Payload，Peer的两个Endpoint分别记录事件和数据。
    - 首目标释放：释放第一个Destination，确认第二个Destination仍保持且Source未收到ACK。
    - 次目标释放：释放第二个Destination，确认Destination为空且Source收到一次Auto ACK。
    - 终态确认：清除Source ACK并确认Mailbox的Destination与Pending全部为0。
  observations:
    - 多目标投递：分别记录两个Destination Endpoint的事件次数和Payload一致性。
    - 首次释放：记录首个Destination释放后的MAILBOX.DESTINATION_ENDPOINTS及Source ACK Service回调增量。
    - 最终释放：记录第二个Destination释放后的MAILBOX.DESTINATION_ENDPOINTS及Source Raw/Masked Pending。
    - 最终ACK：记录Source ACK Payload一致性和Service回调增量。
  pass_criteria:
    - 多目标投递：两个Destination均恰好收到一次相同Payload。
    - 独立释放：首个释放不清除另一个Destination且不提前ACK。
    - 最终ACK：全部Destination释放后Source恰好收到一次ACK。
timeout: 8 s
cleanup: [Abort Peer Job, Release test Mailbox, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer支持两个逻辑事件Endpoint, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [两个Destination均收到数据, 首次释放后剩余Destination, 首次释放后ACK次数为0, 最终ACK次数为1]
failure_observations:
  - {key: destination_a_event_count, label: Destination A事件次数, source: peer, role: actual, format: decimal}
  - {key: destination_b_event_count, label: Destination B事件次数, source: peer, role: actual, format: decimal}
  - {key: destination_payload_match, label: 两个Destination Payload一致, source: oracle, role: actual, format: bool}
  - {key: status_after_first_release, label: 首次释放后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: ack_after_first_release, label: 首个释放后的Source ACK计数, source: dut, role: actual, format: decimal}
  - {key: status_after_final_release, label: 最终释放后MAILBOX.DESTINATION_ENDPOINTS, source: peer, role: actual, format: hex32}
  - {key: final_ack_count, label: 全部释放后的Source ACK计数, source: dut, role: actual, format: decimal}
  - {key: final_ack_data_match, label: 最终Auto ACK Payload一致, source: oracle, role: actual, format: bool}
gap: [case_implementation_gap, multi_destination_driver_gap, dualcore_execution_mapping_gap]
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
    - Payload：链总容量减3字节的可复现二进制Pattern。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 链配置：按MANUAL ACK和LINKED配置连续Mailbox，核对每个链成员快照及末项Link终止。
    - Linked发送：Initiator一次提交完整Payload。
    - Peer处理：Responder按Pending位集合逐Mailbox读取有效字节并发送Manual ACK。
    - 重组判定：Peer按Mailbox顺序重组Payload，Initiator核对ACK链和最终完成状态。
    - 终态确认：读取全链配置和Pending，确认处理后没有遗留事件。
  observations:
    - 链配置：完整记录每个链成员的Mailbox ID、MAILBOX.LINK_MODE和末项终止状态到绑定Artifact。
    - 链事件：记录逐Mailbox Raw Pending和ACK事件顺序，并生成顺序一致性Measurement。
    - 重组摘要：记录实际总长度、数据一致性和首个错误偏移；完整Payload只进入绑定Artifact。
  pass_criteria:
    - 链配置正确：连续成员和末项Link终止准确。
    - 片段完整：每个成员只处理一次，顺序和有效长度正确。
    - 总体正确：重组Payload逐字节一致且ACK链完成。
timeout: 15 s
cleanup: [Abort Peer Job, Release linked Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Linked链范围, 重组总长度, 重组数据一致, Pending与ACK顺序一致]
failure_observations:
  - {key: linked_range, label: Linked Mailbox范围, source: dut_config, role: config, format: text}
  - {key: reconstructed_length, label: Responder重组Payload长度, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: 重组Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: first_mismatch_offset, label: 首个Payload错误偏移, source: oracle, role: actual, format: decimal}
  - {key: pending_sequence_match, label: 逐Mailbox Pending顺序一致, source: oracle, role: actual, format: bool}
  - {key: ack_sequence_match, label: 逐Mailbox ACK顺序一致, source: oracle, role: actual, format: bool}
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
    - Payload：链总容量减3字节且与P2_001不同的二进制Pattern。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 链配置：按AUTO ACK和LINKED配置连续Mailbox并核对链成员。
    - Linked发送：Initiator一次提交完整Payload。
    - Peer处理：Responder逐Mailbox读取片段并通过destination_release推进Auto ACK链。
    - 重组判定：比较完整Payload，核对每个成员释放后状态和Initiator最终ACK完成。
    - 终态确认：读取全链Destination、Raw和Masked Pending，确认均清零。
  observations:
    - 链配置：完整记录每个链成员的MAILBOX.LINK_MODE和MAILBOX.ACK_MODE到绑定Artifact。
    - 释放事件：记录逐Mailbox Destination释放、Raw Pending和Auto ACK顺序，并生成顺序一致性Measurement。
    - 重组摘要：记录实际总长度、数据一致性和首个错误偏移；完整Payload只进入绑定Artifact。
    - 终态硬件：分别记录全链Destination、Raw Pending和Masked Pending是否清零。
  pass_criteria:
    - 链数据完整：所有片段按顺序重组且逐字节一致。
    - Auto ACK正确：每个Destination释放推进对应ACK，不丢失、不重复。
    - 终态干净：全部链成员Destination和Pending均清零。
timeout: 15 s
cleanup: [Abort Peer Job, Release linked Mailboxes, Reset IPCM instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [重组总长度, 重组数据一致, Destination释放顺序一致, Auto ACK顺序一致]
failure_observations:
  - {key: reconstructed_length, label: Responder重组Payload长度, source: peer, role: actual, format: decimal}
  - {key: payload_data_match, label: 重组Payload逐字节一致, source: oracle, role: actual, format: bool}
  - {key: first_mismatch_offset, label: 首个Payload错误偏移, source: oracle, role: actual, format: decimal}
  - {key: destination_release_sequence_match, label: Destination释放顺序一致, source: oracle, role: actual, format: bool}
  - {key: ack_sequence_match, label: Auto ACK顺序一致, source: oracle, role: actual, format: bool}
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
  2. IPCM Mailbox释放与复用
  3. IPCM同Mailbox连续分段传输
p_level: P2
feature_refs: [IPCM_F_003, IPCM_F_011, IPCM_F_015]
method:
  inputs:
    - 总Payload：大于三个单Mailbox容量的可复现二进制Pattern。
    - 分段策略：按单Mailbox容量切分，最后一段使用非4字节对齐长度。
  steps:
    - 基线建立：复位IPCM实例、Service状态和Resource Pool，确认片内Peer Ready。
    - 单Mailbox配置：配置MANUAL ACK模式并启动连续接收Peer Job。
    - 分段循环：Initiator发送当前分段并等待对应ACK完成后再发送下一段。
    - Peer重组：Responder按事件顺序记录每段有效长度和Payload并追加到结果缓冲区。
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
resources: {minimum_level: R2, full_coverage_level: R2, board: ET6801双Core Peer已部署, bench: 无外部接线}
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
| ET6801 | IMPLEMENTATION_GAP=15 | IMPLEMENTATION_GAP=1; MAPPING_GAP=11 | Hardware Truth与Case Plan已闭合；Capability语义、IPCM公共代码和双Core Peer Job尚未实现 | `ET6801_ipcm.md` |

## 5. Common Gap / Evolution

- `case_implementation_gap`：当前自动化平台尚无 IPCM Wrap、Service、PC Driver 和 Formal Case。
- `capability_semantic_gap`：当前ET6801 `ipcm.yaml`只有实例、Base和16个IRQ，尚未表达Mailbox、Channel、Data Word、模式、Linked和Multi-destination能力。
- `dualcore_execution_mapping_gap`：必须建立逻辑Initiator/Responder、事件Endpoint和Core1 Peer部署映射；公共Case不得硬编码Core或IRQ编号。
- `linked_range_driver_gap`：Linked配置必须同时验证起始Mailbox与链长度边界，禁止越界或静默截断。
- `multi_destination_driver_gap`：正式Driver只接收单一Destination Channel，需要在Driver测试扩展区增加逻辑Endpoint集合接口。
- `driver_api_gap`：正式Driver缺少明确返回值、完整Pending位集合、配置快照、严格Payload边界和非对齐安全访问；Wrap不得直接操作寄存器补洞。
- `CORE2CORE`独立门铃中断不属于IPCM Mailbox Feature，必须由Dual-Core/CPU独立Contract承接，不能混入本IP。
- 3101和6003为单核目标，本轮没有读取、映射或继承其资料；未来若某芯片无片内Peer，应由Capability明确不支持，而不是删除公共Feature。
