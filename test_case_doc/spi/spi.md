# SPI Stable IP Contract

> 本文件定义 SPI 的芯片中立 Feature、Case、Oracle、Observation、资源和稳定自动化动作。
> 芯片实例、寄存器、引脚、SDK API、DMA Request 和目标适配差异只进入同目录 `<CHIP>_spi.md`。
> 内部回环只能作为基础数据路径检查，不能替代真实 PAD、SCLK、CS、MOSI 和 MISO 的外部验证。

## 0. Stable IP Contract

### 0.1 稳定配置语义

| 稳定对象 | 公共语义 | 约束 |
|---|---|---|
| `instance_id` | SPI 逻辑实例 | Case 从 Capability 选择实例，不写死芯片实例名。 |
| `role` | `CONTROLLER` / `TARGET` | 旧术语 Master/Slave 只允许出现在芯片资料引用中。 |
| `frame_format` | `MOTOROLA_SPI` / `TI_SSP` / `MICROWIRE` | 支持集合由 Capability 发布。 |
| `clock_mode` | `MODE0` / `MODE1` / `MODE2` / `MODE3` | 等价于 CPOL/CPHA 的四种组合。 |
| `frame_bits` | 单帧有效位宽 | 合法最小值、最大值和离散集合由 Capability 发布。 |
| `transfer_mode` | `TX_RX` / `TX_ONLY` / `RX_ONLY` / `EEPROM_READ` | 不支持的模式必须由 Capability 拒绝，不由 Case 猜测。 |
| `bitrate_hz` | 目标串行时钟频率 | Driver 根据目标输入时钟换算分频；Case 使用 Capability 发布的可达频率点。 |
| `frame_count` | 本次接收帧数 | 必须大于 0；Wire 和 Wrap 不暴露芯片寄存器的减一编码。 |
| `cs_policy` | `AUTO` / `SOFTWARE_HOLD` / `FRAME_TOGGLE` | 目标支持集合和 CS 数量由 Capability 发布。 |
| `rx_sample_delay` | RX 采样延迟逻辑值 | 合法范围由 Capability 发布；不直接暴露寄存器位宽。 |
| `target_output_enabled` | Target 发送输出使能 | 只控制 Target 输出驱动，不隐式改变角色或传输模式。 |

### 0.2 稳定 Observation Endpoint

| Endpoint | 来源 | 原子事实 |
|---|---|---|
| `CONFIG.*` | `dut` | Role、Frame Format、Clock Mode、Frame Bits、Transfer Mode、Bitrate、Frame Count、CS Policy、RX Sample Delay 的硬件读回。 |
| `STATUS.BUSY` | `dut` | SPI 正在传输。 |
| `STATUS.TX_NOT_FULL` / `TX_EMPTY` | `dut` | TX FIFO 可写及空状态。 |
| `STATUS.RX_NOT_EMPTY` / `RX_FULL` | `dut` | RX FIFO 有数据及满状态。 |
| `STATUS.TARGET_TX_ERROR` | `dut` | Target 发送请求时无有效数据。 |
| `STATUS.CONTROLLER_COLLISION` | `dut` | 多 Controller 总线争用状态。 |
| `FIFO.TX_LEVEL` / `RX_LEVEL` | `dut` | FIFO 当前有效帧数。 |
| `FIFO.TX_THRESHOLD` / `RX_THRESHOLD` / `START_THRESHOLD` | `dut` | FIFO 中断和启动阈值配置读回。 |
| `IRQ.RAW` / `IRQ.STATUS` / `IRQ.MASK` | `dut` | Mask 前、Mask 后和屏蔽配置三类独立中断事实。 |
| `IRQ_EVENT.COUNT` / `IRQ_EVENT.SOURCE` | `dut` | 真实进入 SPI 中断向量的次数和固件锁存 Source。 |
| `TRANSFER.TX_COUNT` / `RX_COUNT` | `measurement` | 实际完成的发送、接收帧数。 |
| `TRANSFER.RX_DATA` | `dut` | DUT 实际收到的数据。 |
| `DMA.CHANNEL_STATUS` / `DMA.DESTINATION_DATA` | `peer` | DMA 终态及目标缓冲区内容。 |
| `SPI_WAVEFORM.SCLK_HZ` | `instrument` | 外部观测到的 SCLK 频率。 |
| `SPI_WAVEFORM.CPOL` / `CPHA` | `instrument` | 外部观测到的空闲电平和采样边沿。 |
| `SPI_WAVEFORM.CS_FRAME_COUNT` | `instrument` | CS 有效窗口和帧数量。 |
| `SPI_WAVEFORM.MOSI_DATA` / `MISO_DATA` | `instrument` | 外部解码得到的双向数据。 |

### 0.3 稳定自动化动作

| 动作 | 请求语义 | 约束 |
|---|---|---|
| `capabilities_get` | 获取实例、角色、协议、位宽、模式、频率、FIFO、IRQ、DMA 和采样延迟能力 | 只返回目标硬件事实，不返回 Case 策略。 |
| `configure` | 配置 Role、Format、Mode、Frame Bits、Transfer Mode、Bitrate、Frame Count、CS 和 RX Sample Delay | 接口及参数芯片中立；不暴露 SDK 类型。 |
| `enable` / `disable` | 启停指定实例 | 不隐式执行 Case 流程。 |
| `fifo_reset` | 同时或分别复位 TX/RX FIFO | 复位完成后必须可读取 FIFO Level。 |
| `loopback_set` | 开关片内 Shift-register Loopback | 只用于基础检查，不能代替外部 PAD Case。 |
| `write_frames` / `read_frames` | 执行一次有界帧读写动作 | Firmware 不进行无限轮询；长传输由 PC deadline 驱动多次原子动作。 |
| `status_snapshot_get` | 读取状态和 FIFO Level | 返回原始稳定事实。 |
| `irq_configure` / `irq_snapshot_get` / `irq_event_clear` | 配置、读取和清除 SPI 中断 | Raw、Status、Mask、Delivery 必须分开。 |
| `dma_configure` | 配置 SPI DMA Request 和 Watermark | DMA Channel 的建立与结果由 DMA Driver/Case 协调，SPI Service 不调用 DMA Wrap。 |

### 0.4 Oracle、隔离和接线规则

- 每个 Case 在第一次配置前对所有参与的 SPI 实例执行 CRG Reset，并执行 Service State Reset 和 Resource Pool Reset。
- 多 IP Case 只在 PC Case 中组合 SPI Driver、DMA Driver和仪器 Driver；Firmware SPI Service 只能调用 SPI Wrap。
- Firmware 同步命令只执行一次原子动作；统一 deadline、重试和流程编排由 PC Driver/Case 持有。
- API 返回成功不能替代硬件事实；数据 Case 必须比较实际帧数和实际数据，IRQ Case 必须记录 Raw/Status/Delivery。
- 外部 Case 的接线由 Board/Bench Profile 提供，Case 只声明逻辑端点，不写死具体芯片的GPIO、接插件或仪器通道。
- 同实例被动回接使用 `Controller MOSI -> 同实例 MISO`，同时由数字 Observer 观察 SCLK 和 CS；它验证真实 PAD 输入/输出路径，但不证明 Target 角色。
- 双实例配对使用 `Controller SCLK -> Target SCLK`、`Controller CS -> Target CS`、`Controller MOSI -> Target RX`、`Target TX -> Controller MISO` 和共地；它独立验证 Controller、Target 及双向 PAD 数据链路。
- Case 结束时 Disable 参与实例、关闭 IRQ/DMA、清除本 Case 状态并执行实例 Reset；下一 Case 仍重新建立完整基线。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联 Case |
|---|---|---|---|
| SPI_F_001 | SPI模块Enable/Disable与FIFO复位 | 模块可独立启停，TX/RX FIFO 可恢复为空。 | `SPI_P0_001`, `SPI_P1_004` |
| SPI_F_002 | SPI Controller/Target角色 | 支持能力声明的 Controller 和 Target 工作角色。 | `SPI_P0_001`, `SPI_P1_002` |
| SPI_F_003 | SPI CPOL/CPHA四种模式 | Motorola SPI 支持 MODE0 至 MODE3。 | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002`, `SPI_P1_006` |
| SPI_F_004 | SPI 4至16-bit帧宽 | 支持能力声明范围内的帧位宽。 | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_005 | SPI TX_RX/TX_ONLY/RX_ONLY/EEPROM_READ模式 | 支持四类传输模式及对应收发方向。 | `SPI_P1_003` |
| SPI_F_006 | SPI SCLK分频与Bitrate | Controller 可按 Capability 配置串行时钟频率。 | `SPI_P0_001`, `SPI_P1_001`, `SPI_P1_006`, `SPI_P2_003` |
| SPI_F_007 | SPI片内移位链路Loopback | 片内回环可完成基础收发。 | `SPI_P0_002` |
| SPI_F_008 | SPI外部PAD数据链路 | SCLK、CS、MOSI和MISO通过真实 PAD 完成传输。 | `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_009 | SPI CS自动、保持与逐帧切换 | CS 支持自动控制、软件保持和逐帧切换策略。 | `SPI_P1_006` |
| SPI_F_010 | SPI接收帧数量控制 | RX_ONLY和EEPROM_READ按配置帧数产生接收时钟。 | `SPI_P1_003` |
| SPI_F_011 | SPI TX/RX FIFO深度、Level与复位 | FIFO 容量、Level变化和复位行为准确。 | `SPI_P1_004` |
| SPI_F_012 | SPI FIFO中断阈值与启动阈值 | TX/RX中断阈值及发送启动阈值可配置并生效。 | `SPI_P1_004`, `SPI_P1_005` |
| SPI_F_013 | SPI BUSY与FIFO状态 | BUSY、TX/RX可用和满空状态随传输变化。 | `SPI_P0_002`, `SPI_P1_002`, `SPI_P1_004` |
| SPI_F_014 | SPI TXE/TXO/RXU/RXO/RXF中断 | FIFO中断支持Mask、Raw、Status、Delivery和Clear生命周期。 | `SPI_P1_005` |
| SPI_F_015 | SPI DMA TX/RX请求与Watermark | SPI可按Watermark产生TX/RX DMA Request。 | `SPI_P2_001` |
| SPI_F_016 | SPI RX采样延迟 | Controller 可配置RX采样延迟并在高速链路中保持接收。 | `SPI_P2_003` |
| SPI_F_017 | SPI Motorola/TI SSP/Microwire帧格式 | 支持 Capability 声明的串行帧格式。 | `SPI_P2_002` |
| SPI_F_018 | SPI Target输出使能 | Target输出可独立启停，关闭后不驱动返回数据。 | `SPI_P1_002` |
| SPI_F_019 | SPI多Controller冲突状态与中断 | 总线争用可产生 Collision 状态和 Multi-Controller IRQ。 | `SPI_P2_004` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---:|---|---|---|---:|---|
| SPI_P0_001 | P0 | SPI基础配置与硬件读回测试 | 模块、角色、Bitrate、基础配置 | 每项稳定配置读回等于输入 | R0 | PLANNED |
| SPI_P0_002 | P0 | SPI片内回环模式与帧宽测试 | CPOL/CPHA、帧宽、片内回环、状态 | 各代表节点实际数据一致且终态正确 | R0 | PLANNED |
| SPI_P1_001 | P1 | SPI单实例外部MOSI-MISO回接测试 | 真实PAD、Mode、帧宽、Bitrate | DUT接收数据一致且外部SCLK/CS有效 | R2 | PLANNED |
| SPI_P1_002 | P1 | SPI双实例Controller-Target双向测试 | 双角色、真实PAD、双向数据、Target输出 | 两端接收数据均与对端发送数据一致 | R2 | PLANNED |
| SPI_P1_003 | P1 | SPI四种Transfer Mode与Frame Count测试 | 四种传输模式、接收帧数 | 各模式方向和帧数与配置一致 | R2 | PLANNED |
| SPI_P1_004 | P1 | SPI FIFO容量、阈值、Level与复位测试 | FIFO、阈值、状态 | Level逐步变化、容量边界和复位值正确 | R1 | PLANNED |
| SPI_P1_005 | P1 | SPI FIFO中断生命周期测试 | 五类FIFO IRQ | 每个Source的Raw/Status/Delivery/Clear独立正确 | R1 | PLANNED |
| SPI_P1_006 | P1 | SPI CS策略与时序观测测试 | CS自动/保持/切换、CPOL/CPHA | 外部解码的CS窗口、边沿和帧数符合配置 | R3 | PLANNED |
| SPI_P2_001 | P2 | SPI DMA双向传输测试 | TX/RX DMA Request、Watermark | DMA完成且目标数据完整一致 | R2 | PLANNED |
| SPI_P2_002 | P2 | SPI帧格式协议测试 | Motorola/TI SSP/Microwire | FPGA Peer解码协议、位数和数据均正确 | R3 | PLANNED |
| SPI_P2_003 | P2 | SPI高速Bitrate与RX采样延迟测试 | Bitrate、采样延迟 | 外部频率正确且选定延迟点数据无误码 | R3 | PLANNED |
| SPI_P2_004 | P2 | SPI多Controller总线冲突测试 | Collision、Multi-Controller IRQ | 受控争用产生状态和IRQ并可恢复 | R3 | PLANNED |

## 3. Machine-readable Case Contract

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P0_001
case_name: SPI基础配置与硬件读回测试
report_feature: |-
  1. SPI模块Enable/Disable与FIFO复位
  2. SPI Controller/Target角色
  3. SPI SCLK分频与Bitrate
p_level: P0
feature_refs: [SPI_F_001, SPI_F_002, SPI_F_006]
method:
  inputs:
    - 角色矩阵：Capability发布的Controller和Target角色。
    - 基础配置：一个合法Clock Mode、8-bit帧宽、TX_RX模式、代表Bitrate和CS策略。
  steps:
    - 基线建立：复位目标SPI实例、Service状态和Resource Pool。
    - Controller配置：Disable实例后写入Controller基础配置并Enable。
    - Controller观测：读取CONFIG和Enable硬件状态。
    - Target配置：重新复位实例，写入Target基础配置并Enable。
    - Target观测：读取CONFIG和Enable硬件状态。
    - 关闭观测：Disable实例并确认Enable状态为0。
  observations:
    - 配置硬件读回：记录Role、Clock Mode、Frame Bits、Transfer Mode、Bitrate、CS Policy和Enable实际值。
  pass_criteria:
    - Controller配置正确：全部稳定字段与输入一致。
    - Target配置正确：全部稳定字段与输入一致。
    - 启停正确：Enable和Disable状态与动作一致。
timeout: 5 s
cleanup: [Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [SPI CONFIG硬件快照]
failure_observations:
  - {key: expected_config, label: 期望SPI稳定配置, source: oracle, role: expected, format: text}
  - {key: actual_config, label: SPI CONFIG硬件实际值, source: dut, role: actual, format: text}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P0_002
case_name: SPI片内回环模式与帧宽测试
report_feature: |-
  1. SPI CPOL/CPHA四种模式
  2. SPI 4至16-bit帧宽
  3. SPI片内移位链路Loopback
  4. SPI BUSY与FIFO状态
p_level: P0
feature_refs: [SPI_F_003, SPI_F_004, SPI_F_007, SPI_F_013]
method:
  inputs:
    - Clock Mode矩阵：MODE0、MODE1、MODE2和MODE3。
    - 帧宽矩阵：Capability最小值、8-bit和最大值；重复节点去重。
    - 数据：每个组合使用短小且不对称的帧序列。
  steps:
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 回环配置：配置Controller、当前Mode和Frame Bits，Enable片内Loopback。
    - 数据激励：写入本轮帧序列并以有界轮询读取同等帧数。
    - 数据观测：保存实际TX/RX帧数和RX数据。
    - 状态观测：读取BUSY、TX_EMPTY和RX_NOT_EMPTY终态。
    - 矩阵执行：每个组合重新复位并重复配置、激励和观测。
  observations:
    - 回环数据：记录每个Mode/Frame Bits组合的TX数据、RX数据和帧数。
    - 传输终态：记录BUSY和FIFO状态原始值。
  pass_criteria:
    - 数据正确：所有组合的RX数据逐帧等于TX数据。
    - 帧数正确：实际TX/RX帧数等于请求帧数。
    - 终态正确：传输完成后BUSY=0且TX为空。
timeout: 10 s统一矩阵deadline
cleanup: [Disable Loopback, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [模式位宽矩阵数据与状态快照]
failure_observations:
  - {key: active_mode_and_bits, label: 当前Clock Mode与Frame Bits, source: dut_config, role: config, format: text}
  - {key: expected_rx_frames, label: 期望回环帧数据, source: oracle, role: expected, format: bytes_hex}
  - {key: actual_rx_frames, label: 实际回环帧数据, source: dut, role: actual, format: bytes_hex}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_001
case_name: SPI单实例外部MOSI-MISO回接测试
report_feature: |-
  1. SPI外部PAD数据链路
  2. SPI CPOL/CPHA四种模式
  3. SPI 4至16-bit帧宽
  4. SPI SCLK分频与Bitrate
p_level: P1
feature_refs: [SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_006]
method:
  inputs:
    - 外部接线：Board Profile把代表SPI实例的MOSI短接到同实例MISO，并把SCLK和CS连接到数字Observer，共地。
    - 配置矩阵：四种Clock Mode、8-bit与Capability边界帧宽、低中高三个可达Bitrate点。
    - 数据：每个组合发送至少两组非对称Pattern。
  steps:
    - 接线门禁：读取Bench Profile并确认MOSI-MISO回接及SCLK/CS Observer映射存在。
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 外部模式配置：关闭片内Loopback，配置Controller和当前矩阵节点。
    - 真实PAD激励：从MOSI输出数据，经外部导线返回MISO并读取RX数据。
    - 波形观测：Observer捕获SCLK和CS，测量SCLK频率及CS有效窗口。
    - 矩阵执行：每个节点重新复位后重复数据和波形观测。
    - 结果判定：比较RX数据、帧数、SCLK频率和CS活动事实。
  observations:
    - 外部回接数据：记录MOSI期望数据和MISO实际接收数据。
    - 外部时钟与片选：记录SCLK_HZ和CS有效窗口；证明数据确实经过真实PAD传输。
  pass_criteria:
    - PAD数据正确：所有矩阵节点的RX数据逐帧等于TX数据。
    - 外部信号有效：每轮均观测到SCLK和CS，SCLK频率处于目标容差内。
    - 帧数正确：外部解码帧数和DUT接收帧数均等于请求帧数。
timeout: 20 s统一矩阵deadline
cleanup: [Stop Observer, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R3, board: MOSI到MISO外部短接并共地, bench: 最低需SCLK和CS数字捕获；完整覆盖解码四线SPI}
backend: [FPGA, Silicon]
evidence: [DUT RX数据 + 外部SCLK频率和CS窗口]
failure_observations:
  - {key: bench_mapping, label: 外部回接与Observer映射, source: bench, role: config, format: text}
  - {key: expected_pad_data, label: 期望MOSI帧数据, source: oracle, role: expected, format: bytes_hex}
  - {key: actual_pad_data, label: MISO实际接收帧数据, source: dut, role: actual, format: bytes_hex}
  - {key: measured_sclk_hz, label: 外部观测SCLK频率, source: instrument, role: actual, format: decimal}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_002
case_name: SPI双实例Controller-Target双向测试
report_feature: |-
  1. SPI Controller/Target角色
  2. SPI外部PAD数据链路
  3. SPI CPOL/CPHA四种模式
  4. SPI 4至16-bit帧宽
  5. SPI Target输出使能
p_level: P1
feature_refs: [SPI_F_002, SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_018]
method:
  inputs:
    - 逻辑实例：Capability选择一个Controller实例和一个Target实例，不写死实例编号。
    - 外部接线：Controller SCLK到Target SCLK、Controller CS到Target CS、Controller MOSI到Target RX、Target TX到Controller MISO并共地。
    - 数据：Controller和Target分别准备内容不同的短帧序列。
  steps:
    - 接线门禁：确认Board Profile发布完整四线Controller-Target映射。
    - 基线建立：复位两个SPI实例、Service状态和Resource Pool。
    - Target准备：配置Target、Enable输出并预装Target发送数据。
    - Controller准备：配置相同Mode和Frame Bits的Controller并准备发送数据。
    - 双向激励：Controller发起统一时钟下的全双工传输。
    - 双端观测：读取Controller RX和Target RX数据、帧数及双方终态。
    - 输出关闭检查：重新复位后关闭Target输出，执行短传输并确认Target RX仍有效且Controller不再收到预装返回数据。
  observations:
    - Controller接收：记录Target预装数据和Controller实际RX数据。
    - Target接收：记录Controller发送数据和Target实际RX数据。
    - Target输出关闭：记录关闭前后Controller RX差异和Target RX完整性。
  pass_criteria:
    - 双向数据正确：Controller和Target接收数据分别等于对端发送数据。
    - 帧数正确：两端完成帧数均等于请求帧数。
    - 输出控制正确：关闭Target输出后Target仍可接收，Controller不再得到原预装返回数据。
timeout: 15 s
cleanup: [Disable both SPI instances, Reset both SPI instances, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 两个SPI实例四线交叉连接并共地, bench: 无额外仪器要求}
backend: [FPGA, Silicon]
evidence: [Controller与Target双向数据和状态快照]
failure_observations:
  - {key: controller_instance, label: Controller逻辑实例, source: dut_config, role: config, format: text}
  - {key: target_instance, label: Target逻辑实例, source: dut_config, role: config, format: text}
  - {key: controller_rx_data, label: Controller实际RX数据, source: dut, role: actual, format: bytes_hex}
  - {key: target_rx_data, label: Target实际RX数据, source: dut, role: actual, format: bytes_hex}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_003
case_name: SPI四种Transfer Mode与Frame Count测试
report_feature: |-
  1. SPI TX_RX/TX_ONLY/RX_ONLY/EEPROM_READ模式
  2. SPI接收帧数量控制
p_level: P1
feature_refs: [SPI_F_005, SPI_F_010]
method:
  inputs:
    - 连接：复用双实例Controller-Target四线连接。
    - 模式矩阵：TX_RX、TX_ONLY、RX_ONLY和EEPROM_READ。
    - 帧数矩阵：1帧、代表短帧数和Capability允许的有界边界节点。
  steps:
    - 基线建立：复位两个SPI实例、Service状态和Resource Pool。
    - TX_RX执行：两端准备数据，执行全双工传输并保存双向结果。
    - TX_ONLY执行：重新复位配置，只验证Controller TX到Target RX路径。
    - RX_ONLY执行：重新复位配置，Target预装数据，Controller按Frame Count产生接收时钟。
    - EEPROM执行：重新复位配置，Controller先发命令帧，再按Frame Count接收Target返回帧。
    - 帧数判定：逐模式比较请求、实际发送、实际接收和外部时钟帧数。
  observations:
    - 方向事实：记录每种模式两端实际TX/RX帧数和数据。
    - Frame Count事实：记录配置帧数和实际产生的接收时钟/接收帧数。
  pass_criteria:
    - 模式方向正确：四种模式只产生定义内的发送和接收行为。
    - 数据正确：定义为有效的接收方向数据逐帧匹配。
    - Frame Count正确：RX_ONLY和EEPROM_READ实际接收帧数等于配置值。
timeout: 20 s统一矩阵deadline
cleanup: [Disable both SPI instances, Reset both SPI instances, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 两个SPI实例四线交叉连接并共地, bench: 无额外仪器要求}
backend: [FPGA, Silicon]
evidence: [四种模式方向、帧数和数据结果]
failure_observations:
  - {key: active_transfer_mode, label: 当前Transfer Mode, source: dut_config, role: config, format: text}
  - {key: expected_frame_count, label: 期望接收帧数, source: oracle, role: expected, format: decimal}
  - {key: actual_frame_count, label: 实际接收帧数, source: dut, role: actual, format: decimal}
  - {key: actual_rx_data, label: 实际接收数据, source: dut, role: actual, format: bytes_hex}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_004
case_name: SPI FIFO容量、阈值、Level与复位测试
report_feature: |-
  1. SPI模块Enable/Disable与FIFO复位
  2. SPI TX/RX FIFO深度、Level与复位
  3. SPI FIFO中断阈值与启动阈值
  4. SPI BUSY与FIFO状态
p_level: P1
feature_refs: [SPI_F_001, SPI_F_011, SPI_F_012, SPI_F_013]
method:
  inputs:
    - FIFO容量：从Capability读取，不在公共Case写死。
    - 阈值矩阵：0、代表中间值和合法最大值。
  steps:
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 阈值配置：逐组写入TX、RX和Start Threshold并读取硬件值。
    - TX Level刺激：在不启动外部时钟的受控配置下逐帧写TX FIFO并读取Level。
    - 容量边界：写到Capability容量，确认Level和TX_NOT_FULL/TX_EMPTY状态。
    - RX Level刺激：使用片内回环产生受控RX数据并逐帧读取Level。
    - FIFO复位：执行TX/RX FIFO Reset并读取Level和满空状态。
    - 结果判定：比较阈值、Level递增递减、容量边界和复位终态。
  observations:
    - FIFO配置：记录三个Threshold硬件读回。
    - FIFO动态状态：记录每次读写后的TX/RX Level和满空状态。
  pass_criteria:
    - 阈值正确：全部合法节点读回等于输入。
    - Level正确：TX/RX Level随实际帧写入和读取逐帧变化。
    - 容量正确：到达Capability容量时状态符合定义且不越界。
    - 复位正确：FIFO Reset后TX_LEVEL=0、RX_LEVEL=0且TX_EMPTY=1。
timeout: 10 s
cleanup: [FIFO Reset, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无额外要求, bench: 片内回环用于受控RX填充}
backend: [FPGA, Silicon]
evidence: [FIFO阈值、Level和状态序列]
failure_observations:
  - {key: fifo_capacity, label: Capability声明FIFO容量, source: capability, role: config, format: decimal}
  - {key: expected_fifo_level, label: 期望FIFO Level, source: oracle, role: expected, format: decimal}
  - {key: actual_fifo_level, label: 实际FIFO Level, source: dut, role: actual, format: decimal}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_005
case_name: SPI FIFO中断生命周期测试
report_feature: |-
  1. SPI FIFO中断阈值与启动阈值
  2. SPI TXE/TXO/RXU/RXO/RXF中断
p_level: P1
feature_refs: [SPI_F_012, SPI_F_014]
method:
  inputs:
    - 中断矩阵：TX Empty、TX Overflow、RX Underflow、RX Overflow和RX Full。
    - 阈值：为TX Empty和RX Full选择可稳定达到的代表Threshold。
  steps:
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool，清空事件计数。
    - Source隔离：每轮只Enable并Unmask一个目标Source，其余Source保持Mask。
    - 自然刺激：按Source分别执行空TX、满TX后额外写、空RX读、满RX后继续接收和达到RX Threshold。
    - 状态观测：在Clear前读取IRQ.RAW、IRQ.STATUS、IRQ.MASK和IRQ_EVENT。
    - Mask验证：保持Raw条件，Mask目标Source并确认Status/Delivery被屏蔽而Raw仍可追溯。
    - Clear验证：清除目标Source，解除刺激并确认Raw/Status恢复。
    - 矩阵执行：每个Source重新复位并重复独立生命周期。
  observations:
    - 中断硬件事实：记录每个Source的RAW、STATUS和MASK位。
    - 中断交付事实：记录IRQ_EVENT.COUNT增量和锁存SOURCE。
  pass_criteria:
    - Source可触发：每个目标Source在对应自然刺激下Raw置位。
    - Mask语义正确：Unmask时Status/Delivery有效，Mask时Status被屏蔽。
    - Clear正确：解除刺激并Clear后Raw、Status和事件基线恢复。
timeout: 15 s统一中断矩阵deadline
cleanup: [Mask and Disable all SPI IRQ sources, Clear SPI IRQ, FIFO Reset, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无额外要求, bench: 片内回环或受控无时钟状态产生FIFO刺激}
backend: [FPGA, Silicon]
evidence: [IRQ Raw、Status、Mask、Delivery和Clear矩阵]
failure_observations:
  - {key: active_irq_source, label: 当前SPI IRQ Source, source: dut_config, role: config, format: text}
  - {key: irq_raw, label: IRQ.RAW实际值, source: dut, role: actual, format: hex32}
  - {key: irq_status, label: IRQ.STATUS实际值, source: dut, role: actual, format: hex32}
  - {key: irq_event_count, label: IRQ_EVENT.COUNT实际增量, source: dut, role: actual, format: decimal}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_006
case_name: SPI CS策略与时序观测测试
report_feature: |-
  1. SPI CS自动、保持与逐帧切换
  2. SPI CPOL/CPHA四种模式
  3. SPI SCLK分频与Bitrate
p_level: P1
feature_refs: [SPI_F_009, SPI_F_003, SPI_F_006]
method:
  inputs:
    - CS策略矩阵：AUTO、SOFTWARE_HOLD和FRAME_TOGGLE中由Capability支持的策略。
    - Mode矩阵：MODE0至MODE3；数据使用固定多帧Pattern。
    - Observer：逻辑分析仪或FPGA捕获SCLK、CS和MOSI。
  steps:
    - 接线门禁：确认SPI信号到Observer的Profile映射和采样率满足目标Bitrate。
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 策略配置：配置当前CS策略、Clock Mode、Bitrate和多帧数据。
    - 波形捕获：开始Observer捕获后执行一次有界多帧传输。
    - 波形解码：得到SCLK频率、空闲电平、采样边沿、CS有效窗口和帧数量。
    - 矩阵执行：每个策略和Mode节点重新复位并重复捕获。
    - 结果判定：逐项比较外部波形事实与配置语义。
  observations:
    - CS波形：记录CS有效窗口数量、持续时间和帧边界位置。
    - SCLK波形：记录SCLK_HZ、CPOL和CPHA解码结果。
  pass_criteria:
    - CS策略正确：AUTO、HOLD和TOGGLE的窗口行为分别符合定义。
    - 时钟模式正确：四种Mode的CPOL/CPHA外部解码等于配置。
    - 帧数量正确：Observer解码帧数等于请求帧数。
timeout: 20 s统一波形矩阵deadline
cleanup: [Stop Observer, Release software-held CS, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R3, full_coverage_level: R3, board: SCLK、CS和MOSI可连接数字Observer, bench: FPGA捕获或逻辑分析仪}
backend: [FPGA, Silicon]
evidence: [外部SPI波形解码和DUT配置快照]
failure_observations:
  - {key: expected_cs_policy, label: 期望CS策略, source: oracle, role: expected, format: text}
  - {key: actual_cs_windows, label: 外部观测CS窗口, source: instrument, role: actual, format: text}
  - {key: actual_clock_mode, label: 外部解码CPOL/CPHA, source: instrument, role: actual, format: text}
gap: [case_implementation_gap, bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_001
case_name: SPI DMA双向传输测试
report_feature: |-
  1. SPI DMA TX/RX请求与Watermark
p_level: P2
feature_refs: [SPI_F_015]
method:
  inputs:
    - 连接：复用双实例Controller-Target四线连接。
    - DMA方向：Memory到Controller TX FIFO和Target RX FIFO到Memory；反向路径按Capability再执行一轮。
    - 数据：长度跨越FIFO容量的非对称Pattern。
  steps:
    - 基线建立：复位两个SPI实例、DMA实例、Service状态和Resource Pool。
    - SPI配置：配置Controller/Target相同模式和DMA Watermark。
    - DMA配置：由PC DMA Driver配置M2P和P2M通道，不由SPI Service调用DMA Wrap。
    - 双向启动：先Arm接收DMA，再Arm发送DMA，最后Enable SPI传输。
    - 完成等待：按统一deadline轮询DMA Channel和SPI BUSY终态。
    - 数据观测：读取DMA目标Buffer和双方完成帧数。
    - 恢复检查：Disable DMA Request后执行一次短CPU传输，确认SPI可继续工作。
  observations:
    - DMA终态：记录发送、接收Channel状态和传输计数。
    - 目标数据：记录Expected Pattern和DMA Destination实际数据。
  pass_criteria:
    - DMA完成：参与Channel均在deadline内进入成功终态。
    - 数据正确：目标Buffer逐字节等于Expected Pattern。
    - SPI恢复：关闭DMA后短CPU传输仍成功。
timeout: 按Bitrate和数据长度计算有界deadline并增加统一调度裕量
cleanup: [Disable SPI DMA requests, Stop DMA channels, Disable both SPI instances, Reset SPI and DMA instances, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 两个SPI实例四线交叉连接并共地, bench: 无额外仪器要求}
backend: [FPGA, Silicon]
evidence: [DMA Channel终态、SPI状态和目标Buffer]
failure_observations:
  - {key: dma_tx_status, label: SPI TX DMA Channel状态, source: peer, role: actual, format: text}
  - {key: dma_rx_status, label: SPI RX DMA Channel状态, source: peer, role: actual, format: text}
  - {key: expected_dma_data, label: 期望DMA目标数据, source: oracle, role: expected, format: bytes_hex}
  - {key: actual_dma_data, label: 实际DMA目标数据, source: peer, role: actual, format: bytes_hex}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_002
case_name: SPI帧格式协议测试
report_feature: |-
  1. SPI Motorola/TI SSP/Microwire帧格式
p_level: P2
feature_refs: [SPI_F_017]
method:
  inputs:
    - 协议矩阵：Capability发布的Motorola SPI、TI SSP和Microwire格式。
    - FPGA Peer：按当前协议产生和采集SCLK、CS、MOSI和MISO。
    - 数据：每种协议使用相同逻辑Payload和代表帧宽。
  steps:
    - 能力门禁：读取目标支持的Frame Format并只执行发布项。
    - Bench门禁：加载支持当前协议的FPGA Peer并确认端点映射。
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 协议配置：配置当前Frame Format、Frame Bits和协议专属控制字段。
    - 双向激励：DUT与FPGA Peer交换固定Payload。
    - 协议解码：FPGA记录帧结构、控制位、位数和双向数据。
    - 矩阵判定：逐协议比较实际帧结构和Payload。
  observations:
    - 协议帧结构：记录FPGA解码的Format、控制位和Frame Bits。
    - 双向数据：记录DUT与FPGA Peer实际接收Payload。
  pass_criteria:
    - 帧格式正确：外部解码格式和控制位符合目标协议定义。
    - 位数正确：每帧有效位数等于配置。
    - 数据正确：双向Payload逐帧一致。
timeout: 20 s统一协议矩阵deadline
cleanup: [Stop FPGA Peer, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R3, full_coverage_level: R3, board: SPI四线连接到FPGA Peer, bench: 支持Motorola、TI SSP和Microwire的通用波形Peer}
backend: [FPGA, Silicon]
evidence: [FPGA协议解码和双向数据]
failure_observations:
  - {key: expected_frame_format, label: 期望SPI帧格式, source: oracle, role: expected, format: text}
  - {key: actual_frame_format, label: FPGA实际解码帧格式, source: instrument, role: actual, format: text}
  - {key: actual_peer_data, label: FPGA Peer实际接收数据, source: instrument, role: actual, format: bytes_hex}
gap: [case_implementation_gap, driver_api_gap, bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_003
case_name: SPI高速Bitrate与RX采样延迟测试
report_feature: |-
  1. SPI SCLK分频与Bitrate
  2. SPI RX采样延迟
p_level: P2
feature_refs: [SPI_F_006, SPI_F_016]
method:
  inputs:
    - 频率矩阵：Capability发布的低、中和最高已验证Bitrate节点。
    - 延迟矩阵：0、代表中间值和Capability最大值；先做短数据筛选，再做选定点长数据。
    - Observer：FPGA Peer捕获SCLK并返回已知Pattern。
  steps:
    - Bench门禁：确认FPGA Peer采样能力高于目标最高Bitrate并完成四线映射。
    - 基线建立：复位代表SPI实例、Service状态和Resource Pool。
    - 节点配置：设置当前Bitrate和RX Sample Delay。
    - 短数据筛选：交换短Pattern，记录外部SCLK和数据结果。
    - 长数据验证：对每个Bitrate选择至少一个有效延迟点执行跨FIFO长度传输。
    - 误码统计：统计总帧数、错误帧数和首次错误位置。
    - 结果判定：比较实测SCLK、配置容差和误码数。
  observations:
    - 外部频率：记录每个节点的目标Bitrate和SPI_WAVEFORM.SCLK_HZ。
    - 接收质量：记录RX Sample Delay、总帧数、错误帧数和首次错误位置。
  pass_criteria:
    - 频率正确：实测SCLK位于目标容差内。
    - 数据正确：每个频率至少一个Capability声明有效的延迟点错误帧数为0。
    - 边界明确：最高已验证Bitrate由真实波形和数据共同证明，不由Driver参数上限推断。
timeout: 按频率矩阵和数据长度计算有界deadline
cleanup: [Stop FPGA Peer, Disable SPI, Reset SPI instance, Resource Pool Reset]
resources: {minimum_level: R3, full_coverage_level: R3, board: SPI四线连接到高速FPGA Peer, bench: 采样率满足最高目标Bitrate的数字捕获平台}
backend: [FPGA, Silicon]
evidence: [外部SCLK频率、RX Sample Delay和误码统计]
failure_observations:
  - {key: target_bitrate_hz, label: 目标SPI Bitrate, source: dut_config, role: config, format: decimal}
  - {key: measured_sclk_hz, label: 外部实测SCLK频率, source: instrument, role: actual, format: decimal}
  - {key: rx_sample_delay, label: RX采样延迟配置, source: dut_config, role: config, format: decimal}
  - {key: frame_error_count, label: 接收错误帧数, source: measurement, role: actual, format: decimal}
gap: [case_implementation_gap, capability_limit_gap, bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_004
case_name: SPI多Controller总线冲突测试
report_feature: |-
  1. SPI多Controller冲突状态与中断
p_level: P2
feature_refs: [SPI_F_019]
method:
  inputs:
    - 两个Controller：Capability选择两个独立SPI实例。
    - 受控总线：FPGA隔离/合路两个Controller的SCLK和数据输出，避免未受控直接短接输出。
    - 冲突Pattern：两个Controller在同一窗口发送相反数据。
  steps:
    - 安全门禁：确认FPGA合路具备输出隔离、限流和可恢复控制，禁止直接短接两个推挽输出。
    - 基线建立：复位两个SPI实例、Service状态和Resource Pool，清除冲突IRQ。
    - Controller配置：配置相同Mode和Bitrate，Enable冲突状态及中断。
    - 受控争用：由FPGA在限定帧窗口内连接两个Controller并同步启动相反Pattern。
    - 状态观测：读取CONTROLLER_COLLISION、IRQ.RAW、IRQ.STATUS和IRQ_EVENT。
    - 恢复动作：FPGA断开争用路径，Clear中断并重新复位两个实例。
    - 恢复验证：在无争用单Controller路径执行一笔短传输。
  observations:
    - 冲突事实：记录争用窗口、Collision状态和Multi-Controller IRQ生命周期。
    - 恢复事实：记录断开争用并复位后的状态和短传输结果。
  pass_criteria:
    - 冲突可见：受控争用时Collision Raw和IRQ Delivery有效。
    - 清除正确：解除争用并Clear后Raw/Status恢复。
    - 恢复正确：复位后单Controller短传输成功。
timeout: 10 s
cleanup: [Disconnect FPGA contention route, Mask and Clear SPI IRQ, Disable and Reset both SPI instances, Resource Pool Reset]
resources: {minimum_level: R3, full_coverage_level: R3, board: 两个SPI实例连接FPGA安全隔离合路, bench: 支持受控争用与断开的FPGA路由}
backend: [FPGA, Silicon]
evidence: [FPGA争用窗口、Collision状态、IRQ生命周期和恢复传输]
failure_observations:
  - {key: contention_window, label: FPGA受控争用窗口, source: instrument, role: config, format: text}
  - {key: collision_status, label: STATUS.CONTROLLER_COLLISION实际值, source: dut, role: actual, format: bool}
  - {key: collision_irq_raw, label: Multi-Controller IRQ Raw, source: dut, role: actual, format: hex32}
  - {key: recovery_transfer_match, label: 复位后短传输匹配结果, source: measurement, role: actual, format: bool}
gap: [case_implementation_gap, trigger_semantic_gap, bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=16; NEEDS_VERIFICATION=3 | IMPLEMENTATION_GAP=4; MAPPING_GAP=4; BENCH_GAP=2; NEEDS_VERIFICATION=2 | Hardware Truth和完整Case Plan已闭合；公共SPI代码、Capability语义和Board/Bench映射尚未实现 | `ET6801_spi.md` |

## 5. Common Gap / Evolution

- `case_implementation_gap`：当前自动化平台尚无 SPI Wrap、Service、PC Driver 和 Case。
- `capability_limit_gap`：目标最高可达 Bitrate、FIFO容量、帧格式和RX Sample Delay等语义必须进入Runtime Capability，不能由公共Case硬编码。
- `driver_api_gap`：当正式SDK未暴露硬件Feature时，只允许按测试Driver扩展规则在Driver底部增加清晰命名的测试接口；Wrap不得直接操作寄存器。
- `board_mapping_gap`：外部回接和双实例四线链路必须由Board/Bench Profile声明逻辑端点到实际引脚的映射。
- `bench_mapping_gap`：波形、协议和争用Case需要通用FPGA/逻辑分析仪Observer；未部署时是环境缺口，不删除Case。
- `trigger_semantic_gap`：多Controller冲突必须先从目标RTL/设计资料确认安全、确定性的触发方法；禁止直接短接推挽输出进行试错。
- QSPI是独立IP，不纳入本SPI公共Contract；未来按独立`qspi.md`分析和开发。
