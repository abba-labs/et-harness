# SPI Stable IP Contract

更新时间：2026-09-04 13:00 CST

本文件定义芯片中立的SPI测试意图。保留19个Feature ID；补入参考资料遗漏的测试目的，纠正不充分的判据。公共配置及数据格式在此定义，具体寄存器、SDK差异和接线仅见芯片文档。

## 0. Stable IP Contract

### 0.1 配置与数据

| 对象 | 公共语义与单位 |
|---|---|
| instance_id / role | 可传入的逻辑实例；CONTROLLER产生SCLK，TARGET由外部SCLK/CS驱动。默认代表实例，不把代表实例PASS称作所有实例PASS。 |
| frame_format / clock_mode | MOTOROLA_SPI、TI_SSP、MICROWIRE；Motorola支持MODE0～MODE3，其他格式不能套用四模式。 |
| frame_bits / frame_count | 单帧有效位数、Controller接收帧数，均为正整数；范围由Capability给出，不暴露减一编码。 |
| transfer_mode | TX_RX、TX_ONLY、RX_ONLY、EEPROM_READ；无效方向的数据不设相等/不相等判据。 |
| divider / bitrate_hz | 选择合法分频；实际频率=输入时钟/分频。请求频率与量化后实际频率分别保存，不把Target本地分频作为实际SCLK。 |
| cs_policy / cs_selected | AUTO、SOFTWARE_HOLD、FRAME_TOGGLE；适用格式/相位由Capability限制。SOFTWARE_HOLD表示传输批次间保持，不等于任意GPIO强制电平。 |
| rx_sample_delay | 输入时钟周期数；可写位宽与物理有效范围分别描述。 |
| target_output_enabled | true允许输出，false禁止输出；公共接口不继承反向位编码。 |
| FIFO阈值 | TX IRQ在Level≤T、RX IRQ在Level≥R+1；START_THRESHOLD在TX Level>T启动，全部以帧为单位。 |
| DMA阈值 | TX请求Level≤T、RX请求Level≥R+1；发送/接收请求可独立开关，DMA端点访问宽度由Capability给出。 |
| Microwire配置 | control_bits、SEQUENTIAL/NON_SEQUENTIAL、TX/RX、handshake_enabled；具体协议Case仍待第5节时序依据闭合。 |

统一数据表示：一帧一个无符号整数，按frame_bits截取有效位；本契约Wire每帧使用uint32小端槽，frame_count使用uint32；有效位数不得超过32，当前合法范围仍取Capability。SPI在线上位序与Wire字节序分开，不由Python主机端序决定。Frame Count不等于Byte Count。DMA内存打包服从端点访问宽度，断言先还原帧值再比较。

本计划的独立输入：PATTERN_A第i帧为((0x1357 XOR (i×0x31)) AND ((1<<frame_bits)-1))；PATTERN_B为A在有效位内取反。i从0开始。普通数据轮次各自保留Expected，不能从接收值反推Expected。常规频率节点由目标输入时钟和有效分频预先选定，性能极限另行评审。

### 0.2 直接动作与职责

| 动作 | 请求→返回及副作用 |
|---|---|
| Capability查询 / limits_get | PC从Capability查询角色、格式、IRQ、DMA端点、时钟及适用条件；Wire的limits_get只返回可编程范围，不代替完整Capability，也不发布测试是否实现。 |
| configure / config_get | 实例+稳定配置→接受状态；独立config_get返回硬件读回，不回显缓存代替。配置发生在Disable时，重新配置可能清FIFO，必须先配置再装数据。 |
| enable / disable / fifo_reset | 实例→状态；fifo_reset同时清TX/RX，不承诺独立复位。Disable清FIFO的目标映射写在芯片文档。 |
| cs_select / cs_release / loopback_set | 实例+选择状态/布尔值→状态；可以保持Enable且未选CS，供FIFO静止填充。 |
| write_frames / read_frames | 实例+帧序列/最大读取数→本次实际接受/读出的帧；一次调用不等未来数据，不把入FIFO数当成线上完成数。 |
| fifo_threshold_set / snapshot_get | 设置TX/RX/启动阈值；返回各独立Level/阈值/满空状态；不得隐含读取有读清副作用的错误位。 |
| error_status_read | 显式一次读取可能读清的TARGET_TX_ERROR/CONTROLLER_COLLISION；返回首次原始值和各逻辑位，报告再次读取是另一次动作。 |
| irq_configure / irq_snapshot_get / irq_clear | Source、Mask及投递配置；Raw/Status/Mask独立返回。irq_clear只清可锁存源，不声称消除仍有效的电平条件。 |
| irq_event_reset / irq_event_get | 清零/获取固件ISR软件计数与锁存Source，不访问总线时序、不执行Case断言。 |
| dma_configure | 实例+TX/RX请求开关和水位→状态；SPI Service不配置DMA通道，PC组合DMA Driver。 |
| test_fifo_write_once / test_fifo_read_once | 单次无FIFO满空拦截的数据访问，仅用于明确错误刺激；不能被正常读写API的检查吞掉。不是任意寄存器访问接口。 |

Wire：以上稳定动作的当前命令布局见0.6节，C Service与Python Codec保持同一契约，不创建新通信协议。配置错误返回明确状态，数据未就绪返回本次0帧，长操作由PC deadline累计推进。没有新增固件后台Case状态机。

普通`snapshot_get`只返回无读清副作用的配置、FIFO和IRQ事实；若目标的BUSY等正常状态与读清错误共用寄存器，必须统一经显式`error_status_read`获取该次完整状态。禁止为了得到BUSY而在普通轮询中提前消费错误证据。读取返回的是该次原始状态，不缓存伪造后续硬件状态。

### 0.3 Observation与Oracle

| Endpoint | 来源及含义 |
|---|---|
| CONFIG.ENABLE/ROLE/DIVIDER/FRAME_BITS/TRANSFER_MODE/FRAME_COUNT/LOOPBACK/CS_POLICY/RX_SAMPLE_DELAY | dut：各项硬件配置读回。 |
| STATUS.BUSY/TX_NOT_FULL/TX_EMPTY/RX_NOT_EMPTY/RX_FULL | dut：硬件状态；只读到终态不得声称观察过完整变化过程。 |
| STATUS.TARGET_TX_ERROR/CONTROLLER_COLLISION | dut：显式错误状态读取；读清副作用不能被调试窗口或自动快照提前消耗。 |
| FIFO.TX_LEVEL/RX_LEVEL/TX_THRESHOLD/RX_THRESHOLD/START_THRESHOLD | dut：占用帧数与配置值。 |
| IRQ.RAW/STATUS/MASK | dut：原始/有效/使能状态；逻辑Source编码与实际寄存器位分离。 |
| IRQ_EVENT.COUNT/SOURCE | measurement：ISR执行计数、首次有效Source软件锁存；不称硬件寄存器。 |
| TRANSFER.RX_DATA | dut：实际数据端点；数量为实际读写操作累计的measurement。 |
| DMA.CHANNEL_STATUS/DESTINATION_DATA | dut：同一DUT内DMA硬件终态及目标内存；不是外部Peer。 |
| SPI_WAVEFORM.* | fpga：边沿时间戳、频率、片选窗口和解码数据。改用仪器时实际source=instrument，不伪装来源。 |
| MISO.VOLTAGE | instrument：引脚在预定负载下的电压，Expected来自Bench电平预算。 |

机器块中的failure_observations定义关键留证项，PASS同样采集。最终代码实现时再生成ET_CASE_REPORT模板；不能提前生成有虚假观测值的报告。

### 0.4 执行边界

基线复位仅针对Case使用的SPI以及配合IP，不能复位控制通信UART。多IP顺序由PC Case决定。所有配置在数据激励之前完成。双实例链路为Controller SCLK→Target SCLK、CS→CS、MOSI→Target RX、Target TX→Controller MISO及共地；角色交换时两端改向，不增加输出对打。

收尾复用现有机制：停止外部驱动，屏蔽IRQ/关闭DMA请求并停止通道，释放CS，Disable和复位参与IP，最后释放资源。任何超时保存实际未完成状态，不能通过自动重试或复位后一次成功覆盖本次失败。实际接线由Board/Bench提供。

### 0.5 FIFO IRQ最小刺激

| Source | 刺激及边界 | 消除条件 |
|---|---|---|
| TXE | Controller未选CS；填T帧时Raw应为1，再填1帧到T+1时Raw应为0。 | 填到T+1；T=D-1需填满。 |
| TXO | Enable且未选CS，填满D帧；再执行一次test_fifo_write_once。 | 停止额外写入，显式读清错误源。 |
| RXU | RX FIFO为空，执行一次test_fifo_read_once。 | 停止空读，显式读清错误源。 |
| RXO | Loopback接收D帧不读RX，再发1帧；TX发送可分批，不可同时排空RX。 | 停止接收并显式读清错误源，再排空FIFO。 |
| RXF | Loopback积累R帧仍不触发，再收1帧到R+1；R=0由空到1。 | 读回到R帧；不是对IRQ位写0或写1。 |

每个Source独立复位。需要电平保持的阶段不让ISR自动读FIFO。ISR可以在锁存有效Source后屏蔽该源，避免电平IRQ风暴；PC核对锁存值，不能要求ISR屏蔽后的实时STATUS仍为1。

### 0.6 SPI Wire实现契约

Service ID为`0x010B`；沿用R400 ET-Frame v1，不改变公共帧或其他IP命令。每个请求Body固定为`instance_id:u8 + 参数u32LE数组`；公共头instance_id与Body必须一致。响应不带实例前缀，只包含下表u32LE字段。所有Boolean严格为0或1，所有字段数精确校验；错误响应Body为空。

| Command ID | 命令 | 请求字段（不含实例） | 响应字段 |
|---:|---|---|---|
| 0 | LIMITS_GET | 无 | Limits |
| 1 | CONFIGURE | Config | 无 |
| 2 | CONFIG_GET | 无 | Config |
| 3 | ENABLE_SET | enabled | 无 |
| 4 | FIFO_RESET | 无 | 无 |
| 5 | DIVIDER_SET | divider | 无 |
| 6 | FRAME_COUNT_SET | frame_count | 无 |
| 7 | CS_SET | selected | 无 |
| 8 | LOOPBACK_SET | enabled | 无 |
| 9 | FIFO_THRESHOLDS_SET | tx, rx, start | 无 |
| 10 | SNAPSHOT_GET | 无 | Snapshot |
| 11 | ERROR_STATUS_READ | 无 | raw, flags |
| 12 | WRITE_FRAME | frame | accepted(0/1) |
| 13 | READ_FRAME | 无 | received(0/1), frame |
| 14 | TEST_FIFO_WRITE_ONCE | frame | 无 |
| 15 | TEST_FIFO_READ_ONCE | 无 | frame |
| 16 | DMA_CONFIGURE | tx_enabled, rx_enabled, tx_threshold, rx_threshold | 无 |
| 17 | DMA_ENDPOINT_GET | 无 | address_low, address_high |
| 18 | IRQ_MASK_SET | sources, enabled | 无 |
| 19 | IRQ_CLEAR | sources | 无 |
| 20 | IRQ_CAPTURE_START | sources | 无 |
| 21 | IRQ_CAPTURE_STOP | 无 | 无 |
| 22 | IRQ_EVENT_GET | 无 | IrqEvent |
| 23 | IRQ_EVENT_RESET | 无 | 无 |

字段顺序是协议定义，不依赖C结构体内存布局：

- Config：`role, frame_format, clock_mode, transfer_mode, cs_policy, frame_bits, frame_count, divider, target_output_enabled, loopback, rx_sample_delay, control_bits, sequential, transmit, handshake, reserved`。reserved必须为0；role为TARGET=0/CONTROLLER=1；format为MOTOROLA=0/TI=1/MICROWIRE=2；clock_mode为MODE0～3的0～3；transfer_mode为TX_RX=0/TX_ONLY=1/RX_ONLY=2/EEPROM_READ=3；cs_policy为AUTO=0/HOLD=1/TOGGLE=2。
- Limits：`frame_bits_min, frame_bits_max, fifo_depth, divider_min, divider_max, frame_count_max, rx_delay_max`。只发布可编程数值范围；完整角色、格式、DMA路由和适用组合仍来自Capability，不能用该命令替代YAML。
- Snapshot：`enabled, selected, tx_level, rx_level, tx_threshold, rx_threshold, start_threshold, irq_raw, irq_status, irq_enabled, dma_tx_enabled, dma_rx_enabled, dma_tx_threshold, dma_rx_threshold`。前两项及DMA使能项为Boolean；IRQ使用公共Source位。
- IrqEvent：`raw_status, masked_status, latched_events, event_count, unexpected_count, overflow_count, generation, fault_flags`。前三项是ISR读取/锁存的Source，其他项为软件计数；fault_flags bit0=访问/绑定清理失败、bit1=计数饱和、bit2=非预期来源。保留未知位不能静默接受。
- Source：bit0 TX_EMPTY、bit1 TX_OVERFLOW、bit2 RX_UNDERFLOW、bit3 RX_OVERFLOW、bit4 RX_FULL、bit5 COLLISION。flags：bit0 BUSY、bit1 TX_NOT_FULL、bit2 TX_EMPTY、bit3 RX_NOT_EMPTY、bit4 RX_FULL、bit5 TARGET_TX_ERROR、bit6 COLLISION。raw仅为本次原始硬件值留证，不能在公共Case里按芯片位号解释。

`WRITE_FRAME/READ_FRAME`每条命令最多访问一帧；没有数据时返回0，不等未来FIFO变化，空读返回frame=0但received=0。PC的`write_frames/read_frames`按帧组合这些原子动作，遇满/空即返回；`read_exact/irq_wait`在PC统一Deadline内等待，不在固件增加后台测试状态机。

`IRQ_CAPTURE_START`在未绑定时只重置软件证据、增加generation并绑定现有IRQ Manager；sources声明预期来源，不隐式改变SPI源屏蔽、不清硬件锁存状态。PC先用IRQ_MASK_SET/IRQ_CLEAR建立基线，产生刺激并保存Raw/Status后再绑定，或先绑定再显式Unmask；已有效的源可以在绑定期间立即投递。ISR保存首次Raw/Status和累计Source，屏蔽活动源避免持续IRQ风暴；不排空FIFO、不自动确认Feature。PC显式消除电平条件并调用IRQ_CLEAR，若需继续投递再调用IRQ_MASK_SET。`IRQ_CAPTURE_STOP`先关源再解绑，保留证据；清理失败返回错误，不宣称已释放。绑定失败时屏蔽本IP源并清理实际持有的路由，不以新的绑定覆盖失败。

仅LIMITS_GET、CONFIG_GET、SNAPSHOT_GET、DMA_ENDPOINT_GET、IRQ_EVENT_GET允许Target既有安全重试；所有写操作、FIFO读取和ERROR_STATUS_READ禁止自动重试。DMA端点作为查询结果供既有DMA端点映射核对，不授权Case直接操作物理地址。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联 Case |
|---|---|---|---|
| SPI_F_001 | SPI模块Enable/Disable与FIFO复位 | 启停模块并清空TX/RX FIFO。 | `SPI_P0_001`, `SPI_P1_004` |
| SPI_F_002 | SPI Controller/Target角色 | Controller产生时钟；Target接受外部时钟。 | `SPI_P0_001`, `SPI_P1_002` |
| SPI_F_003 | SPI CPOL/CPHA四种模式 | Motorola MODE0至MODE3。 | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002`, `SPI_P1_006` |
| SPI_F_004 | SPI帧位宽 | 按能力声明的合法位宽收发，忽略帧外高位。 | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_005 | SPI TX_RX/TX_ONLY/RX_ONLY/EEPROM_READ模式 | 双向、单向和命令后读数据。 | `SPI_P1_003` |
| SPI_F_006 | SPI SCLK分频 | Controller配置分频产生串行时钟。 | `SPI_P0_001`, `SPI_P1_001`, `SPI_P1_006`, `SPI_P2_003` |
| SPI_F_007 | SPI片内Loopback | 内部移位数据返回RX，不经过PAD。 | `SPI_P0_002`, `SPI_P1_002` |
| SPI_F_008 | SPI外部PAD收发 | 经真实SCLK、CS、MOSI、MISO连接收发。 | `SPI_P1_001`, `SPI_P1_002`, `SPI_P2_005`, `SPI_P3_002` |
| SPI_F_009 | SPI CS自动、保持与逐帧切换 | 仅测试能力声明的CS策略及适用模式。 | `SPI_P1_006` |
| SPI_F_010 | SPI接收帧数控制 | Controller RX_ONLY/EEPROM_READ接收指定帧数。 | `SPI_P1_003` |
| SPI_F_011 | SPI TX/RX FIFO容量与Level | FIFO满空、占用量变化及复位。 | `SPI_P1_004` |
| SPI_F_012 | SPI FIFO中断阈值与启动阈值 | IRQ电平边界与Controller启动边界。 | `SPI_P1_004`, `SPI_P1_005`, `SPI_P1_008` |
| SPI_F_013 | SPI传输与FIFO状态 | BUSY、FIFO满空及Target TX Error状态。 | `SPI_P0_002`, `SPI_P1_002`, `SPI_P1_004`, `SPI_P1_007`, `SPI_P2_005` |
| SPI_F_014 | SPI TXE/TXO/RXU/RXO/RXF IRQ | 电平中断解除条件，锁存错误读清除。 | `SPI_P1_005` |
| SPI_F_015 | SPI DMA TX/RX请求与Watermark | 水位控制DMA请求，搬运双向数据。 | `SPI_P2_001`, `SPI_P3_002` |
| SPI_F_016 | SPI RX采样延迟 | 改变输入采样时刻；有效范围由硬件依据限定。 | `SPI_P2_003` |
| SPI_F_017 | SPI Motorola/TI SSP/Microwire帧格式 | 串行帧结构以及Microwire控制、方向和握手。 | `SPI_P2_002` |
| SPI_F_018 | SPI Target输出使能 | 禁止输出时为高阻，接收通路不受影响。 | `SPI_P2_007` |
| SPI_F_019 | SPI Controller冲突状态与IRQ | Controller传输中被外部选中时的冲突响应。 | `SPI_P2_004` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---|---|---|---|---|---|
| SPI_P0_001 | P0 | SPI基础配置读回 | SPI_F_001, SPI_F_002, SPI_F_006 | 每个节点角色、分频和帧宽精确匹配；Target不把本地分频当作外部实际SCLK。 | R0 | PLANNED |
| SPI_P0_002 | P0 | SPI片内回环模式与帧宽 | SPI_F_003, SPI_F_004, SPI_F_007, SPI_F_013 | 每组8帧完整相等，没有截断或多余帧。 | R1 | PLANNED |
| SPI_P1_001 | P1 | SPI单实例外部回接 | SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_006 | Loopback关闭且两组RX逐帧等于TX。 | R2 | PLANNED |
| SPI_P1_002 | P1 | SPI双实例双向收发 | SPI_F_002, SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_013, SPI_F_007 | 外接两端交叉匹配；Target回环节点自收数据匹配。 | R2 | PLANNED |
| SPI_P1_003 | P1 | SPI Transfer Mode与接收帧数 | SPI_F_005, SPI_F_010 | 四种模式按定义的数据方向逐帧匹配。 | R2 | PLANNED |
| SPI_P1_004 | P1 | SPI FIFO容量与复位 | SPI_F_001, SPI_F_011, SPI_F_012, SPI_F_013 | 填充和排空每一步Level均与实际操作数一致。 | R1 | PLANNED |
| SPI_P1_005 | P1 | SPI FIFO IRQ触发与清除 | SPI_F_012, SPI_F_014 | Mask阶段无投递、Unmask阶段有目标Source投递。 | R1 | PLANNED |
| SPI_P1_006 | P1 | SPI CS与SCLK波形 | SPI_F_009, SPI_F_003, SPI_F_006 | CPOL/CPHA一致且频率在预先计算的容差内。 | R3 | PLANNED |
| SPI_P1_007 | P1 | SPI Target空TX状态 | SPI_F_013 | 首次1、再次0，且没有新的欠载刺激。 | R2 | PLANNED |
| SPI_P1_008 | P1 | SPI TX启动阈值边界 | SPI_F_012 | 全部T在不足阈值时无RX、越过阈值后收到正确T+1帧。 | R2 | PLANNED |
| SPI_P2_001 | P2 | SPI DMA双向与水位 | SPI_F_015 | TX在Level≤T、RX在Level≥R+1才触发已Arm的单笔DMA。 | R2 | PLANNED |
| SPI_P2_002 | P2 | SPI串行帧格式 | SPI_F_017 | 待第5节补齐依据，不能编码Formal Case | R3 | NEEDS_VERIFICATION |
| SPI_P2_003 | P2 | SPI高速与RX采样延迟 | SPI_F_006, SPI_F_016 | 待第5节补齐依据，不能编码Formal Case | R3 | NEEDS_VERIFICATION |
| SPI_P2_004 | P2 | SPI Controller冲突状态与IRQ | SPI_F_019 | 待第5节补齐依据，不能编码Formal Case | R3 | NEEDS_VERIFICATION |
| SPI_P2_005 | P2 | SPI无时钟等待与恢复 | SPI_F_008, SPI_F_013 | 无SCLK没有RX增长，固件命令返回有界的未完成结果。 | R2 | PLANNED |
| SPI_P2_007 | P2 | SPI Target输出高阻 | SPI_F_018 | 两种相反弱负载均能拉到规定电平，且正常Enable对照不受弱负载破坏。 | R4 | PLANNED |
| SPI_P3_002 | P3 | SPI DMA连续收发 | SPI_F_015, SPI_F_008 | 20轮×两方向×32帧全部匹配，不丢帧、重复或串轮。 | R2 | PLANNED |

共17个测试目标：P0=2、P1=8、P2=6、P3=1。其中14项有完整PLAN，3项保留简明设计草案及待确认依据；尚无已实现Formal Case或实测结果。R0/R1=4项，R2=8项，R3=4项，R4=1项。外部设备类5项保留设计，当前环境按芯片文档的暂缓/SKIP执行安排处理，不计已执行覆盖。

## 3. Machine-readable Case Contract

### SPI_P0_001 SPI基础配置读回

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P0_001
case_name: SPI基础配置读回
report_feature: |-
  1. SPI模块Enable/Disable与FIFO复位
  2. SPI Controller/Target角色
  3. SPI SCLK分频
p_level: P0
feature_refs: [SPI_F_001, SPI_F_002, SPI_F_006]
method:
  inputs:
    - "配置矩阵：全部支持角色，MODE0，合法最小/中间/最大偶数分频；帧宽取支持的8-bit，否则取最小合法值。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "模块关闭：关闭SPI后配置当前角色、分频、帧宽和TX_RX模式。"
    - "配置读取：读CONFIG各独立字段，与输入及输入时钟/分频得到的实际频率比较。"
    - "模块启动：Enable后读取CONFIG.ENABLE，要求为1。"
    - "模块关闭：Disable后读取CONFIG.ENABLE，要求为0。"
    - "节点汇总：逐节点保存配置和启停值；只把本次选中的实例计入已测范围。"
  observations:
    - "配置读回：CONFIG.ROLE、DIVIDER、FRAME_BITS应等于写入值，证明配置进入硬件。"
    - "启停读回：CONFIG.ENABLE应为0→1→0，证明模块启停控制。"
  pass_criteria:
    - "配置一致：每个节点角色、分频和帧宽精确匹配；Target不把本地分频当作外部实际SCLK。"
    - "启停有效：全部节点ENABLE依次为0、1、0。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外接线", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI基础配置读回的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"role","label":"CONFIG.ROLE","source":"dut","role":"actual","format":"text"}
  - {"key":"divider","label":"CONFIG.DIVIDER","source":"dut","role":"actual","format":"decimal"}
  - {"key":"enable_sequence","label":"CONFIG.ENABLE启停序列","source":"dut","role":"actual","format":"text"}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P0_002 SPI片内回环模式与帧宽

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P0_002
case_name: SPI片内回环模式与帧宽
report_feature: |-
  1. SPI CPOL/CPHA四种模式
  2. SPI帧位宽
  3. SPI片内Loopback
  4. SPI传输与FIFO状态
p_level: P0
feature_refs: [SPI_F_003, SPI_F_004, SPI_F_007, SPI_F_013]
method:
  inputs:
    - "参数矩阵：MODE0～MODE3×全部合法整数帧宽；每组发送8帧PATTERN_A，频率取保守可达节点。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "片内配置：Controller、TX_RX、当前模式和帧宽，打开片内Loopback。"
    - "发送准备：Enable且CS未选中时写入8帧；若FIFO不足则按实际容量分批。"
    - "回环启动：选中CS，按PC deadline读出同等数量RX帧，不读取空FIFO。"
    - "结果观测：保存实际RX帧、写入接受数及读出数，再读BUSY和TX_EMPTY。"
    - "逐项判定：逐帧比对输入按帧宽掩码后的值，全部组合完成才汇总通过。"
  observations:
    - "接收数据：TRANSFER.RX_DATA逐帧等于PATTERN_A低frame_bits位，证明内部数据通路。"
    - "完成状态：读完后STATUS.BUSY=0、TX_EMPTY=1；不据此声称观察到运行中BUSY=1。"
  pass_criteria:
    - "数据与数量：每组8帧完整相等，没有截断或多余帧。"
    - "矩阵完整：所有模式/位宽组合满足数据和完成状态判据。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R1, full_coverage_level: R1, board: "无额外接线", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI片内回环模式与帧宽的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"expected","label":"期望回环帧","source":"oracle","role":"expected","format":"bytes_hex"}
  - {"key":"rx","label":"TRANSFER.RX_DATA","source":"dut","role":"actual","format":"bytes_hex"}
  - {"key":"busy","label":"STATUS.BUSY","source":"dut","role":"actual","format":"bool"}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_001 SPI单实例外部回接

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_001
case_name: SPI单实例外部回接
report_feature: |-
  1. SPI外部PAD收发
  2. SPI CPOL/CPHA四种模式
  3. SPI帧位宽
  4. SPI SCLK分频
p_level: P1
feature_refs: [SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_006]
method:
  inputs:
    - "接线与矩阵：同一实例MOSI→MISO并共地；关闭片内Loopback；四模式×最小/8-bit/最大合法帧宽×低/中/高可达频率，去重。"
    - "发送数据：每组PATTERN_A、PATTERN_B各8帧；速率节点在执行前固定。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "PAD准备：按Board映射启用MOSI/MISO/SCLK/CS，确认实际短接而不是内部Loopback。"
    - "节点配置：设置当前模式、位宽、分频及Controller TX_RX。"
    - "外部发送：经MOSI输出输入序列，以有界分批方式同步读取MISO返回帧。"
    - "结果采集：记录RX数据、实际读写帧数以及CONFIG.LOOPBACK=0。"
    - "结果判定：两组数据逐帧相等，全部节点执行；波形时序由P1_006单独证明。"
  observations:
    - "PAD数据：TRANSFER.RX_DATA必须等于发送数据，且CONFIG.LOOPBACK=0，证明实际回接路径。"
    - "传输终态：STATUS.BUSY=0和RX剩余帧数为0，证明本次数据已收齐。"
  pass_criteria:
    - "外部路径：Loopback关闭且两组RX逐帧等于TX。"
    - "节点完整：预定模式、位宽和频率组合均完成；本Case不宣称实测SCLK频率。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "单实例MOSI-MISO短接", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI单实例外部回接的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"loopback","label":"CONFIG.LOOPBACK","source":"dut","role":"actual","format":"bool"}
  - {"key":"expected","label":"期望PAD帧","source":"oracle","role":"expected","format":"bytes_hex"}
  - {"key":"rx","label":"TRANSFER.RX_DATA","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_002 SPI双实例双向收发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_002
case_name: SPI双实例双向收发
report_feature: |-
  1. SPI Controller/Target角色
  2. SPI外部PAD收发
  3. SPI CPOL/CPHA四种模式
  4. SPI帧位宽
  5. SPI传输与FIFO状态
  6. SPI片内Loopback
p_level: P1
feature_refs: [SPI_F_002, SPI_F_008, SPI_F_003, SPI_F_004, SPI_F_013, SPI_F_007]
method:
  inputs:
    - "连接与参数：两个SPI实例四线连接；四模式×最小/8-bit/最大合法帧宽，交换Controller/Target角色再执行。"
    - "数据输入：Controller发送PATTERN_A，Target发送PATTERN_B，每次8帧且不超过较小FIFO容量。"
    - "Target回环：在相同外部SCLK/CS接线下增加Target内部Loopback节点；外接双向节点SRL关闭，两者结果分开记录。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "Target准备：先配置并Enable Target，打开输出后装满本次发送帧。"
    - "Controller准备：配置相同模式和帧宽，CS未选中时装入另一组帧。"
    - "传输启动：选择Target发出SCLK，两个实例完成同一笔全双工传输。"
    - "双端采集：读取两端RX数据、帧数和完成后的BUSY、FIFO状态。"
    - "角色交换：重新复位后交换角色，以相同方法覆盖相反数据方向。"
    - "Target回环：独立复位后仅打开Target Loopback，预装PATTERN_B，由Controller提供SCLK/CS；Target RX应等于自身TX而非Controller的PATTERN_A。"
    - "双向判定：外接节点Controller RX等于Target TX、Target RX等于Controller TX；Target回环节点的RX等于自身TX，分别核对两个角色排列。"
  observations:
    - "双端数据：外接节点两个TRANSFER.RX_DATA分别等于对端不同Pattern；Target回环节点明确检查Target RX等于自身Pattern，不能混报成PAD收发通过。"
    - "终态检查：两端BUSY=0且读出数等于本次帧数；有单独实例标识。"
  pass_criteria:
    - "路径匹配：外接节点两端RX等于对端TX；Target回环节点Target RX等于自身TX；数量均相等。"
    - "角色完整：两个角色排列及全部模式/位宽节点均通过。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线互连并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI双实例双向收发的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"controller_rx","label":"Controller TRANSFER.RX_DATA","source":"dut","role":"actual","format":"bytes_hex"}
  - {"key":"target_rx","label":"Target TRANSFER.RX_DATA","source":"dut","role":"actual","format":"bytes_hex"}
  - {"key":"expected","label":"双方期望数据","source":"oracle","role":"expected","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_003 SPI Transfer Mode与接收帧数

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_003
case_name: SPI Transfer Mode与接收帧数
report_feature: |-
  1. SPI TX_RX/TX_ONLY/RX_ONLY/EEPROM_READ模式
  2. SPI接收帧数控制
p_level: P1
feature_refs: [SPI_F_005, SPI_F_010]
method:
  inputs:
    - "连接与数据：双实例连接；Target保持TX_RX，Controller四种模式，8-bit或合法最小帧宽；N取1与min(4,较小FIFO容量-1)，一帧命令加N帧返回数据。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "双向模式：TX_RX双方预装不同N帧，启动后检查双向各N帧均匹配。"
    - "只发模式：复位后Controller TX_ONLY发送N帧；Target收到N帧，Controller RX FIFO保持空。"
    - "只收模式：复位后Target预装N帧，Controller RX_ONLY设置N并写一帧启动字；读回N帧并等待BUSY=0。"
    - "命令后读：复位后Controller EEPROM_READ先发一帧命令再收N帧；Target预装一帧占位加N帧Pattern，保证命令阶段消耗占位帧。"
    - "额外帧检查：读取Target RX数量与Controller RX数量；RX_ONLY为N，EEPROM_READ总时钟对应N+1，额外窗口内不再增长。"
    - "模式判定：逐模式比较有效方向数据、FIFO数量和终态；无效方向不要求特定数据值。"
  observations:
    - "方向与数量：Controller RX在TX_ONLY为0，在RX_ONLY/EEPROM_READ为N；Target RX分别证明实际时钟帧数。"
    - "有效数据：Controller的接收阶段数据等于Target的N帧Pattern；命令阶段Target首帧等于命令字。"
  pass_criteria:
    - "有效方向：四种模式按定义的数据方向逐帧匹配。"
    - "帧数控制：RX_ONLY总帧N、EEPROM_READ总帧N+1，Controller接收N且BUSY最终为0。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线互连并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI Transfer Mode与接收帧数的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"mode","label":"CONFIG.TRANSFER_MODE","source":"dut","role":"actual","format":"text"}
  - {"key":"rx_count","label":"实际RX帧数","source":"measurement","role":"actual","format":"decimal"}
  - {"key":"rx","label":"TRANSFER.RX_DATA","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_004 SPI FIFO容量与复位

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_004
case_name: SPI FIFO容量与复位
report_feature: |-
  1. SPI模块Enable/Disable与FIFO复位
  2. SPI TX/RX FIFO容量与Level
  3. SPI FIFO中断阈值与启动阈值
  4. SPI传输与FIFO状态
p_level: P1
feature_refs: [SPI_F_001, SPI_F_011, SPI_F_012, SPI_F_013]
method:
  inputs:
    - "边界矩阵：D为Capability FIFO容量；阈值取0、中间值、D-1，设置不同TX阈值与启动阈值，避免读错字段仍相等。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "静止TX准备：Controller Enable但不选中CS，逐次写到D帧，记录TX_LEVEL和满空标志。"
    - "阈值读回：分别设置TX/RX IRQ阈值和启动阈值，读取三个独立字段。"
    - "RX填充：复位后打开片内Loopback，发D帧但不读取RX，等待BUSY=0。"
    - "容量观测：确认RX_LEVEL=D及RX_FULL=1，再逐帧读取并记录Level递减到0。"
    - "双FIFO复位：重新在TX/RX形成非空状态后执行fifo_reset，保存复位前后Level。"
    - "边界判定：全部阈值读回精确一致，FIFO计数及标志正确，复位后两个Level均为0。"
  observations:
    - "TX占用：CS未选中时TX_LEVEL从0递增到D，D时TX_NOT_FULL=0。"
    - "RX占用：RX_LEVEL从D逐帧递减到0；FIFO复位后TX_LEVEL=RX_LEVEL=0。"
  pass_criteria:
    - "容量精确：填充和排空每一步Level均与实际操作数一致。"
    - "配置与复位：三个阈值分别匹配，双FIFO同时清空；启动阈值功能由P1_008另测。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R1, full_coverage_level: R1, board: "无额外接线", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI FIFO容量与复位的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"tx_level","label":"FIFO.TX_LEVEL序列","source":"dut","role":"actual","format":"text"}
  - {"key":"rx_level","label":"FIFO.RX_LEVEL序列","source":"dut","role":"actual","format":"text"}
  - {"key":"thresholds","label":"三个FIFO阈值读回","source":"dut","role":"actual","format":"text"}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_005 SPI FIFO IRQ触发与清除

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_005
case_name: SPI FIFO IRQ触发与清除
report_feature: |-
  1. SPI FIFO中断阈值与启动阈值
  2. SPI TXE/TXO/RXU/RXO/RXF IRQ
p_level: P1
feature_refs: [SPI_F_012, SPI_F_014]
method:
  inputs:
    - "Source矩阵：TXE、TXO、RXU、RXO、RXF，分别按0.5的最小刺激独立运行；阈值覆盖0、中间值、D-1。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "屏蔽准备：仅配置目标Source，先屏蔽它并清零ISR软件计数，不开启自动读RX或自动清错误。"
    - "真实刺激：按0.5填充/读取FIFO，读取IRQ.RAW=1且IRQ.STATUS=0；事件增量应为0。"
    - "解除屏蔽：保持条件并Unmask，先采集有效Status，再开放NVIC投递；回调只锁存Source及计数并屏蔽目标源。"
    - "投递确认：读取回调锁存的有效Source及计数增量，证明进入真实中断；不把读回Status的竞态作为失败。"
    - "状态消除：TXE写到阈值以上、RXF读到阈值以下；TXO/RXU/RXO停止错误访问后执行该Source读清除。"
    - "恢复判定：原始Source从1变0；重新Unmask后没有新增中断，各参数节点独立汇总。"
  observations:
    - "中断硬件：IRQ.RAW/STATUS在Mask前后分别符合目标位关系，错误清除前后Raw为1→0。"
    - "中断交付：ISR锁存Source含目标位且计数增量至少1；它是固件软件记录，不是硬件寄存器。"
  pass_criteria:
    - "隔离成立：Mask阶段无投递、Unmask阶段有目标Source投递。"
    - "清除正确：电平源通过移除条件消失，锁存源通过对应读清除消失；不能统一当W1C。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R1, full_coverage_level: R1, board: "无额外接线", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI FIFO IRQ触发与清除的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"raw","label":"IRQ.RAW前后值","source":"dut","role":"actual","format":"hex32"}
  - {"key":"status","label":"IRQ.STATUS","source":"dut","role":"actual","format":"hex32"}
  - {"key":"isr_source","label":"ISR首次锁存Source","source":"measurement","role":"actual","format":"hex32"}
  - {"key":"events","label":"IRQ_EVENT.COUNT增量","source":"measurement","role":"actual","format":"decimal"}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_006 SPI CS与SCLK波形

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_006
case_name: SPI CS与SCLK波形
report_feature: |-
  1. SPI CS自动、保持与逐帧切换
  2. SPI CPOL/CPHA四种模式
  3. SPI SCLK分频
p_level: P1
feature_refs: [SPI_F_009, SPI_F_003, SPI_F_006]
method:
  inputs:
    - "波形矩阵：FPGA捕获SCLK/CS/MOSI；四种Clock Mode×适用CS策略，低/中/高可达分频；仅生成Capability允许的组合。"
    - "输入与预算：8帧PATTERN_A分成两批4帧，批间停100ms；采样率至少SCLK的10倍，频率误差预算为输入时钟公差加2个采样周期/测量窗口。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "捕获准备：设置FPGA采样率与触发，确认可覆盖批间停顿且返回原始边沿时间戳。"
    - "模式配置：关闭Loopback，配置当前Mode、分频和CS策略，TX_ONLY发送两批数据。"
    - "波形采集：先启动捕获再发送第一批，由TX空及捕获的SCLK停止确认批次结束后保持100ms，再发送第二批并显式释放CS。"
    - "时钟解码：从边沿判定CPOL、采样边沿、位数及实际SCLK频率。"
    - "片选解码：AUTO在每次完成后释放；HOLD跨批间空闲保持有效；TOGGLE在能力适用的帧边界翻转。"
    - "判据比较：按配置的模式、策略、分频预算比较波形，全部节点有效才通过。"
  observations:
    - "时钟事实：SPI_WAVEFORM边沿测得CPOL/CPHA和SCLK_HZ，直接证明外部时序。"
    - "片选事实：CS各有效窗口和帧边界满足策略，且最终释放；数据帧等于PATTERN_A。"
  pass_criteria:
    - "时钟准确：CPOL/CPHA一致且频率在预先计算的容差内。"
    - "片选准确：全部适用策略的窗口关系与定义一致，不能在不适用模式要求TOGGLE。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R3, full_coverage_level: R3, board: "SPI连接Companion FPGA", bench: "独立FPGA波形捕获"}
backend: [FPGA, Silicon]
evidence: ["SPI CS与SCLK波形的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"sclk","label":"FPGA SPI_WAVEFORM.SCLK_HZ","source":"fpga","role":"actual","format":"float"}
  - {"key":"windows","label":"FPGA CS边沿与窗口","source":"fpga","role":"actual","format":"text"}
  - {"key":"mode","label":"FPGA解码CPOL/CPHA","source":"fpga","role":"actual","format":"text"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_007 SPI Target空TX状态

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_007
case_name: SPI Target空TX状态
report_feature: |-
  1. SPI传输与FIFO状态
p_level: P1
feature_refs: [SPI_F_013]
method:
  inputs:
    - "最小刺激：双实例连接，MODE0、8-bit或合法最小帧宽；先发一个有效返回字，再在Target TX为空时产生一帧时钟。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "正常传输：Target预装一帧PATTERN_B，Controller发一帧，确认正常返回且TX已空。"
    - "读清基线：显式读取STATUS.TARGET_TX_ERROR清理既有状态，不开会读取该状态的IRQ回调。"
    - "欠载刺激：不再给Target装数据，Controller再发一帧并等待完成。"
    - "首次读取：立即读取并保存Target错误状态，要求为1；不得提前被通用快照读取。"
    - "再次读取：停止SCLK后再次读取同一状态，要求为0。"
    - "恢复验证：补入一帧新数据再传输，确认返回数据一致且错误不再置位。"
  observations:
    - "错误状态：STATUS.TARGET_TX_ERROR首次为1、第二次为0，证明欠载检测及读清除。"
    - "恢复数据：Controller TRANSFER.RX_DATA等于新Target输入，证明可继续收发。"
  pass_criteria:
    - "触发与读清：首次1、再次0，且没有新的欠载刺激。"
    - "恢复可用：补数据后匹配且错误状态为0；不把该状态混同TX Empty IRQ。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线互连并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI Target空TX状态的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"first","label":"首次STATUS.TARGET_TX_ERROR","source":"dut","role":"actual","format":"bool"}
  - {"key":"second","label":"再次STATUS.TARGET_TX_ERROR","source":"dut","role":"actual","format":"bool"}
  - {"key":"rx","label":"恢复RX数据","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P1_008 SPI TX启动阈值边界

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P1_008
case_name: SPI TX启动阈值边界
report_feature: |-
  1. SPI FIFO中断阈值与启动阈值
p_level: P1
feature_refs: [SPI_F_012]
method:
  inputs:
    - "启动边界：T取0、中间值、D-1；双SPI外部四线连接，关闭Loopback，先保持Controller CS未选中；D取两个FIFO容量的较小值。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "阈值配置：先Enable Target接收；Controller Enable前设置START_THRESHOLD=T及TX_ONLY，Enable后预装T帧。"
    - "不足阈值：选择CS，等待10个理论帧时间后读取Controller TX_LEVEL=T、Target RX_LEVEL=0。"
    - "越过阈值：再写一帧，使TX_LEVEL超过T；不改其他配置。"
    - "启动观测：在deadline内从独立Target读取T+1帧并保存数据，要求与Controller预装序列一致。"
    - "批后状态：读取BUSY=0和TX_LEVEL=0；确认不是读回阈值就判成功。"
    - "节点汇总：每个T重新复位，未启动和启动两个阶段均满足才通过。"
  observations:
    - "启动前：Target RX_LEVEL=0且Controller TX_LEVEL=T，证明未到阈值不发数据。"
    - "启动后：TRANSFER.RX_DATA为完整T+1帧，证明增加一帧真正启动移位。"
  pass_criteria:
    - "边界有效：全部T在不足阈值时无RX、越过阈值后收到正确T+1帧。"
    - "最终空闲：全部节点BUSY=0且TX_LEVEL=0。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线连接并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI TX启动阈值边界的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"before","label":"启动前TX/RX Level","source":"dut","role":"actual","format":"text"}
  - {"key":"rx","label":"启动后RX数据","source":"dut","role":"actual","format":"bytes_hex"}
  - {"key":"threshold","label":"FIFO.START_THRESHOLD","source":"dut","role":"actual","format":"decimal"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P2_001 SPI DMA双向与水位

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_001
case_name: SPI DMA双向与水位
report_feature: |-
  1. SPI DMA TX/RX请求与Watermark
p_level: P2
feature_refs: [SPI_F_015]
method:
  inputs:
    - "DMA矩阵：双SPI外接，交换角色；8-bit及最大帧宽，TX/RX DMA分别单独验证再联合搬运，长度为2D及2D+1，D为较小FIFO容量。"
    - "水位节点：TX静止Level取1及D-1，对应水位先取Level-1再取Level，另测空FIFO水位0；RX边界水位取1及D-1，持续传输RX水位取0避免尾帧滞留；DMA访问宽度来自端点能力。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "静止TX请求：Controller不选CS，FIFO预填L帧；水位L-1时已Arm的单笔TX DMA未完成，改水位为L后应完成且Level增加1；另在空FIFO、水位0时确认单笔请求。"
    - "RX请求边界：独立复位后Target累积R帧且RX DMA不完成；再输入一帧达R+1，单次P2M应完成，记录真实搬运前后状态。"
    - "双向配置：复位双方SPI和DMA；PC先准备接收通道，再准备发送通道，使用硬件握手和端点发布的数据宽度，最后释放CS启动。"
    - "持续传输：若返回路径由CPU预装则限定不超过FIFO；跨FIFO双向使用四个DMA通道，先Arm两端RX再Arm两端TX，禁止软件喂数冒充DMA。"
    - "终态等待：按统一deadline轮询通道完成/错误和SPI BUSY，最后读取两个DMA目的内存。"
    - "数据比较：逐帧掩码后与对端Pattern比较，包含2D+1尾帧；交换角色重新执行。"
    - "恢复验证：关闭DMA请求、停止通道，再用CPU发送一笔8帧数据并核对返回，记录所有节点。"
  observations:
    - "水位证据：DMA单笔未完成→完成及目的内容变化，与SPI水位/Level从不满足到满足请求条件对应。"
    - "搬运证据：DMA硬件完成置位、错误为0，两个目的内存按frame_bits取有效位后精确等于对端输入。"
  pass_criteria:
    - "请求边界：TX在Level≤T、RX在Level≥R+1才触发已Arm的单笔DMA。"
    - "数据完整：每方向实际帧数和数据相等，无尾帧残留且BUSY=0；CPU恢复传输正确。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线互连并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI DMA双向与水位的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"dma","label":"DMA通道硬件终态","source":"dut","role":"actual","format":"hex32"}
  - {"key":"level","label":"SPI FIFO边界Level","source":"dut","role":"actual","format":"decimal"}
  - {"key":"data","label":"DMA目的内存","source":"dut","role":"actual","format":"bytes_hex"}
  - {"key":"expected","label":"独立期望帧","source":"oracle","role":"expected","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P2_005 SPI无时钟等待与恢复

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_005
case_name: SPI无时钟等待与恢复
report_feature: |-
  1. SPI外部PAD收发
  2. SPI传输与FIFO状态
p_level: P2
feature_refs: [SPI_F_008, SPI_F_013]
method:
  inputs:
    - "故障输入：双SPI连接，Target启用且TX预装4帧；Controller暂不启动，因此Target没有SCLK。"
    - "观测窗口：无时钟100ms；恢复后发送4帧PATTERN_A并接收PATTERN_B，统一deadline在执行前确定。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "无时钟准备：先Enable Target并预装数据，Controller保持不发送。"
    - "等待观测：PC多次请求一次性RX读取及FIFO快照，持续100ms，Target RX数保持0、TX帧保持。"
    - "控制活性：每次查询都应及时返回未完成而非阻塞固件；记录请求返回时间和RX计数。"
    - "恢复时钟：启动Controller发出4帧，Target同步收发预装数据。"
    - "恢复读取：获取两端RX帧及BUSY终态，要求交叉匹配且没有重复或截断。"
    - "独立再试：复位双方后再发不同4帧，确认故障等待未影响下一笔传输。"
  observations:
    - "无时钟硬件：Target FIFO.RX_LEVEL=0且TX_LEVEL保持，证明没有伪造完成。"
    - "恢复硬件：两端TRANSFER.RX_DATA分别等于对端Pattern，最终BUSY=0。"
  pass_criteria:
    - "等待正确：无SCLK没有RX增长，固件命令返回有界的未完成结果。"
    - "恢复完整：恢复时钟后和复位后各一笔数据均交叉匹配；不保留旧SDK无限阻塞作为通过条件。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: "双SPI四线互连并共地", bench: "无额外仪器要求"}
backend: [FPGA, Silicon]
evidence: ["SPI无时钟等待与恢复的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"rx_level","label":"无时钟Target RX_LEVEL","source":"dut","role":"actual","format":"decimal"}
  - {"key":"response_ms","label":"请求返回耗时","source":"measurement","role":"actual","format":"float"}
  - {"key":"rx","label":"恢复后双端RX","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P2_007 SPI Target输出高阻

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P2_007
case_name: SPI Target输出高阻
report_feature: |-
  1. SPI Target输出使能
p_level: P2
feature_refs: [SPI_F_018]
method:
  inputs:
    - "环境条件：双SPI四线连接，MISO接可切换弱上拉/下拉及电压Observer；电阻、逻辑电平阈值和负载范围在Bench预先声明。"
    - "对照输入：关闭内部Pad上下拉，Target预装交替0/1返回帧；分别测试输出Enable和Disable，其他配置不变。"
  steps:
    - "独立基线：复位所有参与IP及其Service状态，整池复位资源；每个参数节点重新建立基线。"
    - "正常驱动：Target输出Enable，两种弱负载下发送交替位，Controller均正确接收，证明负载不会压过正常驱动。"
    - "关闭输出：停止传输后复位重配Target output_enabled=false，继续正常接收Controller数据。"
    - "弱上拉观测：施加弱上拉，在CS有效且SCLK运行时测量MISO电平并记录Controller采样帧。"
    - "弱下拉观测：独立复位再禁用输出，施加弱下拉，以相同刺激测量MISO。"
    - "接收检查：两种负载下Target RX仍应等于Controller输入。"
    - "高阻判定：禁用后MISO随弱负载进入各自逻辑电平，Enable时可主动输出交替位；最后恢复安全负载。"
  observations:
    - "PAD电平：Observer测量MISO禁用输出时随弱上拉为高、弱下拉为低；有预先规定的电压阈值。"
    - "接收通路：Target TRANSFER.RX_DATA不因禁止输出而改变，Enable对照传输仍正确。"
  pass_criteria:
    - "高阻成立：两种相反弱负载均能拉到规定电平，且正常Enable对照不受弱负载破坏。"
    - "接收不变：Target仍收到完整正确数据；只看到Controller数据不同不能证明高阻。"
timeout: "每节点理论传输时间加5 s有界调度裕量；无时钟/仪器/器件等待另按本Case输入预算"
cleanup: [Stop external stimulus, Mask IRQ and disable DMA requests, Stop DMA channels when used, Release CS, Reset participating IPs, Resource Pool Reset]
resources: {minimum_level: R4, full_coverage_level: R4, board: "双SPI固定四线互联，MISO接可切换弱上拉/下拉和测量探头", bench: "可切换弱负载和示波器或等效电压Observer"}
backend: [FPGA, Silicon]
evidence: ["SPI Target输出高阻的配置、输入Expected、硬件Actual及关键前后状态"]
failure_observations:
  - {"key":"voltage","label":"MISO实测电平","source":"instrument","role":"actual","format":"float"}
  - {"key":"load","label":"弱负载配置","source":"bench","role":"config","format":"text"}
  - {"key":"target_rx","label":"Target RX数据","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### SPI_P3_002 SPI DMA连续收发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SPI_P3_002
case_name: SPI DMA连续收发
report_feature: |-
  1. SPI DMA TX/RX请求与Watermark
  2. SPI外部PAD收发
p_level: P3
feature_refs: [SPI_F_015, SPI_F_008]
method:
  inputs:
    - "连续范围：双SPI四线连接、MODE1、8-bit；20轮，每轮32帧，双方Pattern按轮次改变，使用独立四DMA通道。"
  steps:
    - "独立基线：开始前复位两个SPI、DMA及其Service状态，整池复位资源。"
    - "初始配置：配置双SPI和四个硬件握手DMA端点，水位取0，先准备两端接收，再准备Target发送，最后Controller发送。"
    - "逐轮收发：先保证Target已有发送数据再启动Controller，轮内DMA完成全部32帧，不用CPU搬运代替。"
    - "逐轮等待：按统一deadline轮询四通道硬件完成及错误，停止本轮通道但保留SPI配置。"
    - "双向比较：读取两端目的内存，逐帧比较对端本轮Pattern，检查BUSY=0及无FIFO错误。"
    - "下一轮准备：在正常完成后更换输入与目的区，重Arm通道继续；失败则记录轮号及硬件状态停止，不能复位重试掩盖。"
    - "连续结论：20/20轮双向数据及终态全部正确；保存实际频率和累计帧数，不声称无限期压力已通过。"
  observations:
    - "DMA终态：每轮四通道完成置位且错误为0，两端目的内存等于对端独立Pattern。"
    - "持续状态：各轮SPI BUSY最终为0，FIFO错误为0，数据不能来自上一轮。"
  pass_criteria:
    - "数据连续：20轮×两方向×32帧全部匹配，不丢帧、重复或串轮。"
    - "终态完整：全部通道在deadline内完成且无SPI/DMA错误。"
timeout: "20轮理论传输时间加每轮5 s有界调度裕量"
cleanup: [Disable SPI DMA requests, Stop DMA channels, Release CS, Reset SPI and DMA, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 双SPI四线互连并共地, bench: 无额外仪器}
backend: [FPGA, Silicon]
evidence: [20轮DMA双向输入输出及硬件终态]
failure_observations:
  - {"key":"round","label":"当前轮次","source":"measurement","role":"actual","format":"decimal"}
  - {"key":"dma","label":"四DMA通道终态","source":"dut","role":"actual","format":"hex32"}
  - {"key":"data","label":"双端目的内存","source":"dut","role":"actual","format":"bytes_hex"}
gap: [case_implementation_gap, board_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=16; NEEDS_VERIFICATION=3 | IMPLEMENTATION_GAP=4; MAPPING_GAP=8; BENCH_GAP=2; NEEDS_VERIFICATION=3 | 19 Feature、17测试目标；14 PLAN、3项设计草案待确认；5项外部设备测试暂缓；未实现、未实测 | `ET6801_spi.md` |

## 5. Common Gap / Evolution

下列ID保留以追溯旧计划；撤下旧机器块是纠正错误刺激/判据，不删除必测目的。补齐依据后在原ID落地完整PLAN。

| Case | 已知测试目的 | 尚缺依据和解除条件 |
|---|---|---|
| SPI_P2_002 | SPI串行帧格式 | Motorola已有完整Case；TI帧同步边沿、Microwire控制段装载顺序及ready电平/采样边沿尚缺目标适用时序依据。MHS约束的是末位之后BUSY释放，不是数据开始，旧计划判断方向错误。 |
| SPI_P2_003 | SPI高速与RX采样延迟 | RX延迟内部移位深度、输入建立/保持预算未定；不得用扫描中任意一个成功点证明整个Feature。 |
| SPI_P2_004 | SPI Controller冲突状态与IRQ | 已知触发为Controller传输时ss_in_n有效；目标芯片该输入到PAD/FPGA的集成连接仍未知，不能用短接两个Controller输出来替代。 |

- P2_002：先固定独立TI/Microwire时序表。Microwire顺序模式一个控制字对应多数据字，非顺序每数据字前一个控制字；握手等待应检查末位之后BUSY保持，ready后BUSY解除，不能照搬旧计划的“未ready不开始数据”。没有ready电平和采样时刻依据时，不编码伪Oracle。
- P2_003：保留低/中/目标最高速率、采样延迟和边界输入时序测试。需要预先固定可达分频、物理延迟范围、输入时序预算和FPGA响应相位，再检查规定点；不得边测边挑成功点形成PASS。寄存器8-bit不代表256个有效延迟级。
- P2_004：用FPGA只驱动已确认的冲突输入，在DUT进行慢速传输时使其有效；显式读取首次Collision及Raw/ISR锁存事实，停止刺激再读清并验证恢复。目标输入路由不明时不能开始刺激，禁止两个推挽SCLK/CS直接相连。
- Capability与Driver缺接口属于实现缺口；Board/Bench缺映射不是硬件不支持。未实测项不写SKIP。
- CS波形和高阻验证不得改成内部回环。新芯片优先复用测试意图，仅调整能力/板卡/设备事实。QSPI另行分析。

### 5.1 本轮范围与外部设备Case

2026-09-04 10:34 CST：按用户指定范围，外部NOR读写擦及连续读写擦属于应用测试，移出本轮SPI功能Case。原SPI_P2_006、SPI_P3_001停止纳入Catalog与PLAN，ID不复用；来源仍在芯片文档追溯。这是范围裁决，不是硬件不支持，也不代表已覆盖NOR应用。

外部设备Case保留简单、直接的测试设计。P1_006和P2_007沿用第3节完整PLAN；下面三项先保留草案，不用未知时序或触发条件拼出虚假完整PLAN。当前设备缺失的执行安排见芯片文档；公共Case不永久硬编码SKIP，也不因缺设备改为片内回环。

#### SPI_P2_002 串行帧格式——简明草案

- 测试Feature：TI SSP/Microwire帧格式及Microwire控制段、方向和握手。
- 输入：每个已确认格式传输4个8-bit数据字，交替0x55/0xAA；Microwire控制字长度、内容和ready时序须先确认，不能随意填值。
- 测试方法：
  1. 确认协议时序表及FPGA协议对端可用；复位参与IP和资源池，闲置SPI退出总线驱动。
  2. 配置当前帧格式、位宽和低速分频；Microwire分别选择发送/接收及适用顺序/握手模式。
  3. FPGA加载独立输入和对应协议时序，先启动捕获，再开始一笔控制段及4个数据字的传输。
  4. 采集SCLK、帧同步/片选和数据；握手节点在协议规定时刻改变ready并观测BUSY。
  5. 读取接收数据和BUSY终态，将捕获波形逐段对照已审核协议时序表。
  6. 比较4个数据字与独立输入，保存首个不同点、实际边沿和BUSY变化。
- 通过条件：数据逐字相等；帧同步、控制段和数据段符合协议；Microwire握手等待与BUSY释放符合已确认时序。
- 尚缺依据：TI同步边沿、Microwire控制字装载顺序和ready电平/采样边沿。未确认前不发布可执行Formal Case。

#### SPI_P2_003 高速与RX采样延迟——简明草案

- 测试Feature：SCLK分频与RX采样延迟。
- 输入：低/中/最高可达速率；每笔16个8-bit交替0x55/0xAA数据；采样延迟和FPGA返回相位必须取预先审核的物理有效点。
- 测试方法：
  1. 确认时序预算、延迟有效范围及FPGA相位控制能力；复位参与IP和资源池，闲置SPI退出驱动。
  2. 配置当前分频和RX采样延迟，读回配置；记录预定SCLK与采样窗口。
  3. FPGA按预定相位返回16个数据字，并捕获SCLK与MISO边沿。
  4. 发起一次传输，在统一deadline内读取全部RX数据和BUSY终态。
  5. 逐字比较输入和接收值，按独立边沿时间戳核对实际频率与输入相位。
  6. 遍历预先规定节点并记录各点结果；不能根据结果临时选取成功节点或放宽预算。
- 通过条件：规定的有效时序节点数据全部正确，频率在事先预算内；采样延迟边界按确认的硬件行为判定。
- 尚缺依据：物理延迟深度、输入时序预算和边界Oracle；不从可写位宽推定全部延迟都有效。

#### SPI_P2_004 Controller冲突——简明草案

- 测试Feature：Controller冲突状态及IRQ。
- 输入：一笔低速16帧传输，FPGA只控制已确认的独立冲突输入；不将两个推挽输出短接。
- 测试方法：
  1. 确认冲突输入的物理路径与有效电平；复位参与IP和资源池，FPGA先保持不触发。
  2. 配置Controller、低速分频和目标IRQ，清历史状态并记录无冲突基线。
  3. 启动16帧传输，FPGA观测到SCLK活动后使独立冲突输入有效。
  4. 锁存首次Collision、IRQ Raw/Status和ISR计数；记录冲突输入与SCLK的时间关系。
  5. 解除刺激，按已确认的读清语义清状态和IRQ，再次读取确认。
  6. 重新配置后发送一笔正常数据，检查完整收发及无新增冲突。
- 通过条件：传输中的有效冲突刺激产生对应状态和真实IRQ；解除并清除后状态恢复，正常传输数据一致。
- 尚缺依据：目标芯片Controller模式下冲突输入的集成路径；无法确认时禁止驱动引脚，不推定硬件不支持。
