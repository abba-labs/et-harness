# DMA Channel Snapshot 跨层 Wire 契约回归。
# 职责：保护 ET6801 Chip Driver -> Wrap -> Service -> PC Codec 的稳定配置读回字段。
# 边界：静态契约测试，不执行目标硬件，也不依赖生成的 Keil 工程元数据。
# 依赖：DMA Firmware源码、PC Codec和公共Wire定义。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_dma_channel_snapshot_normalizes_register_layout_on_target_side() -> None:
    chip_header = _source("firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_ahbdma.h")
    chip_driver = _source("firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_ahbdma.c")
    wrap_header = _source("firmware/wrap/include/et_dma_wrap.h")
    wrap_source = _source("firmware/wrap/src/et_dma_wrap.c")
    service_header = _source("firmware/services/include/et_dma_service.h")
    service_source = _source("firmware/services/src/et_dma_service.c")
    codec = _source("pc/et_test_platform/drivers/dma/codec.py")
    model = _source("pc/et_test_platform/drivers/dma/models.py")

    for field in ("sourceBurst", "destinationBurst", "blockSize", "fifoMode"):
        assert field in chip_header
    assert "AHBDMA0_CH_CTLL_SRC_MSIZE_Msk" in chip_driver
    assert "AHBDMA0_CH_CTLL_DEST_MSIZE_Msk" in chip_driver
    assert "AHBDMA0_CH_CTLH_BLOCK_TS_Msk" in chip_driver
    assert "AHBDMA0_CH_CFGH_FIFO_MODE_Msk" in chip_driver

    for field in ("source_burst", "destination_burst", "block_size", "fifo_mode"):
        assert field in wrap_header
    assert "snapshot->source_burst = driver_snapshot.sourceBurst" in wrap_source
    assert "snapshot->destination_burst = driver_snapshot.destinationBurst" in wrap_source
    assert "snapshot->block_size = driver_snapshot.blockSize" in wrap_source
    assert "snapshot->fifo_mode = driver_snapshot.fifoMode" in wrap_source

    assert "ET_DMA_SERVICE_CHANNEL_SNAPSHOT_RESPONSE_SIZE 52u" in service_header
    for offset in (
        "ET_DMA_SERVICE_CHANNEL_SOURCE_BURST_OFFSET",
        "ET_DMA_SERVICE_CHANNEL_DESTINATION_BURST_OFFSET",
        "ET_DMA_SERVICE_CHANNEL_BLOCK_SIZE_OFFSET",
        "ET_DMA_SERVICE_CHANNEL_FIFO_MODE_OFFSET",
    ):
        assert offset in service_header
        assert offset in service_source

    assert 'CHANNEL_SNAPSHOT = struct.Struct("<13I")' in codec
    assert "source_burst=DmaBurst(values[9])" in codec
    assert "destination_burst=DmaBurst(values[10])" in codec
    assert "block_size=values[11]" in codec
    assert "fifo_mode=DmaFifoMode(values[12])" in codec

    # Public PC Model carries typed stable fields but must not decode ET6801 bit positions.
    assert "source_burst: DmaBurst" in model
    assert "destination_burst: DmaBurst" in model
    assert "block_size: int" in model
    assert "fifo_mode: DmaFifoMode" in model
    assert "self.control_low >>" not in model
    assert "self.control_high & 0xFFF" not in model
    assert "self.config_high >>" not in model
