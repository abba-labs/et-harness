# Framework Validation测试模块。
#
# 职责：验证test_uart_reliability_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[5]
SERVICE_SOURCE = PROJECT_ROOT / "firmware" / "services" / "src" / "et_uart_service.c"
SERVICE_HEADER = PROJECT_ROOT / "firmware" / "services" / "include" / "et_uart_service.h"
FIXTURES_SOURCE = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases" / "uart" / "conftest.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# 按 AST 提取函数，避免函数前注释或空行变化破坏合同测试定位。
def _function_source(path: Path, function_name: str) -> str:
    source = _source(path)
    tree = ast.parse(source, filename=str(path))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    segment = ast.get_source_segment(source, function)
    if segment is None:
        raise AssertionError(f"cannot extract {function_name}")
    return segment


def test_uart_control_role_is_not_gated_as_test_service() -> None:
    fixture = _function_source(FIXTURES_SOURCE, "uart_pair_config")
    assert "pair.control_instance" not in fixture
    assert "_require_uart_runtime_instance" not in fixture


def test_uart_irq_state_get_is_a_pure_cached_snapshot() -> None:
    source = _source(SERVICE_SOURCE)
    start = source.index("static uint16_t handle_irq_state_get(")
    end = source.index("static uint16_t handle_nine_bit_config(", start)
    command = source[start:end]
    assert "et_uart_wrap_get_interrupt_status" not in command
    assert "irq_result_generation" in command
    assert "ET_UART_SERVICE_SNAPSHOT_RETRIES" in command


def test_uart_service_has_one_irq_owner_and_unified_fifo_dma_state() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    assert "static void uart_irq_callback(" in source
    assert "uart_capture_irq" not in source
    assert "uart_bind_event_before_capture" not in source
    assert "irq_applied_wrap_mask" in header
    assert "capture_generation" in header
    assert "uart_apply_irq_mask" in source
    assert source.count("uart_apply_fifo_dma_state(") >= 4
    assert "et_uart_wrap_set_dma_enabled(" not in source


def test_uart_service_has_idempotent_idle_reset_and_reviewable_regions() -> None:
    source = _source(SERVICE_SOURCE)
    assert "static et_wrap_status_t uart_reset_to_idle(" in source
    deinit = source[
        source.index("if (command_id == ET_UART_COMMAND_DEINITIALIZE)") : source.index(
            "if (command_id == ET_UART_COMMAND_WRITE)"
        )
    ]
    assert "service->initialized == 0u" not in deinit
    assert "uart_reset_to_idle(service)" in deinit
    for region in (
        "Wire Helpers",
        "IRQ Mapping",
        "Transfer Helpers",
        "IRQ and Capture Management",
        "Lifecycle and FIFO/DMA State",
        "Command Helpers",
        "Command Dispatch",
        "Public Service Interface",
    ):
        assert region in source


def test_uart_tx_empty_one_shot_requires_explicit_rearm() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    apply_start = source.index("static et_wrap_status_t uart_apply_irq_mask(")
    apply_end = source.index("static et_wrap_status_t uart_rebind_irq_priority(", apply_start)
    apply_body = source[apply_start:apply_end]
    callback_start = source.index("static void uart_irq_callback(", apply_end)
    callback_end = source.index("static et_wrap_status_t uart_cancel_capture(", callback_start)
    callback = source[callback_start:callback_end]
    config_start = source.index("static uint16_t handle_irq_config(")
    config_end = source.index("static uint16_t handle_irq_state_get(", config_start)
    config = source[config_start:config_end]

    assert "irq_suppressed_wrap_mask" in header
    assert "~service->irq_suppressed_wrap_mask" in apply_body
    assert "irq_suppressed_wrap_mask |=" in callback
    assert "ET_UART_WRAP_IRQ_TX_READY" in callback
    assert "irq_suppressed_wrap_mask &= ~configured_wrap_mask" in config


def test_uart_idle_reset_preserves_failed_physical_steps_for_retry() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    start = source.index("static et_wrap_status_t uart_reset_to_idle(")
    end = source.index("static et_wrap_status_t uart_write_fifo_dma_hardware(", start)
    reset = source[start:end]

    assert "default_irq_priority" in header
    assert "if (service->irq_bound != 0u)" in reset
    assert "service->irq_priority = service->default_irq_priority" in reset

    disable_call = reset.index("et_uart_wrap_disable_interrupts")
    clear_mask = reset.index("service->irq_applied_wrap_mask = 0u")
    assert disable_call < clear_mask

    unbind_call = reset.index("et_irq_manager_unbind")
    clear_binding = reset.index("service->irq_bound = 0u")
    assert unbind_call < clear_binding

    deinit_call = reset.index("et_uart_wrap_deinit")
    clear_initialized = reset.index("service->initialized = 0u")
    clear_handle = reset.index("memset(&service->handle")
    assert deinit_call < clear_initialized < clear_handle


def test_uart_software_reset_uses_single_idle_reset_path() -> None:
    source = _source(SERVICE_SOURCE)
    start = source.index("if (command_id == ET_UART_COMMAND_SOFTWARE_RESET)")
    end = source.index("if (command_id == ET_UART_COMMAND_LOOPBACK_SET)", start)
    command = source[start:end]
    assert "uart_reset_to_idle(service)" in command
    assert "et_uart_wrap_software_reset" not in command


def test_uart_wrap_has_no_handle_bypassing_dma_configuration_api() -> None:
    wrap_header = PROJECT_ROOT / "firmware" / "wrap" / "include" / "et_uart_wrap.h"
    wrap_source = PROJECT_ROOT / "firmware" / "wrap" / "src" / "et_uart_wrap.c"
    assert "et_uart_wrap_set_dma_enabled" not in _source(wrap_header)
    assert "et_uart_wrap_set_dma_enabled" not in _source(wrap_source)


# Chip, runtime and Bench rejection reasons stay explicit at their owning layers.
def test_uart_gate_reasons_keep_chip_runtime_and_bench_layers_distinct() -> None:

    fixtures = _source(FIXTURES_SOURCE)
    helpers = _source(PROJECT_ROOT / "pc/et_test_platform/test_cases/uart/uart_helpers.py")
    formal_cases = "\n".join(
        _source(PROJECT_ROOT / "pc/et_test_platform/test_cases/uart" / name)
        for name in (
            "test_uart_p0.py",
            "test_uart_p1.py",
            "test_uart_p2.py",
            "test_uart_p3.py",
        )
    )
    assert "skip_by_chip_capability: UART" in fixtures
    assert "skip_by_bench:" in fixtures
    assert "skip_by_runtime_feature:" in fixtures + formal_cases
    assert "pytest.skip" not in helpers
    assert "skip_by_runtime_feature:" not in helpers
