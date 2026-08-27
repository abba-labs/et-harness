# Framework Validation测试模块。
#
# 职责：验证test_uart_firmware_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[5]
SERVICE_HEADER = PROJECT_ROOT / "firmware" / "services" / "include" / "et_uart_service.h"
SERVICE_SOURCE = PROJECT_ROOT / "firmware" / "services" / "src" / "et_uart_service.c"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_uart_service_command_ids_match_pc_wire_contract() -> None:
    source = _source(SERVICE_HEADER)
    expected = {
        "SNAPSHOT_GET": 0x000C,
        "SOFTWARE_RESET": 0x000D,
        "LOOPBACK_SET": 0x000E,
        "FIFO_CONFIG": 0x000F,
        "STATUS_GET": 0x0010,
        "IRQ_CONFIG": 0x0011,
        "IRQ_STATE_GET": 0x0012,
        "BREAK_SET": 0x0013,
        "HALT_SET": 0x0014,
        "DMA_MODE_SET": 0x0015,
        "NINE_BIT_CONFIG": 0x0016,
        "WRITE_9BIT": 0x0017,
        "READ_9BIT": 0x0018,
        "FLOW_CONTROL_SET": 0x0019,
        "MODEM_CONTROL_SET": 0x001A,
        "MODEM_STATUS_GET": 0x001B,
    }
    for name, value in expected.items():
        match = re.search(
            rf"ET_UART_COMMAND_{name}\s*=\s*0x([0-9A-Fa-f]+)u",
            source,
        )
        assert match, f"missing UART command {name}"
        assert int(match.group(1), 16) == value

    legacy = {
        "CAPABILITIES_GET": 0x0001,
        "DMA_ENDPOINT_GET": 0x0002,
        "DMA_ENABLE_SET": 0x0003,
        "INITIALIZE": 0x0004,
        "DEINITIALIZE": 0x0005,
        "WRITE": 0x0006,
        "READ_EXACT": 0x0007,
        "CAPTURE_START": 0x0008,
        "CAPTURE_GET": 0x0009,
        "CAPTURE_CANCEL": 0x000A,
        "EXCHANGE": 0x000B,
    }
    for name, value in legacy.items():
        match = re.search(
            rf"ET_UART_COMMAND_{name}\s*=\s*0x([0-9A-Fa-f]+)u",
            source,
        )
        assert match, f"missing legacy UART command {name}"
        assert int(match.group(1), 16) == value

    atomic = {
        "WRITE_PARTIAL": 0x001C,
        "BUSY_DETECT_TRIGGER": 0x001D,
        "SHADOW_FIFO_CONFIG": 0x001E,
        "FIFO_ACCESS_SET": 0x001F,
        "FIFO_TX_READ": 0x0020,
        "FIFO_RX_WRITE": 0x0021,
    }
    for name, value in atomic.items():
        match = re.search(
            rf"ET_UART_COMMAND_{name}\s*=\s*0x([0-9A-Fa-f]+)u",
            source,
        )
        assert match, f"missing UART command {name}"
        assert int(match.group(1), 16) == value


def test_uart_service_uses_only_approved_uart_and_common_operations() -> None:
    source = _source(SERVICE_SOURCE)
    required_calls = (
        "et_uart_wrap_get_snapshot",
        "et_uart_wrap_set_loopback",
        "et_uart_wrap_configure_fifo",
        "et_uart_wrap_get_status",
        "et_uart_wrap_enable_interrupts",
        "et_uart_wrap_disable_interrupts",
        "et_uart_wrap_get_interrupt_status",
        "et_uart_wrap_set_break",
        "et_uart_wrap_set_halt",
        "et_uart_wrap_set_dma_mode",
        "et_uart_wrap_configure_nine_bit",
        "et_uart_wrap_write_nine_bit",
        "et_uart_wrap_read_nine_bit",
        "et_uart_wrap_set_flow_control",
        "et_uart_wrap_set_modem_control",
        "et_uart_wrap_get_modem_status",
        "et_uart_wrap_write_partial",
        "et_uart_wrap_trigger_busy_detect",
        "et_uart_wrap_shadow_fifo_config",
        "et_uart_wrap_fifo_access_set",
        "et_uart_wrap_fifo_tx_read",
        "et_uart_wrap_fifo_rx_write",
    )
    for name in required_calls:
        assert name in source, f"Service does not call UART Wrap API {name}"
    assert "et_resource_wrap" not in source
    assert "publish_dma_endpoint" not in source
    assert "et_sysctrl_wrap" not in source

    forbidden = re.compile(r"\b(?:UART|USART)_[A-Za-z0-9_]*\s*->")
    assert not forbidden.search(source), "Service must not access UART registers"


def test_uart_service_explicitly_bounds_et_frame_body_capacity() -> None:
    header = _source(SERVICE_HEADER)
    source = _source(SERVICE_SOURCE)

    assert "ET_UART_SERVICE_BODY_CAPACITY" in header
    assert "ET_TEST_PROTOCOL_MAX_PAYLOAD - ET_MESSAGE_HEADER_SIZE" in header
    assert "ET_UART_SERVICE_MAX_WRITE_CHUNK" in header
    assert "ET_UART_SERVICE_MAX_READ_CHUNK" in header
    assert "data_length > ET_UART_SERVICE_MAX_WRITE_CHUNK" in source
    assert "request_length > ET_UART_SERVICE_BODY_CAPACITY" in source
    assert "requested > ET_UART_SERVICE_MAX_READ_CHUNK" in source


def test_uart_service_uses_exact_response_sizes_and_9bit_bounds() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    for name, size in (
        ("SNAPSHOT", 32),
        ("STATUS", 24),
        ("IRQ_STATE", 24),
        ("MODEM_STATUS", 16),
    ):
        assert f"#define ET_UART_SERVICE_{name}_RESPONSE_SIZE {size}u" in header
        assert f"response_capacity < ET_UART_SERVICE_{name}_RESPONSE_SIZE" in source
    # A count is checked before count*2 and the response is bounded by the
    # caller capacity; this is the overflow-sensitive part of READ_9BIT.
    assert "response_capacity / ET_UART_SERVICE_NINE_BIT_ITEM_SIZE" in source
    assert "request_length - ET_UART_SERVICE_NINE_BIT_HEADER_SIZE" in source
    assert "ET_UART_SERVICE_NINE_BIT_CAPACITY" in source
    assert "uart_status.fifo_flags" in source
    assert "uart_status.error_flags" in source
    assert "uart_status.state_flags" in source
    assert "line_status & 0x1e" not in source


def test_uart_service_rejects_nonzero_reserved_bytes_for_new_commands() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    assert "static uint8_t bytes_are_zero(" in source
    assert "ET_UART_SERVICE_VALUE_RESERVED_OFFSET" in source
    assert "ET_UART_SERVICE_VALUE_RESERVED_SIZE" in source
    assert "ET_UART_SERVICE_IRQ_RESERVED_OFFSET" in source
    assert "ET_UART_SERVICE_IRQ_RESERVED_SIZE" in source
    assert "#define ET_UART_SERVICE_VALUE_RESERVED_OFFSET 1u" in header
    assert "#define ET_UART_SERVICE_VALUE_RESERVED_SIZE 3u" in header


def test_uart_service_irq_uses_observed_status_and_accumulates_masks() -> None:
    source = _source(SERVICE_SOURCE)
    assert "et_uart_wrap_get_interrupt_status" in source
    assert "et_uart_wrap_clear_interrupts" in source
    assert "latched_error_flags |= irq_status.error_flags" in source


# V1 保留的兼容字段必须存在，但 Firmware 仍只执行一次原子读写。
def test_uart_service_preserves_v1_poll_budget_layout_without_firmware_polling() -> None:

    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    assert "ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD 4u" in header
    assert "max_polls = read_u32(request_body)" in source
    assert "max_polls = read_u32(&request_body[ET_UART_SERVICE_POLL_BUDGET_OFFSET])" in source
    assert "max_polls == 0u" in source
    assert "&request_body[ET_UART_SERVICE_DATA_OFFSET]" in source
    assert "ET_UART_SERVICE_NINE_BIT_DATA_OFFSET" in source
    assert "ET_UART_SERVICE_NINE_BIT_ITEM_SIZE" in source
    assert "for (poll" not in source
    assert "while (" not in source
    assert "old_mask | wire_mask" in source
    assert "old_mask & ~wire_mask" in source
    assert "route_events" in source  # callback signature remains stable
    assert "irq_wrap_to_wire(irq_status.interrupt_flags)" in source


def test_uart_irq_snapshot_is_cleared_after_single_callback_observation() -> None:
    source = _source(SERVICE_SOURCE)
    callback = source[source.index("static void uart_irq_callback(") :]
    callback = callback[: callback.index("static et_wrap_status_t uart_cancel_capture(")]
    assert "et_uart_wrap_get_interrupt_status" in callback
    assert "et_uart_wrap_clear_interrupts" in callback
    assert callback.index("et_uart_wrap_get_interrupt_status") < callback.index(
        "et_uart_wrap_clear_interrupts"
    )


# Service/Application stay independent of ET6801 Driver declarations.
def test_uart_service_and_application_do_not_include_chip_driver_types() -> None:
    application = _source(PROJECT_ROOT / "firmware" / "application" / "src" / "et_control_uart.c")
    service = _source(SERVICE_SOURCE)
    for name, source in (("Service", service), ("Application", application)):
        assert "et6x_uart.h" not in source, f"{name} includes chip UART header"
        assert "UART_Type" not in source, f"{name} exposes UART_Type"
        assert "DRV_Status" not in source, f"{name} exposes DRV_Status"
        assert not re.search(r"\bUART_Test[A-Za-z0-9_]*\b", source), (
            f"{name} exposes UART Test Driver symbols"
        )


def test_uart_service_uses_one_callback_for_irq_and_capture() -> None:
    source = _source(SERVICE_SOURCE)
    header = _source(SERVICE_HEADER)
    assert "static void uart_irq_callback(" in source
    assert "uart_capture_irq" not in source
    assert "uart_bind_event_before_capture" not in source
    assert "capture_irq_route" not in header
    assert "capture_irq_bound" not in header
    callback = source[source.index("static void uart_irq_callback(") :]
    callback = callback[: callback.index("static et_wrap_status_t uart_cancel_capture(")]
    assert callback.index("uart_irq_evidence_begin") < callback.index("uart_capture_drain")


def test_uart_service_uses_one_shot_tx_empty_observation() -> None:
    source = _source(SERVICE_SOURCE)
    declaration = source.index("static void uart_irq_callback(")
    callback = source[source.index("static void uart_irq_callback(", declaration + 1) :]
    callback = callback[: callback.index("static et_wrap_status_t uart_cancel_capture(")]
    assert "wire_events & ET_UART_SERVICE_IRQ_WIRE_TX_READY" in callback
    assert "et_uart_wrap_disable_interrupts" in callback
    assert "irq_applied_wrap_mask &= ~ET_UART_WRAP_IRQ_TX_READY" in callback
    config = source[source.index("static uint16_t handle_irq_config(") :]
    config = config[: config.index("static uint16_t handle_irq_state_get(")]
    assert "uart_apply_irq_mask(service)" in config
    assert "if ((new_mask == old_mask)" not in config


def test_uart_service_preserves_reset_reconfigure_and_extended_semantics() -> None:
    source = _source(SERVICE_SOURCE)
    assert "uart_reset_to_idle(service)" in source
    assert "uart_cancel_capture(service)" in source
    assert "uart_apply_fifo_dma_state" in source
    assert "config.enabled = request_body[ET_UART_SERVICE_NINE_BIT_ENABLED_OFFSET]" in source
    assert "ET_STATUS_NOT_SUPPORTED" in source
    assert "modem_status.input_flags" in source
    assert "modem_status.delta_flags" in source
    assert "modem_status.output_flags" in source
    assert "modem_status.raw_status" in source
    assert "latched_error_flags |= irq_status.error_flags" in source
