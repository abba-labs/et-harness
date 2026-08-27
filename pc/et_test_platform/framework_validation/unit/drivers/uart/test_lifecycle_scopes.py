# Framework Validation测试模块。
#
# 职责：验证test_lifecycle_scopes 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.drivers.uart import UART_SERVICE_ID, UartCommand, UartDriver


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes]] = []
        self.failures: dict[tuple[int, bytes], Exception] = {}

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ) -> tuple[ServiceMessage, object]:
        del instance_id
        assert service_id == UART_SERVICE_ID
        command = int(command_id)
        self.calls.append((command, body))
        failure = self.failures.get((command, body))
        if failure is not None:
            raise failure
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=0,
                body=b"",
            ),
            object(),
        )


def test_uart_cleanup_only_scopes_preserve_case_command_order() -> None:
    target = _Target()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with uart.loopback_disable_on_exit(), uart.capture_mode():
        uart.loopback_set(True)
        uart.capture_start(4)

    assert target.calls == [
        (int(UartCommand.LOOPBACK_SET), b"\x01\x00\x00\x00"),
        (int(UartCommand.CAPTURE_START), b"\x04\x00\x00\x00"),
        (int(UartCommand.CAPTURE_CANCEL), b""),
        (int(UartCommand.LOOPBACK_SET), b"\x00\x00\x00\x00"),
    ]


def test_uart_nested_cleanup_scopes_keep_primary_and_cleanup_failures() -> None:
    target = _Target()
    target.failures[(int(UartCommand.CAPTURE_CANCEL), b"")] = RuntimeError("cancel failed")
    target.failures[(int(UartCommand.LOOPBACK_SET), b"\x00\x00\x00\x00")] = RuntimeError(
        "loopback disable failed"
    )
    uart = UartDriver(target)  # type: ignore[arg-type]

    with (
        pytest.raises(OperationCleanupError) as captured,
        uart.loopback_disable_on_exit(),
        uart.capture_mode(),
    ):
        raise RuntimeError("case failed")

    assert str(captured.value.primary_error) == "case failed"
    assert [failure.stage for failure in captured.value.cleanup_failures] == [
        "UART capture cancel",
        "UART loopback disable",
    ]
    assert target.calls == [
        (int(UartCommand.CAPTURE_CANCEL), b""),
        (int(UartCommand.LOOPBACK_SET), b"\x00\x00\x00\x00"),
    ]
