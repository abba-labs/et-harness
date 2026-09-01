# FMAC PC Driver Package 的 models 层。
#
# 职责：定义芯片中立的 FMAC Enum、配置和不可变结果类型。
# 边界：不做 Wire 编解码、不读取 Profile、不保存可变全局状态。
# 依赖：仅依赖标准库dataclass和枚举类型。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 描述目标FMAC运行时公开的稳定能力集合；未知能力位由Codec拒绝。
class FmacFeature(IntFlag):
    FIXED_Q15 = 1 << 0
    FLOAT_INPUT = 1 << 1
    FLOAT_OUTPUT = 1 << 2
    FIR = 1 << 3
    IIR = 1 << 4
    STREAM = 1 << 5
    CLEAR = 1 << 6
    OUTPUT_POLICY = 1 << 7
    STATUS = 1 << 8
    INTERRUPTS = 1 << 9
    DMA_REQUEST = 1 << 10
    TIMED_PROCESS = 1 << 11
    TEST_EXTENSIONS = 1 << 12


# 描述FMAC装载、FIR和IIR等稳定功能选择，不包含芯片SDK枚举。
class FmacFunction(IntEnum):
    LOAD_X1 = 1
    LOAD_X2 = 2
    LOAD_Y = 3
    FIR = 4
    IIR = 5


# 描述FMAC资源中Q15和Float32两种稳定数据格式语义。
class FmacDataFormat(IntEnum):
    Q15 = 0
    FLOAT32 = 1


# 描述FMAC公共Buffer水位选项，具体支持集合由运行时能力返回。
class FmacWatermark(IntEnum):
    ITEMS_1 = 1
    ITEMS_2 = 2
    ITEMS_4 = 4
    ITEMS_8 = 8


# 描述累加结果发生定点溢出时采用饱和或回绕的稳定处理策略。
class FmacFinalPolicy(IntEnum):
    SATURATE = 0
    WRAP = 1


# 描述FMAC输出保持原值或限制到12位、16位范围的稳定模式。
class FmacOutputMode(IntEnum):
    RAW = 0
    SAT12 = 1
    SAT16 = 2


# 描述FMAC输出相对Q15基准的左移、无移位和右移选项。
class FmacShift(IntEnum):
    LEFT8 = 0
    LEFT7 = 1
    LEFT6 = 2
    LEFT5 = 3
    LEFT4 = 4
    LEFT3 = 5
    LEFT2 = 6
    LEFT1 = 7
    NONE = 8
    RIGHT1 = 9
    RIGHT2 = 10
    RIGHT3 = 11
    RIGHT4 = 12
    RIGHT5 = 13
    RIGHT6 = 14
    RIGHT7 = 15


# 描述FMAC公开的请求、溢出、参数及装载错误中断事件集合。
class FmacIrqEvent(IntFlag):
    X1_WRITE_REQUEST = 1 << 0
    Y_READ_REQUEST = 1 << 1
    SATURATION = 1 << 2
    X1_OVERFLOW = 1 << 3
    Y_UNDERFLOW = 1 << 4
    P_ERROR = 1 << 5
    PQ_ERROR = 1 << 6
    Q_ERROR = 1 << 7
    X1_LOAD_ERROR = 1 << 8
    X2_LOAD_ERROR = 1 << 9
    Y_LOAD_ERROR = 1 << 10
    ALL = (1 << 11) - 1


# 描述FMAC输入和输出DMA Request Gate的独立控制位集合。
class FmacDmaRequest(IntFlag):
    NONE = 0
    INPUT = 1 << 0
    OUTPUT = 1 << 1
    ALL = INPUT | OUTPUT


# 保存目标FMAC返回的不可变运行时能力、范围和支持选项快照。
@dataclass(frozen=True)
class FmacCapabilities:
    api_version: int
    features: FmacFeature
    max_transfer_items: int
    logical_address_bits: int
    max_feedforward_taps: int
    max_feedback_taps: int
    watermarks: tuple[FmacWatermark, ...]
    output_modes: tuple[FmacOutputMode, ...]
    shift_count: int
    irq_events: FmacIrqEvent
    fir_first_valid_output_index: int | None
    iir_first_valid_output_index: int | None


# 保存芯片中立的FMAC Buffer、输出和数值格式完整配置。
@dataclass(frozen=True)
class FmacConfig:
    x1_start: int
    x1_size: int
    x1_full_watermark: FmacWatermark
    x2_start: int
    x2_size: int
    y_start: int
    y_size: int
    y_empty_watermark: FmacWatermark
    final_policy: FmacFinalPolicy = FmacFinalPolicy.SATURATE
    output_mode: FmacOutputMode = FmacOutputMode.RAW
    internal_clip: bool = False
    float_input: bool = False
    float_output: bool = False
    output_shift: FmacShift = FmacShift.NONE
    output_offset: int = 0


# 保存一次读取获得的FMAC活动状态、Buffer计数和异常标志。
@dataclass(frozen=True)
class FmacStatus:
    active: bool
    x1_spare_count: int
    y_unread_count: int
    x1_full: bool
    y_empty: bool
    x1_overflow: bool
    y_underflow: bool
    accumulator_saturation: bool
    negative_after_offset: bool
    float_to_q15_overflow: bool


# 保存FMAC中断Raw、有效状态、固件Latch和事件计数快照。
@dataclass(frozen=True)
class FmacIrqSnapshot:
    raw: FmacIrqEvent
    status: FmacIrqEvent
    latched: FmacIrqEvent
    event_count: int
    enabled: FmacIrqEvent
    masked: FmacIrqEvent


# 保存目标端一次FMAC处理实际接受和读出的数据项数量。
@dataclass(frozen=True)
class FmacProcessResult:
    accepted_count: int
    read_count: int


# 保存目标端一次FMAC处理的数据项数量及DWT原始周期计数。
@dataclass(frozen=True)
class FmacTimedProcessResult:
    accepted_count: int
    read_count: int
    elapsed_cycles: int
