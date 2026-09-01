# UART PC Driver Package 的models层。
#
# 职责：提供 UART 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 表示 UartDmaEndpoint 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartDmaEndpoint(IntEnum):
    TX = 0
    RX = 1


# 表示 UartStopBits 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartStopBits(IntEnum):
    ONE = 1
    ONE_AND_HALF = 2
    TWO = 3
    ONE_POINT_FIVE = ONE_AND_HALF


# 表示 UartParity 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartParity(IntEnum):
    NONE = 0
    EVEN = 1
    ODD = 2
    STICK_ZERO = 3
    STICK_ONE = 4
    STICK0 = STICK_ZERO
    STICK1 = STICK_ONE


# 表示 UartDmaMode 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartDmaMode(IntEnum):
    DISABLED = 0
    SINGLE = 1
    MULTI = 2
    OFF = DISABLED
    SINGLE_BLOCK = SINGLE
    MULTI_BLOCK = MULTI


# 表示 UartIrqSource 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartIrqSource(IntFlag):
    RX_READY = 1 << 0
    TX_READY = 1 << 1
    LINE_ERROR = 1 << 2
    MODEM_STATUS = 1 << 3
    CHARACTER_TIMEOUT = 1 << 4
    BUSY = 1 << 5
    NINE_BIT_ADDRESS = 1 << 6
    ERROR = LINE_ERROR
    RX_DATA = RX_READY
    TX_EMPTY = TX_READY
    TIMEOUT = CHARACTER_TIMEOUT


# 表示 UartErrorFlag 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartErrorFlag(IntFlag):
    OVERRUN = 1 << 0
    PARITY = 1 << 1
    FRAMING = 1 << 2
    BREAK = 1 << 3
    RX_FIFO = 1 << 4


UartIrqMask = UartIrqSource
UartDmaTransferMode = UartDmaMode


# 表示 UartFeature 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class UartFeature(IntFlag):
    RX_POLLING = 1 << 0
    TX_POLLING = 1 << 1
    RX_IRQ = 1 << 2
    TX_IRQ = 1 << 3
    RX_DMA = 1 << 4
    TX_DMA = 1 << 5
    FIFO = 1 << 6
    LOOPBACK = 1 << 7
    FLOW_CONTROL = 1 << 8
    BREAK = 1 << 9
    NINE_BIT = 1 << 10
    MODEM = 1 << 11
    HALT = 1 << 12
    SOFTWARE_RESET = 1 << 13
    SHADOW = 1 << 14
    FIFO_ACCESS = 1 << 15


# 表示 UartCapabilities 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartCapabilities:
    features: UartFeature
    min_baudrate: int
    max_baudrate: int
    max_read_size: int
    max_write_size: int


# 表示 UartCapture 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartCapture:
    active: bool
    expected: int
    received: int
    data: bytes

    # 提供 complete 的稳定公共能力；职责限定在当前模块，不泄漏下层实现或隐藏跨层流程。
    @property
    def complete(self) -> bool:

        return not self.active and self.received == self.expected


# 表示 UartSnapshot 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartSnapshot:
    component_parameter: int
    component_version: int
    peripheral_id: int
    scratch: int
    uart_status: int
    line_status: int
    tx_fifo_level: int
    rx_fifo_level: int


# 表示 UartStatus 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartStatus:
    line_status: int
    fifo_flags: int
    tx_fifo_level: int
    rx_fifo_level: int
    error_flags: int
    state_flags: int


# 表示 UartIrqState 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartIrqState:
    enabled_mask: int
    pending_mask: int
    active_mask: int
    event_count: int
    overflow_count: int
    fault_count: int


# 表示 UartModemStatus 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartModemStatus:
    input_flags: int
    delta_flags: int
    output_flags: int
    raw_status: int


# 表示 UartBusyDetectResult 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartBusyDetectResult:
    pre_trigger_usr: int
    observed_iir: int
    observed_usr: int
    trigger_count: int
    cleared: bool
    recovered: bool
    busy_observed: bool
    interrupt_observed: bool


# 表示 UartShadowFifoState 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class UartShadowFifoState:
    enabled: bool
    tx_threshold: int
    rx_threshold: int
