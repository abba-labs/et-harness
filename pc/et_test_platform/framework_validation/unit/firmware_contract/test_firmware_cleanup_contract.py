# Framework Validation测试模块。
#
# 职责：验证test_firmware_cleanup_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]
UART_WRAP = ROOT / "firmware/wrap/src/et_uart_wrap.c"
IRQ_HEADER = ROOT / "firmware/framework/include/et_irq_manager.h"
IRQ_SOURCE = ROOT / "firmware/framework/src/et_irq_manager.c"


def test_uart_wrap_clears_handle_only_after_successful_reset() -> None:
    source = UART_WRAP.read_text(encoding="utf-8")
    start = source.index("et_wrap_status_t et_uart_wrap_deinit(")
    end = source.index("et_wrap_status_t et_uart_wrap_enable_interrupts(", start)
    body = source[start:end]
    reset = body.index("UART_performSoftwareReset")
    status_check = body.index("if (status != ET_WRAP_STATUS_OK)", reset)
    clear_handle = body.index("memset(handle", status_check)
    assert reset < status_check < clear_handle


def test_irq_bind_rollback_keeps_a_non_dispatchable_cleanup_owner() -> None:
    header = IRQ_HEADER.read_text(encoding="utf-8")
    source = IRQ_SOURCE.read_text(encoding="utf-8")
    assert "cleanup_required" in header
    bind_start = source.index("int et_irq_manager_bind(")
    bind_end = source.index("int et_irq_manager_unbind(", bind_start)
    bind = source[bind_start:bind_end]
    assert "free_binding->cleanup_required = 1u" in bind
    assert "cleanup_irq_line(manager, free_binding)" in bind
    assert "memset(free_binding" in bind
    dispatch = source[source.index("int et_irq_manager_dispatch(") :]
    assert "binding->cleanup_required == 0u" in dispatch
