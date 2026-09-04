# CAN / CAN FD Stable IP Contract

更新时间：2026-09-05 00:25 CST

分析稿：39项能力/行为目标（37项已准入Feature、2项待定），42项测试目标；39项形成ET_CASE_PLAN，3项目标仍缺关键硬件语义，未冒充PLAN或SKIP。本轮逐项复核现有Case，修正过滤、DLC、IRQ、停钟和观察前提，并将原DMU时间戳目标拆为RX与TX Event。没有SPEC、注册Case或硬件测试结果；第5节缺口闭合前，不宣称IP分析全部完成。

## 0. Stable IP Contract

### 0.1 测试对象与稳定参数

CAN控制器通过Message RAM保存过滤项、收发帧和发送事件；Classic CAN、CAN FD、时间戳、DMA搬运、错误处理分别定义可观测语义，不把控制器、收发器和外部CAN分析仪当成同一个对象。

| 参数 | 公共语义 |
|---|---|
| instance_id / peer | instance_id来自当前连接与Capability；peer是连接文件选择的对端，可以是另一片上CAN，也可以是CAN盒子。Case不写死实例、GPIO或盒子型号；普通Feature采用代表实例，多实例隔离Case单独枚举。 |
| mode | NORMAL、INTERNAL_LOOPBACK、EXTERNAL_LOOPBACK、MONITOR、RESTRICTED；测试模式能力由芯片声明。 |
| nominal/data timing | 输入时钟Hz、BRP、TSEG1、TSEG2、SJW均为实际正整数，硬件减一编码留在Driver/Mapping。bitrate=f_can/[BRP×(1+TSEG1+TSEG2)]；采样点=(1+TSEG1)/(1+TSEG1+TSEG2)。 |
| frame | id、STANDARD/EXTENDED、CLASSIC/FD、DATA/REMOTE、brs、dlc、payload；payload是byte序列，不暴露SDK结构体或uint16存储槽。 |
| DLC | Classic DLC=0～8对应同长度，9～15均携带8-byte且保留原始DLC；FD 0～15依次映射0～8/12/16/20/24/32/48/64-byte。FD不允许Remote；原始DLC与有效payload长度独立保存，不混用。 |
| filter | ID种类、RANGE/DUAL/MASK、ID与Mask、目标FIFO/Buffer/REJECT、优先级；物理过滤编码不进入Case。 |
| RAM layout | 各区域容量、元素payload容量、逻辑布局标识；地址、对齐、共享关系和DMA元素总长度由Chip Mapping给出。 |
| IRQ | 逻辑Source、逻辑Line、使能与事件捕获；不能把不同芯片IRQn固化在公共协议中。 |
| timestamp | 16-bit内部计数与TSU 32-bit时间戳分开；Marker格式、索引及读取副作用明确，不混用。 |

数据PATTERN_A：第i个有效Byte=(0x31+17×i) mod 256；PATTERN_B为A逐Byte取反。序号Case按小端覆盖前4-byte，不足4-byte的帧使用其有效前缀。Expected先由输入生成，禁止从RX重新生成Expected。

### 0.2 直接动作与边界

| 动作族 | 输入、输出和副作用 |
|---|---|
| reset / configure / config_get | 实例、稳定配置→状态；config_get从硬件独立读取。IP复位由PC调用独立CRG Driver，Service状态与资源池也在配置前复位。 |
| mode_set / start / stop | 改变控制器状态；长等待由PC deadline推进，固件不执行Case重试流程。 |
| filter_configure / layout_configure | 仅配置当前CAN规则与存储；公共API不接收任意裸地址。 |
| tx_write / tx_request / tx_request_mask | 预装帧与发请求分开；批量请求是一次原子硬件动作，用于证明多个同时Pending的顺序。 |
| tx_status / rx_peek / rx_read / rx_ack | 返回实际Pending、Completed、索引和帧；读取帧与Ack分开，不能由通用快照隐式消费。 |
| irq_configure / irq_clear / irq_event_get | 配置中断、清指定锁存源、读ISR留证；ISR不比较Expected，不自动排空Case需要观察的FIFO。 |
| protocol_status_read | 显式消费可能读清的错误状态并返回该次完整值；普通轮询不能提前消费LEC或错误日志。 |
| timestamp / timeout / tx_event | 各自明确启动、重装、读取和Ack；TSU按本轮明确捕获/读清语义规划，不提前分配Wire。 |
| dma_configure / dma_endpoint_get | CAN仅配置自身DMU并提供端点；PC通过DMA Driver配置搬运。CAN Service不能调用DMA/GPIO/CRG Wrap。 |
| test_mram_* / test_ecc_irq_* | 若Driver缺失，在Chip Driver底部测试补充区增加明确、受限接口；Wrap不能直接操作寄存器。 |
| tdc_configure / tdc_status_get | 配置补偿Enable、offset和filter（单位为控制器最小时钟周期），返回配置及硬件第二采样点位置；线路延迟由独立Observer测量；基础通信与补偿极限测试分开。 |

外部Peer只需稳定动作：设置帧格式/速率、开始捕获、发送帧、查询实际发送结果、读取捕获帧、停止。静默、Non-ISO、错误帧注入和精确时间测量是独立能力，不默认随基础收发提供。DUT的CRG/GPIO配置不能用于配置CAN盒子；外部Peer没有DUT寄存器时，使用其设备发送完成/捕获记录，禁止伪造TXBTO等读值。未知设备能力属于待确认事实，不自动记为SKIP。

Service/Command ID及命令Body由0.7节唯一声明，PC Codec与Firmware Service必须同步。借用旧FDCAN Handle内存布局不是合法Wire。

### 0.3 最小硬件Observation

| Endpoint | 事实来源 |
|---|---|
| IDENTITY / CONFIG.* | dut：只读身份与当前配置读回；芯片映射负责解释字段和复位值。 |
| TX.PENDING / COMPLETED / CANCELLED | dut：硬件请求与终态位；提交成功不是完成。 |
| RXn.FILL / FULL / LOST / GET_INDEX / PUT_INDEX | dut：FIFO状态；RX.FRAME来自按索引读取的真实接收元素。 |
| RX_BUFFER / NEW_DATA / HIGH_PRIORITY | dut：专用Buffer、New Data位图及优先级过滤命中。 |
| TX_EVENT.* | dut：硬件事件元素、占用与丢失；软件计数单独标识。 |
| IRQ.RAW / IRQ_EVENT.* | dut为原始状态；measurement为ISR锁存的实例、Line、Source和计数。不能把ISR次数称硬件寄存器。 |
| TIMESTAMP / TIMEOUT / CLOCK.* | dut：计数、锁存、回绕、停钟请求/应答，实际名称见芯片文档。 |
| MESSAGE_RAM[offset] | dut：受限RAM读值；地址范围与访问总数字段必须可复核。 |
| DMA.STATUS / DMA.DESTINATION_* / DMU.ERROR | dut：DMA硬件终态、实际目标内存及DMU错误。 |
| ECC_IRQ.* / PROTOCOL.* | dut：明确的ECC和协议状态；Force通过不能扩大为真实ECC覆盖。 |
| OBSERVER.CAPTURE | peer或instrument：真实外部设备/另一CAN控制器捕获；同芯片另一实例须写明，不伪称独立仪器。 |

以下Endpoint是分组导航，不是允许把整组寄存器绑定到一条Observation：例如TX.PENDING、TX.COMPLETED和IRQ.RAW各自独立保存source/endpoint/value，ISR计数另记Measurement。机器块中复合摘要字段须由这些原子事实或已登记Artifact只读生成，不能给拼接对象伪造单个硬件端点。

机器块的failure_observations在PASS和FAIL均采集；保留原值和实际端点名称，未来报告模板以简短中文句子填值，不直接把字典倾倒为备注。

### 0.4 固定连接与执行预算

1. 内部回环不需要接线，仅证明控制器内路径；必须保留正常外部总线Case。
2. 被测CAN经收发器连接对端CANH/CANL；对端允许为CAN盒子，不要求再接第二个MCU实例。两端终端匹配且共地。MCU TX输出到本节点收发器TXD，收发器RXD回本节点RX。不得把两路TX对接。
3. 常规收发、速率、错误对照尽量保持这条总线不换线；Observer并接。需要无ACK时以受控静默模式实现，不人工拔线制造不可复现条件。
4. AUX时钟和错误注入/延迟观察需预留专用连接；未核实的引脚不填虚假GPIO或连接器号。
5. 单节点普通收发deadline为5 s；过滤拒绝的零帧观察在发送端真实完成后持续100 ms。预期无ACK、禁止TX或格式错误的节点不能等待TX成功；须以Peer/仪器确认刺激已发生作为100 ms负向窗口起点，CAN错误与Pending另按各Case判定。时间计数Case按公式设期限，压力每轮5 s。deadline耗尽必须保存最后硬件状态，不加无限轮询。
6. 所有参数节点在开始配置前独立复位参与IP、Service状态与资源池；结束先停外部激励和DMA，再停CAN并释放资源。多实例或共享RAM测试一次复位全部参与者，不能在活动传输中复位共享资源。

### 0.5 外部设备分工与固定接线

CAN盒子优先用于帧收发，但不是设备上限。需要仪器的Case必须按下列动作配齐，不把示波器当刺激源，也不把发送软件时间戳当引脚时刻。具体实例/GPIO、仪器通道和电压只在活动连接配置中指定。

| Case | 刺激由谁产生 | 观察位置与必须保存的量 | 固定夹具方式 |
|---|---|---|---|
| P1_017、P1_019 | 支持静默/无ACK合法位流的CAN设备；盒子不足时用协议发生器 | 示波器看DUT TX、RX及ACK槽；CAN盒子保留帧；无ACK重试还需错误位流捕获 | 收发器与CANH/L不换线；协议设备电控切正常/静默 |
| P2_009 | 支持指定位翻转/错误填充/CRC注入的协议发生器 | 示波器或位流分析仪核对注入位，DUT锁存首错误 | bit0节点隔离收发器RXD并由受控回送驱动，不能在推挽引脚强拉 |
| P2_011 | 可按参考帧触发回复的CAN盒子/协议发生器 | 示波器带CAN解码或等效硬件时间戳捕获SOF；总误差不超过1 NTU | 同一CANH/L；不靠PC sleep产生回复时刻 |
| P2_012 | 合法电平的20MHz时钟发生器 | AUX PAD由示波器实测频率、电平和占空比；CAN盒子核对收发 | AUX专用输入长期预留，不占控制UART |
| P3_002 | 可控数字延迟器或配测FPGA | 示波器CH1=DUT TX、CH2=实际RX；实测总延迟及首次错误 | 夹具电控选择透传/延迟；同时确认仲裁段回送仍合法 |
| P3_003 | 可外触发的脉冲发生器/AWG或配测FPGA | 示波器CH1=实际RX脉冲、CH2=TEST Sample Point；保存宽度、相位和采样网格 | 隔离RXD后注入；不要求专门开发配测FPGA才能采波形，判据缺口见5.3 |
| P3_004 | DUT预装连续帧，Peer只ACK | 示波器/CAN硬件解码测3对EOF结束至SOF间隔 | 正常固定CAN总线并接探头，无需延迟器 |
| P3_005 | 安全数字电平源给RX，DUT TEST控制TX | 示波器确认TX电平/采样周期；TEST.RX与实际引脚对照 | 电控隔离收发器、恢复后同一总线回归 |

TSU外部时间基是片内32-bit总线接入，RAM Watchdog是CAN主机RAM应答延迟；普通示波器不能制造这两种片内刺激。前者需目标提供真实外部时间基入口，后者需目标FPGA/测试接口提供受控延迟，不能用PC慢访问代替。

仪器型号暂不写死；执行前按当前配置校验所需触发、输出电平、解码和时间精度。设备不足时保留完整方法及缺少的动作；只有真实物理资源不满足时才能给出对应运行SKIP，本轮没有执行，不能预填SKIP结果。

### 0.6 已实现的基础Wrap接口

当前实现范围为控制器身份、INIT状态、位时序和核心选项；已接入Service及静态实例注册，尚无Formal Case，不等于本章全部动作已实现。

| 接口 | 参数与输出 | 执行边界 |
|---|---|---|
| `et_can_wrap_get_identity` | 逻辑实例→revision、endian原始身份 | 只读本IP Driver，不清状态 |
| `et_can_wrap_set_initializing` / `get_initializing` | Boolean请求 / 实际硬件状态 | 请求与查询分开；PC负责等待；不隐式调用CRG |
| `et_can_wrap_get_timing_limits` | 两阶段BRP、TSEG1、TSEG2、SJW实际计数上限 | 只描述编码范围，不保证实际输入时钟或总线速率 |
| `et_can_wrap_set_timing` / `get_timing` | 两阶段实际正整数计数 / 独立硬件读回 | 仅INIT中配置；非法计数无写入；硬件减一编码由内部Driver适配 |
| `et_can_wrap_set_options` / `get_options` | FD、BRS、自动重传、TX Pause、Edge Filter、Protocol Exception、TDC及RAM Watchdog | 各Boolean必须0/1；TDC Offset/Filter和Watchdog为实际控制器周期数；仅INIT中配置；不修改位时序、RAM布局、过滤规则 |
| `et_can_wrap_get_option_limits` | TDC Offset、Filter、RAM Watchdog上限 | 只描述芯片字段上限，不填测试默认值 |

公共Header只用固定宽度类型和统一Wrap状态；实现不访问寄存器，不调用GPIO、CRG、DMA或IRQ Wrap。芯片实例和计数上限来自Chip Config。SDK没有revision读取接口，因此仅在CAN Driver底部隔离区增加`CAN_testGetRevision`，未增加任意寄存器访问接口。

### 0.7 基础命令Wire

CAN Service ID=`0x010C`，复用既有ET-Frame。Body前缀为`instance_id:u8`；后续字段及响应均为小端u32，不直接传C结构体。实例必须与路由选择的Service实例一致，保留命令返回INVALID_COMMAND，长度不足或多余均返回INVALID_PARAM。写命令响应为空；错误时响应长度为0。

| Command | ID | 请求（前缀之后） | 响应 |
|---|---:|---|---|
| IDENTITY_GET | 0 | 无 | revision、endian |
| INITIALIZING_SET | 1 | initializing（严格0/1） | 无；仅发送请求，随后独立查询应答 |
| INITIALIZING_GET | 2 | 无 | initializing（实际状态0/1） |
| TIMING_LIMITS_GET | 3 | 无 | nominal/data各BRP、TSEG1、TSEG2、SJW实际计数上限，共8项 |
| TIMING_SET | 4 | nominal/data各BRP、TSEG1、TSEG2、SJW实际正整数，共8项 | 无；未处于INIT返回BUSY |
| TIMING_GET | 5 | 无 | nominal/data硬件时序读回，共8项 |
| OPTIONS_SET | 6 | FD、BRS、automatic_retry、TX Pause、Edge Filter、Protocol Exception、TDC Enable、TDC Offset、TDC Filter、RAM Watchdog，共10项 | 无；INIT前提及参数校验与TIMING_SET相同 |
| OPTIONS_GET | 7 | 无 | 上述10项独立硬件读回 |
| OPTION_LIMITS_GET | 8 | 无 | TDC Offset、TDC Filter、RAM Watchdog三项上限 |
| RAM_LIMITS_GET | 9 | 无 | ram_bytes、std_count、ext_count、tx_count、rx_fifo_count、event_count、rx_buffer_count，共7项 |
| RAM_LAYOUT_SET | 10 | 下述完整RAM布局24项 | 无；INIT前提，全部范围和重叠检查先于写入 |
| RAM_LAYOUT_GET | 11 | 无 | 24项真实配置读回，不使用请求缓存 |
| BUS_CONFIG_SET | 12 | 下述总线配置11项 | 无；INIT前提，不改变RAM、位时序或TEST/LBCK |
| BUS_CONFIG_GET | 13 | 无 | 11项实际配置 |
| LOOPBACK_SET | 14 | mode：0关闭、1内部、2外部 | 无；INIT前提，内部MON=1，外部/关闭MON=0 |
| LOOPBACK_GET | 15 | 无 | 实际有效mode；由TEST/LBCK与MON共同决定 |
| BUS_LIMITS_GET | 16 | 无 | timestamp_divisor、timeout_period上限 |
| TX_WRITE | 17 | index、identifier、flags、dlc、marker共5个u32，加64-byte固定payload区 | 无；只装载，不请求发送 |
| TX_REQUEST | 18 | 非零TX Buffer位图mask | 无；一次原子请求，不代表完成 |
| TX_STATUS_GET | 19 | 无 | pending、completed、cancelled、free_count、get_index、put_index、full，共7项 |
| RX_FIFO_STATUS_GET | 20 | FIFO索引 | fill、get_index、put_index、full、lost，共5项 |
| RX_READ | 21 | source、index | 下述8个u32及64-byte固定payload区；不Ack |
| RX_FIFO_ACK | 22 | FIFO索引、已观测的Get Index | 无；只Ack当前非空FIFO头，拒绝过期索引 |
| RX_BUFFER_STATUS_GET | 23 | 无 | low、high两组u32新数据位图 |
| RX_BUFFER_ACK | 24 | low、high两组显式位图 | 无；不读取Buffer，不清FIFO |

帧flags是公共Wire位图：EXTENDED=1、REMOTE=2、FD=4、BRS=8、ESI=16、STORE_EVENT=32、CAPTURE_TIME=64；后两项仅用于TX。Identifier为未移位的正常ID；DLC是协议四位编码，Classic DLC9～15仍为8-byte，Remote没有payload。TX有效payload长度必须匹配DLC，Wire剩余区填零；FD不允许Remote，Classic不接受BRS/ESI标记。基础TX Marker当前是8-bit，宽Marker功能必须另行实现后才能覆盖P1_010，不默默截断。

RX source：0为Dedicated Buffer，1为FIFO0，2为FIFO1。FIFO读取index参数固定为0表示当前头；响应顺序是`identifier, flags, dlc, timestamp, filter_index, nonmatching, data_length, index`，后接64-byte数据区。`index`为实际读取位置；`data_length`为真实槽内存储长度，可能短于DLC表达的总线长度，不能用零补成“完整帧”。Case应在刺激停止或明确受控窗口内读取，硬件状态快照不宣称跨寄存器原子采样。

TX_WRITE检查实际RAM容量和Pending，不允许覆盖硬件占用的槽；FIFO/Queue写入必须使用当前Put Index。TX_REQUEST只接受已分配Buffer范围内的mask，不自动装帧；先前准备的数据、发送请求、完成状态和RX观测必须在Case中分别执行并验证。TX/RX等待由PC Driver单一Deadline实现；超时保留最后事实，不自动重发、复位或延长预算。

总线配置顺序：`monitor, restricted, timestamp_divisor, timestamp_source, timeout_source, timeout_period, timeout_enabled, reject_remote_ext, reject_remote_std, unmatched_ext, unmatched_std`。Boolean严格0/1；timestamp_divisor为实际正分频数，timeout_period为计数重装值。Timestamp来源0关闭/1内部/2外部；Timeout来源0连续/1TX Event/2RX0/3RX1；未命中策略0RX0/1RX1/2拒绝。

该配置组对应已有Chip Driver的完整配置动作，不隐式选择测试模式。Case先选择回环，再写最终BUS_CONFIG，明确决定MON/ASM；例如内部回环必须保持monitor=true，restricted测试不能与回环组合。LOOPBACK_SET不启动CAN；BUS_CONFIG_GET不读取/清除协议错误计数，不把设置成功等同真实总线行为。

RAM布局顺序：`std_offset, std_count, ext_offset, ext_count, tx_offset, tx_buffer_count, tx_fifo_count, tx_queue, tx_payload_bytes, event_offset, event_count, event_watermark, rx0_offset, rx0_count, rx0_watermark, rx0_overwrite, rx1_offset, rx1_count, rx1_watermark, rx1_overwrite, rx_buffer_offset, rx_buffer_payload_bytes, rx0_payload_bytes, rx1_payload_bytes`。

- Offset单位为CAN Message RAM内的字节偏移，不是CPU物理地址；要求自然字对齐，各有效区域不重叠、不越过RAM容量。
- Payload字段为实际字节容量；queue/overwrite严格0或1。计数为0显式关闭对应区域，不能保持旧配置；允许RX-only布局。
- Dedicated RX没有硬件数量寄存器，因此布局按RAM_LIMITS_GET发布的rx_buffer_count预留完整区域，不虚构数量读回。PC布局规划必须计算该区间；其他计数区域可设0。
- SET仅配置布局，不清RAM、不Ack、不复位；数据准备与状态隔离仍是Case显式步骤。

Service只解码、调用本CAN Wrap、编码；不执行GPIO/CRG配置或测试判断。Wrap的STATE_ERROR映射现有ET_STATUS_BUSY（当前状态不满足配置前提），其他Driver执行错误映射INTERNAL_ERROR；未新增公共状态码或旧协议兼容分支。后续数据通路命令只能追加ID并在此处同步，不复用已分配ID。

### 0.8 PC基础接口

`CanDriver`绑定调用者提供的逻辑实例；构造不操作硬件。动作与0.7命令一一对应，配置模型使用实际正整数时序计数和Boolean，不暴露SDK枚举。GET独立读取硬件，不返回先前请求缓存。

`wait_initializing`仅在单一Deadline内查询INIT，不发送切换请求、不复位IP。GPIO、CRG及外部CAN盒子由Case分别调用各自Driver/Adapter；CAN Driver不代为编排。只有只读命令允许声明安全重试。

RAM对应`CanRamLayout`、`CanRamLimits`及`ram_layout_set/get`、`ram_limits_get`。模型显式传参，不在Driver内选择测试布局；这些动作均只等待本次响应，失败原样上抛，不替调用者复位。

总线配置对应`CanBusConfig`、`CanBusLimits`、`bus_config_set/get`、`bus_limits_get`；回环使用`CanLoopback`与`loopback_set/get`。Selector必须传公共Enum，不能直接传芯片数值。SET不自动重试；GET对未知Enum/非法Boolean拒绝解码。

## 1. Feature Catalog

本表37项已有明确硬件行为及观测/判据；真实ECC和边沿过滤2项候选行为仍在第5节保留。DMU RX时间戳已形成PLAN；TX Event附加时间戳仍有格式缺口。编号空位不作为有效引用；具有PLAN不表示当前盒子已满足其资源要求。

| Feature ID | 报告名称 | 稳定语义 | 等级 | 关联 Case |
|---|---|---|---|---|
| CAN_F_001 | CAN复位与受保护配置 | 复位基线、INIT/CCE配置窗口和独立硬件读回 | P0 | CAN_P0_001 |
| CAN_F_002 | CAN内部回环 | 无需引脚链路的发送、接收及完成状态 | P0 | CAN_P0_002、CAN_P2_005 |
| CAN_F_003 | CAN外部总线收发 | 正常模式双节点收发；内部/外部回环的引脚输出区别 | P0 | CAN_P0_003、CAN_P2_005 |
| CAN_F_004 | Classic CAN帧格式与长度 | 11/29-bit ID、DLC与0～8-byte数据 | P1 | CAN_P0_002、CAN_P0_003、CAN_P1_001 |
| CAN_F_005 | CAN FD帧长度与BRS | FD DLC映射、最长64-byte、BRS开关 | P1 | CAN_P1_001、CAN_P3_001 |
| CAN_F_006 | CAN位时序与输入时钟 | 仲裁/数据速率及Sample Point随输入时钟正确配置 | P1 | CAN_P1_012、CAN_P2_012 |
| CAN_F_007 | CAN标准ID过滤 | Range、Dual、Mask、未匹配处理与优先级标记 | P1 | CAN_P1_002 |
| CAN_F_008 | CAN扩展ID过滤 | 29-bit Range、Dual、Mask、XIDAM与未匹配处理 | P1 | CAN_P1_003 |
| CAN_F_009 | CAN Remote帧过滤 | Classic RTR的允许/拒绝，不把FD帧构造为Remote | P1 | CAN_P1_004 |
| CAN_F_010 | CAN RX FIFO水位与满状态 | FIFO0/1新消息、水位、Full、Get/Put环回与Ack | P1 | CAN_P1_005 |
| CAN_F_011 | CAN RX FIFO阻塞与覆盖 | 满后丢弃新帧或覆盖旧帧，并验证丢失标志 | P1 | CAN_P1_006 |
| CAN_F_012 | CAN专用RX Buffer与New Data | 定向接收、New Data位、独立清除和边界Buffer | P1 | CAN_P1_007 |
| CAN_F_013 | CAN TX Buffer、FIFO与Queue顺序 | 同时挂起的专用Buffer/Queue按ID优先，FIFO按入队顺序 | P1 | CAN_P1_008 |
| CAN_F_014 | CAN取消请求与重发 | 无ACK失败、自动重发开关及挂起请求取消 | P1 | CAN_P1_017 |
| CAN_F_015 | CAN TX Event FIFO存取 | 发送事件、Marker、水位、满/丢失、Ack | P1 | CAN_P1_009 |
| CAN_F_016 | CAN Message Marker位宽 | 8-bit和16-bit Marker与时间戳互斥关系 | P1 | CAN_P1_010 |
| CAN_F_017 | CAN双中断线与W1C | Source使能、Line路由、ISR事实与单独清除 | P1 | CAN_P1_011 |
| CAN_F_018 | CAN 16-bit时间戳 | 关闭/内部计数、分频、消息锁存、清零和回绕 | P1 | CAN_P1_013 |
| CAN_F_019 | CAN Timeout计数 | 连续、RX FIFO0/1及TX Event FIFO控制的超时 | P1 | CAN_P1_014 |
| CAN_F_020 | CAN TSU捕获与New/Lost | 内外32-bit时间基、单槽捕获、覆盖丢失与读清 | P1 | CAN_P1_018、CAN_P2_008、CAN_P2_013 |
| CAN_F_021 | CAN Clock Stop请求与恢复 | 空闲时请求、应答和恢复收发；不等同功耗测量 | P1 | CAN_P1_015 |
| CAN_F_022 | CAN Message RAM读写与March C- | 受限RAM区域的固定模式、地址模式和March C-覆盖 | P1 | CAN_P1_016 |
| CAN_F_023 | CAN多实例存储隔离 | 实例独立配置和Message RAM不互相覆盖 | P2 | CAN_P2_004 |
| CAN_F_024 | CAN DMU发送与接收搬运 | DMA通过DMU虚拟窗口搬运帧，RX0/RX1选择 | P2 | CAN_P2_001、CAN_P2_008 |
| CAN_F_025 | CAN DMU TX Event搬运 | DMA搬运TX Event并推进硬件队列 | P2 | CAN_P2_002、CAN_P2_013 |
| CAN_F_026 | CAN DMU非法访问IRQ | 最短非法窗口访问及对应错误中断、复位恢复 | P2 | CAN_P2_007 |
| CAN_F_027 | CAN ECC中断Force、Mask与Clear | 验证ECC中断链，不代表真实RAM纠错 | P2 | CAN_P2_003 |
| CAN_F_029 | CAN Monitor与Restricted | 合法帧接收、ACK行为和禁止主动发送 | P1 | CAN_P1_019 |
| CAN_F_030 | CAN TDC启用收发 | 补偿配置读回及启用后的外部FD BRS通信；延迟边界另测 | P1 | CAN_P1_021、CAN_P3_002 |
| CAN_F_032 | CAN TX发送暂停 | 连续Pending帧间增加两个nominal bit | P3 | CAN_P3_004 |
| CAN_F_033 | CAN协议错误与Bus Off | ACK/Bit/Stuff/Form/CRC错误及Bus Off协议恢复 | P2 | CAN_P2_009 |
| CAN_F_034 | TTCAN触发表与时间窗 | Level1参考消息、周期发送及接收漏帧MSC | P2 | CAN_P2_011 |
| CAN_F_035 | CAN Message RAM访问看门狗 | 真实CAN主机RAM访问超时及WDI中断 | P2 | CAN_P2_010 |
| CAN_F_036 | CAN连续收发 | 有界连续帧、序号、数量、数据与丢帧检查 | P3 | CAN_P3_001 |
| CAN_F_037 | CAN FD ISO与Non-ISO | 两种FD编码同格式收发及交叉格式拒绝 | P1 | CAN_P1_020 |
| CAN_F_038 | CAN TEST引脚控制 | TX强制电平/采样点输出、RX实际输入读回 | P3 | CAN_P3_005 |
| CAN_F_039 | CAN AUX时钟收发 | 外部时钟输入作为CAN时钟时的总线数据路径 | P2 | CAN_P2_012 |

## 2. Case Catalog

39个PLAN是设计数量，不是通过数；3个DESIGN_GAP（P2_006、P2_013、P3_003）已列具体确认步骤及转PLAN条件，不冒充实现就绪。参数执行数不计入Case数量。基础外部收发允许片上Peer或CAN盒子；位流注入、精确时标和电气隔离另列资源，不能假定盒子全具备。

| Case ID | 测试目的 | 等级 | 资源 | 设计状态 |
|---|---|---|---|---|
| CAN_P0_001 | CAN复位与受保护配置 | P0 | R0 | PLANNED，见第3节 |
| CAN_P0_002 | CAN内部回环基础收发 | P0 | R1 | PLANNED，见第3节 |
| CAN_P0_003 | CAN双节点正常总线收发 | P0 | R2 | PLANNED，见第3节 |
| CAN_P1_001 | CAN帧格式与DLC边界 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_002 | CAN标准ID过滤与路由 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_003 | CAN扩展ID过滤与掩码 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_004 | CAN Remote帧允许与拒绝 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_005 | CAN RX FIFO水位、满与环回 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_006 | CAN RX FIFO满后阻塞与覆盖 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_007 | CAN专用RX Buffer及New Data边界 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_008 | CAN TX FIFO与Queue优先级 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_009 | CAN TX Event FIFO水位与丢失 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_010 | CAN 8-bit与16-bit Message Marker | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_011 | CAN中断Line路由与独立清除 | P1 | R1～R2 | PLANNED，见第3节 |
| CAN_P1_012 | CAN位速率与时钟矩阵 | P1 | R2 | PLANNED，见第3节 |
| CAN_P1_013 | CAN内部16-bit时间戳 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_014 | CAN Timeout四种计数源 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_015 | CAN Clock Stop请求与恢复 | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_016 | CAN Message RAM模式与March C- | P1 | R1 | PLANNED，见第3节 |
| CAN_P1_017 | CAN取消请求与重发 | P1 | R4 | PLANNED，见第3节 |
| CAN_P1_018 | CAN TSU内外时间基与丢失 | P1 | R1～R3 | PLANNED，见第3节 |
| CAN_P1_019 | CAN Monitor与Restricted模式 | P1 | R4 | PLANNED，见第3节 |
| CAN_P1_020 | CAN FD ISO与Non-ISO格式 | P1 | R2～R4 | PLANNED，见第3节 |
| CAN_P1_021 | CAN TDC启用后的FD总线收发 | P1 | R2～R4 | PLANNED，见第3节 |
| CAN_P2_001 | CAN DMA经DMU发送与接收 | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_002 | CAN DMA搬运TX Event | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_003 | CAN ECC中断链强制触发 | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_004 | CAN多实例Message RAM隔离 | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_005 | CAN内部与外部回环引脚对照 | P2 | R2 | PLANNED，见第3节 |
| CAN_P2_006 | CAN Message RAM真实ECC注入 | P2 | R1 | DESIGN_GAP，见第5节 |
| CAN_P2_007 | CAN DMU非法访问与中断 | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_008 | CAN DMU接收TSU时间戳 | P2 | R1 | PLANNED，见第3节 |
| CAN_P2_009 | CAN协议错误与Bus Off恢复 | P2 | R4 | PLANNED，见第3节 |
| CAN_P2_010 | CAN Message RAM访问Watchdog | P2 | R3 | PLANNED，见第3节 |
| CAN_P2_011 | TTCAN触发表与时间窗 | P2 | R4 | PLANNED，见第3节 |
| CAN_P2_012 | CAN AUX时钟下总线收发 | P2 | R4 | PLANNED，见第3节 |
| CAN_P2_013 | CAN DMU TX Event附加TSU时间戳 | P2 | R1 | DESIGN_GAP，见第5节 |
| CAN_P3_001 | CAN有界连续收发 | P3 | R2 | PLANNED，见第3节 |
| CAN_P3_002 | CAN TDC发送延迟补偿 | P3 | R4 | PLANNED，见第3节 |
| CAN_P3_003 | CAN接入边沿过滤 | P3 | R4 | DESIGN_GAP，见第5节 |
| CAN_P3_004 | CAN发送Pause间隔 | P3 | R4 | PLANNED，见第3节 |
| CAN_P3_005 | CAN测试模式TX与RX引脚 | P3 | R4 | PLANNED，见第3节 |

## 3. Machine-readable Case Contract

### CAN_P0_001 CAN复位与受保护配置

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P0_001
case_name: CAN复位与受保护配置
report_feature: |-
  1. CAN复位与受保护配置
p_level: P0
feature_refs: [CAN_F_001]
method:
  inputs:
    - "配置输入：选Capability指定的代表实例；仲裁500 kbit/s，另选一组可达位时序；寄存器复位值取芯片映射，不由当前读值推导。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "复位读取：读取IDENTITY及CONFIG.INIT、FD_ENABLED和BIT_TIMING，与芯片复位定义比较。"
    - "配置窗口：进入INIT并确认后打开配置写权限，写入第一组位时序与FD开关。"
    - "独立读回：从硬件CONFIG读取实际值，关闭写权限后尝试改变受保护位时序。"
    - "保护验证：确认窗口关闭时受保护字段保持原值，再重新开启窗口并写第二组配置。"
    - "再次复位：确认第二组读回成功，执行IP复位后复查初始字段，保存前后值。"
  observations:
    - "配置事实：CONFIG.BIT_TIMING在允许写时等于输入，禁止写时保持原值；证明硬件保护而非缓存回显。"
    - "复位事实：IDENTITY不变，CONFIG指定字段回到芯片映射复位值。"
  pass_criteria:
    - "保护正确：两组写入与禁止写场景全部满足配置窗口语义。"
    - "复位正确：被修改字段确实先变化、复位后恢复，不使用全寄存器零值断言。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "代表CAN实例；本Case仅配置和读回", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN复位与受保护配置：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"config","label":"CONFIG.BIT_TIMING允许写/禁止写/复位后读回","source":"dut","role":"actual","format":"text"}
  - {"key":"identity","label":"IDENTITY与CONFIG.INIT/FD_ENABLED前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN复位与受保护配置的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P0_002 CAN内部回环基础收发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P0_002
case_name: CAN内部回环基础收发
report_feature: |-
  1. CAN内部回环
  2. Classic CAN帧格式与长度
p_level: P0
feature_refs: [CAN_F_002, CAN_F_004]
method:
  inputs:
    - "帧输入：Classic、标准ID 0x123，8-byte PATTERN_A及PATTERN_B各一帧；仲裁500 kbit/s，接收路由FIFO0。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "模式配置：在INIT窗口配置内部回环、位时序及小型互不重叠Message RAM布局，接收该ID到FIFO0。"
    - "总线启动：退出INIT，确认模式读回为内部回环，启用轮询而非DMA/ISR搬运。"
    - "逐帧发送：装入一帧并发出请求，等待TX.COMPLETED及RX0.FILL至少1，再处理下一帧。"
    - "读取应答：按RX0.GET_INDEX读取完整帧并Ack对应索引，确认FIFO退回空。"
    - "结果比较：分别比较ID、格式、DLC、长度及逐Byte数据，确认两帧无残留、无丢失标志。"
  observations:
    - "帧数据：RX.FRAME与两组独立Expected完全相同，TX.COMPLETED对应本次请求。"
    - "FIFO事实：RX0.FILL由0到1再到0，RX0.LOST为0；证明真实接收和Ack。"
  pass_criteria:
    - "逐帧一致：两帧均有发送完成且元数据和有效字节一致。"
    - "队列正常：读取并Ack后FIFO为空，未产生丢帧；不能据此声称已验证外部引脚。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN内部回环基础收发：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"frame","label":"RX.FRAME实际ID、DLC及payload","source":"dut","role":"actual","format":"text"}
  - {"key":"fifo","label":"RX0.FILL/LOST与TX.COMPLETED","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN内部回环基础收发的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P0_003 CAN双节点正常总线收发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P0_003
case_name: CAN双节点正常总线收发
report_feature: |-
  1. CAN外部总线收发
  2. Classic CAN帧格式与长度
p_level: P0
feature_refs: [CAN_F_003, CAN_F_004]
method:
  inputs:
    - "固定连接：由连接文件选择被测CAN和Peer（另一CAN节点或CAN盒子）；收发器接同一CANH/CANL总线及共地，两端正确终端匹配；禁止把TX/RX直接相连作为正常CAN总线。"
    - "帧输入：正常模式、500 kbit/s；两端依次发送标准ID 0x123和0x321，各2帧8-byte且序号不同。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "引脚与总线：经独立GPIO Driver配置被测端TX/RX及收发器Enable；另一片上节点同样配置，CAN盒子由其设备接口设置，不能向盒子发送DUT的GPIO命令。"
    - "双端初始化：两端配置相同位时序和接收过滤，关闭所有回环，退出INIT。"
    - "正向发送：被测CAN发两帧，逐帧等待硬件TX完成、对端RX有效并Ack。"
    - "反向发送：保持同一接线，对端发两帧，被测CAN接收并Ack。"
    - "双向核对：逐帧检查ID、长度、序号和数据，以及双方TX完成、无RX Lost和Bus Off。"
  observations:
    - "外部路径：对端RX.FRAME对应被测端输入，反向同理；两端回环均关闭。"
    - "硬件终态：被测端TX.COMPLETED有效、RX.LOST=0、PROTOCOL.BUS_OFF=0；Peer必须提供真实发送完成和接收记录，不要求盒子暴露DUT寄存器。"
  pass_criteria:
    - "链路真实：四帧均由另一控制器接收，不能使用本机回环数据代替。"
    - "数据正确：双方有效字节和元数据逐项相等，无多帧、少帧和超时。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "被测CAN经收发器连接Peer；实例和GPIO来自连接文件", bench: "另一CAN节点或CAN盒子，支持基础发送/捕获；无需示波器"}
backend: [FPGA, Silicon]
evidence: ["CAN双节点正常总线收发：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"frames","label":"被测CAN RX.FRAME的ID、序号及payload","source":"dut","role":"actual","format":"text"}
  - {"key":"peer_frames","label":"Peer实际捕获帧及发送完成记录","source":"peer","role":"actual","format":"text"}
  - {"key":"status","label":"被测CAN TX.COMPLETED、RX.LOST和PROTOCOL.BUS_OFF","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN双节点正常总线收发的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_001 CAN帧格式与DLC边界

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_001
case_name: CAN帧格式与DLC边界
report_feature: |-
  1. Classic CAN帧格式与长度
  2. CAN FD帧长度与BRS
p_level: P1
feature_refs: [CAN_F_004, CAN_F_005]
method:
  inputs:
    - "参数矩阵：标准/扩展ID；Classic DLC=0～15，其中9～15均为8-byte且RX原始DLC须保留；FD DLC=0～15映射0～8、12、16、20、24、32、48、64-byte；FD覆盖BRS关/开，Classic不使用BRS。"
    - "数据与速率：两种PATTERN依次发送；标准ID取0和0x7FF，扩展ID取0和0x1FFFFFFF；仲裁500 kbit/s、FD数据2 Mbit/s或预先确认的可达值。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "节点配置：按当前格式与BRS配置内部回环、位时序和64-byte接收元素，明确DLC与有效字节长度映射。"
    - "帧组装：按当前ID、DLC构造两帧不同数据，零长度帧不读取数据字节。"
    - "传输等待：逐帧请求发送，等待TX完成和接收就绪，不以入队成功作为完成。"
    - "接收读取：保存RX格式、BRS、ID、DLC及实际有效字节，按正确索引Ack。"
    - "矩阵判定：逐项对照输入及独立DLC表，全部合法参数节点满足才通过。"
  observations:
    - "帧格式：RX.FRAME的ID类型、ID、FD、BRS和DLC与输入一致。"
    - "长度与数据：RX有效长度等于DLC表，数据逐Byte等于Expected；SDK结构体大小不是线上长度。"
  pass_criteria:
    - "节点完整：全部声明组合完成，缺少数据速率映射是实施缺口而不是删除矩阵。"
    - "帧准确：格式、有效长度和数据均正确；该R1结果不替代外部BRS速率测量。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN帧格式与DLC边界：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"format","label":"RX.FRAME的ID、XTD、FD、BRS、DLC和有效长度","source":"dut","role":"actual","format":"text"}
  - {"key":"payload","label":"RX.FRAME有效payload与首个不匹配","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN帧格式与DLC边界的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_002 CAN标准ID过滤与路由

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_002
case_name: CAN标准ID过滤与路由
report_feature: |-
  1. CAN标准ID过滤
p_level: P1
feature_refs: [CAN_F_007]
method:
  inputs:
    - "过滤矩阵：标准ID；Range闭区间0x120～0x180输入0x11F/0x120/0x150/0x180/0x181，Dual输入0x101/0x110/0x111，Mask配置ID=0x400、Mask=0x700并输入0x400/0x4FF/0x500。"
    - "重叠顺序：增加两条均精确匹配ID 0x123的规则，索引0到FIFO0、索引1到FIFO1；交换两条的路由再执行，最后禁用索引0。Expected分别只入FIFO0、只入FIFO1、只入索引1的FIFO，匹配索引为0/0/1。"
    - "路由矩阵：匹配路由FIFO0、FIFO1、拒绝；未匹配路由FIFO0、FIFO1、拒绝独立配置；另以单一匹配规则置高优先级标记。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "过滤配置：内部回环，两个FIFO均深度4；普通节点只启用当前项；重叠节点同时启用两项，未匹配统一拒绝；其他项禁用。"
    - "边界发送：逐个发送当前规则的命中及不命中ID，每帧包含唯一序号；每帧先等待TX完成。"
    - "接收检查：接收型预期读取目标FIFO并Ack；拒绝型预期在100 ms窗口内两个FIFO均无新增，且TX已经完成。"
    - "规则索引：ANMF=0时检查RX.FILTER_INDEX；ANMF=1时索引无效，不作等值断言。重叠节点检查首个启用命中项并确认另一FIFO没有副本；高优先级节点另检查HIGH_PRIORITY.FILTER_INDEX及HP IRQ。"
    - "判据汇总：用PC对输入ID执行Range、等值或按位Mask逻辑得Expected；核对路由、数量、ID和序号。"
  observations:
    - "过滤结果：RX0/RX1.FILL及RX.FILTER_INDEX与当前匹配规则一致，拒绝时两个FIFO无新增。"
    - "优先级事实：HIGH_PRIORITY的Filter索引及IRQ.RAW对应唯一命中规则，不以滤波配置读回代替接收验证。"
  pass_criteria:
    - "命中准确：所有边界及未匹配策略与PC独立判定一致，数据和序号不丢失。"
    - "路由准确：只在预期FIFO出现一帧；拒绝的无数据观察必须建立在该帧TX完成后。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN标准ID过滤与路由：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"route","label":"RX0/RX1.FILL与RX.FILTER_INDEX","source":"dut","role":"actual","format":"text"}
  - {"key":"priority","label":"HIGH_PRIORITY.FILTER_INDEX及IRQ.RAW","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN标准ID过滤与路由的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_003 CAN扩展ID过滤与掩码

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_003
case_name: CAN扩展ID过滤与掩码
report_feature: |-
  1. CAN扩展ID过滤
p_level: P1
feature_refs: [CAN_F_008]
method:
  inputs:
    - "过滤矩阵：扩展ID；Range闭区间0x120～0x180输入0x11F/0x120/0x150/0x180/0x181，Dual输入0x101/0x110/0x111，Mask配置ID=0x400、Mask=0x700并输入0x400/0x4FF/0x500。"
    - "全局Mask：精确Range 0x120～0x120，输入0x120/0x121/0x12F/0x130；XIDAM=0x1FFFFFFF时仅0x120命中，XIDAM=0x1FFFFFF0时前三项命中；Range绕过XIDAM时仍仅0x120命中。Mask作用于收到的ID，不改写保存的原始RX ID。"
    - "高位区分：Dual规则为0x10000123和0x1FFFFFED，再发低位相同的0x123作反例；前两项接收，后一项拒绝，不能只用11-bit范围的输入验证29-bit比较。"
    - "重叠顺序：增加两条均精确匹配ID 0x123的规则，索引0到FIFO0、索引1到FIFO1；交换两条的路由再执行，最后禁用索引0。Expected分别只入FIFO0、只入FIFO1、只入索引1的FIFO，匹配索引为0/0/1。"
    - "路由矩阵：匹配路由FIFO0、FIFO1、拒绝；未匹配路由FIFO0、FIFO1、拒绝独立配置；另以单一匹配规则置高优先级标记。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "过滤配置：内部回环，两个FIFO均深度4；普通节点只启用当前项；重叠节点同时启用两项，未匹配统一拒绝；其他项禁用。"
    - "边界发送：逐个发送当前规则的命中及不命中ID，每帧包含唯一序号；每帧先等待TX完成。"
    - "接收检查：接收型预期读取目标FIFO并Ack；拒绝型预期在100 ms窗口内两个FIFO均无新增，且TX已经完成。"
    - "规则索引：ANMF=0时检查RX.FILTER_INDEX；ANMF=1时索引无效，不作等值断言。重叠节点检查首个启用命中项并确认另一FIFO没有副本；高优先级节点另检查HIGH_PRIORITY.FILTER_INDEX及HP IRQ。"
    - "判据汇总：用PC先按当前XIDAM或绕过模式处理输入ID，再执行Range、等值或单项Mask得Expected；核对路由、数量、ID和序号。"
  observations:
    - "过滤结果：RX0/RX1.FILL及RX.FILTER_INDEX与当前匹配规则一致，拒绝时两个FIFO无新增。"
    - "优先级事实：HIGH_PRIORITY的Filter索引及IRQ.RAW对应唯一命中规则，不以滤波配置读回代替接收验证。"
  pass_criteria:
    - "命中准确：所有边界及未匹配策略与PC独立判定一致，数据和序号不丢失。"
    - "路由准确：只在预期FIFO出现一帧；拒绝的无数据观察必须建立在该帧TX完成后。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN扩展ID过滤与掩码：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"route","label":"RX0/RX1.FILL与RX.FILTER_INDEX","source":"dut","role":"actual","format":"text"}
  - {"key":"priority","label":"HIGH_PRIORITY.FILTER_INDEX及IRQ.RAW","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN扩展ID过滤与掩码的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_004 CAN Remote帧允许与拒绝

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_004
case_name: CAN Remote帧允许与拒绝
report_feature: |-
  1. CAN Remote帧过滤
p_level: P1
feature_refs: [CAN_F_009]
method:
  inputs:
    - "Remote输入：内部回环；Classic标准/扩展ID各用0x123，RTR=1、DLC=0和8；允许/拒绝Remote两种策略。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "过滤配置：使当前ID匹配，FIFO0接收；先允许该ID类型的Remote帧。"
    - "允许刺激：分别发DLC=0、8的Remote帧，等待TX完成及RX帧。"
    - "Remote核对：读取RTR、DLC和ID，确认RTR=1；Remote没有有效数据，不比较8个数据字节。"
    - "拒绝刺激：重新建立基线并设置拒绝Remote，再发同样帧；TX完成后100 ms观察FIFO不新增。"
    - "恢复对照：同ID改发8-byte数据帧，要求收到并匹配，排除过滤全部关闭造成假拒绝。"
  observations:
    - "接收类型：RX.FRAME.RTR/DLC/ID等于输入；拒绝时RX0.FILL保持0。"
    - "对照数据：拒绝Remote配置下同ID数据帧仍可接收，证明仅过滤Remote。"
  pass_criteria:
    - "允许正确：四种ID类型/DLC组合均接收，Remote不伪造数据长度。"
    - "拒绝正确：Remote无新增而数据对照有效；不构造不合法的FD Remote。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN Remote帧允许与拒绝：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"frame","label":"RX.FRAME.RTR/DLC/ID和数据帧正对照","source":"dut","role":"actual","format":"text"}
  - {"key":"fill","label":"拒绝窗口RX0.FILL","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Remote帧允许与拒绝的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_005 CAN RX FIFO水位、满与环回

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_005
case_name: CAN RX FIFO水位、满与环回
report_feature: |-
  1. CAN RX FIFO水位与满状态
p_level: P1
feature_refs: [CAN_F_010]
method:
  inputs:
    - "FIFO参数：FIFO0/FIFO1分别执行；深度4、水位2、阻塞模式；输入6个不同序号的Classic 8-byte帧，匹配规则只路由当前FIFO。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "FIFO配置：内部回环，配置深度/水位并禁用自动读取FIFO的ISR和DMA；清历史IRQ。"
    - "水位刺激：发送第一帧后读取FILL=1及水位IRQ=0；第二帧后读取FILL=2及水位IRQ=1。"
    - "满状态刺激：继续发到4帧，确认FILL=4、FULL=1；此阶段不超深度。"
    - "索引环回：读取并Ack最早两帧，再发送两帧，按GET_INDEX排空剩余四帧，记录索引跨界。"
    - "终态判定：读取FILL=0、FULL=0，六个序号按输入次序且LOST=0，核对新消息、水位和满事件。"
  observations:
    - "水位边界：RXn.FILL从1到2时水位事件首次出现，4帧时FULL有效。"
    - "环回事实：RXn.GET_INDEX/PUT_INDEX环回，六帧序号完整且排空后FILL=0。"
  pass_criteria:
    - "边界准确：水位和满的阈值均准确，不让回调提前排空掩盖状态。"
    - "数据准确：环回后无重复、丢失、错序，RXn.LOST=0。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN RX FIFO水位、满与环回：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"fifo","label":"RXn.FILL/FULL及GET_INDEX/PUT_INDEX","source":"dut","role":"actual","format":"text"}
  - {"key":"irq","label":"RXn水位/满IRQ.RAW及LOST","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN RX FIFO水位、满与环回的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_006 CAN RX FIFO满后阻塞与覆盖

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_006
case_name: CAN RX FIFO满后阻塞与覆盖
report_feature: |-
  1. CAN RX FIFO阻塞与覆盖
p_level: P1
feature_refs: [CAN_F_011]
method:
  inputs:
    - "满后输入：FIFO0/FIFO1分别执行；深度4、序号0～4共5帧；Blocking和Overwrite独立复位执行。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "接收配置：内部回环、当前FIFO深度4，选择Blocking或Overwrite；关闭自动出队。"
    - "填满确认：逐帧发序号0～3，确认4次TX完成、FILL=4、FULL=1。"
    - "超容量刺激：再发送序号4并等TX完成，保存FILL、FULL及LOST首次状态。"
    - "内容读取：停止发送，按GET_INDEX读四帧并逐个Ack，保存完整序号序列。"
    - "恢复验证：对Blocking清丢失事件，Overwrite按已确认语义处理其原值，然后发序号5并接收；Blocking期望旧0～3、Overwrite期望新1～4，恢复帧须完整。"
  observations:
    - "保留数据：RX.FRAME序号在Blocking为0/1/2/3，在Overwrite为1/2/3/4，FILL不超过4。"
    - "丢失与恢复：Blocking超容量后RXn.LOST/对应IRQ必须有效；Overwrite是否设置该事件尚缺目标语义，先保留原值，不用它判定覆盖成功；覆盖以实际保留序号为判据。"
  pass_criteria:
    - "模式区别：两种模式均准确保留各自四帧，不能只检查Full位。"
    - "恢复正常：新帧5正确，丢失清除后没有未消除的持续刺激。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN RX FIFO满后阻塞与覆盖：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"sequence","label":"RX.FRAME保留的四帧序号","source":"dut","role":"actual","format":"text"}
  - {"key":"overflow","label":"RXn.FILL/FULL/LOST首次值及恢复后值","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN RX FIFO满后阻塞与覆盖的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap", "overwrite_lost_flag_semantics_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_007 CAN专用RX Buffer及New Data边界

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_007
case_name: CAN专用RX Buffer及New Data边界
report_feature: |-
  1. CAN专用RX Buffer与New Data
p_level: P1
feature_refs: [CAN_F_012]
method:
  inputs:
    - "Buffer参数：合法专用RX容量允许时选索引0、31、32、63；不足时保留实际首/末和存在的32-bit分组边界，覆盖范围随Capability记录。"
    - "定向输入：每个Buffer分配不同匹配ID及8-byte PATTERN_A；过滤项索引不复用覆盖，FIFO不接收这些ID。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "布局配置：内部回环，按所选最高索引分配完整专用RX区域，过滤精确指向每个索引。"
    - "定向发送：依次发送各Buffer唯一ID，等待TX完成及该Buffer的NEW_DATA置位。"
    - "隔离读取：读取各Buffer帧和完整NEW_DATA位图，确认其他未写入Buffer不置位。"
    - "单独清除：只清一个Buffer NEW_DATA，确认该位清零而其他已置位的保留，再逐个清完。"
    - "重复接收：用新序号向第一个Buffer再发一帧，确认NEW_DATA重新置位且数据更新。"
  observations:
    - "接收端点：RX_BUFFER[index].FRAME等于对应ID和数据，NEW_DATA仅目标位变化。"
    - "清除隔离：NEW_DATA跨分组和末端位可独立清除，未出现FIFO路由。"
  pass_criteria:
    - "定向正确：每个选定Buffer都有真实接收数据而非仅位图读写。"
    - "位图正确：置位、清除和再次置位成立，数据不被相邻Buffer覆盖。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN专用RX Buffer及New Data边界：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"bitmap","label":"NEW_DATA置位/清单项/重接收位图","source":"dut","role":"actual","format":"text"}
  - {"key":"buffers","label":"RX_BUFFER[index].FRAME实际ID和payload","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN专用RX Buffer及New Data边界的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_008 CAN TX FIFO与Queue优先级

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_008
case_name: CAN TX FIFO与Queue优先级
report_feature: |-
  1. CAN TX Buffer、FIFO与Queue顺序
p_level: P1
feature_refs: [CAN_F_013]
method:
  inputs:
    - "挂起输入：3帧标准ID按0x300、0x100、0x200存入索引0/1/2；每帧序号等于索引。专用Buffer、FIFO、Queue三种模式分别复位。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "存储配置：内部回环，选择三种TX组织之一并分配3项，RX FIFO深度至少3。"
    - "预装帧组：在没有任何发送请求时写好三项，确认TX.PENDING=0，内容读回对应输入。"
    - "同时请求：一次原子批量请求挂起全部三项，不能循环调用单项请求造成第一帧提前起发。"
    - "接收记录：等三项发送完成，按接收先后读取3帧ID及序号并Ack。"
    - "顺序比较：FIFO期望0x300/0x100/0x200；Queue和专用Buffer期望0x100/0x200/0x300，检查完成位及最终TX空。"
  observations:
    - "发送顺序：RX.FRAME按接收顺序排列，独立Expected由TX组织和ID优先规则给出。"
    - "请求终态：TX.PENDING清零、三项COMPLETED有效、TX FIFO/Queue回到空。"
  pass_criteria:
    - "预装可靠：请求前全部数据已就绪、同一次硬件批量请求，不把调度竞态当优先级。"
    - "次序准确：三种模式分别满足其完整顺序且无丢失；不据此宣称验证跨节点仲裁。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN TX FIFO与Queue优先级：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"order","label":"RX.FRAME接收ID顺序","source":"dut","role":"actual","format":"text"}
  - {"key":"status","label":"TX.PENDING/COMPLETED及TX FIFO空闲状态","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN TX FIFO与Queue优先级的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","atomic_tx_request_driver_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_009 CAN TX Event FIFO水位与丢失

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_009
case_name: CAN TX Event FIFO水位与丢失
report_feature: |-
  1. CAN TX Event FIFO存取
p_level: P1
feature_refs: [CAN_F_015]
method:
  inputs:
    - "事件输入：内部回环，TX Event FIFO深度4、水位2；5帧8-byte且Marker为0～4，接收FIFO及时排空防止RX溢出混淆。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "事件配置：启用逐帧存TX Event，配置水位与深度，关闭自动读事件的ISR/DMU。"
    - "水位检查：发第一帧确认事件FILL=1、水位未到；发第二帧确认FILL=2及水位事件。"
    - "填满检查：发到第四帧，每帧确认TX成功，保存TX_EVENT.FULL和FILL=4。"
    - "事件丢失：发第五帧，确认数据仍成功接收但TX_EVENT.LOST置位；读取并Ack前四项。"
    - "清除恢复：检查前四项ID/Marker/发送类型，清事件丢失后再发Marker=5，确认出现一条正确新事件。"
  observations:
    - "事件内容：TX_EVENT.DATA的ID、Marker、发送结果来自真实成功发送，前四项不变。"
    - "容量边界：FILL在水位2/满4准确，额外帧成功但Event丢失，Ack后恢复。"
  pass_criteria:
    - "事件准确：已保存四条与发送序列一致，数据接收成功不能代替事件断言。"
    - "满后行为：第五条不覆盖前四条、LOST置位；排空清除后新事件正常。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN TX Event FIFO水位与丢失：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"events","label":"TX_EVENT.DATA的ID/Marker序列","source":"dut","role":"actual","format":"text"}
  - {"key":"status","label":"TX_EVENT.FILL/FULL/LOST在1/2/4/5帧后的值","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN TX Event FIFO水位与丢失的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_010 CAN 8-bit与16-bit Message Marker

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_010
case_name: CAN 8-bit与16-bit Message Marker
report_feature: |-
  1. CAN Message Marker位宽
p_level: P1
feature_refs: [CAN_F_016]
method:
  inputs:
    - "Marker矩阵：8-bit模式使用0x12和0xAB，16-bit模式使用0x1234和0xABCD；关闭TSU，发送事件启用，内部回环8-byte帧。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "Marker配置：配置当前Marker位宽，16-bit模式明确占用事件中原16-bit时间戳位置。"
    - "帧构造：写两帧不同Marker，先保存Marker Expected，确认配置读回。"
    - "发送完成：逐帧等TX.COMPLETED及TX_EVENT.FILL增加，不用RX时间戳推导Marker。"
    - "事件读取：读取完整原始TX Event，按当前模式解码Marker并Ack。"
    - "位宽判断：比较两条Marker完整有效位；16-bit模式不同时声称验证16-bit TX时间戳。"
  observations:
    - "标记端点：TX_EVENT.MARKER与两组Expected完全一致，高字节不能截断。"
    - "格式事实：CONFIG.MARKER_WIDTH与解码模式一致，TX完成且事件数量为2。"
  pass_criteria:
    - "位宽正确：两种模式各两条全部匹配，不以低8-bit相同判通过。"
    - "语义分离：16-bit Marker占用位不能再输出伪造的TX时间戳。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN 8-bit与16-bit Message Marker：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"marker","label":"TX_EVENT.MARKER实际8/16-bit值","source":"dut","role":"actual","format":"text"}
  - {"key":"mode","label":"CONFIG.MARKER_WIDTH及TX.COMPLETED","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN 8-bit与16-bit Message Marker的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_011 CAN中断Line路由与独立清除

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_011
case_name: CAN中断Line路由与独立清除
report_feature: |-
  1. CAN双中断线与W1C
p_level: P1
feature_refs: [CAN_F_017]
method:
  inputs:
    - "中断参数：RX FIFO New Message和TX Complete两源，分别路由Line0/Line1并交换；内部回环、外部回环和Normal+Peer三种路径；其他源禁用。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "事件基线：配置本节点模式及路由，开启本次TX Buffer完成事件产生条件，清历史Raw和ISR计数；先关闭Source及Line投递。"
    - "屏蔽刺激：回环节点发一帧；Normal节点DUT先发一帧并等Peer确认收到，再由Peer回发另一ID帧。确认本机TX完成与RX就绪后读取Raw中两源已置位、ISR计数仍0，避免把本机发出视作本机收到。"
    - "路由投递：打开目标Source及Line，等待各线路ISR锁存；ISR只锁存并屏蔽，不清本次待验证Raw。"
    - "独立清除：先W1C清TX Complete，确认RX Raw保留；再清RX Raw并Ack接收帧，确认两位均0。"
    - "新事件验证：重开使能并重复当前路径，要求再次投递到正确线路；交换路由后重复。外部路径保留Peer捕获，外部回环时Peer只听，Normal时Peer正常ACK。"
  observations:
    - "中断硬件：IRQ.RAW在屏蔽时可置位，各目标位W1C独立清除。"
    - "回调证据：IRQ_EVENT.LINE/SOURCE/COUNT记录实际ISR执行，线路交换后仍对应配置。"
  pass_criteria:
    - "路由正确：关闭投递无ISR，开放后每源至少一次正确线路投递，不能只验证Raw。"
    - "清除正确：无新刺激时清指定源不影响另一源，清后新事件仍可投递。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R2, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "内部回环无需接线；外部回环/Normal使用固定CAN总线及可切换静默/正常模式的Peer"}
backend: [FPGA, Silicon]
evidence: ["CAN中断Line路由与独立清除：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"raw","label":"IRQ.RAW屏蔽/开放/逐源清除前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"isr","label":"IRQ_EVENT实例/Line/Source/Count","source":"measurement","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN中断Line路由与独立清除的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_012 CAN位速率与时钟矩阵

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_012
case_name: CAN位速率与时钟矩阵
report_feature: |-
  1. CAN位时序与输入时钟
p_level: P1
feature_refs: [CAN_F_006]
method:
  inputs:
    - "历史参数：输入时钟20/40/80 MHz；Classic速率125k/250k/500k/800k/1M，FD仲裁500k/1M、数据2M/5M；只对硬件实际可提供的时钟列声明结果，缺项必须保留适配缺口。"
    - "独立时序：按输入时钟和合法BRP、TSEG1、TSEG2计算实际速率及采样点；选择可精确表示的配置，SJW不超过相关段长；每节点发两组不同64-byte或8-byte数据。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "时钟选择：通过独立CRG Driver设置参与CAN的输入时钟，确认Chip Mapping读回，不修改控制通信时钟。"
    - "位时序推导：PC按公式求仲裁/数据参数，并给两端配置相同实际速率和合法采样点。"
    - "配置核对：被测CAN的BIT_TIMING读回与PC计算值比较；Peer配置同一线上速率，但不用共享DUT输入时钟或寄存器布局；两端正常模式、关闭回环。"
    - "帧传输：两端轮流各发送两帧，FD设置BRS，使真实总线经历数据速率切换。"
    - "参数判定：比较对端帧、TX完成和错误状态，保存每节点时钟及实际速率；不可达项说明硬件依据而非静默丢弃。"
  observations:
    - "时序读回：CONFIG.INPUT_CLOCK_HZ及BIT_TIMING等于预定组合，实际速率由独立公式计算。"
    - "外部通信：DUT接收元素和Peer实际捕获逐Byte正确，DUT无Bus Off，双方发送完成；证明组合可通信，不代表示波器频率精度。"
  pass_criteria:
    - "参数完整：所有本芯片硬件允许的历史组合都有结论，不支持的时钟须有硬件依据。"
    - "双向完整：每节点四帧均正确完成，速率/采样点和实际时钟明确留证。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "被测CAN经收发器连接Peer；实例和GPIO来自连接文件", bench: "另一CAN节点或支持所列速率/帧格式的CAN盒子，无示波器要求"}
backend: [FPGA, Silicon]
evidence: ["CAN位速率与时钟矩阵：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"timing","label":"CONFIG.INPUT_CLOCK_HZ与BIT_TIMING实际参数","source":"dut","role":"actual","format":"text"}
  - {"key":"frame","label":"被测CAN RX.FRAME及PROTOCOL.BUS_OFF","source":"dut","role":"actual","format":"text"}
  - {"key":"peer_frames","label":"Peer实际捕获帧及发送结果","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN位速率与时钟矩阵的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","clock_profile_gap","board_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_013 CAN内部16-bit时间戳

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_013
case_name: CAN内部16-bit时间戳
report_feature: |-
  1. CAN 16-bit时间戳
p_level: P1
feature_refs: [CAN_F_018]
method:
  inputs:
    - "计数矩阵：时间戳关闭/内部计数，分频1/2/16；Classic内部回环，仲裁1 Mbit/s；消息时间戳只在8-bit Marker且TSU关闭时解码。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "关闭对照：关闭时间戳后发一帧，读取COUNTER及RX.TIMESTAMP，要求均为0。"
    - "分频配置：重新复位，选择内部时间戳与当前分频，清时间戳计数及Wrap IRQ。"
    - "锁存检查：发送两帧，每帧在发送前读取COUNTER、完成后读取COUNTER和RX.TIMESTAMP；用PC monotonic包围整个命令序列得到保守时间上界，必须小于半个回绕周期，随后按模65536核对锁存区间。PC时间只限制采样窗口，不充当计数精度Oracle。"
    - "回绕观察：持续轮询至Wrap IRQ，保存回绕前后COUNTER；相邻读值的monotonic上界也须小于半周期。若控制链路不能满足该预算，应先降低本Case仲裁速率并重新固定配置，不靠重复重跑找一次碰巧合格的样本。"
    - "清零检查：停止帧刺激，以一次受限Driver动作写计数清零后立即读回；实现前按实际总线访问最坏周期固定该动作耗时上界L，Expected上限为ceil(L×仲裁速率/分频)+1。记录L及原值，三个分频节点独立执行。"
  observations:
    - "锁存来源：RX.TIMESTAMP位于本次发送前后COUNTER的模区间内，不用PC串口耗时作精密时间基。"
    - "回绕事实：TIMESTAMP.WRAP_IRQ置位且COUNTER从高值回到低值；清零后的值小于读回延迟预算。"
  pass_criteria:
    - "功能完整：关闭为0，内部模式锁存来自正确计数窗口并有真实回绕。"
    - "边界明确：分频1/2/16读回正确；清零动作预算L须在实施前固定，窗口由独立时间上界判定；不合格窗口属于测量无效，不能当硬件计数错误或PASS。"
timeout: "每分频节点2×65536×分频/仲裁速率+5 s；每次前后计数窗口小于半个回绕周期"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN内部16-bit时间戳：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"timestamp","label":"TIMESTAMP.COUNTER前后值与RX.TIMESTAMP","source":"dut","role":"actual","format":"text"}
  - {"key":"wrap","label":"TIMESTAMP.WRAP_IRQ及清零前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN内部16-bit时间戳的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","atomic_timestamp_snapshot_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_014 CAN Timeout四种计数源

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_014
case_name: CAN Timeout四种计数源
report_feature: |-
  1. CAN Timeout计数
p_level: P1
feature_refs: [CAN_F_019]
method:
  inputs:
    - "超时矩阵：连续、RX FIFO0、RX FIFO1、TX Event FIFO四源，TOP=1000、分频1、仲裁500 kbit/s；IRQ捕获启用，FIFO深度4。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "计数配置：内部回环，配置当前超时源；先禁用计数，确认无Timeout事件。"
    - "装载启动：连续模式写入重装动作启动；FIFO模式先确认空时计数保持TOP，再发一帧使目标FIFO非空启动。"
    - "到期观察：不消费当前源FIFO，等待TIMEOUT.IRQ有效，保存COUNTER到期值和ISR锁存。"
    - "重装验证：连续模式写重装，FIFO模式读取并Ack到空，检查COUNTER重新为TOP或从TOP开始下降。"
    - "禁止对照：关闭计数，清IRQ并保持同样条件，等待至少两倍理论周期确认无新Timeout。"
  observations:
    - "计数来源：FIFO空/非空与TIMEOUT.COUNTER启动/重装关系一致，连续模式按写重装生效。"
    - "到期中断：TIMEOUT.IRQ及IRQ_EVENT出现，关闭计数后无新事件。"
  pass_criteria:
    - "来源准确：四种控制源分别满足启停和到期；不把Message RAM Watchdog当Timeout。"
    - "中断准确：至少两倍周期的禁止窗口无新事件，启用阶段必须产生到期及ISR事实。"
timeout: "到期等待2×TOP×分频/仲裁速率+5 s；禁用观察至少2×理论周期"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN Timeout四种计数源：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"counter","label":"TIMEOUT.COUNTER装载/到期/重装值","source":"dut","role":"actual","format":"text"}
  - {"key":"irq","label":"TIMEOUT.IRQ及对应IRQ_EVENT","source":"measurement","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Timeout四种计数源的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_015 CAN Clock Stop请求与恢复

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_015
case_name: CAN Clock Stop请求与恢复
report_feature: |-
  1. CAN Clock Stop请求与恢复
p_level: P1
feature_refs: [CAN_F_021]
method:
  inputs:
    - "停钟输入：内部回环正常收发一帧后无挂起TX，RX已Ack；只测试请求/应答，不直接关CRG时钟或宣称低功耗通过。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "运行基线：配置内部回环，发送PATTERN_A并确认TX完成及RX匹配。"
    - "停钟请求：确认TX无挂起后置CLOCK.STOP_REQUEST，等待INIT进入及STOP_ACK有效。"
    - "应答读取：保存请求、应答和模式；不读取已实际关闭总线时钟的寄存器。"
    - "退出请求：保持模块时钟开启，先解除请求并等待STOP_ACK=0，再清INIT并确认可运行；ACK仍有效时INIT受硬件保持，不能颠倒顺序。"
    - "恢复发送：发送不同PATTERN_B并比较RX与TX终态，确认不是读取旧接收帧。"
  observations:
    - "请求应答：CLOCK.STOP_REQUEST、STOP_ACK和CONFIG.INIT按顺序变化。"
    - "恢复数据：RX.FRAME为新的PATTERN_B且TX.COMPLETED有效。"
  pass_criteria:
    - "应答准确：空闲时请求可获应答、解除可退出，不把请求位回读当应答。"
    - "恢复正确：新的独立帧收发成功；功耗和外部唤醒另列待完善目标。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN Clock Stop请求与恢复：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"clock","label":"CLOCK.STOP_REQUEST/STOP_ACK与CONFIG.INIT","source":"dut","role":"actual","format":"text"}
  - {"key":"frame","label":"恢复后的RX.FRAME及TX.COMPLETED","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Clock Stop请求与恢复的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_016 CAN Message RAM模式与March C-

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_016
case_name: CAN Message RAM模式与March C-
report_feature: |-
  1. CAN Message RAM读写与March C-
p_level: P1
feature_refs: [CAN_F_022]
method:
  inputs:
    - "访问范围：仅Chip Mapping明确给出的可测试Message RAM区域；关闭该RAM所有CAN、DMU及DMA访问者，CPU 32-bit对齐访问，ECC按映射要求初始化。"
    - "模式算法：先全区域0x5A5A5A5A、0xA5A5A5A5与地址异或模式逐字写读；March C-为全写0、升序读0写1、升序读1写0、降序读0写1、降序读1写0、全读0。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "排他停机：停止全部共享RAM访问者并进入INIT，确认受测区域不包含控制寄存器或协议资源。"
    - "固定模式：遍历每个对齐地址写模式并逐字读回，记录首个不匹配地址、Expected和Actual。"
    - "地址模式：每个字写相对字索引异或0x5A5A5A5A，完整回读，检查地址别名。"
    - "March执行：按输入定义六个阶段遍历完整区域，每次读紧跟对应Expected，不用最后一次读取替代全程检查。"
    - "重建验证：全部清零并重建最小CAN布局，发一帧内部回环；保留实际测试字数及每阶段计数。"
  observations:
    - "RAM读回：MESSAGE_RAM[offset]等于每阶段独立Expected，测试范围及首错地址明确。"
    - "恢复端点：重建后TX完成和RX.FRAME正确，证明测试没有留下破坏性布局。"
  pass_criteria:
    - "遍历完整：每阶段访问数等于声明区域字数，所有读回正确；不能只抽样称全RAM通过。"
    - "结果区分：本Case只验证可寻址RAM读写/March C-，不声称完成ECC注入、纠错和所有物理阵列覆盖。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN Message RAM模式与March C-：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"ram","label":"MESSAGE_RAM首错offset/Expected/Actual","source":"dut","role":"actual","format":"text"}
  - {"key":"range","label":"Message RAM测试范围、字数及March阶段计数","source":"measurement","role":"actual","format":"text"}
  - {"key":"restore","label":"重建后RX.FRAME及TX.COMPLETED","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Message RAM模式与March C-的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","message_ram_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_017 CAN取消请求与重发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_017
case_name: CAN取消请求与重发
report_feature: |-
  1. CAN取消请求与重发
p_level: P1
feature_refs: [CAN_F_014]
method:
  inputs:
    - "发送条件：Normal、Classic 500 kbit/s、专用TX Buffer、ID 0x123及8-byte PATTERN_A；总线上只有DUT和可控Peer，关闭回环。"
    - "模式矩阵：自动重发开启/关闭各一轮；Peer静默时不提供ACK，恢复正常时提供ACK，禁止用无ACK推导Bus Off。"
  steps:
    - "独立基线：复位参与IP、Service和资源池，清捕获；配置CAN与TX完成/取消事件，先用正常Peer确认一帧可成功发送。"
    - "无ACK配置：Peer转静默，DUT配置本轮自动重发设置，预装一帧后只提交一次TX请求。"
    - "失败观测：由Peer捕获发送尝试及ACK槽，锁存DUT第一次ACK错误；重发关闭要求只有一次尝试且Pending退出，重发开启要求观察至少两次尝试且无Transmit Occurred。"
    - "取消挂起：仅重发开启分支向仍Pending的Buffer发取消；静默期间不可能成功ACK，等待Pending=0、Cancelled=1、Completed=0并记录取消事件。"
    - "恢复通信：Peer恢复正常，重新请求一帧不同序号，要求Completed=1、Pending=0，Peer捕获payload正确。"
    - "分支判定：两种重发配置均满足各自终态；取消与完成竞态只按本Case无ACK条件判定，不把Completed=1且Cancelled=1一概判为硬件错误。"
  observations:
    - "尝试与错误：Peer记录实际一次/多次发送尝试，DUT首次PROTOCOL.LAST_ERROR为ACK错误，排除尚未上总线造成假取消。"
    - "取消终态：自动重发开启分支TX.PENDING由1变0，TX.CANCELLED=1且TX.COMPLETED=0；恢复帧TX.COMPLETED=1且Peer实际收到。"
  pass_criteria:
    - "重发行为：禁重发仅一次失败尝试；允许重发出现至少两次尝试，均无发送完成。"
    - "取消与恢复：挂起请求取消有终态，恢复帧元数据和8-byte完全匹配，无残留Pending。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "可切换静默/正常并记录发送尝试的CAN Peer；当前盒子能力待确认"}
backend: [FPGA, Silicon]
evidence: ["CAN取消请求与重发：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"tx_state","label":"TX.PENDING/COMPLETED/CANCELLED前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"first_error","label":"PROTOCOL.LAST_ERROR首次值","source":"dut","role":"actual","format":"text"}
  - {"key":"attempts","label":"Peer发送尝试/ACK槽/恢复帧","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN取消请求与重发预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_018 CAN TSU内外时间基与丢失

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_018
case_name: CAN TSU内外时间基与丢失
report_feature: |-
  1. CAN TSU捕获与New/Lost
p_level: P1
feature_refs: [CAN_F_020]
method:
  inputs:
    - "时间基矩阵：内部计数分频4、外部固定值0x12345678/0x89ABCDEF；从硬件读取时间戳槽数N，合法N为4/8/16，SOF/EOF只枚举硬件声明支持的捕获位置。"
    - "单一捕获源：内部回环Classic 8-byte，TX Timestamp Capture开启，RX过滤不启用SYNC，避免一帧TX和RX各捕获一次；只直接读取已映射的TS0。"
  steps:
    - "独立基线：复位CAN、Service和资源池，配置内部回环、TSU使能及当前时间基；外部模式先稳定输入值并用ACTIVE_TIMEBASE读回确认。"
    - "新值捕获：记录ATB_before，逐帧发一个TX捕获，最多N帧，直到TSU.NEW[0]=1；期间只读New/Lost和发送状态，不读取时间戳槽。"
    - "读清核对：记录ATB_after及TSU.NEW/LOST，读取TS0一次，再读New/Lost；TS0对应New/Lost必须清零，其他槽位不受此次读取影响。"
    - "覆盖刺激：在2N次捕获开始前记录ATB_before，不再读取任何时间戳槽，连续完成2N个TX捕获后记录ATB_after；保存TSU.NEW[0]和LOST[0]，两者均须为1。"
    - "覆盖读清：停止新的捕获后读取TS0，按上一步区间核对数值，再检查New/Lost均清零；外部模式逐次更换两组常量，所有比较均保留捕获前后的独立输入。"
    - "值与状态判定：外部TS0必须等于送入的32-bit常量；内部TS0按32-bit模运算落入相应前后时间基区间，区间小于半量程；每组均验证New置位、覆盖Lost置位和读清。"
  observations:
    - "捕获内容：TSU.TS0等于外部固定输入，或位于内部ATB_before到ATB_after之间；TX.COMPLETED证明捕获刺激真实完成。"
    - "状态变化：TSU.NEW[0]捕获后为1，2N次未读捕获后LOST[0]=1，读TS0后两位为0且无关槽位不被清除。"
  pass_criteria:
    - "独立数值：外部两组常量逐bit一致；内部捕获有计数区间Oracle，不以非零判通过。"
    - "状态完整：每个合法时间基/捕获位置节点都形成New、Lost及读清前后证据；没有外部时间基资源时不得用内部结果代替。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R3, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "内部时间基不接线；外部时间基需能给TSU输入稳定32-bit数值的FPGA测试接口，不是CAN盒子的接收时间"}
backend: [FPGA, Silicon]
evidence: ["CAN TSU内外时间基与丢失：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"ts0","label":"TSU.TS0实际捕获值","source":"dut","role":"actual","format":"text"}
  - {"key":"flags","label":"TSU.NEW/LOST读清前后位图","source":"dut","role":"actual","format":"text"}
  - {"key":"timebase","label":"TSU.ACTIVE_TIMEBASE采样区间","source":"dut","role":"actual","format":"text"}
  - {"key":"capture_source","label":"本参数时间基选择及独立输入/时间区间","source":"oracle","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN TSU内外时间基与丢失预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_019 CAN Monitor与Restricted模式

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_019
case_name: CAN Monitor与Restricted模式
report_feature: |-
  1. CAN Monitor与Restricted
p_level: P1
feature_refs: [CAN_F_029]
method:
  inputs:
    - "模式矩阵：Normal、Monitor、Restricted三个独立节点；Classic 500 kbit/s，标准ID 0x123、8-byte PATTERN_A，关闭内部/外部Loopback。"
    - "刺激约束：仅DUT能提供ACK；Peer每次发送一帧完整合法位流，Monitor下不因ACK缺失插入主动错误帧，不把ACK失败后的损坏帧当合法接收刺激。"
  steps:
    - "独立基线：每个模式前复位CAN、Service和资源池；配置同一过滤项、位时序及Peer捕获，保持其他总线节点静默。"
    - "正常对照：Normal节点接收Peer合法帧，确认DUT ACK槽为dominant、接收数据匹配，并由DUT主动发送一帧成功。"
    - "模式切换：重新基线后分别进入Monitor或Restricted，读回模式；配置和运行期间均禁止Loopback。"
    - "接收与ACK：Peer发送完整合法帧，读取DUT RX元素，同时独立观察ACK槽；Monitor不驱动ACK，Restricted应驱动ACK。"
    - "禁止主动发送：DUT提交一帧不同ID请求，观察100 ms内无对应SOF/帧；Monitor还需Pending保持复位，Restricted不要求与Monitor有相同Pending值。"
    - "退出与恢复：取消残留请求、退出特殊模式后重新发恢复帧，Peer必须收到且DUT完成；逐模式核对接收、ACK和发送三项结果。"
  observations:
    - "总线输出：Normal/Restricted对合法帧提供ACK，Monitor只保持recessive；独立捕获不能由模式读回替代。"
    - "接收与禁止发送：DUT RX.FRAME正确，特殊模式无主动发送帧；退出后恢复帧可被Peer接收，证明负向捕获链有效。"
  pass_criteria:
    - "模式区别：三个模式分别满足ACK/接收/主动发送表，禁止把Monitor的预期无ACK判成通信故障。"
    - "恢复可用：退出后数据和完成状态正确；不要求用复杂错误帧验证本基础模式Case。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "受控CAN位流Peer，能忽略无ACK并发送完整合法EOF、捕获ACK槽；普通CAN盒子是否支持须核实"}
backend: [FPGA, Silicon]
evidence: ["CAN Monitor与Restricted模式：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"mode","label":"CAN MODE实际读回","source":"dut","role":"actual","format":"text"}
  - {"key":"received","label":"CAN RX.FRAME","source":"dut","role":"actual","format":"text"}
  - {"key":"capture","label":"Peer ACK槽与主动发送/恢复捕获","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Monitor与Restricted模式预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_020 CAN FD ISO与Non-ISO格式

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_020
case_name: CAN FD ISO与Non-ISO格式
report_feature: |-
  1. CAN FD ISO与Non-ISO
p_level: P1
feature_refs: [CAN_F_037]
method:
  inputs:
    - "格式矩阵：DUT/Peer依次ISO/ISO、Non-ISO/Non-ISO、ISO/Non-ISO、Non-ISO/ISO；仲裁500 kbit/s、数据2 Mbit/s、BRS=1。"
    - "帧输入：FD 16-byte和64-byte各一帧，标准ID 0x123，PATTERN_A；分别覆盖不同CRC长度。"
  steps:
    - "独立基线：每种格式组合及长度前复位参与IP、Service和资源池，清Peer捕获与DUT首次错误锁存。"
    - "格式配置：配置DUT模式并读回，Peer通过自身设备设置对应格式；两端关闭回环，禁用自动重发防止错误风暴。"
    - "匹配收发：同格式节点双向各发送一帧，等待完成并比较真实接收帧、DLC、BRS及payload。"
    - "失配刺激：交叉格式节点由Peer只发一次；DUT作为接收者锁存第一次协议错误和RX占用，禁止发送后续成功帧覆盖首次错误。"
    - "负向判定：交叉格式不得进入有效RX元素，DUT必须留有真实协议错误事件及错误码，Peer记录实际发出的格式；不固定一种实现相关的首错误类型。"
    - "恢复验证：重新基线，两端设同一ISO格式，再双向各发一帧；核对恢复成功及全部8个格式/长度节点的预期。"
  observations:
    - "匹配结果：同格式DUT RX.FRAME/Peer.CAPTURE等于原始输入，TX.COMPLETED有效。"
    - "失配结果：DUT有效RX新增数为0，首次PROTOCOL.LAST_ERROR或DATA_LAST_ERROR属于真实协议错误而非无变化值，IRQ协议错误源有效。"
  pass_criteria:
    - "格式正反例：四组合乘两长度全部执行；同格式接收正确，失配有实际错误且不误收。"
    - "恢复正确：重新匹配后的双向帧准确，不能仅以失配超时作为格式差异证据。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "支持ISO/Non-ISO和单次发送的CAN FD Peer，禁止静默忽略不支持的格式"}
backend: [FPGA, Silicon]
evidence: ["CAN FD ISO与Non-ISO格式：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"format","label":"CAN FD格式配置读回","source":"dut","role":"actual","format":"text"}
  - {"key":"rx","label":"CAN RX新增量与实际帧","source":"dut","role":"actual","format":"text"}
  - {"key":"error","label":"首次PROTOCOL错误码和IRQ源","source":"dut","role":"actual","format":"text"}
  - {"key":"peer","label":"Peer格式及实际发送/捕获记录","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN FD ISO与Non-ISO格式预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P1_021 CAN TDC启用后的FD总线收发

参考历史“开启TDC后发送FD帧”的实际路径，单独保留基础覆盖；不要求为本Case增加可编程延迟器。补偿失效边界仍由P3_002负责，不能把本Case通过写成延迟极限通过。

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P1_021
case_name: CAN TDC启用后的FD总线收发
report_feature: |-
  1. CAN TDC启用收发
  2. CAN FD帧长度与BRS
p_level: P1
feature_refs: [CAN_F_030, CAN_F_005]
method:
  inputs:
    - "补偿参数：TDC开启、filter=0，offset采用Chip Timing Profile声明的合法值，单位为控制器最小时钟周期；不能跨芯片复制旧数值。"
    - "帧与速率：标准ID 0x123/0x321，FD、BRS=1、64-byte PATTERN_A/B；仲裁1 Mbit/s，数据2/5 Mbit/s分别形成节点，硬件适用性和Peer能力分别核对。"
  steps:
    - "独立基线：复位被测CAN、配合IP、Service和整池资源，停止Peer旧发送并清捕获；不复位控制通信UART。"
    - "总线配置：保持固定总线，配置DUT和Peer相同线上速率，关闭回环；DUT配置对应TDC参数，Peer采用自身正常FD配置。"
    - "配置读回：读取DUT的TDC.ENABLE、OFFSET、FILTER及BIT_TIMING，逐项核对本轮输入并启动Peer捕获。"
    - "正向传输：DUT依次发送两帧不同序号的64-byte FD数据，等待硬件完成，读取Peer真实捕获及DUT的TDC第二采样点位置。"
    - "反向传输：Peer发送两帧PATTERN_B，被测CAN逐帧接收、读元素后Ack，保存实际ID、BRS、DLC和payload。"
    - "独立判定：四帧元数据和有效字节分别对照PC原始输入，DUT无挂起TX、无Bus Off；按数据速率重复，保留每个节点的实际补偿配置。"
  observations:
    - "补偿配置：TDC.ENABLE=1且OFFSET/FILTER等于本轮Profile输入；证明测试未漏开启补偿，不能单凭配置判通过。"
    - "真实数据：Peer.CAPTURE及DUT RX.FRAME各两帧，ID/BRS/DLC/payload与PC输入一致，TX.COMPLETED有效；证明启用补偿后的外部FD路径可用。"
    - "采样点读值：记录TDC.SAMPLE_POINT实际值，不把固定接线下非零或任意常量作为PASS条件，也不据此推导最大补偿能力。"
  pass_criteria:
    - "配置与传输：每个适用速率节点均按声明开启TDC，双向各两帧完全匹配且无永久Pending或Bus Off。"
    - "结论边界：只判定启用TDC后的FD通信；不能要求TDC关闭必然失败，亦不能声称补偿边界已测。"
timeout: "每个速率节点5 s，超时记录最后TX/RX和协议状态，不自动重试覆盖"
cleanup: ["停止Peer发送和捕获", "停止并复位参与CAN和Service", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "固定CAN总线与收发器", bench: "另一CAN节点或支持对应CAN FD/BRS速率的CAN盒子；无需额外延迟器"}
backend: [FPGA, Silicon]
evidence: ["逐速率TDC配置、硬件第二采样点位置、双向原始帧、PC Expected及首个差异；保留Peer真实身份"]
failure_observations:
  - {key: tdc_config, label: "TDC.ENABLE/OFFSET/FILTER读回", source: dut, role: actual, format: text}
  - {key: tdc_sample_point, label: "TDC.SAMPLE_POINT实际值", source: dut, role: actual, format: text}
  - {key: peer_frames, label: "Peer.CAPTURE实际FD帧", source: peer, role: actual, format: text}
  - {key: dut_frames, label: "CAN RX.FRAME及TX.COMPLETED", source: dut, role: actual, format: text}
  - {key: expected, label: "PC输入FD帧及TDC配置", source: oracle, role: expected, format: text}
gap: [case_implementation_gap, tdc_timing_profile_gap, peer_capability_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_001 CAN DMA经DMU发送与接收

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_001
case_name: CAN DMA经DMU发送与接收
report_feature: |-
  1. CAN DMU发送与接收搬运
p_level: P2
feature_refs: [CAN_F_024]
method:
  inputs:
    - "端点矩阵：内部回环、FD 64-byte BRS开启，两帧PATTERN_A/B；RX FIFO0/FIFO1分别执行；消息格式大小由Chip Mapping给出，不把payload字节数当DMA总长度。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "RAM与DMU配置：配置CAN回环和当前RX FIFO，设置DMU RX选择；禁用时间戳附加，查询TX及RX虚拟端点。"
    - "DMA预配置：通过独立DMA Driver配置RX通道并先启动，再配置TX通道；32-bit端点步进及请求号来自Mapping。"
    - "发送搬运：启动TX通道写完整头部和数据，等待DMA通道完成及CAN TX完成；不能由CPU代写帧数据。"
    - "接收搬运：等待RX通道完成，读取目标内存头部与有效数据，检查FIFO推进和DMU无错误。"
    - "逐帧验证：比较两帧ID、DLC、BRS、有效字节和通道实际搬运长度；RX0/RX1分别形成完整结论。"
  observations:
    - "搬运终态：DMA.TX/RX.STATUS均完成无错误，CAN TX.COMPLETED有效。"
    - "目标数据：DMA.DESTINATION_FRAME解码等于独立输入，DMU.ERROR=0且相应RX队列已推进。"
  pass_criteria:
    - "路径真实：仅DMA访问虚拟数据窗口，CPU不能补传或补收来制造成功。"
    - "完整准确：两个选择×两帧全部完整；头部长度、payload长度和DMA长度分别留证。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN DMA经DMU发送与接收：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"dma","label":"DMA.TX/RX.STATUS与实际搬运长度","source":"dut","role":"actual","format":"text"}
  - {"key":"frame","label":"DMA.DESTINATION_FRAME及DMU.ERROR","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN DMA经DMU发送与接收的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","dma_endpoint_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_002 CAN DMA搬运TX Event

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_002
case_name: CAN DMA搬运TX Event
report_feature: |-
  1. CAN DMU TX Event搬运
p_level: P2
feature_refs: [CAN_F_025]
method:
  inputs:
    - "事件输入：内部回环FD 64-byte两帧，Marker为0x12和0x34；启用TX Event，DMU RX选择TX Event，关闭TSU附加。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "端点配置：配置CAN与Event FIFO，设置DMU选择Event，查询Event端点宽度、请求号和元素长度。"
    - "DMA准备：申请两项Event目标区并用0xA5预填，配置独立DMA通道从Event虚拟窗口读取。"
    - "产生事件：CPU经CAN Driver分别请求两帧成功发送，不由CPU读取TX Event数据窗口。"
    - "等待搬运：确认两次TX成功及DMA完成，观察Event FIFO由非空被DMU推进。"
    - "事件比较：解码DMA目标区的两项ID、Marker和Event Type，逐项与成功发送输入比较。"
  observations:
    - "事件数据：DMA.DESTINATION_EVENT的Marker和ID逐项正确，非0xA5旧内存。"
    - "队列终态：DMA.STATUS完成、TX_EVENT.FILL归零、DMU.ERROR=0。"
  pass_criteria:
    - "搬运有效：目标内存为两次发送的真实事件，CPU未提前消费事件。"
    - "队列准确：Event Ack由DMU语义推进，无重复、丢失和残留。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN DMA搬运TX Event：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"events","label":"DMA.DESTINATION_EVENT实际ID和Marker","source":"dut","role":"actual","format":"text"}
  - {"key":"status","label":"DMA.STATUS、TX_EVENT.FILL和DMU.ERROR","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN DMA搬运TX Event的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","dma_endpoint_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_003 CAN ECC中断链强制触发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_003
case_name: CAN ECC中断链强制触发
report_feature: |-
  1. CAN ECC中断Force、Mask与Clear
p_level: P2
feature_refs: [CAN_F_027]
method:
  inputs:
    - "源矩阵：Corrected/Uncorrected两个ECC中断源分别Force；本测试不注入真实RAM错误，不用其结果证明纠错能力。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "中断配置：隔离其他CAN的ECC源，清全部历史ECC Raw/ISR记录，关闭当前源投递。"
    - "屏蔽触发：Force当前源并另保留一个关闭投递的非目标源，保存两者Raw有效且IRQ_EVENT计数未变；Force的自清位不是Raw。"
    - "开放投递：仅使能并解除屏蔽当前源，等待ECC ISR锁存具体实例和源，另一源保持屏蔽。"
    - "清除验证：停止Force，清目标Raw，读取Raw/Status为0，确认未清另一个人为保留的源。"
    - "再次触发：重新Force当前源并确认再次捕获；逐源、逐目标实例执行。"
  observations:
    - "ECC中断：ECC_IRQ.RAW/STATUS的屏蔽及清除关系符合配置，共享线路回调保存实例。"
    - "回调事实：IRQ_EVENT的Source与实例对应此次Force，计数有新增。"
  pass_criteria:
    - "独立投递：屏蔽时无ISR、开放后投递正确，清目标不清非目标。"
    - "证据边界：仅判定ECC中断链通过，真实ECC纠错另见独立待完善目标。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN ECC中断链强制触发：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"ecc","label":"ECC_IRQ.RAW/STATUS屏蔽与清除前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"isr","label":"IRQ_EVENT实例/Source/Count","source":"measurement","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN ECC中断链强制触发的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","misc_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_004 CAN多实例Message RAM隔离

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_004
case_name: CAN多实例Message RAM隔离
report_feature: |-
  1. CAN多实例存储隔离
p_level: P2
feature_refs: [CAN_F_023]
method:
  inputs:
    - "实例矩阵：从Capability枚举全部实例；每实例使用不同ID及带实例序号数据，芯片映射明确RAM独立或共享及不重叠切片。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "RAM布局：按全部实例的同时使用预算划分RAM，写各区首尾Guard，不假定每实例均拥有最大可独占容量。"
    - "独立配置：每实例内部回环、不同Filter ID及RAM布局，读回确认后一实例配置未改变前一实例。"
    - "交错收发：依次给各实例挂一帧，在任何实例读取前确认各自RX就绪，再交错读取和Ack。"
    - "隔离刺激：仅重配最后一个实例的空闲Filter并再发帧，检查其他实例配置及Guard均未变化。"
    - "交叉核对：逐实例匹配其ID、数据、完成位和Guard，保存参与实例数及物理区域映射摘要。"
  observations:
    - "实例端点：每个RX.FRAME只包含自己发出的实例序号，CONFIG/RAM Guard未被其他实例覆盖。"
    - "并存终态：所有实例各自TX完成、RX无Lost，修改一实例不影响其他实例。"
  pass_criteria:
    - "覆盖明确：全部可同时运行的实例均参与，不将代表实例结果扩大为全实例。"
    - "隔离成立：数据、配置和Guard三者均隔离；RAM物理别名关系需先由芯片映射确认。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN实例；按Case需要增加片内DMA/CRG/SYSCTRL", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["CAN多实例Message RAM隔离：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"frames","label":"各实例RX.FRAME实际ID和payload","source":"dut","role":"actual","format":"text"}
  - {"key":"guards","label":"各实例CONFIG和Message RAM Guard前后值","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN多实例Message RAM隔离的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","message_ram_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_005 CAN内部与外部回环引脚对照

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_005
case_name: CAN内部与外部回环引脚对照
report_feature: |-
  1. CAN内部回环
  2. CAN外部总线收发
p_level: P2
feature_refs: [CAN_F_002, CAN_F_003]
method:
  inputs:
    - "观察拓扑：被测CAN和具有静默捕获能力的独立CAN节点/分析仪连接固定总线；内部回环、外部回环两个配置各发两帧1 Mbit/s Classic 8-byte；回环观察阶段Observer只听不ACK；Normal正对照阶段允许Peer正常ACK。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "捕获基线：先将Peer设正常模式并提供ACK，完成一帧Normal正对照及真实捕获；之后切换listen-only，清捕获记录。不能要求仅静默Peer存在时Normal发送成功。"
    - "内部回环：切内部回环并启动Observer，发两帧，确认本机TX完成及本机RX匹配。"
    - "静默判定：内部回环完成后100 ms捕获窗口内不得出现这两帧，保存完整捕获窗口有效性。"
    - "外部回环：重新基线并切外部回环，以不同序号发两帧，确认本机完成和本机接收。"
    - "外部核对：Observer必须收到外部回环两帧且数据一致；无效捕获、未启动设备不能被判为无外发。"
  observations:
    - "引脚输出：Observer.CAPTURE中内部回环0帧、外部回环2帧，正对照证明捕获链可用。"
    - "本机完成：两种回环均有TX.COMPLETED和本机RX数据，排除根本没发送造成假静默。"
  pass_criteria:
    - "隔离正确：内部无外发且本机通过，外部有真实捕获且本机通过。"
    - "观察有效：相同固定接线、有效捕获窗口和正对照全部成立；只读模式位不能替代此Case。"
timeout: "单参数节点5 s；负向无帧窗口为TX完成后100 ms"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "被测CAN经收发器连接Peer；实例和GPIO来自连接文件", bench: "静默Observer及正对照捕获，可用支持静默捕获的CAN盒子"}
backend: [FPGA, Silicon]
evidence: ["CAN内部与外部回环引脚对照：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"capture","label":"OBSERVER.CAPTURE正对照/内部/外部窗口帧序列","source":"peer","role":"actual","format":"text"}
  - {"key":"loop","label":"两种回环TX.COMPLETED及本机RX.FRAME","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN内部与外部回环引脚对照的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap","board_mapping_gap","observer_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_007 CAN DMU非法访问与中断

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_007
case_name: CAN DMU非法访问与中断
report_feature: |-
  1. CAN DMU非法访问IRQ
p_level: P2
feature_refs: [CAN_F_026]
method:
  inputs:
    - "单故障矩阵：读TX只写窗口、写RX1只读窗口、写TX Event只读窗口、空RX1出队、空Event出队、8-byte TX容量写FD DLC=15、CCE=1访问窗口、TX从非起始word开始、TX先写word0再跳过word1写word2，共9个独立节点。"
    - "基线参数：TX FIFO与RX FIFO深度2、payload容量8-byte，合法恢复帧Classic ID 0x123、8-byte PATTERN_A；无活动DMA。"
  steps:
    - "独立基线：每个错误节点先复位CAN、Service和资源池，配置回环与DMU，确认DMU错误状态为0且没有活动服务。"
    - "前提核对：空出队确认对应FIFO空且无请求；TX节点确认有可用元素、容量8-byte且DMU空闲；CCE节点保持INIT/CCE，其余退出CCE；采用TX FIFO而非专用Buffer。"
    - "中断布置：只使能目标DMU错误源并注册真实IRQ记录；ISR首次锁存后屏蔽该源，避免未知清除语义造成中断风暴；原始状态读取副作用按Chip Mapping执行，首个值必须保留。"
    - "最短违规刺激：通过受限测试接口执行该行明确的读/写序列；非法DLC顺序写两个头word，跳号节点只写word0和word2，其余一次访问；不让软件参数校验提前拒绝而未触达硬件。"
    - "错误判定：读取并保留目标DMU.ERROR位及ISR源/次数，目标位必须置1且ISR实际执行；非法读取返回数据不参与功能判定。"
    - "复位恢复：保存证据后硬复位CAN并重建合法DMU配置，经DMU发一帧回环并核对数据、入/出队完成，不能凭未知W1C规则盲写DMUIR。"
  observations:
    - "非法访问事件：每行刺激对应目标DMU.ERROR位由0变1；IRQ_EVENT记录目标源，区别于API INVALID_PARAM。"
    - "恢复结果：复位后DMU错误回到0，合法帧真实完成并匹配8-byte；本Case声明硬复位恢复，不声称未验证的软件清除。"
  pass_criteria:
    - "错误可重复：全部9个独立节点均产生目标硬件错误及中断；额外伴随位只记录，不随意要求整个寄存器等于单bit。"
    - "后续可用：各节点后的合法恢复帧准确，无残留活动DMA或未完成DMU服务。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "无需外部仪器；受限Chip Test Driver提供一次指定DMU窗口访问，不开放任意地址"}
backend: [FPGA, Silicon]
evidence: ["CAN DMU非法访问与中断：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"error","label":"DMU.ERROR刺激前后实际位图","source":"dut","role":"actual","format":"text"}
  - {"key":"irq","label":"DMU IRQ实际Source/Count","source":"measurement","role":"actual","format":"text"}
  - {"key":"recovery","label":"DMU入出队计数与恢复RX.FRAME","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN DMU非法访问与中断预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_008 CAN DMU接收TSU时间戳

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_008
case_name: CAN DMU接收TSU时间戳
report_feature: |-
  1. CAN TSU捕获与New/Lost
  2. CAN DMU发送与接收搬运
p_level: P2
feature_refs: [CAN_F_020, CAN_F_024]
method:
  inputs:
    - "正常矩阵：RX FIFO0/FIFO1乘DMU时间戳传送关闭/开启；内部回环、FD 8-byte、64-byte接收元素、标准ID 0x123、PATTERN_A，TSU内部计数及EOF捕获。"
    - "单一捕获：UTSU和匹配过滤SYNC开启，TX捕获关闭；仅接收路径捕获。负向节点只用已映射覆盖错误源的RX FIFO，输入64-byte占满同一元素，不把该节点算数据完整性正例。"
  steps:
    - "独立基线：复位CAN、DMA、Service及资源池，配置内部TSU、当前RX路由和DMU传送开关；清旧状态，禁用ISR自动读取元素或TSU槽。"
    - "槽位定位：按硬件槽数N最多完成N帧单捕获；从不消费的RX元素头读取Captured及Pointer，直到指向已映射TS0。此前元素单独Ack，当前元素保持未出队；记录当前帧发送前后ATB，未映射槽地址不得推算访问。"
    - "搬运准备：停止所有后续发送，要求当前帧Captured=1且Pointer=0、TSU.NEW[0]=1、LOST[0]=0；记录当前FIFO占用和DMU出队计数，申请DMA目标与首尾Guard，目标预填0xA5。"
    - "实际搬运：通过独立DMA接口读取当前DMU RX虚拟元素，完整字数、末word位置和步进取已核对Mapping；DMA前不直接读取TS0，不允许CPU补写目标数据或补Ack。"
    - "数值核对：DMA完成后再读取TS0；传送开启时目标末word必须等于TS0，并位于当前帧前后ATB的32-bit模区间内；关闭时只检查真实头部及8-byte有效数据，不断言无效padding。ATB区间必须小于半量程。"
    - "冲突对照：独立复位，选有明确覆盖错误位的RX FIFO，开启传送并输入FD 64-byte；重复单捕获和DMA过程，要求末word为该次TS0、覆盖错误置位，仅前60-byte等于原payload，不要求被替换4-byte仍完整。"
    - "终态判定：正常矩阵要求ID、DLC、有效8-byte、Guard及timestamp关系全部正确，FIFO减少1且出队计数模增1；负向节点记录真实覆盖位，随后复位并重做一帧8-byte合法搬运验证恢复。"
  observations:
    - "接收头部：RX.CAPTURED和RX.TIMESTAMP_POINTER证明本次消息关联TS0，DMA目标ID、DLC与有效payload等于输入。"
    - "时间戳事实：TSU.TS0、ATB前后值及DMA末word分别保存；开启时三者关系一致，直接槽读取放在DMA之后，避免读清影响前置操作。"
    - "传送与冲突：DMA硬件完成且Guard不变，正常出队仅一次；满payload负向节点出现对应覆盖错误，前60-byte与输入一致，恢复帧无错误。"
  pass_criteria:
    - "数据和时间独立：四个正常节点全部执行；只有真实DMA目标timestamp与TSU相等且落在独立ATB区间时判定传送正确，不能只看非零。"
    - "冲突准确：负向使用已确认错误位，未映射另一FIFO错误组不猜位号；真实覆盖不能被当成普通收发FAIL，也不能省略原始64-byte冲突覆盖。"
timeout: "每节点5 s，槽定位最多N帧；ATB前后窗口小于32-bit半量程"
cleanup: ["停止捕获刺激", "停止DMA与DMU", "复位CAN和Service状态", "Resource Pool Reset"]
resources: {minimum_level: R1, full_coverage_level: R1, board: "CAN内部回环、TSU及独立DMA，受限Message RAM只读访问", bench: "不需要外部接线"}
backend: [FPGA, Silicon]
evidence: ["保存逐节点配置、输入、完整DMA元素、Guard、TS0及ATB原值、Captured/Pointer、出队计数和覆盖错误，不只保存匹配布尔值"]
failure_observations:
  - {key: timestamp_word, label: "DMA目标末word时间戳", source: dut, role: actual, format: hex32}
  - {key: ts0, label: "TSU.TS0本次捕获", source: dut, role: actual, format: hex32}
  - {key: atb_before, label: "ATB发送前读值", source: dut, role: actual, format: hex32}
  - {key: atb_after, label: "ATB接收后读值", source: dut, role: actual, format: hex32}
  - {key: overwrite_error, label: "DMU接收元素时间戳覆盖错误", source: dut, role: actual, format: hex32}
  - {key: expected_payload, label: "PC生成的有效payload", source: oracle, role: expected, format: text}
gap: ["case_implementation_gap", "dma_endpoint_mapping_gap", "rx_timestamp_element_mapping_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_009 CAN协议错误与Bus Off恢复

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_009
case_name: CAN协议错误与Bus Off恢复
report_feature: |-
  1. CAN协议错误与Bus Off
p_level: P2
feature_refs: [CAN_F_033]
method:
  inputs:
    - "独立错误：ACK、发送bit0/bit1、接收Stuff/Form/CRC；Classic 500 kbit/s、8-byte确定载荷，每轮仅注入一种，首个错误由ISR锁存。"
    - "Bus Off刺激：从Error Active开始，反复在DUT发送的数据段非仲裁recessive位施加dominant；不使用持续无ACK作为Bus Off唯一刺激。"
  steps:
    - "独立基线：每类错误前复位DUT和资源，先正常完成一帧；清旧错误记录，设置单次发送或有界注入次数并启动位流捕获。"
    - "精确错误注入：ACK只取消ACK；bit1在数据段翻recessive为dominant，bit0需隔离RX回送并在应dominant的数据位回送recessive；Stuff构造6同值违反填充，Form改固定分隔位，CRC只改CRC校验且重做合法填充。"
    - "首次错误读取：在任何恢复帧前记录DUT首次LEC/DLEC、协议IRQ及TEC/REC；对照注入器位索引和实际捕获，确认不是更早的其他错误。"
    - "Bus Off递进：新基线下只重复数据段bit1错误，最多64次注入；在阈值附近保存EW、EP、BO及计数，不要求误差计数每次恰好固定步长。"
    - "隔离恢复：BO=1后停止注入，检查硬件进入INIT；释放总线并请求离开INIT，提供至少129组11个recessive位的恢复条件，等待BO清零。"
    - "恢复收发：确认错误状态退出，正常双向各发一帧；每类错误码与刺激对应，Bus Off必须有真实进入和退出记录，不以复位代替协议恢复。"
  observations:
    - "首次错误：ACK/bit0/bit1/Stuff/Form/CRC各由已验证注入触发对应首次错误码及协议IRQ，不能用任意损坏帧证明所有错误类型。"
    - "错误状态：EW/EP/BO随有界发送错误出现，BO置位后停止正常发送；恢复序列后BO=0、TEC/REC恢复，数据重新通过。"
  pass_criteria:
    - "错误匹配：全部错误节点的首次硬件错误与精确注入一致，capture确认刺激位置。"
    - "Bus Off闭合：有BO=1及后续BO=0证据，按协议恢复后双向数据准确；64次未触发应失败并留证，不无限注入。"
timeout: "每错误节点5 s；Bus Off最多64次有界注入、5 s；释放后的恢复5 s，不把等待扩大为新刺激"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "协议位级注入器及捕获；可屏蔽ACK、覆写指定非仲裁位、发送重算CRC或故意错误CRC帧"}
backend: [FPGA, Silicon]
evidence: ["CAN协议错误与Bus Off恢复：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"first_error","label":"PROTOCOL首次错误码及IRQ源","source":"dut","role":"actual","format":"text"}
  - {"key":"counters","label":"TEC/REC与EW/EP/BO关键状态","source":"dut","role":"actual","format":"text"}
  - {"key":"injection","label":"注入位索引与总线捕获","source":"instrument","role":"actual","format":"text"}
  - {"key":"recovery","label":"恢复后CAN RX帧和完成状态","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN协议错误与Bus Off恢复预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_010 CAN Message RAM访问Watchdog

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_010
case_name: CAN Message RAM访问Watchdog
report_feature: |-
  1. CAN Message RAM访问看门狗
p_level: P2
feature_refs: [CAN_F_035]
method:
  inputs:
    - "延迟矩阵：Watchdog限制16个CAN系统时钟周期；CAN主机RAM请求被接受后，分别延迟8和32周期返回应答；另设Watchdog关闭且延迟32周期的对照。"
    - "单次访问：CAN预装Classic 8-byte TX帧，通过一次TX请求触发CAN主机取数；其余RAM访问正常，不阻塞CPU控制通道。"
  steps:
    - "独立基线：复位CAN、Service和资源池，暂停其他RAM使用者；配置回环单帧，注入器默认透传。"
    - "看门狗配置：配置当前限制16或关闭，读回WATCHDOG.CONFIG，清WDI历史事件并注册中断记录。"
    - "握手触发：预装一帧并提交TX，注入器仅拦截首个CAN主机RAM请求，以真实请求/应答握手计数实现当前8或32周期延迟。"
    - "超时观测：记录实际延迟周期、WDI和ISR；16限制/8延迟不应报警，16限制/32延迟应报警，关闭/32延迟不应报警。"
    - "路径恢复：释放注入并停止被中断的传输，保存事实后复位重建CAN，发送无延迟的合法帧。"
    - "结果核对：三个延迟/开关节点均符合矩阵，恢复帧完全匹配；如未证实请求被延迟不得把未触发WDI认定为硬件失败。"
  observations:
    - "真实RAM延迟：注入器记录CAN主机请求身份及请求到应答的8/32周期，排除CPU轮询慢或其他端口阻塞。"
    - "超时状态：仅开启且实际延迟超过限制时IRQ.WDI有效并投递ISR；正常/关闭对照无WDI，恢复数据正确。"
  pass_criteria:
    - "阈值对照：三个节点均按独立握手计数满足超时预期，不能用TOCC代替RAM Watchdog。"
    - "恢复可用：去除延迟后单帧回环通过，控制通信未被阻塞。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R3, full_coverage_level: R3, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "可控Message RAM应答延迟及握手观察，必须作用于CAN主机访问而非CPU或DMA等待"}
backend: [FPGA, Silicon]
evidence: ["CAN Message RAM访问Watchdog：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"wd","label":"WATCHDOG.CONFIG/VALUE及IRQ.WDI","source":"dut","role":"actual","format":"text"}
  - {"key":"handshake","label":"CAN主机RAM请求/应答周期捕获","source":"instrument","role":"actual","format":"text"}
  - {"key":"irq","label":"WDI ISR Source/Count","source":"measurement","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN Message RAM访问Watchdog预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_011 TTCAN触发表与时间窗

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_011
case_name: TTCAN触发表与时间窗
report_feature: |-
  1. TTCAN触发表与时间窗
p_level: P2
feature_refs: [CAN_F_034]
method:
  inputs:
    - "最小调度：TTCAN Level1、500 kbit/s即NTU=2 us，DUT为Time Master、严格周期、1个Basic Cycle/Matrix；参考ID 0x100，TX数据ID 0x123，RX数据ID 0x321。"
    - "触发表：Time Base在100 NTU预取，TX Continuous在1000 NTU，RX检查在5000 NTU，参考触发10000 NTU，Watch在12000 NTU，末尾End；前3项每周期有效，TX窗口16 NTU、期望TX触发数1，专用TX Buffer0为参考、1为8-byte PATTERN_A；参考数据至少1-byte。"
  steps:
    - "独立基线：复位CAN和资源，配置正常总线；Peer先仅ACK和捕获，不在同步前发送其他帧，避免错误启动。"
    - "调度配置：配置Level1、NTU=nominal bit、潜在Time Master、一个Basic Cycle、专用TX Buffer和匹配0x321的Filter；按时间升序写6项Trigger，RX Trigger开启时间标记IRQ，ISR仅锁存MSC和Cycle Count；初始Watchdog取最大值、无关同步/看门狗关闭，读回整表和MSC=0。"
    - "周期启动：预装TX Buffer1并置请求，退出INIT；DUT生成参考消息，至少观察两次参考完成及硬件In_Schedule，开始记录连续3个稳定周期。"
    - "时间窗收发：每周期DUT应在1000 NTU窗口发0x123；Peer按参考SOF触发在6000 us后发送0x321，使其完成早于5000 NTU检查点；保留实际收发时间戳。"
    - "接收正反例：先3周期正常回复，检查RX Trigger MSC保持0；随后独立重建调度，只省略一个周期的0x321，下一次RX检查MSC必须从0增到1，不用长时间丢帧累积严重错误。"
    - "调度判定：用参考SOF统一时间零点核对TX窗口、Peer RX完成时刻、DUT RX数据和MSC；检查无配置错误，最后停止周期发送，不能以普通CAN收发替代Trigger执行。"
  observations:
    - "同步与时间窗：TT.SYNC_STATE=In_Schedule、TT.MASTER_STATE=Master；将真实参考SOF及0x123的SOF边沿时间戳按配置的采样偏移换算到规范定义的参考点/TX开始采样点，再比较1000至1016 NTU窗口，Observer误差不超过1 NTU。"
    - "接收检查：正常周期0x321接收匹配且RX Trigger时间标记ISR记录MSC=0；单次漏帧后的同一检查点记录MSC=1，避免后续成功周期递减掩盖；TT.CONFIG_ERROR保持0。"
  pass_criteria:
    - "硬件调度：3个稳定周期参考和数据帧均正确，时间窗由设备时间戳验证，不用PC命令到达时间推断。"
    - "漏帧检测：正常/单次漏帧两组形成MSC 0到1对照；只要求最小Level1，不冒称覆盖所有TTCAN等级/主节点竞争。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "能ACK、捕获并根据参考帧定时发一帧的CAN Peer；不要求Peer自身实现TTCAN协议栈"}
backend: [FPGA, Silicon]
evidence: ["TTCAN触发表与时间窗：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"tt","label":"TT.SYNC_STATE/MASTER_STATE/CONFIG_ERROR","source":"dut","role":"actual","format":"text"}
  - {"key":"msc","label":"RX_TRIGGER.MSC及DUT RX.FRAME","source":"dut","role":"actual","format":"text"}
  - {"key":"capture","label":"Peer参考帧/数据帧硬件时间戳","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"TTCAN触发表与时间窗预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P2_012 CAN AUX时钟下总线收发

历史最小方法是提供独立AUX时钟、按该时钟配置1 Mbit/s、观察外部接收。本PLAN补齐双向数据和恢复判据，不把“没有额外时钟源”当作设计不清。PAD和FPGA时钟接入是否实现留在芯片适配中，不复制参考芯片引脚。

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P2_012
case_name: CAN AUX时钟下总线收发
report_feature: |-
  1. CAN AUX时钟收发
  2. CAN位时序与输入时钟
p_level: P2
feature_refs: [CAN_F_039, CAN_F_006]
method:
  inputs:
    - "时钟输入：连接文件声明AUX入口、合法电平和信号源；提供20 MHz、50%占空比方波，超出目标能力时须先依据硬件事实调整并评审，不能临场猜频率。"
    - "总线输入：保持DUT与Peer固定CAN总线，Classic、1 Mbit/s、标准ID 0x123/0x321、8-byte PATTERN_A/B各两帧；Peer不使用DUT的AUX时钟。"
  steps:
    - "独立基线：停止外部发送，复位参与CAN、Service和资源池；确认AUX路径不占用控制通信引脚，DUT保持INIT。"
    - "时钟准备：独立GPIO接口配置AUX输入，信号源设置20 MHz及板级电平，示波器在实际AUX入口测频率、电平及占空比，与芯片时钟Profile允许误差比较；未稳定前不启动CAN。"
    - "时钟切换：通过独立时钟接口选择CAN的AUX源和合法分频，读回源选择；按实际CAN输入频率独立计算1 Mbit/s位时序。"
    - "链路启动：DUT配置上述位时序、过滤和Normal模式；Peer独立配置1 Mbit/s并启动捕获，双方关闭回环。"
    - "双向通信：DUT发送两帧PATTERN_A并读取Peer捕获；Peer发送两帧PATTERN_B并读取DUT RX元素，记录发送完成。"
    - "恢复与判定：先停CAN再切回默认时钟，重配默认位时序后再双向各发一帧；逐帧核对ID、长度和数据，最后才关闭AUX信号源。"
  observations:
    - "源选择读回：CLOCK.SOURCE为AUX且分频符合输入；AUX入口实测频率/电平/占空比与真实外部收发共同证明该配置下链路可用，发生器设定值不能冒充实测值。"
    - "总线接收：Peer.CAPTURE和DUT RX.FRAME在AUX阶段各两帧、恢复阶段各一帧，与PC输入逐Byte一致，DUT TX.COMPLETED有效。"
  pass_criteria:
    - "AUX路径：时钟源读回为AUX，四帧外部收发全部正确且无挂起TX或Bus Off；不能只用本机回环证明时钟。"
    - "恢复路径：默认时钟读回恢复，两帧恢复数据准确，不以复位后忽略恢复测试结束。"
timeout: "AUX通信5 s、恢复通信5 s；信号源稳定时间按设备规定有界等待"
cleanup: ["停止Peer和CAN", "恢复默认CAN时钟后关闭AUX源", "复位参与IP与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "固定CAN总线及独立AUX时钟输入连接，电压与入口由芯片/板级配置提供", bench: "CAN Peer及20 MHz时钟源；无需示波器作为本Case Oracle"}
backend: [FPGA, Silicon]
evidence: ["AUX源/分频读回、信号源配置与输出记录、AUX和恢复阶段的双向帧及独立Expected"]
failure_observations:
  - {key: clock_source, label: "CLOCK.SOURCE及DIVIDER前后读回", source: dut, role: actual, format: text}
  - {key: clock_generator, label: "AUX信号源频率/电平/输出设置", source: instrument, role: config, format: text}
  - {key: peer_frames, label: "Peer.CAPTURE的AUX与恢复阶段帧", source: peer, role: actual, format: text}
  - {key: dut_frames, label: "CAN RX.FRAME及TX.COMPLETED", source: dut, role: actual, format: text}
  - {key: expected, label: "各阶段PC原始帧与时钟配置", source: oracle, role: expected, format: text}
gap: [case_implementation_gap, aux_clock_mapping_gap, aux_source_connection_gap]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P3_001 CAN有界连续收发

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P3_001
case_name: CAN有界连续收发
report_feature: |-
  1. CAN连续收发
  2. CAN FD帧长度与BRS
p_level: P3
feature_refs: [CAN_F_036, CAN_F_005]
method:
  inputs:
    - "压力输入：20轮，每轮双向各32帧FD 64-byte、BRS开启，仲裁1 Mbit/s/数据5 Mbit/s或芯片明确可达组合；payload前4-byte为全局序号，其余PATTERN_A/B。"
  steps:
    - "独立基线：复位本Case参与的CAN及配合IP，复位Service状态和整池资源；每个参数节点重新建立基线，不复位控制通信UART。"
    - "链路配置：固定双节点总线、Normal模式和匹配过滤；确认实际速率，清软计数和历史丢失标志。"
    - "正向连续：被测端按FIFO可用槽连续排队32帧，对端有界接收，记录实际ID、序号和数据。"
    - "反向连续：原接线交换发送方向执行32帧，不逐帧复位，使用新的序号区间。"
    - "轮次累计：共20轮，每轮保留TX/RX数量及Lost、Error、Bus Off，遇错保留首次事实不自动重跑覆盖。"
    - "全量校验：两方向各640帧，逐Byte、逐序号比较，确认无重复、漏帧和未完成TX。"
  observations:
    - "连续数据：两方向RX序号各完整640个且payload逐Byte等于输入。"
    - "硬件状态：TX无挂起、RX.LOST=0、TX_EVENT.LOST在启用时为0、PROTOCOL.BUS_OFF=0。"
  pass_criteria:
    - "数量完整：20轮全部执行，640+640帧均准确；不能只比较累计发送调用次数。"
    - "有界无错：无永久忙死和错误重试掩盖，速率参数随报告记录，不称极限性能测量。"
timeout: "每轮5 s，共20轮；失败不自动续跑覆盖"
cleanup: ["停止外部刺激", "屏蔽相关中断并停止DMA/DMU", "停止并复位参与CAN与Service状态", "Resource Pool Reset"]
resources: {minimum_level: R2, full_coverage_level: R4, board: "被测CAN经收发器连接Peer；实例和GPIO来自连接文件", bench: "另一CAN节点或支持CAN FD/BRS及连续捕获的CAN盒子，无示波器要求"}
backend: [FPGA, Silicon]
evidence: ["CAN有界连续收发：保存输入、硬件配置、method.observations逐项实际值、Expected及首个不匹配；不可只留布尔结论"]
failure_observations:
  - {"key":"frames","label":"被测CAN RX序号首个丢失/重复/不匹配和实际数据","source":"dut","role":"actual","format":"text"}
  - {"key":"peer_frames","label":"Peer实际捕获序号及数据","source":"peer","role":"actual","format":"text"}
  - {"key":"counts","label":"各轮TX/RX累计实收帧数","source":"measurement","role":"actual","format":"text"}
  - {"key":"status","label":"TX.PENDING、RX.LOST及PROTOCOL.BUS_OFF","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN有界连续收发的输入与独立Expected","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P3_002 CAN TDC发送延迟补偿

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P3_002
case_name: CAN TDC发送延迟补偿
report_feature: |-
  1. CAN TDC启用收发
p_level: P3
feature_refs: [CAN_F_030]
method:
  inputs:
    - "延迟构造：由当前数据位时序得到正常采样位置S个mtq、位宽B个mtq；选Dlow=S-2、Dhigh=S+2，满足0<Dlow<S<Dhigh且Dhigh+S<127并在允许SSP范围；不满足时先选合法时序。"
    - "输入矩阵：TDC关/开乘Dlow/Dhigh四节点；TDCO=S、TDCF=0，FD BRS、64-byte交替0x55/0xAA；固定仲裁速率，延迟只施加本机RX回送而不破坏Peer所见的TX帧。"
  steps:
    - "独立基线：复位CAN和资源，确认外部夹具可安全隔离RX回送；Peer维持正常ACK，先无延迟发送一帧作为有效链路对照。"
    - "延迟校准：在DUT TX与实际RX引脚测得总回送延迟D，不用设备设定值代替实际值；误差小于0.5 mtq，加入收发器及夹具本底。"
    - "矩阵配置：为本节点设置TDC开关、OFFSET/FILTER和所选实际延迟，读回配置；禁止把PSR采样点位置误当纯线路延迟。"
    - "传输启动：只提交一次64-byte测试帧并捕获发送终态、首次数据段错误及Peer有效帧，错误节点关闭自动重发避免无限占线。"
    - "补偿判定：低延迟两种模式均应完成；高延迟且关闭补偿应有数据位监测错误，开启补偿应成功，采样点位置约为D+OFFSET，计量误差和同步量化合计预算2 mtq。"
    - "恢复验证：撤销夹具延迟并恢复正常线路，发送一帧正确数据；四节点和正对照全部留证，不把未进入高延迟条件的成功当补偿证明。"
  observations:
    - "延迟独立量测：OBSERVER.TX_RX_DELAY给出实际D；TDC开启且完成测量时，TDC.SAMPLE_POINT与D+OFFSET之差在2 mtq内；TDC关闭时不对无效TDCV强加关系断言。"
    - "补偿作用：高延迟关产生真实首次数据位错误，高延迟开TX完成且Peer有效帧正确，低延迟正对照通过。"
  pass_criteria:
    - "开关对照：全部四节点满足预先计算的采样关系和数据判据；不事后按结果调整延迟窗口。"
    - "故障边界：只验证正常采样点两侧的有限对照，不声称测得芯片最大延迟规格；恢复帧准确。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "可将DUT TX回送到RX并加入已测延迟的安全夹具，以及真实总线ACK/捕获Peer"}
backend: [FPGA, Silicon]
evidence: ["CAN TDC发送延迟补偿：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"delay","label":"OBSERVER.TX_RX_DELAY实际总延迟","source":"instrument","role":"actual","format":"text"}
  - {"key":"ssp","label":"TDC.SAMPLE_POINT及OFFSET","source":"dut","role":"actual","format":"text"}
  - {"key":"result","label":"TX.COMPLETED与首次DATA_LAST_ERROR","source":"dut","role":"actual","format":"text"}
  - {"key":"peer","label":"Peer有效FD帧","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN TDC发送延迟补偿预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P3_004 CAN发送Pause间隔

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P3_004
case_name: CAN发送Pause间隔
report_feature: |-
  1. CAN TX发送暂停
p_level: P3
feature_refs: [CAN_F_032]
method:
  inputs:
    - "帧列与模式：Classic 500 kbit/s、8-byte同一载荷，预装4帧TX FIFO并一次提交全部请求；Pause关/开各一组，总线上Peer只ACK不发其他帧。"
    - "独立预算：仲裁位时间2 us，Pause引入额外2 bit即4 us；边沿测量误差每组不超过0.1 bit，差分容差0.2 bit。"
  steps:
    - "独立基线：每组前复位CAN和资源，确认Error Active，配置Normal、同一FIFO及Peer正常ACK。"
    - "整组预装：先把4帧写入FIFO，再一次原子TX请求建立连续Pending，不能逐帧等待或在帧间由PC再次提交。"
    - "间隔捕获：记录全部4帧位流，对每相邻帧定位前帧EOF结束与后帧SOF，获得3个真实空闲间隔。"
    - "暂停对照：重新基线后仅改变Pause为开，用相同帧和请求方式重复，检查开启/关闭配置读回。"
    - "差分判定：只比较无仲裁、无错误的对应间隔；开启组应比关闭组多2个仲裁位时间，计入独立仪器误差，不使用主机收发时间。"
    - "恢复核对：关闭Pause再发一帧恢复，核对所有帧ID/数据和TX完成，保存原始位流供复核。"
  observations:
    - "真实帧间隔：OBSERVER.EOF_TO_SOF的3对间隔差均为2 bit，容差0.2 bit；捕获证明无其他节点仲裁或错误帧。"
    - "发送前提：Pause配置读回正确，4帧事先同时Pending并最终完成，数据一致。"
  pass_criteria:
    - "暂停作用：3对间隔全部满足差分，不能只以最终收发正确判Pause通过。"
    - "链路有效：无Bus Off、Error Passive或错误重发污染间隔，恢复帧完成。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "可解码EOF/SOF的位级CAN捕获；仅毫秒级帧时间戳不够"}
backend: [FPGA, Silicon]
evidence: ["CAN发送Pause间隔：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"pause","label":"CAN TRANSMIT_PAUSE读回","source":"dut","role":"actual","format":"text"}
  - {"key":"gaps","label":"OBSERVER.EOF_TO_SOF开关对照","source":"instrument","role":"actual","format":"text"}
  - {"key":"tx","label":"TX请求掩码及最终COMPLETED","source":"dut","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN发送Pause间隔预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

### CAN_P3_005 CAN测试模式TX与RX引脚

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CAN_P3_005
case_name: CAN测试模式TX与RX引脚
report_feature: |-
  1. CAN TEST引脚控制
p_level: P3
feature_refs: [CAN_F_038]
method:
  inputs:
    - "TX控制矩阵：强制dominant、强制recessive、输出Sample Point；RX分别输入稳定0/1；Classic 500 kbit/s作为采样点时基。"
    - "连接要求：测试夹具先禁用收发器输出冲突路径；受控输入满足PAD电压，静态dominant最长100 us且短于所选收发器保护时限。"
  steps:
    - "独立基线：复位CAN及资源，Peer停止发送；夹具隔离外部总线与受控引脚，独立读取隔离/电平状态，禁止带冲突强驱动。"
    - "测试模式配置：在INIT/CCE配置Test Enable和位时序，关闭Loopback，读回Test Enable；仅使用规定的TX控制枚举。"
    - "静态TX观测：依次选择dominant和recessive，由独立探头读取DUT TX实际电平，每项立即恢复recessive，不能用TEST配置值代替引脚观察。"
    - "RX输入对照：TX保持recessive，夹具分别给RX稳定低/高电平，实际探头值和TEST.RX读回必须分别为0/1。"
    - "采样点输出：选择Sample Point输出、退出INIT使位时序运行，在RX保持recessive时捕获连续8个TX采样脉冲，周期应为一个仲裁位时间，容差0.1 bit；不要求INIT保持状态下产生脉冲。"
    - "模式退出：退出测试模式、恢复收发器连接和正常CAN配置，与Peer双向各发一帧，确认数据路径恢复且无静态强驱动残留。"
  observations:
    - "引脚直接观察：DUT TX的强制低/高由外部探头确认，RX引脚实际0/1与TEST.RX一致。"
    - "采样与恢复：8个采样脉冲的相邻周期符合仲裁位时间，退出后Peer和DUT实际收发正确。"
  pass_criteria:
    - "测试控制：所有静态TX、RX及Sample Point节点满足独立电平/时间Oracle。"
    - "安全恢复：测试控制已退出，正常双向帧准确，禁止只验证寄存器读回。"
timeout: "每个参数节点5 s；负向主动发送观察100 ms；位级时间测量按method独立预算执行"
cleanup: ["先停止Peer发送和外部注入，恢复高阻/透传", "屏蔽相关IRQ并停止DMA/DMU", "停止并复位参与CAN及Service", "Resource Pool Reset"]
resources: {minimum_level: R4, full_coverage_level: R4, board: "代表CAN及本Case明确参与的片内IP，实例/引脚来自连接映射", bench: "安全隔离收发器的固定测试夹具，受控RX输入及TX电平/采样点捕获；不能把两个推挽输出硬短接"}
backend: [FPGA, Silicon]
evidence: ["CAN测试模式TX与RX引脚：逐参数保存输入配置、首次决定性硬件状态、独立Expected和实际刺激证据；PASS/FAIL均记录，不用API成功代替硬件结果"]
failure_observations:
  - {"key":"pins","label":"探头观察DUT TX/RX电平及采样脉冲","source":"instrument","role":"actual","format":"text"}
  - {"key":"test_rx","label":"TEST.RX和TEST.TX配置读回","source":"dut","role":"actual","format":"text"}
  - {"key":"recovery","label":"DUT/Peer恢复帧记录","source":"peer","role":"actual","format":"text"}
  - {"key":"expected","label":"CAN测试模式TX与RX引脚预先确定的输入和判据","source":"oracle","role":"expected","format":"text"}
gap: ["case_implementation_gap"]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=37 | IMPLEMENTATION_GAP=39; NEEDS_VERIFICATION=3 | 37准入Feature、2待定能力；39 PLAN、3项确认流程；无实现/实测结论 | `ET6801_can.md` |

## 5. Common Gap / Evolution

原14个目标中11项此前已形成PLAN，本轮将DMU接收时间戳补成PLAN，并为独立TX Event格式缺口保留P2_013。以下3项仍有明确硬件语义疑点，不是缺少仪器的同义词，不改成SKIP，不用试到的数值反向定义硬件正确性。

### 5.1 CAN_P2_006 Message RAM真实ECC注入

测试目的：单错读回纠正、双错上报不可纠正，记录实际错误地址；不能由Force中断或普通RAM模式读写代替。

1. 独立复位CAN与资源；由SYSCTRL自身Driver配置ECC和注入，CAN Driver只负责受限RAM访问。保留一处已确认合法RAM word，写0x5AA55AA5，无注入回读和ECC源作为正对照。
2. **写阶段注入分支**：只在一次目标word写入期间开启单错注入，关闭后由同一硬件访问端读取该word；记录数据、Corrected/Uncorrected源和错误地址。
3. **读阶段注入分支**：新基线写同一Expected，只在一次读取期间开启注入，读取后立即关闭；记录同样事实。不能跨两阶段持续注入，以免两次翻转抵消。
4. 单错语义确定后，对双错重复同样两个隔离分支；可能产生总线异常的读取必须经具备错误终态的受控硬件访问，不能让CPU异常后继续假造结果。
5. 正式单错判据必须同时满足：实际读值等于Golden、Corrected置位、地址指向目标word；双错要求Uncorrected和目标地址，不能要求双错仍得到正确数据。
6. 关闭注入、重写Golden，复查错误源清除和正常读取；保存每阶段注入配置及访问者身份。

尚缺的是注入作用于写入ECC码还是读取数据、作用范围/持续方式，以及单/双错控制描述的冲突。上述双分支是**硬件行为确认诊断**，不是“两条任意一条出错误就PASS”。需得到对应芯片设计定义或经人工确认的诊断结论，固定唯一触发序列后再发布正式PLAN；硬件地址、位号与冲突见芯片文档3.4。

### 5.2 CAN_P2_013 DMU TX Event附加TSU时间戳

原CAN_P2_008的RX0/RX1与TX Event在实施前拆分：RX方法已形成第3节PLAN；TX Event保留为本目标，不能因为拆分而遗漏。两条合计保留原目标，未迁移已发布SPEC或已实现Case ID。

1. 复位CAN/DMA与资源，打开UTSU、发送捕获和Event存储，只发一帧，RX同步捕获关闭，防止混淆槽位。
2. 无副作用地读取原始Event头，确认Captured、Pointer和Marker；等待发送完成后不再发新帧。
3. 用受限DMU Debug窗口比较当前Event原始字与TSU槽，记录DMUC.TTS开/关两组，不消费正式虚拟窗口。
4. 根据目标DMU格式定义确认TTS开启后的有效字数、timestamp位置及触发出队的最后访问地址，再固定DMA描述符；不能以扫描窗口试到一个相等值来定义格式。
5. 正式方法需同时检查Marker/ID/Event Type、独立TSU时间戳、FIFO减少1与出队计数模增1；DMA前不预读TSU，数值比对在停止新捕获后的DMA完成后执行。
6. 关闭附加、复位并重新生成正常事件，验证基础Event搬运恢复。

**剩余唯一格式缺口**：TX Event开启TTS后的元素布局与结束地址。Bosch AN004的RX示例只证明接收末word替换；没有证据允许把同一位置套到两word Event。示波器可以观察总线时刻，但不能补足片内DMU元素格式，因此本项仍为DESIGN_GAP而不是环境SKIP。

### 5.3 CAN_P3_003 Bus Integration边沿过滤

最小刺激固定为**关闭/开启过滤 × 短/长dominant脉冲**，不再写“发送错误帧看看”：

1. 固定夹具隔离CAN收发器RX输出；由支持触发延时的脉冲发生器/AWG或配测FPGA控制DUT RX；示波器CH1观察RX实际电平，CH2捕获DUT TEST Sample Point输出，保持控制UART可用。
2. 配置500 kbit/s位时序并独立读回，以实际nominal tq为单位；RX先为recessive，退出INIT进入Bus Integration。
3. 在尚未完成11个recessive bit接入前，仅注入一次dominant脉冲；短脉冲宽1 tq，长脉冲宽3 tq；发生器由接入开始后的TEST采样脉冲触发，不能由PC命令计时。脉冲相位避开tq采样边界，记录实际波形；仪器时间分辨率及总抖动预算不超过0.1 tq，确认短脉冲仅覆盖一个tq采样、长脉冲覆盖至少两个，不与每bit的Sample Point混淆。
4. 在脉冲前后捕获Sample Point时刻，与无脉冲基线的采样网格比较；先用关闭过滤的正对照确认当前脉冲相位确实能产生可分辨的硬同步相位变化。
5. 过滤开启时，短脉冲不应造成硬同步；长脉冲仍应造成同步。比较的是同步响应，不能以最终收到/收不到帧或任意延迟变化代替。
6. 退出TEST、恢复总线，发送一帧正常数据，证明控制器与夹具恢复；全部节点复位后独立重做。

需要先确认**TEST采样点在接入阶段是否可观测、其变化与硬同步的唯一对应及量化预算**；ET6801 SVD没有给出硬同步状态字段。若该输出不足以区分同步，需要设计人员确认采样输出的同步关系，或改用被测FPGA明确导出的hard-sync事件观测，不凭空命名一个寄存器。原厂“两个连续dominant tq”定义不能直接转换为“随便1 tq脉冲必定被滤掉”，必须保留采样相位约束。示波器可直接采集本方案，不再限定必须开发配测FPGA；若采样输出的同步关系经目标设计确认，则仪器未接入只剩Bench Gap。当前缺的是相位变化如何唯一代表硬同步的依据，不能把任意波形变化判为通过；该依据未闭合前仍保留DESIGN_GAP。

### 5.4 其余覆盖边界

本轮已补P1_003的XIDAM/绕过/29-bit高位、P1_002/003首匹配顺序、P1_001 Classic DLC 9～15、P1_011外部路径IRQ与P2_008 RX同步时间戳。P1_013清零原子动作的最坏耗时仍需实现阶段给出并先固定，不得事后调整。跨节点仲裁、Message RAM布局容量极值、实际时钟停振/唤醒的独立验证仍需补充，不能以本轮修正为由宣称全部Feature已覆盖。TTCAN当前PLAN只覆盖最小Level1周期、TX窗和一次RX漏帧，不声称覆盖所有TT等级或冗余主节点竞争。PLAN语法通过不等于所有硬件语义已经完成。
