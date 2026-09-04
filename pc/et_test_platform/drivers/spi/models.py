# SPI公共参数和只读结果。
# 职责：表达帧、配置、FIFO/IRQ事实；不绑定芯片位号。
# 边界：不执行硬件访问，不保存测试判定。
# 依赖：标准库不可变类型。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 稳定选项通过固件映射到Driver编码，不能作为寄存器值直接写入。
class SpiRole(IntEnum):
    TARGET = 0
    CONTROLLER = 1


# 稳定选项通过固件映射到Driver编码，不能作为寄存器值直接写入。
class SpiFormat(IntEnum):
    MOTOROLA = 0
    TI = 1
    MICROWIRE = 2


# 稳定选项通过固件映射到Driver编码，不能作为寄存器值直接写入。
class SpiClockMode(IntEnum):
    MODE0 = 0
    MODE1 = 1
    MODE2 = 2
    MODE3 = 3


# 稳定选项通过固件映射到Driver编码，不能作为寄存器值直接写入。
class SpiTransferMode(IntEnum):
    TX_RX = 0
    TX_ONLY = 1
    RX_ONLY = 2
    EEPROM_READ = 3


# 稳定选项通过固件映射到Driver编码，不能作为寄存器值直接写入。
class SpiCsPolicy(IntEnum):
    AUTO = 0
    HOLD = 1
    TOGGLE = 2


# 独立的公共中断源，可组合选择；物理IRQ号不出现在PC接口中。
class SpiIrq(IntFlag):
    TX_EMPTY = 1 << 0
    TX_OVERFLOW = 1 << 1
    RX_UNDERFLOW = 1 << 2
    RX_OVERFLOW = 1 << 3
    RX_FULL = 1 << 4
    COLLISION = 1 << 5
    ALL = (1 << 6) - 1


# 同一次显式状态读取的语义位；读取可能清除后两项错误状态。
class SpiStatusFlag(IntFlag):
    BUSY = 1 << 0
    TX_NOT_FULL = 1 << 1
    TX_EMPTY = 1 << 2
    RX_NOT_EMPTY = 1 << 3
    RX_FULL = 1 << 4
    TARGET_TX_ERROR = 1 << 5
    COLLISION = 1 << 6


# 全配置均显式提供；读回类型也可表达硬件复位值，不能用配置参数覆盖读回。
@dataclass(frozen=True, slots=True)
class SpiConfig:
    role: SpiRole
    frame_format: SpiFormat
    clock_mode: SpiClockMode
    transfer_mode: SpiTransferMode
    cs_policy: SpiCsPolicy
    frame_bits: int
    frame_count: int
    divider: int
    target_output_enabled: bool
    loopback: bool
    rx_sample_delay: int
    control_bits: int
    sequential: bool
    transmit: bool
    handshake: bool


# 固件返回的可编程范围；允许不同芯片使用不同边界，不表示物理时序已通过验证。
@dataclass(frozen=True, slots=True)
class SpiLimits:
    frame_bits_min: int
    frame_bits_max: int
    fifo_depth: int
    divider_min: int
    divider_max: int
    frame_count_max: int
    rx_delay_max: int


# 独立阈值上限，不能用FIFO容量推导寄存器可编程范围。
@dataclass(frozen=True, slots=True)
class SpiFifoLimits:
    tx_irq_max: int
    rx_irq_max: int
    tx_start_max: int
    dma_tx_max: int
    dma_rx_max: int


# 普通快照不包含BUSY/读清错误；IRQ值采用稳定Source编码。
@dataclass(frozen=True, slots=True)
class SpiSnapshot:
    enabled: bool
    selected: bool
    tx_level: int
    rx_level: int
    tx_threshold: int
    rx_threshold: int
    start_threshold: int
    irq_raw: SpiIrq
    irq_status: SpiIrq
    irq_enabled: SpiIrq
    dma_tx_enabled: bool
    dma_rx_enabled: bool
    dma_tx_threshold: int
    dma_rx_threshold: int


# ISR锁存属于软件采集事实，不得把计数冒充芯片寄存器。
@dataclass(frozen=True, slots=True)
class SpiIrqEvent:
    raw_status: SpiIrq
    masked_status: SpiIrq
    latched_events: SpiIrq
    event_count: int
    unexpected_count: int
    overflow_count: int
    generation: int
    fault_flags: int


# 原始状态和语义位来自同一次读取，禁止随后自动重读。
@dataclass(frozen=True, slots=True)
class SpiErrorStatus:
    raw: int
    flags: SpiStatusFlag
