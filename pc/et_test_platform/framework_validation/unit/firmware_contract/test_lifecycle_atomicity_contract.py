# Framework Validation测试模块。
#
# 职责：验证test_lifecycle_atomicity_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]
RESOURCE_SERVICE = ROOT / "firmware/services/src/et_resource_service.c"
SERVICES = ROOT / "firmware/services/src/et_services.c"
CONTROL_UART = ROOT / "firmware/application/src/et_control_uart.c"


def test_resource_create_rolls_back_failed_response_resolution() -> None:
    source = RESOURCE_SERVICE.read_text(encoding="utf-8")
    block = source[source.index("case ET_RESOURCE_COMMAND_CREATE:") :]
    block = block[: block.index("case ET_RESOURCE_COMMAND_WRITE:")]
    assert "et_resource_wrap_destroy(handle)" in block
    assert block.index("et_resource_wrap_resolve") < block.index("et_resource_wrap_destroy(handle)")


def test_service_batch_registration_restores_router_checkpoint() -> None:
    source = SERVICES.read_text(encoding="utf-8")
    assert "checkpoint = et_service_count(router)" in source
    assert "goto rollback" in source
    assert "et_service_router_truncate(router, checkpoint)" in source
    rollback = source[source.index("rollback:") :]
    assert "return -1" in rollback


def test_control_uart_close_commits_each_finished_step() -> None:
    source = CONTROL_UART.read_text(encoding="utf-8")
    close = source[source.index("int et_control_uart_close(") :]
    close = close[: close.index("void et_control_uart_poll(")]
    assert close.index("et_uart_wrap_disable_interrupts") < close.index(
        "transport->irq_enabled = 0u"
    )
    assert close.index("et_irq_manager_unbind") < close.index("transport->irq_bound = 0u")
    assert close.index("et_uart_wrap_deinit") < close.index("transport->uart_initialized = 0u")


def test_control_uart_publishes_cleanup_ownership_before_irq_enable() -> None:
    source = CONTROL_UART.read_text(encoding="utf-8")
    open_body = source[source.index("int et_control_uart_open(") :]
    open_body = open_body[: open_body.index("int et_control_uart_close(")]
    assert open_body.index("transport->irq_enabled = 1u") < open_body.index(
        "et_uart_wrap_enable_interrupts"
    )
