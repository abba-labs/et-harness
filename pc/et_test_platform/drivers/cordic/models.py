# CORDIC PC Driver Package 的 models 层。
#
# 职责：提供 CORDIC 稳定 Enum、配置和不可变结果类型。
# 边界：不做 Wire 编解码、不访问 Target/Profile、不保存可变全局状态。
# 依赖：仅依赖标准库 dataclass 和 Enum。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# CORDIC 对外发布的数学函数编号，与 Firmware Wrap 合同逐值对应。
class CordicFunction(IntEnum):
    SINCOS = 0
    PHASE_MODULUS = 1
    ARCTAN = 2
    HSINCOS = 3
    ATANH = 4
    EXP = 5
    LN = 6
    SQRT = 7
    TAN = 8


# CORDIC 输入和结果的稳定数值模式，用于区分定点 Raw Word 与 IEEE-754 Raw Word。
class CordicNumericMode(IntEnum):
    FIXED = 0
    FLOAT32 = 1


# CORDIC 参数与结果的稳定数据宽度，分别表达 16-Bit 与 32-Bit 硬件访问语义。
class CordicWidth(IntEnum):
    BITS_16 = 16
    BITS_32 = 32


# CORDIC 输入域的稳定编码，不解释具体数学 Codec。
class CordicInputRange(IntEnum):
    NORMALIZED = 0
    DIRECT_ANGLE = 1


# 可配置函数返回的稳定结果字数量，用于声明单结果或双结果输出路径。
class CordicResultCount(IntEnum):
    ONE = 1
    TWO = 2


# CORDIC 计算触发与结果获取的稳定工作模式。
class CordicWorkMode(IntEnum):
    INTERRUPT = 0
    POLLING = 1
    ZERO_OVERHEAD = 2
    DMA = 3


# CORDIC Runtime Service 对外报告的 Feature 位。
class CordicFeature(IntFlag):
    FIXED = 1 << 0
    FLOAT32 = 1 << 1
    WIDTH_16 = 1 << 2
    WIDTH_32 = 1 << 3
    NORMALIZED_RANGE = 1 << 4
    DIRECT_ANGLE_RANGE = 1 << 5
    POLLING = 1 << 6
    INTERRUPT = 1 << 7
    ZERO_OVERHEAD = 1 << 8
    DMA = 1 << 9
    STATUS = 1 << 10
    INTERRUPTS = 1 << 11


# CORDIC 已发布的计算与输入状态位，支持位组合读取和精确 W1C 清除。
class CordicStatus(IntFlag):
    ARG_OVERFLOW = 1 << 0
    COMPLETE = 1 << 1
    PM_ARG2_ERROR = 1 << 2
    ALL = ARG_OVERFLOW | COMPLETE | PM_ARG2_ERROR


# CORDIC Float-to-Fixed 转换状态位。
class CordicConversionStatus(IntFlag):
    UNDERFLOW = 1 << 0
    OVERFLOW = 1 << 1
    ALL = UNDERFLOW | OVERFLOW


# CORDIC Service 对外暴露的稳定 IRQ 事件位。
class CordicIrqEvent(IntFlag):
    ARG_OVERFLOW = 1 << 0
    CALCULATION_COMPLETE = 1 << 1
    PM_ARG2_ERROR = 1 << 2
    ALL = ARG_OVERFLOW | CALCULATION_COMPLETE | PM_ARG2_ERROR


# CORDIC Runtime Service 的能力事实。
@dataclass(frozen=True)
class CordicCapabilities:
    api_version: int
    features: CordicFeature
    functions: tuple[CordicFunction, ...]
    maximum_scale: int
    maximum_precision_cycles: int
    irq_events: CordicIrqEvent


# 一份完整且芯片无关的 CORDIC 配置；所有字段在发送前由 Runtime Capability 校验。
@dataclass(frozen=True)
class CordicConfig:
    numeric_mode: CordicNumericMode = CordicNumericMode.FIXED
    argument_width: CordicWidth = CordicWidth.BITS_32
    result_width: CordicWidth = CordicWidth.BITS_32
    input_range: CordicInputRange = CordicInputRange.NORMALIZED
    scale: int = 0
    precision_cycles: int = 8
    sincos_result_count: CordicResultCount = CordicResultCount.TWO
    phase_modulus_result_count: CordicResultCount = CordicResultCount.TWO
    hsincos_result_count: CordicResultCount = CordicResultCount.TWO
    work_mode: CordicWorkMode = CordicWorkMode.POLLING


# 一次 CORDIC 运算返回的两个 Raw 结果字。
@dataclass(frozen=True)
class CordicResult:
    primary_raw: int
    secondary_raw: int


# 一次目标侧计时事务返回的Raw结果和DWT周期事实。
@dataclass(frozen=True)
class CordicTimedResult:
    primary_raw: int
    secondary_raw: int
    elapsed_cycles: int


# 同一次原子读取获得的 CORDIC Raw、Status 和 Firmware 回调证据。
@dataclass(frozen=True)
class CordicIrqSnapshot:
    raw: CordicIrqEvent
    status: CordicIrqEvent
    event_count: int
    last_event: CordicIrqEvent
    last_raw: CordicIrqEvent
