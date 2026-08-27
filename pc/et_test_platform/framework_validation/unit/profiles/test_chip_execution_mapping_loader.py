# Framework Validation测试模块。
#
# 职责：验证test_chip_execution_mapping_loader 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.core.errors import UnsupportedCapability
from et_test_platform.profiles.chip_execution_mappings import (
    DmaPeripheralDirection,
    load_aes_dma_mapping,
    load_uart_dma_mappings,
)


def test_loader_reads_et6801_aes_dma_extension() -> None:
    mapping = load_aes_dma_mapping("et6801")

    assert mapping.input_fifo_address == 0x4020505C
    assert mapping.output_fifo_address == 0x40205074
    assert mapping.input_register_address == 0x4020504C
    assert mapping.output_register_address == 0x40205064
    assert (mapping.input_request_id, mapping.output_request_id) == (112, 113)


def test_loader_reads_et6801_uart_dma_extension() -> None:
    mappings = load_uart_dma_mappings("et6801")

    tx = mappings[(1, DmaPeripheralDirection.TX)]
    rx = mappings[(1, DmaPeripheralDirection.RX)]
    assert tx.peripheral_address == 0x40501000
    assert tx.request_id == 194
    assert rx.request_id == 195


def test_loader_fails_closed_when_chip_extension_is_absent() -> None:
    with pytest.raises(UnsupportedCapability, match="execution mapping is unavailable"):
        load_uart_dma_mappings("chip_without_mapping")
