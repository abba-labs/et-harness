# Framework Validation测试模块。
#
# 职责：验证test_dma_case_support_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[6]
DMA_ROOT = ROOT / "pc" / "et_test_platform" / "test_cases" / "dma"

PURE_SUPPORT_CASES = (
    "test_dma_p0.py",
    "test_dma_p1.py",
    "test_dma_p3.py",
)


def test_migrated_pure_dma_cases_use_support_not_target_plumbing() -> None:
    for filename in PURE_SUPPORT_CASES:
        source = (DMA_ROOT / filename).read_text(encoding="utf-8")
        assert "DmaSupportFactory" in source, filename
        assert "dma_support_for" in source, filename
        for forbidden in (
            "def _drivers(",
            "FrameworkDriver",
            "framework_communication",
            "ResourceDriver(target",
            "DmaDriver(target",
            ".target_client",
        ):
            assert forbidden not in source, f"{filename}: {forbidden}"


def test_dma_interrupt_cases_use_managed_support_not_target_plumbing() -> None:
    p1 = (DMA_ROOT / "test_dma_p1.py").read_text(encoding="utf-8")
    p2 = (DMA_ROOT / "test_dma_p2.py").read_text(encoding="utf-8")
    interrupt_start = p2.index("def test_dma_p2_004_combined_irq(")
    interrupt_end = p2.index("# NORMAL / ACC Access View", interrupt_start)
    p2_interrupts = p2[interrupt_start:interrupt_end]
    combined = p1 + "\n" + p2_interrupts

    assert not (DMA_ROOT / "test_interrupts.py").exists()
    for case_name in (
        "test_dma_p1_004_transfer_complete_irq",
        "test_dma_p1_005_block_complete_irq",
        "test_dma_p1_006_interrupt_mask_raw_clear",
    ):
        assert f"def {case_name}(" in p1
        assert f"def {case_name}(" not in p2_interrupts
    for case_name in (
        "test_dma_p2_004_combined_irq",
        "test_dma_p2_005_source_transaction_irq",
        "test_dma_p2_006_destination_transaction_irq",
    ):
        assert f"def {case_name}(" in p2_interrupts
        assert f"def {case_name}(" not in p1

    assert "DmaSupportFactory" in combined
    assert "DmaUartSupportFactory" in p2_interrupts
    assert "dma_support_for" in combined
    assert "dma_uart_support_for" in p2_interrupts
    for forbidden in (
        "def _drivers(",
        "FrameworkDriver",
        "framework_communication",
        "DmaPeripheralPairConfig",
        "resolve_uart_dma_route(",
        "ResourceDriver(target",
        "DmaDriver(target",
        "SysctrlDriver(target",
        ".target_client",
        "wait_capture(",
        "wait_channel_free,",
        "wait_for_irq_count(",
    ):
        assert forbidden not in combined, forbidden
    assert "dma.wait_channel_free(" in combined
    assert "dma.wait_irq_count(" in combined
    assert "uart_peer.capture_wait(" in p2_interrupts
    assert "DmaUpdateMode.LINKED_LIST" in p1
    assert "DmaTransferType.PERIPHERAL_TO_MEMORY" in p2_interrupts
    assert "DmaTransferType.MEMORY_TO_PERIPHERAL" in p2_interrupts


def test_dma_handshake_cases_are_consolidated_in_p2() -> None:
    p2 = (DMA_ROOT / "test_dma_p2.py").read_text(encoding="utf-8")

    assert not (DMA_ROOT / "test_handshake.py").exists()
    for case_name in (
        "test_dma_p2_008_memory_to_peripheral",
        "test_dma_p2_009_peripheral_to_memory",
        "test_dma_p2_010_peripheral_to_peripheral",
        "test_dma_p2_011_software_handshake",
        "test_dma_p2_012_handshake_mode",
    ):
        assert f"def {case_name}(" in p2

    assert "DmaPeripheralDirection" in p2
    assert "chip_execution_mappings.et6801" not in p2
    assert "DmaUartSupportFactory" in p2
    assert "dma_uart_support_for" in p2
    assert "require_dma_transfer_capability(" in p2
    assert "resolve_uart_dma_route(" in p2
    assert "uart_peer_handle.exchange(" in p2
    for forbidden in (
        "def _run_dma_",
        "DmaDriver(",
        "ResourceDriver(",
        "SysctrlDriver(target",
        ".target_client",
    ):
        assert forbidden not in p2, forbidden


def test_migrated_dma_runtime_waits_call_driver_directly() -> None:
    sources = {
        filename: (DMA_ROOT / filename).read_text(encoding="utf-8")
        for filename in (
            "test_dma_p0.py",
            "test_dma_p1.py",
            "test_dma_p2.py",
            "test_dma_p3.py",
        )
    }
    for filename, source in sources.items():
        assert "wait_channel_free," not in source, filename
        assert "wait_for_irq_count" not in source, filename
        assert "dma.wait_" in source, filename

    p0 = sources["test_dma_p0.py"]
    p1 = sources["test_dma_p1.py"]
    p2 = sources["test_dma_p2.py"]
    p3 = sources["test_dma_p3.py"]
    assert "DmaAccessView.NORMAL" in p0
    assert "DmaAccessView.ACC" in p2
    assert "DmaUpdateMode.LINKED_LIST" in p2
    assert "DmaUpdateMode.CONTIGUOUS" in p2
    assert "DmaUpdateMode.RELOAD" in p1
    assert "DmaAddressMode.FIXED" in p1
    assert "DMA_CONFIG_SOURCE_GATHER" in p1
    assert "DMA_CONFIG_DESTINATION_SCATTER" in p1
    for token in ("DmaWidth", "DmaBurst", "DmaFifoMode"):
        assert token in p0 + p1 + p2 + p3


def test_dma_formal_cases_do_not_hardcode_et6801_instance_channel_or_transfer_scale() -> None:
    sources = "\n".join(
        (DMA_ROOT / filename).read_text(encoding="utf-8")
        for filename in (
            "test_dma_p0.py",
            "test_dma_p1.py",
            "test_dma_p2.py",
            "test_dma_p3.py",
        )
    )
    for forbidden in (
        '@pytest.mark.parametrize("instance_id", [0, 1])',
        '@pytest.mark.parametrize("channel", range(8))',
        '@pytest.mark.parametrize("channel", [0, 7])',
        'assert instances == ("dma0", "dma1")',
        "dynamic.channel_count == 8",
        "dynamic.max_transfer_count == 4095",
        "for instance_id in (0, 1)",
    ):
        assert forbidden not in sources


def test_dma_all_channels_preserves_sequential_wait_semantics() -> None:
    source = (DMA_ROOT / "test_dma_p1.py").read_text(encoding="utf-8")
    start = source.index("def test_dma_p1_001_all_channels_concurrent(")
    end = source.index(
        "\n\n# =============================================================================",
        start + 1,
    )
    case = source[start:end]

    assert "dma.start_channels(channel_mask)" in case
    assert (
        "for channel in range(dynamic.channel_count):\n            dma.wait_channel_free(channel)"
        in case
    )
    assert "dma.wait_channels_free(" not in case
    assert case.index("dma.start_channels(channel_mask)") < case.index(
        "dma.wait_channel_free(channel)"
    )
    assert case.index("dma.wait_channel_free(channel)") < case.index(
        "actual = [resource.read(item) for item in destinations]"
    )
    assert "statuses = [dma.channel_status(channel)" in case
    assert "all_channels_free = all(status.is_free for status in statuses)" in case
    assert "assert all_channels_free" in case


# 边界IRQ Case只能展开运行时首末通道，不能退化为固定0/7或全通道笛卡尔积。
def test_dma_boundary_irq_case_uses_runtime_first_last_channel_matrix() -> None:
    fixtures = (DMA_ROOT / "conftest.py").read_text(encoding="utf-8")
    p1 = (DMA_ROOT / "test_dma_p1.py").read_text(encoding="utf-8")
    start = p1.index("def test_dma_p1_005_block_complete_irq(")
    end = p1.index("\n\n# 测试 Feature：", start + 1)
    case = p1[start:end]

    assert '@pytest.fixture(params=("first", "last")' in fixtures
    assert "def dma_boundary_channel(" in fixtures
    assert "channel_count - 1" in fixtures
    assert "dma_boundary_channel: int" in case
    assert "channel = dma_boundary_channel" in case
    assert "Channel 0/7" not in p1


def test_crg_specific_dma_case_uses_explicit_crg_fixture_not_generic_support() -> None:
    source = (DMA_ROOT / "test_dma_p2.py").read_text(encoding="utf-8")
    assert "crg_driver: CrgDriver" in source
    assert "support.resource, support.dma, crg_driver" in source
    assert "CrgDriver(" not in source
