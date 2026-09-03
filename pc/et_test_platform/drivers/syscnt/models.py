# SYSCNT稳定语义类型。
# 职责：区分计数窗口、暂停策略、控制读回与参考采样。
# 边界：不包含芯片寄存器、时钟频率或测试结论。
# 依赖：标准库。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 选择同一个逻辑计数器的控制窗口或读取窗口，不把两个窗口当作不同硬件实例。
class SyscntView(IntEnum):
    CONTROL = 0
    READ = 1


# 策略配置与实际debug_halted状态分开。
class SyscntHaltPolicy(IntEnum):
    RUN_FREE = 0
    PAUSE = 1


# 固件发布可执行的本IP原子操作集合；这些标志不表示硬件Feature已经测试通过。
class SyscntFeature(IntFlag):
    ENABLE = 1 << 0
    LOAD = 1 << 1
    DUAL_VIEW = 1 << 2
    FREQUENCY_ID = 1 << 3
    HALT = 1 << 4
    REFERENCE = 1 << 5
    ALL = ENABLE | LOAD | DUAL_VIEW | FREQUENCY_ID | HALT | REFERENCE


# 只读能力快照保留计数器、参考计数器和组成字的独立位宽，不包含实际时钟频率。
@dataclass(frozen=True, slots=True)
class SyscntCapabilities:
    features: SyscntFeature
    counter_bits: int
    view_mask: int
    reference_bits: int
    word_bits: int


# 硬件控制读回分别表达使能、暂停策略、实际暂停状态及频率登记，不混淆配置和现象。
@dataclass(frozen=True, slots=True)
class SyscntControl:
    enabled: bool
    halt_policy: SyscntHaltPolicy
    debug_halted: bool
    frequency_id_hz: int


# 一次原子采样按参考前值、本IP值、参考后值排序；只返回原始数值，不预先换算时间。
@dataclass(frozen=True, slots=True)
class SyscntReferenceSample:
    reference_before: int
    count: int
    reference_after: int
