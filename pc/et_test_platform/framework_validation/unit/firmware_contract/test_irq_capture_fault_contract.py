# Framework Validation测试模块。
#
# 职责：验证test_irq_capture_fault_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]
DMA_SERVICE = ROOT / "firmware/services/src/et_dma_service.c"
UART_DRIVER = ROOT / "pc/et_test_platform/drivers/uart/driver.py"
UART_HELPERS = ROOT / "pc/et_test_platform/test_cases/uart/uart_helpers.py"


def test_dma_irq_status_failure_calls_bounded_fault_handler() -> None:
    source = DMA_SERVICE.read_text(encoding="utf-8")
    callback = source[source.index("static void dma_irq_callback(") :]
    callback = callback[: callback.index("static void reset_irq_session(")]
    assert "record_irq_observation_fault(service)" in callback
    helper = source[source.index("static void record_irq_observation_fault(") :]
    helper = helper[: helper.index("static void dma_irq_callback(")]
    assert "unexpected_count" in helper
    assert "overflow_count" in helper
    assert "et_dma_wrap_disable_interrupts" in helper
    assert "et_dma_wrap_clear_interrupts" in helper


def test_uart_driver_owns_capture_wait_fault_checks_without_case_wrapper() -> None:
    driver = UART_DRIVER.read_text(encoding="utf-8")
    helpers = UART_HELPERS.read_text(encoding="utf-8")
    assert "baseline_irq =" in driver
    assert "final_irq.fault_count > baseline_irq.fault_count" in driver
    assert "def capture_wait(" in driver
    assert "irq_state.fault_count != 0" in driver
    assert driver.count("capture_irq_cleanup_fault") >= 2
    assert "wait_capture" not in helpers
    assert "capture_wait(" not in helpers
    assert "irq_state_get(" not in helpers
