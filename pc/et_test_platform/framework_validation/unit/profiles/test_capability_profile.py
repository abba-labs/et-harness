# Framework Validation测试模块。
#
# 职责：验证test_capability_profile 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

import pytest

from et_test_platform.core.errors import (
    CapabilityLookupError,
    ConfigurationError,
    UnsupportedCapability,
)
from et_test_platform.profiles.capabilities import (
    load_capability_profile,
    load_chip_capabilities,
)

TEST_DATA = Path(__file__).parents[2] / "test_data" / "capabilities" / "dma.yaml"


def test_load_and_query_flat_capability_index() -> None:
    profile = load_capability_profile(TEST_DATA)

    assert profile.chip_id == "et6801"
    assert profile.ip_id == "dma"
    assert profile.instances == ("dma0", "dma1")
    assert profile.supporting_instances("dma.feature.transfer.memory_to_memory") == ("dma0", "dma1")
    assert profile.supports(
        "dma.feature.interrupt.transfer_done",
        instance="dma1",
    )
    assert (
        profile.value(
            "dma.limit.max_block_transfers",
            instance="dma0",
        )
        == 4095
    )
    assert profile.value(
        "dma.option.transfer_width_bits",
        instance="dma0",
    ) == (8, 16, 32)
    assert (
        profile.value(
            "dma.identity.component_id",
            instance="dma1",
        )
        == "0x44571110"
    )


def test_missing_feature_is_unsupported_without_scanning() -> None:
    profile = load_capability_profile(TEST_DATA)

    assert not profile.supports(
        "dma.feature.transfer.linked_list",
        instance="dma0",
    )
    with pytest.raises(UnsupportedCapability, match="linked_list"):
        profile.require(
            "dma.feature.transfer.linked_list",
            instance="dma0",
        )


def test_manual_set_and_remove_are_merged_once(tmp_path) -> None:
    profile_path = tmp_path / "dma.yaml"
    text = TEST_DATA.read_text(encoding="utf-8")
    text = text.replace(
        "  set: {}\n  remove: []",
        """
  set:
    dma.feature.transfer.vendor_extension: [dma1]
    dma.limit.channel_count:
      dma0: 4
      dma1: 6
  remove:
    - dma.feature.interrupt.error
""".rstrip(),
    )
    profile_path.write_text(text, encoding="utf-8")

    profile = load_capability_profile(profile_path)

    assert profile.supports(
        "dma.feature.transfer.vendor_extension",
        instance="dma1",
    )
    assert not profile.supports(
        "dma.feature.transfer.vendor_extension",
        instance="dma0",
    )
    assert profile.value("dma.limit.channel_count", instance="dma0") == 4
    assert not profile.supports(
        "dma.feature.interrupt.error",
        instance="dma0",
    )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            "dma.feature.interrupt.error: [dma0, dma1]",
            "uart.feature.interrupt.error: [dma0, dma1]",
            "does not belong to IP",
        ),
        (
            "dma.feature.interrupt.error: [dma0, dma1]",
            "dma.feature.interrupt.error: [dma0, dma0]",
            "repeats instance",
        ),
        (
            "dma.limit.channel_count:\n      dma0: 8\n      dma1: 8",
            "dma.limit.channel_count:\n      dma0: true\n      dma1: 8",
            "must be numeric",
        ),
    ],
)
def test_invalid_capability_yaml_fails_closed(
    tmp_path,
    old: str,
    new: str,
    message: str,
) -> None:
    profile_path = tmp_path / "invalid.yaml"
    profile_path.write_text(
        TEST_DATA.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=message):
        load_capability_profile(profile_path)


def test_query_rejects_wrong_kind_and_unknown_instance() -> None:
    profile = load_capability_profile(TEST_DATA)

    with pytest.raises(CapabilityLookupError, match="use supports"):
        profile.value(
            "dma.feature.interrupt.error",
            instance="dma0",
        )
    with pytest.raises(CapabilityLookupError, match="unknown dma instance"):
        profile.supports(
            "dma.feature.interrupt.error",
            instance="dma8",
        )
    with pytest.raises(CapabilityLookupError, match="expected 'feature'"):
        profile.supporting_instances("dma.limit.channel_count")
    with pytest.raises(CapabilityLookupError, match="does not belong to IP"):
        profile.value("uart.limit.channel_count", instance="dma0")


def test_chip_index_loads_ip_files_once_and_routes_by_capability_id() -> None:
    capabilities = load_chip_capabilities(TEST_DATA.parent)

    assert capabilities.chip_id == "et6801"
    assert capabilities.ip_ids == ("dma",)
    assert capabilities.instances("dma") == ("dma0", "dma1")
    assert capabilities.supports(
        "dma.feature.transfer.memory_to_memory",
        instance="dma0",
    )
    assert (
        capabilities.value(
            "dma.limit.channel_count",
            instance="dma1",
        )
        == 8
    )

    with pytest.raises(CapabilityLookupError, match="no capability profile"):
        capabilities.instances("uart")
