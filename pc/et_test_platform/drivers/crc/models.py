# CRC PC Driver Package 的 models 层。
#
# 职责：提供 CRC 稳定 Model、Enum 和不可变结果类型。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile、不保存可变全局状态。
# 依赖：仅依赖标准库 dataclass 和 Enum。

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# CRC 硬件计算宽度，与 Firmware Wrap 合同逐值对应。
class CrcMode(IntEnum):
    CRC8 = 8
    CRC16 = 16
    CRC32 = 32


# CRC 最终结果异或模式，与 Firmware 配置字段的稳定取值逐值对应。
class CrcXorOut(IntEnum):
    ALL_ZERO = 0
    ALL_ONE = 1


# CRC 测试专用单次输入访问宽度，用于明确验证 8、16、32-Bit 输入行为。
class CrcInputAccessWidth(IntEnum):
    BITS_8 = 8
    BITS_16 = 16
    BITS_32 = 32


# CRC Service 对外暴露的稳定 IRQ 事件位。
class CrcIrqEvent(IntFlag):
    NONE = 0
    BUS_ERROR = 1 << 0
    LENGTH_ERROR = 1 << 1
    CHECK_ERROR = 1 << 2
    ALL = BUS_ERROR | LENGTH_ERROR | CHECK_ERROR


# CRC Runtime Service 对外报告的 Feature 位。
class CrcFeature(IntFlag):
    MODULE_ENABLE = 1 << 0
    POLYNOMIAL = 1 << 1
    INITIAL_SEED = 1 << 2
    BYTE_SWAP = 1 << 3
    REF_IN = 1 << 4
    REF_OUT = 1 << 5
    XOR_OUT = 1 << 6
    AUTO_LENGTH_RELOAD = 1 << 7
    RESULT_CHECK = 1 << 8
    LENGTH = 1 << 9
    RESULT = 1 << 10
    FIFO_THRESHOLD = 1 << 11
    FIFO_OVERFLOW = 1 << 12
    IRQ_ENABLE = 1 << 13
    IRQ_MASK = 1 << 14
    IRQ_FORCE = 1 << 15
    IRQ_CLEAR = 1 << 16
    IRQ_RAW_STATUS = 1 << 17
    CALCULATE = 1 << 18
    TEST_INPUT_WRITE = 1 << 19
    TEST_CALCULATE_TIMED = 1 << 20
    TEST_INPUT_BURST = 1 << 21


# CRC Runtime Service 能力事实。
@dataclass(frozen=True, slots=True)
class CrcCapabilities:
    api_version: int
    features: CrcFeature
    modes: tuple[CrcMode, ...]
    irq_events: CrcIrqEvent
    fifo_threshold_max: int
    bounded_synchronous_calculate: bool
    max_calculate_bytes: int


# 一份完整且芯片无关的 CRC 配置，供 Driver 校验后编码为稳定 Wire 请求。
@dataclass(frozen=True, slots=True)
class CrcConfig:
    mode: CrcMode
    polynomial: int
    initial_value: int
    ref_in: bool = False
    ref_out: bool = False
    byte_swap: bool = False
    auto_length_reload: bool = False
    result_check: bool = False
    xor_out: CrcXorOut = CrcXorOut.ALL_ZERO
    fifo_threshold: int = 1


# 一次同步 CRC 计算返回的结果与硬件剩余输入数。
@dataclass(frozen=True, slots=True)
class CrcCalculateResult:
    result: int
    remaining_input_count: int


# CRC FIFO 可自动观测的稳定状态，仅表达硬件已经发布的 Overflow 事实。
@dataclass(frozen=True, slots=True)
class CrcFifoStatus:
    overflow: bool


# 同一次原子读取获得的 CRC Raw、Mask 后状态和 Firmware 回调计数证据。
@dataclass(frozen=True, slots=True)
class CrcIrqSnapshot:
    raw: CrcIrqEvent
    status: CrcIrqEvent
    event_count: int
    last_event: CrcIrqEvent
    last_raw: CrcIrqEvent


# 目标侧 DWT 计时返回的 CRC 结果、周期数和实际处理字节数事实。
@dataclass(frozen=True, slots=True)
class CrcTimedResult:
    result: int
    elapsed_cycles: int
    measured_bytes: int


# 一次目标端紧凑输入 Burst 返回的检查点、最终结果和 FIFO 状态事实。
@dataclass(frozen=True, slots=True)
class CrcInputBurstResult:
    count: int
    checkpoint_count: int
    checkpoint_result: int
    final_result: int
    overflow: bool
