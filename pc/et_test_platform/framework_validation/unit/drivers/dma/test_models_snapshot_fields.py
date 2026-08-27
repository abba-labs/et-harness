# DMA Channel Snapshot 稳定字段 Wire 解码回归。
# 职责：保护 FIFO/Burst/Block 由目标侧归一后通过 Wire 进入公共 PC Model。
# 边界：纯数据测试；PC 不解释 ET6801 Control/Config 寄存器位布局。
# 依赖：DMA公共Model、Codec和Wire结构常量。

import struct

from et_test_platform.drivers.dma import DmaBurst, DmaFifoMode
from et_test_platform.drivers.dma.codec import decode_channel_snapshot


def test_dma_channel_snapshot_uses_target_normalized_config_fields() -> None:
    # 前9个 raw word 故意为零；稳定配置值来自追加的目标侧归一字段。
    body = struct.pack(
        "<13I",
        0x1000,
        0x2000,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        int(DmaBurst.ITEMS_64),
        int(DmaBurst.ITEMS_16),
        257,
        int(DmaFifoMode.HALF_DEPTH),
    )

    snapshot = decode_channel_snapshot(body)

    assert snapshot.source_burst is DmaBurst.ITEMS_64
    assert snapshot.destination_burst is DmaBurst.ITEMS_16
    assert snapshot.block_size == 257
    assert snapshot.fifo_mode is DmaFifoMode.HALF_DEPTH
