# CAN芯片中立的配置和硬件读回。
# 职责：不可变参数、实际时序计数及控制状态。
# 边界：不编码协议、不选择实例、时钟或引脚，不保存测试结果。
# 依赖：标准库dataclass。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# ECC专用源命名空间，不等同控制器BEC/BEU中断。
class CanEccSource(IntFlag):
    NONE = 0
    CORRECTED = 1
    UNCORRECTED = 2


# ECC寄存器的独立真实观测，不把Raw重新计算为Status。
@dataclass(frozen=True, slots=True)
class CanEccSnapshot:
    raw: CanEccSource
    status: CanEccSource
    enabled: CanEccSource
    masked: CanEccSource


# ECC共享线路按实例独立锁存；尚无回调时instance_id为None。
@dataclass(frozen=True, slots=True)
class CanEccEvent:
    raw_status: CanEccSource
    masked_status: CanEccSource
    latched_events: CanEccSource
    event_count: int
    unexpected_count: int
    overflow_count: int
    generation: int
    fault_flags: int
    instance_id: int | None


# 公共错误语义，不使用ECC源位图解释控制器LEC。
class CanError(IntEnum):
    NONE = 0
    STUFF = 1
    FORM = 2
    ACK = 3
    BIT1 = 4
    BIT0 = 5
    CRC = 6
    UNCHANGED = 7


# 公共通信状态，用于解释实际活动，不作为TX完成替代证据。
class CanActivity(IntEnum):
    SYNCHRONIZING = 0
    IDLE = 1
    RECEIVER = 2
    TRANSMITTER = 3


# CAN中断源使用公共语义位图；数值不允许Case解释为ET6801 IR寄存器位。
class CanIrqSource(IntFlag):
    NONE = 0
    RX_FIFO0_NEW = 1 << 0
    RX_FIFO0_WATERMARK = 1 << 1
    RX_FIFO0_FULL = 1 << 2
    RX_FIFO0_LOST = 1 << 3
    RX_FIFO1_NEW = 1 << 4
    RX_FIFO1_WATERMARK = 1 << 5
    RX_FIFO1_FULL = 1 << 6
    RX_FIFO1_LOST = 1 << 7
    HIGH_PRIORITY = 1 << 8
    TX_COMPLETE = 1 << 9
    TX_CANCEL_FINISHED = 1 << 10
    TX_FIFO_EMPTY = 1 << 11
    TX_EVENT_NEW = 1 << 12
    TX_EVENT_WATERMARK = 1 << 13
    TX_EVENT_FULL = 1 << 14
    TX_EVENT_LOST = 1 << 15
    TIMESTAMP_WRAP = 1 << 16
    RAM_ACCESS_FAILURE = 1 << 17
    TIMEOUT = 1 << 18
    RX_BUFFER_NEW = 1 << 19
    BIT_ERROR_CORRECTED = 1 << 20
    BIT_ERROR_UNCORRECTED = 1 << 21
    ERROR_LOG_OVERFLOW = 1 << 22
    ERROR_PASSIVE = 1 << 23
    WARNING = 1 << 24
    BUS_OFF = 1 << 25
    RAM_WATCHDOG = 1 << 26
    PROTOCOL_ARBITRATION = 1 << 27
    PROTOCOL_DATA = 1 << 28
    RESERVED_ACCESS = 1 << 29


# 非破坏读取控制器IRQ配置；line1_sources表示被选择到第二条控制器输出线的源。
@dataclass(frozen=True, slots=True)
class CanIrqSnapshot:
    raw_status: CanIrqSource
    enabled_sources: CanIrqSource
    line1_sources: CanIrqSource
    enabled_lines: int


# 固定ISR证据由Service维护；硬件状态和软件诊断字段保持分离。
@dataclass(frozen=True, slots=True)
class CanIrqEvent:
    raw_status: CanIrqSource
    masked_status: CanIrqSource
    latched_events: CanIrqSource
    event_count: int
    unexpected_count: int
    overflow_count: int
    generation: int
    fault_flags: int


# PSR类状态再ECR类计数的连续一次采样；不是同时快照，会消费读清字段。
@dataclass(frozen=True, slots=True)
class CanProtocolStatus:
    last_error: CanError
    activity: CanActivity
    error_passive: bool
    warning: bool
    bus_off: bool
    data_last_error: CanError
    received_esi: bool
    received_brs: bool
    received_fd: bool
    protocol_exception: bool
    tdc_position: int
    tx_error_count: int
    rx_error_count: int
    rx_error_passive: bool
    error_log_count: int


# 值直接来自控制器身份查询，不从Profile制造读回。
@dataclass(frozen=True, slots=True)
class CanIdentity:
    revision: int
    endian: int


# 正整数物理计数，减一寄存器编码只在固件适配内部处理。
@dataclass(frozen=True, slots=True)
class CanPhaseTiming:
    prescaler: int
    segment1: int
    segment2: int
    sjw: int


# 仲裁和数据阶段分别配置；同类型也用于表达各字段的可表示上限。
@dataclass(frozen=True, slots=True)
class CanTiming:
    nominal: CanPhaseTiming
    data: CanPhaseTiming


# 全部选项由调用者提供；不隐式补充测试模式或数据路径配置。
@dataclass(frozen=True, slots=True)
class CanOptions:
    fd_enabled: bool
    brs_enabled: bool
    automatic_retry: bool
    tx_pause: bool
    edge_filter: bool
    protocol_exception: bool
    tdc_enabled: bool
    tdc_offset_cycles: int
    tdc_filter_cycles: int
    ram_watchdog_cycles: int


# 三项硬件周期上限，不代表Observer精度或PC等待时间。
@dataclass(frozen=True, slots=True)
class CanOptionLimits:
    tdc_offset_cycles: int
    tdc_filter_cycles: int
    ram_watchdog_cycles: int


# 完整RAM布局；offset为CAN RAM内字节偏移，不是CPU地址。
# dedicated RX没有硬件数量字段，按ram_limits.rx_buffer_count预留，避免缓存虚构读回。
@dataclass(frozen=True, slots=True)
class CanRamLayout:
    std_offset: int
    std_count: int
    ext_offset: int
    ext_count: int
    tx_offset: int
    tx_buffer_count: int
    tx_fifo_count: int
    tx_queue: bool
    tx_payload_bytes: int
    event_offset: int
    event_count: int
    event_watermark: int
    rx0_offset: int
    rx0_count: int
    rx0_watermark: int
    rx0_overwrite: bool
    rx1_offset: int
    rx1_count: int
    rx1_watermark: int
    rx1_overwrite: bool
    rx_buffer_offset: int
    rx_buffer_payload_bytes: int
    rx0_payload_bytes: int
    rx1_payload_bytes: int


# 由目标实例发布的区域最大数量，不使用寄存器字段位宽猜测上限。
@dataclass(frozen=True, slots=True)
class CanRamLimits:
    ram_bytes: int
    std_count: int
    ext_count: int
    tx_count: int
    rx_fifo_count: int
    event_count: int
    rx_buffer_count: int


# 时间戳来源为公共语义，不是芯片寄存器位值。
# EXTERNAL只表示选择外部计数输入，不会自动连接或启动外部仪器。
class CanTimestampSource(IntEnum):
    DISABLED = 0
    INTERNAL = 1
    EXTERNAL = 2


# 超时计数器由连续时基或指定硬件FIFO门控。
# 这是计数来源选择，不是PC等待超时；硬件实际分频由BusConfig单独指定。
class CanTimeoutSource(IntEnum):
    CONTINUOUS = 0
    TX_EVENT = 1
    RX0 = 2
    RX1 = 3


# 未命中具体Filter时的全局处理策略。
# RX0/RX1表示存入对应FIFO，REJECT表示丢弃；不替代具体ID Filter配置。
class CanUnmatchedPolicy(IntEnum):
    RX0 = 0
    RX1 = 1
    REJECT = 2


# 回环方式与INIT分开，关闭内部回环也退出MON隔离。
class CanLoopback(IntEnum):
    DISABLED = 0
    INTERNAL = 1
    EXTERNAL = 2


# 对应现有Chip Driver的完整配置组，不填测试默认值。
@dataclass(frozen=True, slots=True)
class CanBusConfig:
    monitor: bool
    restricted: bool
    timestamp_divisor: int
    timestamp_source: CanTimestampSource
    timeout_source: CanTimeoutSource
    timeout_period: int
    timeout_enabled: bool
    reject_remote_ext: bool
    reject_remote_std: bool
    unmatched_ext: CanUnmatchedPolicy
    unmatched_std: CanUnmatchedPolicy


# 时间戳实际分频数和超时重装值的最大值。
# 由当前实例查询返回，只描述可配置上限，不代表实际工作频率或测量结果。
@dataclass(frozen=True, slots=True)
class CanBusLimits:
    timestamp_divisor: int
    timeout_period: int


# 公共帧格式与发送附加控制，位号属于Wire合同，不是Message RAM寄存器位号。
# RX只返回EXTENDED至ESI五项；STORE_EVENT和CAPTURE_TIME仅用于TX。
class CanFrameFlags(IntFlag):
    NONE = 0
    EXTENDED = 1
    REMOTE = 2
    FD = 4
    BRS = 8
    ESI = 16
    STORE_EVENT = 32
    CAPTURE_TIME = 64


# 明确的待发帧；DLC与有效payload长度必须匹配，Remote帧没有payload。
# identifier使用正常整数ID，不要求Case自行做芯片Message RAM移位。
@dataclass(frozen=True, slots=True)
class CanTxFrame:
    identifier: int
    flags: CanFrameFlags
    dlc: int
    marker: int
    data: bytes


# 真实接收帧和存储位置；data可因RAM槽容量而短于DLC表达的总线长度。
# timestamp保留实际字段值；它的来源由Case读取配置后解释，不伪装为秒。
@dataclass(frozen=True, slots=True)
class CanRxFrame:
    identifier: int
    flags: CanFrameFlags
    dlc: int
    timestamp: int
    filter_index: int
    nonmatching: bool
    index: int
    data: bytes


# 发送请求、完成和取消为独立硬件位图；命令被接受不代表completed已经置位。
# FIFO计数和索引保留真实值，不在Model中判断Case是否通过。
@dataclass(frozen=True, slots=True)
class CanTxStatus:
    pending: int
    completed: int
    cancelled: int
    free_count: int
    get_index: int
    put_index: int
    full: bool


# TX Event FIFO非破坏性状态；查询不会确认当前事件，也不会清除lost。
@dataclass(frozen=True, slots=True)
class CanTxEventStatus:
    fill: int
    get_index: int
    put_index: int
    full: bool
    lost: bool


# TX Event类型为公共语义；保留值不作为有效事件返回。
class CanTxEventType(IntEnum):
    TRANSMITTED = 1
    TRANSMITTED_AFTER_CANCEL = 2


# 一项实际TX Event FIFO元素；index用于显式Ack当前硬件头。
@dataclass(frozen=True, slots=True)
class CanTxEvent:
    identifier: int
    flags: CanFrameFlags
    dlc: int
    timestamp: int
    event_type: CanTxEventType
    marker: int
    index: int


# TSU配置：源0内部/1外部，捕获0 EOF/1 SOF，分频为实际值。
@dataclass(frozen=True)
class CanTsuConfig:
    enabled: bool
    external: bool
    sof: bool
    divisor: int


# 槽数与内部源/SOF支持必须由目标读回，不从请求缓存推断。
@dataclass(frozen=True)
class CanTsuLimits:
    slots: int
    internal: bool
    sof: bool


# 实际事件格式；TSU启用时硬件使用16-bit Marker。
@dataclass(frozen=True, slots=True)
class CanEventFormat:
    marker_bits: int
    tsu_enabled: bool


# 显式有效性的事件读回，None代表该格式没有内部时间戳或未捕获TSU时间戳。
# TSU pointer只是寄存器槽编号，不是TSU时间戳值或消息顺序号。
@dataclass(frozen=True, slots=True)
class CanTxEventDetails:
    identifier: int
    flags: CanFrameFlags
    dlc: int
    timestamp: int | None
    event_type: CanTxEventType
    marker: int
    index: int
    tsu_pointer: int | None


# 接收FIFO非破坏性观测；查询不Ack、不清lost，也不将fill自动转换成测试结果。
@dataclass(frozen=True, slots=True)
class CanRxFifoStatus:
    fill: int
    get_index: int
    put_index: int
    full: bool
    lost: bool


# Dedicated RX Buffer新数据位图，两组u32覆盖公共Wire的64个标志位置。
# 实际可用Buffer数量仍取目标能力和RAM上限，不能由这两个整数猜测。
@dataclass(frozen=True, slots=True)
class CanRxBufferStatus:
    low: int
    high: int


# 指定读取Dedicated Buffer或某个FIFO的当前头；不是物理RAM地址。
# FIFO读取的index参数必须为0，返回帧会给出实际硬件Get Index以供显式Ack。
class CanRxSource(IntEnum):
    BUFFER = 0
    FIFO0 = 1
    FIFO1 = 2


# 过滤匹配的公共语义，不向Case暴露SFT/EFT位值。
# RANGE_NO_MASK只对扩展格式有效，DISABLED类型只对标准格式有效。
class CanFilterType(IntEnum):
    RANGE = 0
    DUAL = 1
    MASK = 2
    RANGE_NO_MASK = 3
    DISABLED = 4


# 过滤命中后的存储/优先级事件动作，不配置NVIC或全局过滤策略。
# BUFFER是精确ID匹配，独立buffer_index指定目标，不把它塞入第二个ID。
class CanFilterAction(IntEnum):
    DISABLED = 0
    FIFO0 = 1
    FIFO1 = 2
    REJECT = 3
    PRIORITY = 4
    PRIORITY_FIFO0 = 5
    PRIORITY_FIFO1 = 6
    BUFFER = 7


# High Priority Message的存储结果是公共语义，不暴露芯片HPMS位编码。
class CanHighPriorityStorage(IntEnum):
    NO_FIFO = 0
    FIFO_MESSAGE_LOST = 1
    FIFO0 = 2
    FIFO1 = 3


# 一次非破坏High Priority状态读取；filter_extended区分标准/扩展Filter列表。
@dataclass(frozen=True, slots=True)
class CanHighPriorityStatus:
    buffer_index: int
    storage: CanHighPriorityStorage
    filter_index: int
    filter_extended: bool


# DMU逻辑虚拟元素；不是DMA通道、寄存器偏移或任意地址选择器。
class CanDmuElement(IntEnum):
    TX = 0
    RX0 = 1
    RX1 = 2
    TX_EVENT = 3


# 三种接收侧请求互斥；切换前由调用方停止相关DMA活动。
class CanDmuRequest(IntEnum):
    RX0 = 0
    RX1 = 1
    TX_EVENT = 2


# 成功入队/出队累计值，不是当前FIFO占用量；modulus供调用方计算回绕差值。
@dataclass(frozen=True, slots=True)
class CanDmuCounters:
    tx_enqueued: int
    rx0_dequeued: int
    rx1_dequeued: int
    tx_event_dequeued: int
    modulus: int


# 仅错误语义；成功入队/出队及Debug事件不混入本掩码。
class CanDmuError(IntFlag):
    NONE = 0
    CONFIGURATION_ACCESS = 1 << 0
    EVENT_WRITE = 1 << 1
    EVENT_SEQUENCE = 1 << 2
    EVENT_DEQUEUE = 1 << 3
    EVENT_START = 1 << 4
    RX1_TIMESTAMP_OVERWRITE = 1 << 5
    RX1_WRITE = 1 << 6
    RX1_SEQUENCE = 1 << 7
    RX1_DEQUEUE = 1 << 8
    RX1_START = 1 << 9
    MEMORY_UNCORRECTED = 1 << 10
    MEMORY_CORRECTED = 1 << 11
    TX_READ = 1 << 12
    TX_AFTER_TRIGGER = 1 << 13
    TX_DLC = 1 << 14
    TX_SEQUENCE = 1 << 15
    TX_ENQUEUE = 1 << 16
    TX_START = 1 << 17


# 错误标志先读一次，再读两个状态；不是同时采样，不自动清除或重试。
@dataclass(frozen=True, slots=True)
class CanDmuStatus:
    errors: CanDmuError
    enabled: bool
    transfer_timestamp: bool


# DMU独立IRQ首次读值；与控制器/ECC事件位图不混用。
@dataclass(frozen=True, slots=True)
class CanDmuEvent:
    raw_status: CanDmuError
    masked_status: CanDmuError
    latched_events: CanDmuError
    event_count: int
    unexpected_count: int
    overflow_count: int
    generation: int
    fault_flags: int
    instance_id: int | None


# 非消费FIFO头部元数据；内部时间戳和TSU指针有互斥有效性。
@dataclass(frozen=True, slots=True)
class CanRxTimestamp:
    internal_timestamp: int | None
    tsu_pointer: int | None
    index: int


# DMA复制后解码的RX；index为0xffffffff表示镜像不携带FIFO索引。
# frame.data只保留真实有效负载，TSU覆盖的末字节不冒充接收数据。
@dataclass(frozen=True, slots=True)
class CanDmuRxImage:
    frame: CanRxFrame
    internal_timestamp_valid: bool
    tsu_pointer: int | None
    transferred_timestamp: int | None


# DMA事件镜像不重新读取FIFO或TSU；None表示未附加有效时间戳。
@dataclass(frozen=True, slots=True)
class CanDmuEventImage:
    event: CanTxEventDetails
    transferred_timestamp: int | None


# 一个过滤器的显式配置或实际读回，格式和列表索引由Driver方法参数指定。
# 普通过滤buffer_index必须为0；BUFFER使用RANGE、id2=0，不隐式选择时间戳捕获。
@dataclass(frozen=True, slots=True)
class CanFilter:
    type: CanFilterType
    action: CanFilterAction
    id1: int
    id2: int
    buffer_index: int = 0
