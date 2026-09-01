# DMA PC Driver Package 的models层。
#
# 职责：提供 DMA 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 选择 DMA 寄存器快照的普通视图或 ACC 视图。
class DmaAccessView(IntEnum):
    NORMAL = 0
    ACC = 1


# DMA 四类稳定传输方向，与 Firmware Wrap 合同逐值对应。
class DmaTransferType(IntEnum):
    MEMORY_TO_MEMORY = 0
    MEMORY_TO_PERIPHERAL = 1
    PERIPHERAL_TO_MEMORY = 2
    PERIPHERAL_TO_PERIPHERAL = 3


# 表示 DMA 单次传输的数据宽度编码，仅允许 Wrap 合同定义的 8/16/32 Bit。
class DmaWidth(IntEnum):
    BITS_8 = 0
    BITS_16 = 1
    BITS_32 = 2


# 表示 DMA 源或目标地址的更新方式，只允许递增、递减或固定三种稳定语义。
class DmaAddressMode(IntEnum):
    INCREMENT = 0
    DECREMENT = 1
    FIXED = 2


# DMA Burst 长度编码，与 Wrap 的 1 到 256 Item 定义一致。
class DmaBurst(IntEnum):
    ITEMS_1 = 0
    ITEMS_4 = 1
    ITEMS_8 = 2
    ITEMS_16 = 3
    ITEMS_32 = 4
    ITEMS_64 = 5
    ITEMS_128 = 6
    ITEMS_256 = 7


# 表示 DMA FIFO 阈值策略，仅允许单项模式或半深度模式两种稳定取值。
class DmaFifoMode(IntEnum):
    SINGLE = 0
    HALF_DEPTH = 1


# DMA 地址更新由连续地址、Reload 或 Linked List 驱动。
class DmaUpdateMode(IntEnum):
    CONTIGUOUS = 0
    RELOAD = 1
    LINKED_LIST = 2


# 表示 DMA Config 可组合功能位，只允许 Gather、Scatter 与 Initial Done。
class DmaConfigFlag(IntFlag):
    NONE = 0
    SOURCE_GATHER = 1 << 0
    DESTINATION_SCATTER = 1 << 1
    INITIAL_DONE = 1 << 2


# DMA Service 对外暴露的稳定中断事件位。
class DmaIrqEvent(IntFlag):
    TRANSFER_DONE = 1 << 0
    BLOCK_DONE = 1 << 1
    SOURCE_TRANSACTION = 1 << 2
    DESTINATION_TRANSACTION = 1 << 3
    ERROR = 1 << 4


# 选择 DMA 端点由硬件握手还是 PC 软件请求节拍。
class DmaHandshakeMode(IntEnum):
    HARDWARE = 0
    SOFTWARE = 1


# 表示 DMA 硬件握手输入的有效电平，仅允许高有效或低有效两种模式。
class DmaHandshakePolarity(IntEnum):
    ACTIVE_HIGH = 0
    ACTIVE_LOW = 1


# 表示 DMA 软件握手请求作用端点，只允许源端点或目标端点两种取值。
class DmaHandshakeTarget(IntEnum):
    SOURCE = 0
    DESTINATION = 1


# 选择软件握手请求写入 Transfer、Single 或 Last 寄存器族。
class DmaSoftwareRequestKind(IntEnum):
    TRANSFER = 0
    SINGLE = 1
    LAST = 2


# 运行时 DMA Service 返回的稳定 Feature 位。
class DmaFeature(IntFlag):
    MEMORY_TO_MEMORY = 1 << 0
    MEMORY_TO_PERIPHERAL = 1 << 1
    PERIPHERAL_TO_MEMORY = 1 << 2
    PERIPHERAL_TO_PERIPHERAL = 1 << 3
    SUSPEND_RESUME = 1 << 4
    INTERRUPTS = 1 << 5
    RELOAD = 1 << 6
    SOURCE_GATHER = 1 << 7
    DESTINATION_SCATTER = 1 << 8
    LINKED_LIST = 1 << 9
    ATOMIC_CHANNEL_MASK_START = 1 << 10
    SOFTWARE_HANDSHAKE = 1 << 11
    HANDSHAKE_MODE = 1 << 12
    HANDSHAKE_POLARITY = 1 << 13


# 一个运行中 DMA Firmware Service 返回的稳定 Feature 和边界事实。
@dataclass(frozen=True, slots=True)
class DmaCapabilities:
    features: DmaFeature
    channel_count: int
    max_transfer_count: int
    max_gather_scatter_interval: int
    max_gather_scatter_count: int
    irq_events: DmaIrqEvent


# 一个 DMA Channel 的稳定配置事实。
#
# 有限集合的业务语义使用具名 Enum；Channel、Priority、Interface、Address 和
# Count 保持数值类型，因为它们由运行时 Capability、Resolver 或具体 Case 决定。
@dataclass(frozen=True, slots=True)
class DmaConfig:
    channel: int
    source_address: int
    destination_address: int
    transfer_count: int
    transfer_type: DmaTransferType = DmaTransferType.MEMORY_TO_MEMORY
    priority: int = 0
    source_width: DmaWidth = DmaWidth.BITS_8
    destination_width: DmaWidth = DmaWidth.BITS_8
    source_address_mode: DmaAddressMode = DmaAddressMode.INCREMENT
    destination_address_mode: DmaAddressMode = DmaAddressMode.INCREMENT
    source_burst: DmaBurst = DmaBurst.ITEMS_1
    destination_burst: DmaBurst = DmaBurst.ITEMS_1
    fifo_mode: DmaFifoMode = DmaFifoMode.SINGLE
    source_interface: int = 0
    destination_interface: int = 0
    source_update_mode: DmaUpdateMode = DmaUpdateMode.CONTIGUOUS
    destination_update_mode: DmaUpdateMode = DmaUpdateMode.CONTIGUOUS
    source_handshake_mode: DmaHandshakeMode = DmaHandshakeMode.HARDWARE
    destination_handshake_mode: DmaHandshakeMode = DmaHandshakeMode.HARDWARE
    source_handshake_polarity: DmaHandshakePolarity = DmaHandshakePolarity.ACTIVE_HIGH
    destination_handshake_polarity: DmaHandshakePolarity = DmaHandshakePolarity.ACTIVE_HIGH
    flags: DmaConfigFlag = DmaConfigFlag.NONE
    linked_list_address: int = 0
    source_gather_interval: int = 0
    source_gather_count: int = 0
    destination_scatter_interval: int = 0
    destination_scatter_count: int = 0


# 一次 DMA IRQ 观测得到的锁存事件与计数事实。
@dataclass(frozen=True, slots=True)
class DmaIrqResult:
    latched_events: DmaIrqEvent
    irq_count: int
    unexpected_count: int
    overflow_count: int


# 一个 DMA Channel 的空闲、FIFO 与中断状态事实。
@dataclass(frozen=True, slots=True)
class DmaChannelStatus:
    is_free: bool
    fifo_empty: bool
    interrupt_events: DmaIrqEvent


# DMA Component 参数寄存器的只读快照。
@dataclass(frozen=True, slots=True)
class DmaComponentSnapshot:
    dma_id: int
    component_id: int
    channel_params: tuple[int, ...]
    multi_block_params: int
    max_block_size_params: int


# 保存 DMA 原始、屏蔽后、Mask 和组合中断寄存器的同一次只读快照事实。
@dataclass(frozen=True, slots=True)
class DmaInterruptSnapshot:
    raw: tuple[int, ...]
    status: tuple[int, ...]
    mask: tuple[int, ...]
    combined_status: int


# 一个 DMA Channel 的地址、原始诊断字和稳定配置读回快照。
#
# 原始 Control/Config Word 仅用于诊断；Burst/Block/FIFO 等稳定业务字段由目标侧
# Chip Driver/Wrap 解码后显式返回，PC Model 不解释任何芯片寄存器位布局。
@dataclass(frozen=True, slots=True)
class DmaChannelSnapshot:
    source_address: int
    destination_address: int
    linked_list_address: int
    control_low: int
    control_high: int
    config_low: int
    config_high: int
    source_gather: int
    destination_scatter: int
    source_burst: DmaBurst
    destination_burst: DmaBurst
    block_size: int
    fifo_mode: DmaFifoMode


# DMA Start-to-IRQ 的目标 DWT 计时事实。
@dataclass(frozen=True, slots=True)
class DmaTimingSnapshot:
    complete: bool
    channel: int
    elapsed_cycles: int
