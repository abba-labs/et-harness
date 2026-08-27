# STIMER PC Driver稳定模型。
# 职责：表达跨芯片配置、计数、状态与IRQ事实。
# 边界：不包含目标芯片SDK类型、地址或IRQ号。
# 依赖：仅依赖标准库 dataclass、IntEnum 和 IntFlag。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# STIMER 周期结束后的稳定运行模式，与 Firmware Wrap 合同对应。
class StimerMode(IntEnum):
    ONE_SHOT = 0
    FREE_RUN = 1


# STIMER 周期和 Compare 配置的公共加载时机语义。
class StimerLoadMode(IntEnum):
    IMMEDIATE = 0
    SHADOW = 1


# STIMER在CPU被Debugger Halt时的稳定运行策略。
class StimerDebugHaltPolicy(IntEnum):
    PAUSE = 0
    RUN_FREE = 1


# STIMER Runtime Service 对外发布的稳定 Feature 能力位。
class StimerFeature(IntFlag):
    START_STOP = 1 << 0
    PERIOD = 1 << 1
    PRESCALER = 1 << 2
    ONE_SHOT = 1 << 3
    FREE_RUN = 1 << 4
    CLEAR = 1 << 5
    PAUSE_RESUME = 1 << 6
    LOAD_MODE = 1 << 7
    LATCH = 1 << 8
    COMPARE = 1 << 9
    INTERRUPTS = 1 << 10
    STATUS = 1 << 11
    EVENT_PULSE_WIDTH = 1 << 12
    DMA_REQUEST = 1 << 13
    DEBUG_HALT = 1 << 14
    EMERGENCY_CAPTURE = 1 << 15


# STIMER 公共 IRQ Source 位图，隔离芯片 IRQn 和寄存器位定义。
class StimerIrqEvent(IntFlag):
    NONE = 0
    COMPARE0 = 1 << 0
    COMPARE1 = 1 << 1
    COMPARE2 = 1 << 2
    COMPARE3 = 1 << 3
    OVERFLOW = 1 << 4
    ALL = COMPARE0 | COMPARE1 | COMPARE2 | COMPARE3 | OVERFLOW


# STIMER 当前运行状态位图，用于表达真实硬件状态读回。
class StimerRuntimeStatus(IntFlag):
    NONE = 0
    COMPARE0_VALUE_ERROR = 1 << 0
    COMPARE1_VALUE_ERROR = 1 << 1
    COMPARE2_VALUE_ERROR = 1 << 2
    COMPARE3_VALUE_ERROR = 1 << 3
    OVERFLOW = 1 << 4
    COMPARE0_REPEAT = 1 << 5
    COMPARE1_REPEAT = 1 << 6
    COMPARE2_REPEAT = 1 << 7
    COMPARE3_REPEAT = 1 << 8
    ALL = (1 << 9) - 1


# STIMER 跨芯片完整配置，不暴露芯片 SDK 类型或 Raw 位值。
@dataclass(frozen=True, slots=True)
class StimerConfig:
    period_ticks: int
    prescaler_divider: int = 1
    mode: StimerMode = StimerMode.ONE_SHOT
    load_mode: StimerLoadMode = StimerLoadMode.IMMEDIATE


# STIMER Runtime Service 返回的实例、范围、Feature 和 IRQ 能力。
@dataclass(frozen=True, slots=True)
class StimerCapabilities:
    features: StimerFeature
    maximum_period_ticks: int
    maximum_prescaler_divider: int
    compare_channel_count: int
    instance_count: int
    irq_events: StimerIrqEvent


# STIMER Raw、Status、ISR latch 和事件计数的同一时刻快照。
@dataclass(frozen=True, slots=True)
class StimerIrqSnapshot:
    raw: StimerIrqEvent
    status: StimerIrqEvent
    latched: StimerIrqEvent
    event_count: int
    last_raw: StimerIrqEvent
    last_event: StimerIrqEvent
