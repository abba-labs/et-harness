# Framework Validation测试模块。
#
# 职责：验证test_uart_wrap_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[5]
WRAP_HEADER = PROJECT_ROOT / "firmware" / "wrap" / "include" / "et_uart_wrap.h"
WRAP_SOURCE = PROJECT_ROOT / "firmware" / "wrap" / "src" / "et_uart_wrap.c"
DRIVER_HEADER = (
    PROJECT_ROOT / "firmware" / "chips" / "et6801" / "sdk" / "ET6x_Driver" / "Inc" / "et6x_uart.h"
)
DRIVER_SOURCE = (
    PROJECT_ROOT / "firmware" / "chips" / "et6801" / "sdk" / "ET6x_Driver" / "Src" / "et6x_uart.c"
)

TEST_DRIVER_BEGIN = "/******************** TEST DRIVER EXTENSION BEGIN ********************/"
TEST_DRIVER_END = "/********************* TEST DRIVER EXTENSION END *********************/"


def test_uart_wrap_exposes_atomic_feature_contract() -> None:
    source = WRAP_HEADER.read_text(encoding="utf-8")
    required_symbols = (
        "et_uart_wrap_get_snapshot",
        "et_uart_wrap_software_reset",
        "et_uart_wrap_set_loopback",
        "et_uart_wrap_configure_fifo",
        "et_uart_wrap_get_status",
        "et_uart_wrap_set_break",
        "et_uart_wrap_set_halt",
        "et_uart_wrap_set_dma_mode",
        "et_uart_wrap_configure_nine_bit",
        "et_uart_wrap_read_nine_bit",
        "et_uart_wrap_write_nine_bit",
        "et_uart_wrap_set_flow_control",
        "et_uart_wrap_set_modem_control",
        "et_uart_wrap_get_modem_status",
        "ET_UART_WRAP_ERROR_OVERRUN",
        "ET_UART_WRAP_STATE_BUSY",
        "input_flags",
        "delta_flags",
        "output_flags",
        "raw_status",
    )
    missing = [symbol for symbol in required_symbols if symbol not in source]
    assert missing == [], f"missing UART Wrap APIs: {missing}"


def test_uart_wrap_public_contract_has_extended_line_values() -> None:
    source = WRAP_HEADER.read_text(encoding="utf-8")
    required_tokens = (
        "ET_UART_WRAP_PARITY_STICK_ZERO",
        "ET_UART_WRAP_PARITY_STICK_ONE",
        "ET_UART_WRAP_STOP_BITS_1",
        "ET_UART_WRAP_STOP_BITS_1_5",
        "ET_UART_WRAP_STOP_BITS_2",
    )
    missing = [token for token in required_tokens if token not in source]
    assert missing == [], f"missing UART line configuration values: {missing}"


def test_uart_wrap_exposes_atomic_busy_partial_and_fifo_test_operations() -> None:
    source = WRAP_HEADER.read_text(encoding="utf-8")
    required_symbols = (
        "et_uart_wrap_write_partial",
        "et_uart_wrap_trigger_busy_detect",
        "et_uart_wrap_shadow_fifo_config",
        "et_uart_wrap_fifo_access_set",
        "et_uart_wrap_fifo_tx_read",
        "et_uart_wrap_fifo_rx_write",
        "ET_UART_WRAP_CAP_SHADOW",
        "ET_UART_WRAP_CAP_FIFO_ACCESS",
    )
    missing = [symbol for symbol in required_symbols if symbol not in source]
    assert missing == [], f"missing UART atomic Wrap APIs: {missing}"


def test_uart_wrap_fifo_thresholds_use_semantic_byte_counts() -> None:
    source = WRAP_HEADER.read_text(encoding="utf-8")
    expected_values = (
        "ET_UART_WRAP_TXFIFO_THRESHOLD_0 = 0u",
        "ET_UART_WRAP_TXFIFO_THRESHOLD_2 = 2u",
        "ET_UART_WRAP_TXFIFO_THRESHOLD_4 = 4u",
        "ET_UART_WRAP_TXFIFO_THRESHOLD_8 = 8u",
        "ET_UART_WRAP_RXFIFO_THRESHOLD_1 = 1u",
        "ET_UART_WRAP_RXFIFO_THRESHOLD_4 = 4u",
        "ET_UART_WRAP_RXFIFO_THRESHOLD_8 = 8u",
        "ET_UART_WRAP_RXFIFO_THRESHOLD_14 = 14u",
    )
    missing = [value for value in expected_values if value not in source]
    assert missing == [], f"UART Wrap FIFO thresholds must expose stable byte counts: {missing}"


def test_uart_wrap_source_contains_no_register_access() -> None:
    source = WRAP_SOURCE.read_text(encoding="utf-8")
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//.*?$", "", source, flags=re.MULTILINE)
    forbidden = re.compile(
        r"\b(?:READ_REG|WRITE_REG|SET_BIT|CLEAR_BIT|MODIFY_REG)\s*\(|"
        r"(?:&\s*)?\b[A-Za-z_]\w*\s*->\s*[A-Z][A-Z0-9_]*\b"
    )
    assert forbidden.search(source) is None


def test_uart_driver_additions_are_isolated_to_test_extension() -> None:
    header = DRIVER_HEADER.read_text(encoding="utf-8")
    source = DRIVER_SOURCE.read_text(encoding="utf-8")
    required_symbols = (
        "UART_testGetComponentSnapshot",
        "UART_testGetStatusSnapshot",
        "UART_testGetInterruptSnapshot",
        "UART_testConfigureFIFO",
        "UART_testSetLoopback",
        "UART_testSetBreak",
        "UART_testSetNineBitEnabled",
        "UART_testTriggerBusyDetect",
        "UART_testConfigureShadowFIFO",
        "UART_testSetFIFOAccess",
        "UART_testReadTxFIFO",
        "UART_testWriteRxFIFO",
    )
    begin_h = header.find(TEST_DRIVER_BEGIN)
    end_h = header.find(TEST_DRIVER_END)
    begin_c = source.find(TEST_DRIVER_BEGIN)
    end_c = source.find(TEST_DRIVER_END)
    assert begin_h >= 0 and end_h > begin_h
    assert begin_c >= 0 and end_c > begin_c
    for symbol in required_symbols:
        assert symbol in header[begin_h:end_h]
        assert symbol in source[begin_c:end_c]

    test_api = re.compile(r"\b[A-Za-z_]\w*_test[A-Z]\w*\s*\(")
    for path, text in ((DRIVER_HEADER, header), (DRIVER_SOURCE, source)):
        begin = text.find(TEST_DRIVER_BEGIN)
        end = text.find(TEST_DRIVER_END)
        for match in test_api.finditer(text):
            assert begin < match.start() < end, (
                f"Test Driver API outside extension block: {path}:{match.group(0)}"
            )


# The read-clear address bit must be classified inside the UART Driver.
def test_uart_address_irq_is_resolved_from_one_driver_snapshot() -> None:
    header = DRIVER_HEADER.read_text(encoding="utf-8")
    source = DRIVER_SOURCE.read_text(encoding="utf-8")
    wrap = WRAP_SOURCE.read_text(encoding="utf-8")

    assert "UART_TestInterruptSnapshot_TypeDef" in header
    assert "UART_testGetInterruptSnapshot" in header
    driver_function = source[source.index("UART_testGetInterruptSnapshot") :]
    assert driver_function.index("UART_getInterruptStatus") < driver_function.index(
        "UART_getLineStatusFlag"
    )
    assert "UART_LINE_STA_ADDR_RCVD_FLAG" in driver_function
    assert "UART_IT_9BITS_ADDR_RESV_FLAG" in driver_function

    wrap_function = wrap[wrap.index("et_uart_wrap_get_interrupt_status") :]
    assert "UART_testGetInterruptSnapshot" in wrap_function
    assert "irq_status->line_flags" in wrap_function
    assert "irq_status->error_flags" in wrap_function


# Public UART boundaries expose normalized evidence only.
def test_uart_wrap_keeps_chip_snapshot_private() -> None:
    public_sources = (
        WRAP_HEADER,
        PROJECT_ROOT / "firmware" / "services" / "src" / "et_uart_service.c",
        PROJECT_ROOT / "firmware" / "application" / "src" / "et_control_uart.c",
    )
    leaked = [
        str(path) for path in public_sources if "chip_status" in path.read_text(encoding="utf-8")
    ]
    assert leaked == [], "Chip Driver status must not cross the UART Wrap boundary"

    wrap = WRAP_SOURCE.read_text(encoding="utf-8")
    assert "last_interrupt_status" in wrap
    assert "last_snapshot_valid" in wrap
    assert "irq_status->chip_status" not in wrap


# Clearing an IRQ consumes the most recent snapshot from the handle.
def test_uart_wrap_clear_pairs_with_the_cached_snapshot() -> None:
    header = WRAP_HEADER.read_text(encoding="utf-8")
    source = WRAP_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"et_wrap_status_t et_uart_wrap_clear_interrupts\(\s*"
        r"et_uart_wrap_handle_t \*handle\s*\);",
        header,
    )
    clear_function = source[source.index("et_uart_wrap_clear_interrupts") :]
    assert "const et_uart_wrap_irq_status_t *" not in clear_function
    assert "private->last_interrupt_status" in clear_function
