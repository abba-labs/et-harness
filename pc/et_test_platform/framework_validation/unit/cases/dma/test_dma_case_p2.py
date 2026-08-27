# Framework Validation测试模块。
#
# 职责：验证test_dma_case_p2 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[6]
DMA_ROOT = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases" / "dma"
P2_SOURCE = DMA_ROOT / "test_dma_p2.py"
DEFERRED_SOURCE = DMA_ROOT / "deferred_features.py"
HANDSHAKE_SECTION = "# Peripheral Handshake"


def _handshake_source() -> str:
    source = P2_SOURCE.read_text(encoding="utf-8")
    start = source.index(HANDSHAKE_SECTION)
    return source[start:]


def _case_source(source: str, function_name: str) -> str:
    start = source.index(f"def {function_name}(")
    next_case = source.find("\n\n@pytest.mark.parametrize", start + 1)
    return source[start : next_case if next_case >= 0 else len(source)]


def test_p2_012_handshake_mode_is_split_from_polarity() -> None:
    handshake = _handshake_source()
    deferred = DEFERRED_SOURCE.read_text(encoding="utf-8")

    assert "DmaHandshakeMode.HARDWARE" in handshake
    assert "DmaHandshakeMode.SOFTWARE" in handshake
    assert "def test_dma_p2_012_handshake_mode(" in handshake
    assert "def _deferred_dma_p2_012_handshake_polarity(" in deferred
    assert "controllable polarity source" in deferred


def test_p2_012_handshake_mode_uses_managed_support_and_direct_irq_evidence() -> None:
    case = _case_source(_handshake_source(), "test_dma_p2_012_handshake_mode")

    for required in (
        "DmaIrqEvent.TRANSFER_DONE",
        "dma_uart_support_for",
        "DmaPeripheralDirection.TX",
        "configure_route(",
        "case_cleanup_scope(",
        "uart_peer.capture_wait(",
        "dma.wait_irq_count(",
        "dma.wait_channel_free(",
    ):
        assert required in case
    for forbidden in (
        "framework_communication",
        "target_capabilities",
        "resolve_uart_dma_route",
        "wait_for_irq_count",
        "wait_channel_free,",
        "execute_software_handshake_requests",
        "execute_peripheral_transfer",
        "_cleanup_all",
        "build_dma_peripheral_pair",
        "configure_dma_request(",
    ):
        assert forbidden not in case


def test_deferred_p2_plans_are_not_pytest_cases_or_skips() -> None:
    source = DEFERRED_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    planned = (
        "test_dma_p2_003_lli_fault_and_recovery",
        "test_dma_p2_007_error_irq_and_recovery",
        "test_dma_p2_012_handshake_polarity",
        "test_dma_p2_014_core_context_and_tcm",
    )
    for test_name in planned:
        deferred_name = f"_deferred_{test_name.removeprefix('test_')}"
        assert test_name not in functions
        assert deferred_name in functions
        deferred_source = ast.get_source_segment(source, functions[deferred_name])
        assert deferred_source is not None
        assert "pytest.skip" not in deferred_source
