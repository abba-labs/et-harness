# Framework Validation测试模块。
#
# 职责：验证test_dma_handshake_support_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[6]
P2_SOURCE_PATH = ROOT / "pc/et_test_platform/test_cases/dma/test_dma_p2.py"
HANDSHAKE_SECTION = "# Peripheral Handshake"


def _handshake_source() -> str:
    source = P2_SOURCE_PATH.read_text(encoding="utf-8")
    start = source.index(HANDSHAKE_SECTION)
    return source[start:]


def _case_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    segment = ast.get_source_segment(source, function)
    if segment is None:
        raise AssertionError(f"cannot extract {function_name}")
    return segment


def test_dma_handshake_cases_remove_case_local_driver_and_wait_plumbing() -> None:
    source = _handshake_source()
    for forbidden in (
        "def _drivers(",
        "DmaDriver(",
        "ResourceDriver(",
        "SysctrlDriver(",
        "wait_capture(",
        "wait_channel_free,",
        "wait_for_irq_count(",
        "DMA_TRANSFER_MEMORY_TO_PERIPHERAL =",
        "DMA_TRANSFER_PERIPHERAL_TO_MEMORY =",
        "DMA_TRANSFER_PERIPHERAL_TO_PERIPHERAL =",
        "DMA_ADDRESS_FIXED =",
    ):
        assert forbidden not in source, forbidden
    assert "dma.wait_channel_free(" in source
    assert "dma.wait_irq_count(" in source
    assert "uart_peer.capture_wait(" in source


def test_single_route_handshake_cases_use_managed_route_support() -> None:
    source = _handshake_source()
    expectations = {
        "test_dma_p2_008_memory_to_peripheral": (
            "DmaPeripheralDirection.TX",
            "DmaTransferType.MEMORY_TO_PERIPHERAL",
        ),
        "test_dma_p2_009_peripheral_to_memory": (
            "DmaPeripheralDirection.RX",
            "DmaTransferType.PERIPHERAL_TO_MEMORY",
        ),
        "test_dma_p2_011_software_handshake": (
            "DmaPeripheralDirection.TX",
            "DmaTransferType.MEMORY_TO_PERIPHERAL",
        ),
        "test_dma_p2_012_handshake_mode": (
            "DmaPeripheralDirection.TX",
            "DmaTransferType.MEMORY_TO_PERIPHERAL",
        ),
    }
    for function_name, (direction, transfer_type) in expectations.items():
        case = _case_source(source, function_name)
        assert "dma_uart_support_for" in case
        assert direction in case
        assert transfer_type in case
        for forbidden in (
            "framework_communication",
            "target_capabilities",
            "resolve_uart_dma_route(",
            ".capabilities_get()",
        ):
            assert forbidden not in case, f"{function_name}: {forbidden}"


def test_unique_p2p_case_reuses_base_support_without_new_route_framework() -> None:
    source = _handshake_source()
    case = _case_source(source, "test_dma_p2_010_peripheral_to_peripheral")
    assert "dma_support_for(instance_id)" in case
    assert "sysctrl = sysctrl_driver" in case
    assert case.count("resolve_uart_dma_route(") == 2
    assert "DmaTransferType.PERIPHERAL_TO_PERIPHERAL" in case
    assert "DmaAddressMode.FIXED" in case
    assert "uart_peer_handle.exchange(payload, timeout_s=2.0)" in case
    assert "dma.wait_channel_free(0, timeout_s=2.0)" in case


def test_handshake_cleanup_and_cross_ip_actions_remain_visible_in_cases() -> None:
    source = _handshake_source()
    assert source.count("with case_cleanup_scope(cleanup_actions):") == 5
    for action in (
        "sysctrl.configure_route(",
        ".dma_enable_set(True)",
        "dma.controller_enable()",
        "dma.configure(",
        "dma.start(0)",
    ):
        assert action in source
