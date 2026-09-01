# Framework Validation测试模块。
#
# 职责：验证test_uart_package 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from collections import defaultdict, deque

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.uart import (
    CAPTURE_HEADER,
    TRANSFERRED,
    UART_CONFIG,
    UART_IRQ_STATE,
    UART_SERVICE_ID,
    UartCommand,
    UartDmaMode,
    UartDriver,
    UartParity,
    UartStopBits,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Target:
    def __init__(self) -> None:
        self.responses: dict[int, deque[bytes]] = defaultdict(deque)
        self.failures: dict[int, Exception] = {}
        self.calls: list[tuple[int, bytes, float | None]] = []

    def queue(self, command: UartCommand, *responses: bytes) -> None:
        self.responses[int(command)].extend(responses)

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        timeout_s: float | None = None,
    ) -> tuple[ServiceMessage, object]:
        del instance_id
        assert service_id == UART_SERVICE_ID
        command = int(command_id)
        self.calls.append((command, body, timeout_s))
        if command in self.failures:
            raise self.failures[command]
        response = self.responses[command].popleft() if self.responses[command] else b""
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=0,
                body=response,
            ),
            object(),
        )


def test_uart_public_line_config_wire_is_stable_after_package_split() -> None:
    target = _Target()
    driver = UartDriver(target)  # type: ignore[arg-type]

    driver.initialize(
        baudrate=115200,
        data_bits=8,
        stop_bits=UartStopBits.TWO,
        parity=UartParity.EVEN,
    )

    assert UART_CONFIG.size == 8
    assert target.calls == [
        (
            int(UartCommand.INITIALIZE),
            bytes.fromhex("00c2010008030100"),
            None,
        )
    ]


def test_uart_write_uses_one_decreasing_total_deadline() -> None:
    clock = _Clock()
    target = _Target()
    target.queue(
        UartCommand.WRITE,
        TRANSFERRED.pack(0),
        TRANSFERRED.pack(2),
    )
    driver = UartDriver(  # type: ignore[arg-type]
        target,
        clock=clock,
        sleep=clock.sleep,
    )

    assert driver.write(b"AB", timeout_s=1.0, poll_interval_s=0.2) == 2

    assert [item[2] for item in target.calls] == pytest.approx([1.0, 0.8])
    assert [item[1] for item in target.calls] == [b"\x01\x00\x00\x00AB"] * 2
    assert clock.now == pytest.approx(0.2)


def test_uart_exchange_reuses_one_deadline_for_write_and_capture() -> None:
    clock = _Clock()
    target = _Target()
    target.queue(
        UartCommand.IRQ_STATE_GET,
        UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 0),
        UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 0),
    )
    target.queue(UartCommand.CAPTURE_START, b"")
    target.queue(UartCommand.WRITE, TRANSFERRED.pack(0), TRANSFERRED.pack(1))
    target.queue(
        UartCommand.CAPTURE_GET,
        CAPTURE_HEADER.pack(0, 1, 1) + b"Z",
    )
    driver = UartDriver(  # type: ignore[arg-type]
        target,
        clock=clock,
        sleep=clock.sleep,
    )

    assert (
        driver.exchange(
            b"Z",
            timeout_s=1.0,
            poll_interval_s=0.25,
        )
        == b"Z"
    )

    assert [item[0] for item in target.calls] == [
        int(UartCommand.IRQ_STATE_GET),
        int(UartCommand.CAPTURE_START),
        int(UartCommand.WRITE),
        int(UartCommand.WRITE),
        int(UartCommand.CAPTURE_GET),
        int(UartCommand.IRQ_STATE_GET),
    ]
    assert [item[2] for item in target.calls] == pytest.approx([1.0, 1.0, 1.0, 0.75, 0.75, 0.75])


def test_uart_exchange_keeps_capture_cancel_failure_with_primary_error() -> None:
    target = _Target()
    target.queue(
        UartCommand.IRQ_STATE_GET,
        UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 0),
    )
    target.queue(UartCommand.CAPTURE_START, b"")
    target.queue(UartCommand.WRITE, TRANSFERRED.pack(2))
    target.failures[int(UartCommand.CAPTURE_CANCEL)] = RuntimeError("cancel failed")
    driver = UartDriver(target)  # type: ignore[arg-type]

    with pytest.raises(OperationCleanupError) as captured:
        driver.exchange(b"X", timeout_s=1.0)

    assert "write response exceeds request" in str(captured.value.primary_error)
    assert [item.stage for item in captured.value.cleanup_failures] == ["UART capture cancel"]


def test_uart_nine_bit_rejects_invalid_deadline_before_request() -> None:
    target = _Target()
    driver = UartDriver(target)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="timeout_s"):
        driver.write_9bit((0x1FF,), timeout_s=0)
    with pytest.raises(ValueError, match="poll_interval_s"):
        driver.read_9bit(1, poll_interval_s=False)  # type: ignore[arg-type]

    assert target.calls == []


def test_uart_dma_multi_mode_keeps_original_single_byte_wire() -> None:
    target = _Target()
    driver = UartDriver(target)  # type: ignore[arg-type]

    driver.dma_mode_set(UartDmaMode.MULTI)

    assert target.calls == [
        (
            int(UartCommand.DMA_MODE_SET),
            b"\x02\x00\x00\x00",
            None,
        )
    ]


def test_uart_exchange_rejects_capture_cleanup_fault_after_complete_data() -> None:
    target = _Target()
    target.queue(
        UartCommand.IRQ_STATE_GET,
        UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 0),
        UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 1),
    )
    target.queue(UartCommand.CAPTURE_START, b"")
    target.queue(UartCommand.WRITE, TRANSFERRED.pack(1))
    target.queue(
        UartCommand.CAPTURE_GET,
        CAPTURE_HEADER.pack(0, 1, 1) + b"Z",
    )
    driver = UartDriver(target)  # type: ignore[arg-type]

    with pytest.raises(ProtocolError, match="capture_irq_cleanup_fault"):
        driver.exchange(b"Z", timeout_s=1.0)

    assert target.calls[-1][0] == int(UartCommand.CAPTURE_CANCEL)
