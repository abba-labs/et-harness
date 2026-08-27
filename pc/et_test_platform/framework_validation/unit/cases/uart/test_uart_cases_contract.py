# Framework Validation测试模块。
#
# 职责：验证test_uart_cases_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[6]
UART_ROOT = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases" / "uart"
FIXTURES_SOURCE = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases" / "uart" / "conftest.py"

EXPECTED_COLLECTED = {
    "test_uart_p0.py": 4,
    "test_uart_p1.py": 17,
    "test_uart_p2.py": 9,
    "test_uart_p3.py": 3,
}
EXPECTED_DEFERRED = {"deferred_features.py": 7}
DMA_SUPPORT_FIXTURES = {
    "test_uart_p2_001_dma_tx": "uart_dma_tx_support",
    "test_uart_p2_002_dma_rx": "uart_dma_rx_support",
    "test_uart_p2_003_dma_full_duplex": "uart_dma_full_duplex_support",
}


def _case_functions(path: Path) -> tuple[ast.FunctionDef, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and (node.name.startswith("test_uart_") or node.name.startswith("_deferred_uart_"))
    )


def _read(*filenames: str) -> str:
    return "\n".join((UART_ROOT / filename).read_text(encoding="utf-8") for filename in filenames)


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


def _fixture_source(source: str, function_name: str) -> str:
    start = source.index(f"def {function_name}(")
    next_fixture = source.find("\n\n@pytest.fixture\ndef ", start + 1)
    next_function = source.find("\n\ndef ", start + 1)
    candidates = [index for index in (next_fixture, next_function) if index >= 0]
    end = min(candidates) if candidates else len(source)
    return source[start:end]


def _executable_source(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _leading_comment(path: Path, function: ast.FunctionDef) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    anchor = (
        min(
            (decorator.lineno for decorator in function.decorator_list),
            default=function.lineno,
        )
        - 1
    )
    index = anchor - 1
    block: list[str] = []
    while index >= 0 and (not lines[index].strip() or lines[index].lstrip().startswith("#")):
        block.append(lines[index])
        index -= 1
    return "\n".join(reversed(block))


def _has_numbered_comment_items(block: str, heading: str, next_heading: str | None) -> bool:
    start = block.find(heading)
    if start < 0:
        return False
    end = block.find(next_heading, start + len(heading)) if next_heading else len(block)
    section = block[start : end if end >= 0 else len(block)]
    return re.search(r"(?m)^#\s+1\.\s+\S", section) is not None


def test_uart_case_files_have_final_collection_and_deferred_counts() -> None:
    legacy_files = (
        "test_polling.py",
        "test_interrupts.py",
        "test_dma_tx.py",
        "test_dma_rx.py",
        "test_dma_full_duplex.py",
    )
    assert all(not (UART_ROOT / filename).exists() for filename in legacy_files)

    for filename, expected in EXPECTED_COLLECTED.items():
        path = UART_ROOT / filename
        assert path.is_file(), f"missing UART P-level Case file: {path}"
        collected = [node for node in _case_functions(path) if node.name.startswith("test_")]
        assert len(collected) == expected, (filename, [node.name for node in collected])

    for filename, expected in EXPECTED_DEFERRED.items():
        path = UART_ROOT / filename
        assert path.is_file(), f"missing UART deferred Feature file: {path}"
        deferred = [node for node in _case_functions(path) if node.name.startswith("_deferred_")]
        assert len(deferred) == expected, (filename, [node.name for node in deferred])


def test_uart_case_functions_use_fixture_handles_and_codex_comment_structure() -> None:
    violations: list[str] = []
    for filename in EXPECTED_COLLECTED:
        path = UART_ROOT / filename
        for function in _case_functions(path):
            if not function.name.startswith("test_"):
                continue
            location = f"{path.relative_to(PROJECT_ROOT)}:{function.lineno}"
            parameters = {argument.arg for argument in function.args.args}
            support_fixture = DMA_SUPPORT_FIXTURES.get(function.name)
            if support_fixture is not None:
                if support_fixture not in parameters:
                    violations.append(f"{location}: missing {support_fixture} fixture")
            elif "uart_dut_handle" not in parameters:
                violations.append(f"{location}: missing uart_dut_handle fixture")

            comment = _leading_comment(path, function)
            for section in ("测试 Feature：", "测试方法：", "通过条件："):
                if section not in comment:
                    violations.append(f"{location}: missing {section}")
            if not _has_numbered_comment_items(comment, "测试方法：", "通过条件："):
                violations.append(f"{location}: test methods are not numbered")
            if not _has_numbered_comment_items(comment, "通过条件：", None):
                violations.append(f"{location}: pass conditions are not numbered")
    assert violations == [], "UART Case contract violations:\n" + "\n".join(violations)


def test_uart_case_executable_source_has_no_chip_or_instance_shortcuts() -> None:
    forbidden = (
        "UartDriver(",
        "TargetClient(",
        "instance_id=0",
        "instance_id=1",
        "instance_id=2",
        "UART0",
        "UART1",
        "UART2",
        "J25",
        "J30",
        "ET6801",
    )
    violations: list[str] = []
    for filename in EXPECTED_COLLECTED:
        source = _executable_source(UART_ROOT / filename)
        for token in forbidden:
            if token in source:
                violations.append(f"{filename}: forbidden executable token {token!r}")
    assert violations == [], "UART Case executable shortcuts:\n" + "\n".join(violations)


def test_uart_reviewed_driver_extensions_remain_explicit_in_level_cases() -> None:
    p1 = _read("test_uart_p1.py")
    for token in (
        "busy_detect_trigger(",
        "busy_observed",
        "interrupt_observed",
        "trigger_count",
        "cleared",
        "recovered",
    ):
        assert token in p1

    p3 = _read("test_uart_p3.py")
    shadow = _case_source(p3, "test_uart_p3_007_shadow_fifo_configuration")
    direct = _case_source(p3, "test_uart_p3_009_direct_fifo_access")
    assert "shadow_fifo_config(" in shadow
    assert "test_fifo_access_set(" not in shadow
    assert "test_fifo_access_set(" in direct
    assert "test_fifo_tx_read(" in direct
    assert "test_fifo_rx_write(" in direct
    assert "UartFeature.SHADOW" in shadow
    assert "UartFeature.FIFO_ACCESS" in direct
    assert "UART_CPR_" not in shadow + direct
    assert "component_parameter" not in shadow + direct


def test_uart_address_match_is_separate_from_address_irq() -> None:
    p2 = _read("test_uart_p2.py")
    match_source = _case_source(p2, "test_uart_p2_005_nine_bit_hardware_address_match")
    irq_source = _case_source(p2, "test_uart_p2_010_nine_bit_address_irq")
    assert "irq_config(" not in match_source
    assert "irq_state_get(" not in match_source
    assert "UartIrqSource.NINE_BIT_ADDRESS" in irq_source
    assert "irq_config(" in irq_source
    assert "irq_state_get(" in irq_source
    assert "fault_delta" in irq_source
    assert "source_observed" in irq_source
    assert "_require_irq_event(" not in irq_source


def test_uart_dma_full_duplex_is_atomic_and_two_sided() -> None:
    source = _case_source(_read("test_uart_p2.py"), "test_uart_p2_003_dma_full_duplex")
    assert "uart_dma_full_duplex_support" in source
    assert "resolve_uart_dma_route(" not in source
    assert "DmaFeature.ATOMIC_CHANNEL_MASK_START" not in source
    assert source.count("sysctrl.configure_route(") == 2
    assert "dma.start_channels(channel_mask)" in source
    assert "channel_mask = (1 << tx_channel) | (1 << rx_channel)" in source
    assert "DmaTransferType.MEMORY_TO_PERIPHERAL" in source
    assert "DmaTransferType.PERIPHERAL_TO_MEMORY" in source
    assert "destination_interface=tx_route.interface" in source
    assert "source_interface=rx_route.interface" in source
    assert "dma.wait_channels_free((tx_channel, rx_channel))" in source
    assert "dma.wait_irq()" in source
    assert "uart_peer.capture_wait(len(tx_payload))" in source
    assert "guards_intact" in source
    assert "exact overlap" not in source.lower()


def test_uart_dma_cases_use_managed_support_and_bench_framing() -> None:
    module_source = _read("test_uart_p2.py")
    for function_name, fixture_name in DMA_SUPPORT_FIXTURES.items():
        source = _case_source(module_source, function_name)
        assert fixture_name in source
        assert "FrameworkDriver" not in source
        assert "ChipCapabilities" not in source
        assert "DmaExecutionSupport" not in source
        assert "resolve_uart_dma_route(" not in source
        assert "ResourceDriver(" not in source
        assert "DmaDriver(" not in source
        assert "SysctrlDriver(" not in source
        assert "pair.baudrate" in source
        assert "pair.data_bits" in source
        assert "pair.parity" in source
        assert "pair.stop_bits" in source


def test_uart_dma_cases_reset_resources_during_cleanup() -> None:
    module_source = _read("test_uart_p2.py")
    source = "\n".join(_case_source(module_source, name) for name in DMA_SUPPORT_FIXTURES)
    assert source.count("case_cleanup_scope(cleanup_actions)") == 3
    assert "with resource.pool_mode():" not in source
    assert source.count("resource.reset()") == 3
    assert source.count('("Resource pool reset", resource.reset)') == 3
    assert source.count("release_dma_request") >= 4
    assert "_cleanup_full_duplex(" not in source
    assert "_cleanup_dma(" not in source


def test_uart_dma_managed_support_owns_environment_facts_only() -> None:
    fixtures = FIXTURES_SOURCE.read_text(encoding="utf-8")
    resolver = _fixture_source(fixtures, "_resolve_uart_dma_support")
    assert "_require_uart_feature(" in resolver
    assert "resolve_uart_dma_route(" in resolver
    assert "return UartDmaSupport(" in resolver

    tx_support = _fixture_source(fixtures, "uart_dma_tx_support")
    rx_support = _fixture_source(fixtures, "uart_dma_rx_support")
    full_support = _fixture_source(fixtures, "uart_dma_full_duplex_support")
    assert "DmaPeripheralDirection.TX" in tx_support
    assert "DmaPeripheralDirection.RX" in rx_support
    for required in (
        "UartFeature.TX_DMA",
        "UartFeature.RX_DMA",
        "resolve_uart_dma_route(",
        "DmaFeature.ATOMIC_CHANNEL_MASK_START",
        "return UartDmaFullDuplexSupport(",
    ):
        assert required in full_support

    combined = resolver + tx_support + rx_support + full_support
    for forbidden in (
        ".initialize(",
        ".dma_enable_set(",
        ".configure_route(",
        ".controller_enable(",
        ".configure(",
        ".find_free_channel(",
        ".capture_start(",
        ".start(",
        ".reset(",
    ):
        assert forbidden not in combined


def test_uart_required_feature_gates_precede_cleanup_scopes() -> None:
    p2 = _read("test_uart_p2.py")
    expectations = {
        "test_uart_p2_004_nine_bit_software_transfer": "UartFeature.NINE_BIT",
        "test_uart_p2_005_nine_bit_hardware_address_match": "UartFeature.NINE_BIT",
        "test_uart_p2_010_nine_bit_address_irq": "UartFeature.NINE_BIT",
        "test_uart_p2_008_reset_recovery": "UartFeature.SOFTWARE_RESET",
    }
    for function_name, feature in expectations.items():
        function_source = _case_source(p2, function_name)
        assert feature in function_source
        assert ".capabilities_get()" in function_source
        assert "skip_by_runtime_feature:" in function_source
        cleanup_index = function_source.find("with case_cleanup_scope(cleanup_actions):")
        if cleanup_index >= 0:
            assert "pytest.skip" not in function_source[cleanup_index:]


def test_uart_flow_and_modem_cases_use_internal_loopback_contracts() -> None:
    source = _read("test_uart_p2.py")
    for case_name in (
        "test_uart_p2_006_automatic_flow_control",
        "test_uart_p2_007_modem_internal_loopback",
    ):
        assert f"def {case_name}(" in source
    assert "fifo_config(enabled=True" in source
    assert "flow_control_set(enabled=True" in source
    assert "loopback_set(True)" in source
    assert source.count("write_partial(") >= 2
    assert "modem_control_set(rts=False, dtr=False)" in source
    assert "modem_control_set(rts=True, dtr=True)" in source
    assert "modem_status_get()" in source
    assert "MODEM_INPUT_CTS_MASK" in source
    assert "MODEM_INPUT_DSR_MASK" in source
    assert 'unsupported_inputs=["RI", "DCD"]' in source


def test_uart_irq_cases_assert_source_and_fault_facts_directly() -> None:
    source = _read("test_uart_p1.py")
    for case_name in (
        "test_uart_p1_002_rx_data_available_irq",
        "test_uart_p1_003_tx_empty_irq",
        "test_uart_p1_004_rx_fifo_threshold_irq",
        "test_uart_p1_005_tx_fifo_threshold_irq",
        "test_uart_p1_006_character_timeout_irq",
        "test_uart_p1_011_interrupt_mask_enable_clear",
    ):
        case_source = _case_source(source, case_name)
        assert "fault_delta" in case_source, case_name
        assert "source_observed" in case_source, case_name
        assert "_require_irq_event(" not in case_source, case_name

    for case_name, flag in (
        ("test_uart_p1_007_parity_error_detection", "UartErrorFlag.PARITY"),
        ("test_uart_p1_008_framing_error_detection", "UartErrorFlag.FRAMING"),
        ("test_uart_p1_009_overrun_error_detection", "UartErrorFlag.OVERRUN"),
        ("test_uart_p1_010_break_send_and_detect", "UartErrorFlag.BREAK"),
    ):
        case_source = _case_source(source, case_name)
        assert flag in case_source
        assert "fault_delta" in case_source
        assert "source_observed" in case_source
        assert "_require_irq_event(" not in case_source


def test_uart_mask_case_requires_all_requested_bits_without_priority_claim() -> None:
    source = _case_source(_read("test_uart_p1.py"), "test_uart_p1_011_interrupt_mask_enable_clear")
    assert "enabled.enabled_mask & requested_mask == requested_mask" in source
    assert "priority_clear" not in source.lower()
    assert "优先级" not in source


def test_uart_reset_recovery_does_not_claim_unasserted_clock_probe() -> None:
    source = _case_source(_read("test_uart_p2.py"), "test_uart_p2_008_reset_recovery")
    assert "clock_off_probe" not in source
    assert "CrgDriver" not in source


def test_uart_baudrate_matrix_uses_dut_and_peer_capability_intersection() -> None:
    source = _case_source(_read("test_uart_p1.py"), "test_uart_p1_015_baudrate_matrix")
    assert source.count("capabilities_get()") == 2
    assert "lower = max(dut_capabilities.min_baudrate, peer_capabilities.min_baudrate)" in source
    assert "upper = min(dut_capabilities.max_baudrate, peer_capabilities.max_baudrate)" in source
    assert "UART DUT/Peer baudrate ranges do not overlap" in source
    assert source.index("pytest.skip") < source.index("uart_dut_handle.initialize(")


def test_uart_semantic_capabilities_and_shared_runtime_gate() -> None:
    helpers = _read("uart_helpers.py")
    p2 = _read("test_uart_p2.py")
    p3 = _read("test_uart_p3.py")
    fixtures = FIXTURES_SOURCE.read_text(encoding="utf-8")
    assert "def require_uart_runtime_feature(" not in helpers
    assert "pytest.skip" not in helpers
    assert "skip_by_runtime_feature:" not in helpers
    assert "def _require_uart_feature(" in fixtures
    assert p2.count(".capabilities_get()") >= 4
    assert "skip_by_runtime_feature:" in p2
    assert "UartFeature.SHADOW" in p3
    assert "UartFeature.FIFO_ACCESS" in p3
