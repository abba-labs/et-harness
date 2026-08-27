# Framework Validation测试模块。
#
# 职责：验证test_capability_v2_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from et_test_platform.core.errors import ConfigurationError
from et_test_platform.profiles.capabilities import (
    CapabilityEvidence,
    InterruptCapability,
    load_capability_audit,
    load_capability_profile,
    load_chip_capabilities,
    load_packaged_chip_capabilities,
)

TEST_DATA = Path(__file__).parents[2] / "test_data" / "capabilities_v2"
IP_DATA = TEST_DATA / "ip"


def test_v2_dma_profile_supports_natural_semantic_queries() -> None:
    profile = load_capability_profile(IP_DATA / "dma.yaml")

    assert profile.schema == "et-ip-capability/v2"
    assert profile.has_feature("linked_list", instance="dma0")
    assert profile.limit("max_block_transfers", instance="dma1") == 4095
    assert profile.options("transfer_types", instance="dma0") == (
        "memory_to_memory",
        "memory_to_peripheral",
        "peripheral_to_memory",
    )
    assert profile.parameter_members("fifo_depth", instance="dma0") == ("channel_0", "channel_1")
    assert profile.parameter("fifo_depth", instance="dma0", member="channel_1") == 32
    assert profile.interrupt("transfer_done", instance="dma1") == InterruptCapability(
        svd_name="DMA1_TFR", irqn=12
    )
    assert profile.identity("base_address", instance="dma0") == "0x40200000"


def test_v2_chip_index_routes_dma_uart_and_gpio_queries() -> None:
    capabilities = load_chip_capabilities(IP_DATA)

    assert capabilities.schema == "et-ip-capability/v2"
    assert capabilities.ip_ids == ("dma", "gpio", "uart")
    assert capabilities.has_feature("dma", "linked_list", instance="dma0")
    assert capabilities.limit("uart", "fifo_depth", instance="uart0") == 32
    assert capabilities.options("gpio", "interrupt_edges", instance="gpio0") == (
        "rising",
        "falling",
        "both",
    )
    assert (
        capabilities.parameter(
            "dma",
            "fifo_depth",
            instance="dma1",
            member="channel_0",
        )
        == 16
    )
    assert capabilities.interrupt("gpio", "combined", instance="gpio0").irqn == 40


def test_packaged_et6801_profile_is_queryable_by_chip_id() -> None:
    capabilities = load_packaged_chip_capabilities("et6801")

    assert capabilities.chip_id == "et6801"
    assert capabilities.instances("dma") == ("dma0", "dma1")
    assert "memory_to_memory" in capabilities.options(
        "dma",
        "transfer_type_and_flow_control",
        instance="dma0",
    )
    assert (
        capabilities.parameter(
            "dma",
            "max_block_size",
            instance="dma0",
            member="channel_0",
        )
        == 4095
    )
    assert (
        capabilities.interrupt(
            "dma",
            "transfer_done",
            instance="dma0",
        ).irqn
        == 6
    )


def test_packaged_chip_profile_fails_closed_for_unknown_chip() -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_packaged_chip_capabilities("et_unknown")
    with pytest.raises(ConfigurationError, match="must match"):
        load_packaged_chip_capabilities("../et6801")


def test_v2_evidence_is_indexed_and_instance_scoped() -> None:
    profile = load_capability_profile(IP_DATA / "dma.yaml")

    evidence = profile.evidence("feature", "linked_list", instance="dma1")
    assert evidence == (
        CapabilityEvidence(
            instance="dma1",
            kind="field",
            path="DMA1.CH0_CTL.LLP_SRC_EN",
            rule="field_presence",
        ),
    )
    assert profile.evidence(
        "parameter",
        "fifo_depth",
        instance="dma0",
        member="channel_1",
    ) == (
        CapabilityEvidence(
            instance="dma0",
            member="channel_1",
            kind="field",
            path="DMA0.COMP.CH1_FIFO_DEPTH",
            rule="readonly_component_parameter",
        ),
    )


def test_v2_audit_is_separate_from_runtime_profile() -> None:
    audit = load_capability_audit(TEST_DATA / "audit" / "dma.yaml")

    assert audit.chip_id == "et_contract_test"
    assert audit.ip_id == "dma"
    assert len(audit.unclassified) == 2
    assert audit.unclassified[0].reason == "no_semantic_mapping"


def test_v2_missing_capability_evidence_fails_closed(tmp_path: Path) -> None:
    raw = yaml.safe_load((IP_DATA / "dma.yaml").read_text(encoding="utf-8"))
    del raw["evidence"]["dma.feature.linked_list"]
    profile_path = tmp_path / "dma.yaml"
    profile_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ConfigurationError, match="evidence: missing"):
        load_capability_profile(profile_path)


def test_v2_evidence_must_cover_every_value_instance(tmp_path: Path) -> None:
    raw = yaml.safe_load((IP_DATA / "dma.yaml").read_text(encoding="utf-8"))
    raw["evidence"]["dma.limit.max_block_transfers"].pop()
    profile_path = tmp_path / "dma.yaml"
    profile_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ConfigurationError, match="missing instances dma1"):
        load_capability_profile(profile_path)


def test_v2_parameter_evidence_must_cover_every_member(tmp_path: Path) -> None:
    raw = yaml.safe_load((IP_DATA / "dma.yaml").read_text(encoding="utf-8"))
    raw["evidence"]["dma.parameter.fifo_depth"].pop()
    profile_path = tmp_path / "dma.yaml"
    profile_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ConfigurationError, match="missing members"):
        load_capability_profile(profile_path)


def test_v2_invalid_irqn_fails_closed(tmp_path: Path) -> None:
    raw = yaml.safe_load((IP_DATA / "dma.yaml").read_text(encoding="utf-8"))
    raw["capabilities"]["interrupts"]["transfer_done"]["dma0"]["irqn"] = -1
    profile_path = tmp_path / "dma.yaml"
    profile_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ConfigurationError, match="non-negative integer"):
        load_capability_profile(profile_path)


def test_chip_directory_must_not_mix_v1_and_v2(tmp_path: Path) -> None:
    v1_path = TEST_DATA.parent / "capabilities" / "dma.yaml"
    v1_text = v1_path.read_text(encoding="utf-8").replace("chip: et6801", "chip: et_contract_test")
    (tmp_path / "dma.yaml").write_text(
        v1_text,
        encoding="utf-8",
        newline="\n",
    )
    (tmp_path / "uart.yaml").write_bytes((IP_DATA / "uart.yaml").read_bytes())

    with pytest.raises(ConfigurationError, match="mixes schemas"):
        load_chip_capabilities(tmp_path)
