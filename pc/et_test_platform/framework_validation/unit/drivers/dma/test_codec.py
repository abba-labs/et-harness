# Framework Validation测试模块。
#
# 职责：验证test_codec 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from typing import get_type_hints

import pytest

from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.dma import (
    CAPABILITIES,
    DMA_CONFIG,
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaConfigFlag,
    DmaFifoMode,
    DmaHandshakeMode,
    DmaHandshakePolarity,
    DmaTransferType,
    DmaUpdateMode,
    DmaWidth,
)
from et_test_platform.drivers.dma.codec import decode_capabilities, encode_config
from et_test_platform.drivers.dma.models import DmaConfig as DmaConfigModel


def _golden_config() -> DmaConfig:
    return DmaConfig(
        channel=0,
        transfer_type=DmaTransferType.PERIPHERAL_TO_PERIPHERAL,
        priority=2,
        source_width=DmaWidth.BITS_32,
        destination_width=DmaWidth.BITS_16,
        source_address_mode=DmaAddressMode.FIXED,
        destination_address_mode=DmaAddressMode.DECREMENT,
        source_burst=DmaBurst.ITEMS_256,
        destination_burst=DmaBurst.ITEMS_128,
        fifo_mode=DmaFifoMode.HALF_DEPTH,
        source_interface=10,
        destination_interface=11,
        source_update_mode=DmaUpdateMode.LINKED_LIST,
        destination_update_mode=DmaUpdateMode.RELOAD,
        source_handshake_mode=DmaHandshakeMode.SOFTWARE,
        destination_handshake_mode=DmaHandshakeMode.HARDWARE,
        source_handshake_polarity=DmaHandshakePolarity.ACTIVE_LOW,
        destination_handshake_polarity=DmaHandshakePolarity.ACTIVE_LOW,
        source_address=0x1122334455667788,
        destination_address=0x8877665544332211,
        transfer_count=0xAABBCCDD,
        flags=(
            DmaConfigFlag.SOURCE_GATHER
            | DmaConfigFlag.DESTINATION_SCATTER
            | DmaConfigFlag.INITIAL_DONE
        ),
        linked_list_address=0x0123456789ABCDEF,
        source_gather_interval=0x11121314,
        source_gather_count=0x21222324,
        destination_scatter_interval=0x31323334,
        destination_scatter_count=0x41424344,
    )


def test_dma_config_golden_bytes_remain_unchanged_for_valid_contract_values() -> None:
    expected = (
        "000302020102010706010a0b02010302"
        "88776655443322111122334455667788"
        "ddccbbaa07000000efcdab8967452301"
        "14131211242322213433323144434241"
    )

    config = _golden_config()

    assert DMA_CONFIG.size == 64
    assert encode_config(config).hex() == expected
    assert config.encode().hex() == expected


def test_dma_config_uses_named_types_for_stable_semantics() -> None:
    hints = get_type_hints(DmaConfigModel)
    assert hints["transfer_type"] is DmaTransferType
    assert hints["source_width"] is DmaWidth
    assert hints["destination_width"] is DmaWidth
    assert hints["source_address_mode"] is DmaAddressMode
    assert hints["destination_address_mode"] is DmaAddressMode
    assert hints["source_burst"] is DmaBurst
    assert hints["destination_burst"] is DmaBurst
    assert hints["fifo_mode"] is DmaFifoMode
    assert hints["source_update_mode"] is DmaUpdateMode
    assert hints["destination_update_mode"] is DmaUpdateMode
    assert hints["flags"] is DmaConfigFlag


def test_stable_model_has_no_wire_methods_but_facade_keeps_legacy_encode() -> None:
    assert not hasattr(DmaConfigModel, "encode")
    assert hasattr(DmaConfig, "encode")
    assert issubclass(DmaConfig, DmaConfigModel)


def test_capability_decoder_rejects_invalid_length_and_limits() -> None:
    with pytest.raises(ProtocolError, match="response length"):
        decode_capabilities(b"\x00")

    invalid_limits = CAPABILITIES.pack(0, 0, 0, 0, 0, 0)
    with pytest.raises(ProtocolError, match="invalid limits"):
        decode_capabilities(invalid_limits)
