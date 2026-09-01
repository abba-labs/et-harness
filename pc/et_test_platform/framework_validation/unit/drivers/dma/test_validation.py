# Framework Validation测试模块。
#
# 职责：验证test_validation 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.drivers.dma import (
    DmaConfig,
    DmaConfigFlag,
)
from et_test_platform.drivers.dma.validation import (
    normalize_descriptor_handle,
    validate_channel_mask,
    validate_config_semantics,
    validate_descriptor_offset,
    validate_start_wait,
)


def test_config_semantics_rejects_unknown_stable_values() -> None:
    invalid_width = DmaConfig(
        channel=0,
        source_address=0x20000000,
        destination_address=0x20000100,
        transfer_count=1,
        source_width=3,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="source_width"):
        validate_config_semantics(invalid_width)

    invalid_handshake = DmaConfig(
        channel=0,
        source_address=0x20000000,
        destination_address=0x20000100,
        transfer_count=1,
        source_handshake_mode=2,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="source_handshake_mode"):
        validate_config_semantics(invalid_handshake)

    invalid_flags = DmaConfig(
        channel=0,
        source_address=0x20000000,
        destination_address=0x20000100,
        transfer_count=1,
        flags=DmaConfigFlag(1 << 8),
    )
    with pytest.raises(ValueError, match="unknown bits"):
        validate_config_semantics(invalid_flags)


def test_legacy_descriptor_handle_requires_explicit_integer() -> None:
    assert normalize_descriptor_handle(7) == 7

    with pytest.raises(ValueError, match="must be an integer"):
        normalize_descriptor_handle(True)
    with pytest.raises(ValueError, match="must be an integer"):
        normalize_descriptor_handle(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonzero uint32"):
        normalize_descriptor_handle(0)
    with pytest.raises(ValueError, match="fit uint32"):
        validate_descriptor_offset(0x1_0000_0000)


def test_wait_and_channel_mask_validation_preserve_existing_messages() -> None:
    with pytest.raises(ValueError, match="max_polls must be a nonzero uint32"):
        validate_start_wait(0, 0.001)
    with pytest.raises(ValueError, match="poll_interval_s must be positive"):
        validate_start_wait(1, 0)
    with pytest.raises(ValueError, match="exceeds 4 runtime channels"):
        validate_channel_mask(1 << 4, 4)
