# Formal Case本地Support模块。
#
# 职责：聚合本测试域的只读事实、Driver构造和小粒度复用操作。
# 边界：不隐藏完整Case、不拥有最终断言，也不改变公共Scheduling。
# 依赖：仅依赖本IP Driver、Profile事实和稳定公共工具。

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfigFlag,
    DmaFifoMode,
    DmaTransferType,
    DmaWidth,
)

__all__ = [
    "DMA_ADDRESS_DECREMENT",
    "DMA_ADDRESS_FIXED",
    "DMA_ADDRESS_INCREMENT",
    "DMA_CONFIG_DESTINATION_SCATTER",
    "DMA_CONFIG_INITIAL_DONE",
    "DMA_CONFIG_SOURCE_GATHER",
    "DMA_DESTINATION_FILL",
    "DMA_FIFO_HALF_DEPTH",
    "DMA_FIFO_SINGLE",
    "DMA_GUARD_SIZE",
    "DMA_GUARD_VALUE",
    "DMA_TRANSFER_MEMORY_TO_MEMORY",
    "DMA_TRANSFER_MEMORY_TO_PERIPHERAL",
    "DMA_TRANSFER_PERIPHERAL_TO_MEMORY",
    "DMA_TRANSFER_PERIPHERAL_TO_PERIPHERAL",
    "DMA_WIDTH_BYTES",
    "DmaM2MVector",
    "build_dma_m2m_vector",
    "dma_m2m_measurement",
]

DMA_WIDTH_BYTES = {
    DmaWidth.BITS_8: 1,
    DmaWidth.BITS_16: 2,
    DmaWidth.BITS_32: 4,
}
DMA_ADDRESS_INCREMENT = DmaAddressMode.INCREMENT
DMA_ADDRESS_DECREMENT = DmaAddressMode.DECREMENT
DMA_ADDRESS_FIXED = DmaAddressMode.FIXED
DMA_TRANSFER_MEMORY_TO_MEMORY = DmaTransferType.MEMORY_TO_MEMORY
DMA_TRANSFER_MEMORY_TO_PERIPHERAL = DmaTransferType.MEMORY_TO_PERIPHERAL
DMA_TRANSFER_PERIPHERAL_TO_MEMORY = DmaTransferType.PERIPHERAL_TO_MEMORY
DMA_TRANSFER_PERIPHERAL_TO_PERIPHERAL = DmaTransferType.PERIPHERAL_TO_PERIPHERAL
DMA_FIFO_SINGLE = DmaFifoMode.SINGLE
DMA_FIFO_HALF_DEPTH = DmaFifoMode.HALF_DEPTH
DMA_CONFIG_SOURCE_GATHER = DmaConfigFlag.SOURCE_GATHER
DMA_CONFIG_DESTINATION_SCATTER = DmaConfigFlag.DESTINATION_SCATTER
DMA_CONFIG_INITIAL_DONE = DmaConfigFlag.INITIAL_DONE
DMA_GUARD_SIZE = 8
DMA_GUARD_VALUE = 0xD3
DMA_DESTINATION_FILL = 0xA5


# Pure M2M source/expected bytes and start offsets for one parameter vector.
@dataclass(frozen=True, slots=True)
class DmaM2MVector:
    source_data: bytes
    expected_destination: bytes
    width_bytes: int
    source_start_offset: int
    destination_start_offset: int


def _item_bytes(index: int, width_bytes: int) -> bytes:
    mask = (1 << (width_bytes * 8)) - 1
    value = (0x31 + index * 0x01020305) & mask
    return value.to_bytes(width_bytes, "little")


# Build expected M2M bytes and start offsets without hardware I/O.
def build_dma_m2m_vector(
    transfer_count: int,
    width: int | DmaWidth,
    source_mode: int | DmaAddressMode,
    destination_mode: int | DmaAddressMode,
) -> DmaM2MVector:

    width_value = DmaWidth(width)
    source_mode_value = DmaAddressMode(source_mode)
    destination_mode_value = DmaAddressMode(destination_mode)
    width_bytes = DMA_WIDTH_BYTES[width_value]
    source_items = [_item_bytes(index, width_bytes) for index in range(transfer_count)]
    if source_mode_value is DmaAddressMode.INCREMENT:
        transfer_items = source_items
        source_start_offset = DMA_GUARD_SIZE
    elif source_mode_value is DmaAddressMode.DECREMENT:
        transfer_items = list(reversed(source_items))
        source_start_offset = DMA_GUARD_SIZE + len(source_items) * width_bytes - width_bytes
    elif source_mode_value is DmaAddressMode.FIXED:
        transfer_items = [source_items[0]] * transfer_count
        source_start_offset = DMA_GUARD_SIZE
    else:  # pragma: no cover - enum normalization above owns rejection
        raise ValueError("unknown DMA source address mode")

    expected = bytearray([DMA_DESTINATION_FILL] * (transfer_count * width_bytes))
    if destination_mode_value is DmaAddressMode.INCREMENT:
        for index, item in enumerate(transfer_items):
            expected[index * width_bytes : (index + 1) * width_bytes] = item
        destination_start_offset = DMA_GUARD_SIZE
    elif destination_mode_value is DmaAddressMode.DECREMENT:
        for index, item in enumerate(transfer_items):
            physical = transfer_count - 1 - index
            expected[physical * width_bytes : (physical + 1) * width_bytes] = item
        destination_start_offset = DMA_GUARD_SIZE + transfer_count * width_bytes - width_bytes
    elif destination_mode_value is DmaAddressMode.FIXED:
        expected[:width_bytes] = transfer_items[-1]
        destination_start_offset = DMA_GUARD_SIZE
    else:  # pragma: no cover - enum normalization above owns rejection
        raise ValueError("unknown DMA destination address mode")

    return DmaM2MVector(
        source_data=b"".join(source_items),
        expected_destination=bytes(expected),
        width_bytes=width_bytes,
        source_start_offset=source_start_offset,
        destination_start_offset=destination_start_offset,
    )


# Convert already-observed M2M facts into a pure measurement mapping.
def dma_m2m_measurement(
    *,
    instance_id: int,
    channel: int,
    transfer_count: int,
    width: DmaWidth,
    source_mode: DmaAddressMode,
    destination_mode: DmaAddressMode,
    source_burst: DmaBurst,
    destination_burst: DmaBurst,
    fifo_mode: DmaFifoMode,
    vector: DmaM2MVector,
    actual: bytes,
) -> dict[str, object]:

    return {
        "controller": instance_id,
        "channel": channel,
        "transfer_count": transfer_count,
        "width": int(width),
        "width_bytes": vector.width_bytes,
        "source_address_mode": int(source_mode),
        "destination_address_mode": int(destination_mode),
        "source_burst": int(source_burst),
        "destination_burst": int(destination_burst),
        "fifo_mode": int(fifo_mode),
        "source_sha256": hashlib.sha256(vector.source_data).hexdigest(),
        "expected_sha256": hashlib.sha256(vector.expected_destination).hexdigest(),
        "actual_sha256": hashlib.sha256(actual).hexdigest(),
        "data_match": actual == vector.expected_destination,
    }
