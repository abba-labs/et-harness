# Framework Validation测试模块。
#
# 职责：验证test_formal_case_v2_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parents[6]
UART_P2_FILE = ROOT / "pc/et_test_platform/test_cases/uart/test_uart_p2.py"
UART_DMA_CASES = (
    "test_uart_p2_001_dma_tx",
    "test_uart_p2_002_dma_rx",
    "test_uart_p2_003_dma_full_duplex",
)
FIXTURES = ROOT / "pc/et_test_platform/test_cases/uart/conftest.py"
DMA_LLI_FILES = (
    ROOT / "pc/et_test_platform/test_cases/dma/test_dma_p1.py",
    ROOT / "pc/et_test_platform/test_cases/dma/test_dma_p2.py",
)
DMA_PEER = ROOT / "pc/et_test_platform/test_cases/dma/dma_peer.py"
FORMAL_CASE_ROOT = ROOT / "pc/et_test_platform/test_cases"
CASE_DOCUMENT_ROOT = ROOT / "test_case_doc"
CODE_CASE_ID = re.compile(r"^test_([a-z0-9]+)_p([0-3])_(\d{3})_")
DOCUMENT_CASE_ID = re.compile(r"(?m)^#{1,6}\s+([A-Z0-9]+)-P([0-3])-(\d{3})\b")


def _function_source(source: str, function_name: str) -> tuple[str, ast.FunctionDef]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    segment = ast.get_source_segment(source, function)
    if segment is None:
        raise AssertionError(f"cannot extract {function_name}")
    return segment, function


def test_uart_dma_cases_use_managed_resolve_and_execute_sysctrl_v2_directly() -> None:
    fixtures = FIXTURES.read_text(encoding="utf-8")
    for fixture_name in (
        "uart_dma_tx_support",
        "uart_dma_rx_support",
        "uart_dma_full_duplex_support",
    ):
        assert f"def {fixture_name}(" in fixtures
    assert "resolve_uart_dma_route(" in fixtures

    module_source = UART_P2_FILE.read_text(encoding="utf-8")
    for function_name in UART_DMA_CASES:
        source, function = _function_source(module_source, function_name)
        assert "resolve_uart_dma_route" not in source
        assert "DmaRequestRoute" in source
        assert "configure_route(" in source
        for forbidden in (
            "configure_dma_request(",
            "DmaEndpoint",
            "UartDmaEndpoint",
            "dma_endpoint_get(",
            "_run_dma_",
        ):
            assert forbidden not in source, f"{function_name}: {forbidden}"
        calls = {
            node.func.attr
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert {"configure_route", "configure", "start"} <= calls or {
            "configure_route",
            "configure",
            "start_channels",
        } <= calls


def test_dma_cross_ip_adapter_is_removed_from_formal_case_layer() -> None:
    assert not DMA_PEER.exists()


def test_formal_dma_lli_cases_use_descriptor_address_v2() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DMA_LLI_FILES)
    assert "lli_descriptor_init_v2(" in combined
    assert "lli_descriptor_init(" not in combined
    assert "descriptor.handle" not in combined


# Guard stable IDs without adding a runtime registry or migration layer.
def test_formal_case_ids_are_unique_in_code_and_feature_documents() -> None:

    code_locations: list[tuple[tuple[str, str, str], str]] = []
    for path in FORMAL_CASE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            match = CODE_CASE_ID.match(node.name)
            if match is not None:
                code_locations.append((match.groups(), f"{path.relative_to(ROOT)}:{node.lineno}"))

    document_locations: list[tuple[tuple[str, str, str], str]] = []
    for path in CASE_DOCUMENT_ROOT.glob("*.md"):
        source = path.read_text(encoding="utf-8")
        for match in DOCUMENT_CASE_ID.finditer(source):
            case_id = (match.group(1).lower(), match.group(2), match.group(3))
            line = source.count("\n", 0, match.start()) + 1
            document_locations.append((case_id, f"{path.relative_to(ROOT)}:{line}"))

    code_counts = Counter(case_id for case_id, _ in code_locations)
    document_counts = Counter(case_id for case_id, _ in document_locations)
    duplicate_code = {
        case_id: [location for current, location in code_locations if current == case_id]
        for case_id, count in code_counts.items()
        if count > 1
    }
    duplicate_documents = {
        case_id: [location for current, location in document_locations if current == case_id]
        for case_id, count in document_counts.items()
        if count > 1
    }

    assert duplicate_code == {}, f"duplicate formal Case IDs in code: {duplicate_code}"
    assert duplicate_documents == {}, (
        f"duplicate formal Case IDs in Feature documents: {duplicate_documents}"
    )
