# WDG PC Driver 的稳定模型。
# 职责：表达跨芯片 WDG 配置、状态、IRQ 与持久记录。
# 边界：不包含目标芯片 SDK 类型、地址、IRQ 号或测试流程。
# 依赖：仅依赖标准库。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# WDG 计数窗口模式，与 Firmware Wrap 的公共取值逐值对应。
class WdgMode(IntEnum):
    WINDOW = 0
    INDEPENDENT = 1


# WDG 目标处理域工作模式，不暴露具体芯片寄存器编码。
class WdgWorkMode(IntEnum):
    ROUND1_IRQ_ROUND2_RESET = 0
    SAME_ROUND_IRQ_RESET = 1


# WDG Runtime Service 对外发布的稳定 Feature 能力位。
class WdgFeature(IntFlag):
    ENABLE = 1 << 0
    FEED = 1 << 1
    WINDOW = 1 << 2
    RESET_OUTPUT = 1 << 3
    WORK_MODE = 1 << 4
    HALT_PAUSE = 1 << 5
    LOCK = 1 << 6
    MODULE_RESET = 1 << 7
    INTERRUPTS = 1 << 8
    PERSISTENT_RECORDS = 1 << 9
    CONFIG_READBACK = 1 << 10


# WDG 公共 IRQ Source 位图，隔离芯片 IRQn 和寄存器位定义。
class WdgIrqEvent(IntFlag):
    NONE = 0
    TIMEOUT = 1 << 0
    ALL = TIMEOUT


# WDG 持久复位和中断记录的稳定选择位图，用于精确读取和清除。
class WdgRecord(IntFlag):
    NONE = 0
    RESET = 1 << 0
    INTERRUPT = 1 << 1
    ALL = RESET | INTERRUPT


# WDG 跨芯片完整配置，不暴露芯片 SDK 类型或 Raw 位值。
@dataclass(frozen=True, slots=True)
class WdgConfig:
    reload_count: int
    window_low_count: int = 0
    window_high_count: int = 0
    mode: WdgMode = WdgMode.INDEPENDENT
    work_mode: WdgWorkMode = WdgWorkMode.ROUND1_IRQ_ROUND2_RESET
    reset_enable: bool = False
    halt_pause_enable: bool = True


# WDG Runtime Service 返回的实例、范围、Feature 和 IRQ 能力。
@dataclass(frozen=True, slots=True)
class WdgCapabilities:
    features: WdgFeature
    maximum_reload_count: int
    maximum_window_count: int
    modes: tuple[WdgMode, ...]
    work_modes: tuple[WdgWorkMode, ...]
    irq_events: WdgIrqEvent
    instance_count: int


# WDG 当前使能状态和真实硬件计数读回，不由 PC 端缓存伪造。
@dataclass(frozen=True, slots=True)
class WdgStatus:
    enabled: bool
    counter: int


# WDG Raw、Status、ISR latch 和事件计数的同一时刻快照。
@dataclass(frozen=True, slots=True)
class WdgIrqSnapshot:
    raw: WdgIrqEvent
    status: WdgIrqEvent
    latched: WdgIrqEvent
    event_count: int
    last_raw: WdgIrqEvent


# WDG 复位记录和中断记录的独立硬件读回，保留两类记录的分层语义。
@dataclass(frozen=True, slots=True)
class WdgRecordSnapshot:
    reset: bool
    interrupt: bool
