# Framework Validation测试模块。
#
# 职责：验证test_dma_uart_wait_drivers 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from collections import defaultdict

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.dma import (
    CHANNEL_STATUS,
    DMA_SERVICE_ID,
    IRQ_RESULT,
    DmaCommand,
    DmaDriver,
    DmaIrqEvent,
)
from et_test_platform.drivers.uart import (
    CAPTURE_HEADER,
    UART_IRQ_STATE,
    UART_SERVICE_ID,
    UartCommand,
    UartDriver,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, interval_s: float) -> None:
        self.sleeps.append(interval_s)
        self.now += interval_s


class _DmaIrqTarget:
    def __init__(self) -> None:
        self.commands: list[int] = []
        self.timeouts: list[float] = []
        self._counts = iter((0, 1))

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int,
        body: bytes,
        retry_safe: bool = False,
        timeout_s: float,
    ):
        assert service_id == DMA_SERVICE_ID
        assert instance_id == 0
        assert body == b""
        assert retry_safe
        self.commands.append(command_id)
        self.timeouts.append(timeout_s)
        count = next(self._counts)
        events = DmaIrqEvent.TRANSFER_DONE if count else DmaIrqEvent(0)
        response = IRQ_RESULT.pack(int(events), count, 0, 0)
        return ServiceMessage(service_id, command_id, instance_id, 0, response), object()


class _DmaChannelTarget:
    def __init__(self, states: dict[int, tuple[bool, ...]]) -> None:
        self.commands: list[tuple[int, int]] = []
        self.timeouts: list[float] = []
        self._states = states
        self._indexes: dict[int, int] = defaultdict(int)

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int,
        body: bytes,
        retry_safe: bool = False,
        timeout_s: float,
    ):
        assert service_id == DMA_SERVICE_ID
        assert command_id == int(DmaCommand.CHANNEL_STATUS_GET)
        assert instance_id == 0
        assert retry_safe
        channel = body[0]
        self.commands.append((command_id, channel))
        self.timeouts.append(timeout_s)
        states = self._states[channel]
        index = min(self._indexes[channel], len(states) - 1)
        self._indexes[channel] += 1
        response = CHANNEL_STATUS.pack(int(states[index]), 1, 0)
        return ServiceMessage(service_id, command_id, instance_id, 0, response), object()


class _UartCaptureTarget:
    def __init__(self) -> None:
        self.commands: list[int] = []
        self.timeouts: list[float] = []
        self._captures = iter(
            (
                CAPTURE_HEADER.pack(1, 3, 1) + b"E",
                CAPTURE_HEADER.pack(0, 3, 3) + b"ET!",
            )
        )

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int,
        body: bytes,
        timeout_s: float,
    ):
        assert service_id == UART_SERVICE_ID
        assert instance_id == 2
        assert body == b""
        self.commands.append(command_id)
        self.timeouts.append(timeout_s)
        if command_id == int(UartCommand.CAPTURE_GET):
            response = next(self._captures)
        elif command_id == int(UartCommand.IRQ_STATE_GET):
            response = UART_IRQ_STATE.pack(0, 0, 0, 0, 0, 0)
        else:
            raise AssertionError(f"unexpected UART command {command_id}")
        return ServiceMessage(service_id, command_id, instance_id, 0, response), object()


def test_dma_wait_irq_preserves_existing_poll_sequence() -> None:
    clock = _Clock()
    target = _DmaIrqTarget()
    driver = DmaDriver(target, clock=clock, sleep=clock.sleep)

    result = driver.wait_irq(timeout_s=0.01, minimum_count=1, poll_interval_s=0.001)

    assert result.latched_events == DmaIrqEvent.TRANSFER_DONE
    assert result.irq_count == 1
    assert target.commands == [int(DmaCommand.IRQ_RESULT_GET), int(DmaCommand.IRQ_RESULT_GET)]
    assert target.timeouts == pytest.approx([0.01, 0.009])
    assert clock.sleeps == [0.001]


def test_dma_wait_irq_count_preserves_strict_helper_semantics() -> None:
    clock = _Clock()
    target = _DmaIrqTarget()
    driver = DmaDriver(target, clock=clock, sleep=clock.sleep)

    result = driver.wait_irq_count(minimum_count=1, timeout_s=0.01, poll_interval_s=0.001)

    assert result.irq_count == 1
    assert target.commands == [int(DmaCommand.IRQ_RESULT_GET), int(DmaCommand.IRQ_RESULT_GET)]
    assert target.timeouts == pytest.approx([0.01, 0.009])
    assert clock.sleeps == [0.001]


def test_dma_wait_channel_free_preserves_status_poll_sequence() -> None:
    clock = _Clock()
    target = _DmaChannelTarget({3: (False, True)})
    driver = DmaDriver(target, clock=clock, sleep=clock.sleep)

    status = driver.wait_channel_free(3, timeout_s=0.01, poll_interval_s=0.001)

    assert status.is_free
    assert target.commands == [
        (int(DmaCommand.CHANNEL_STATUS_GET), 3),
        (int(DmaCommand.CHANNEL_STATUS_GET), 3),
    ]
    assert target.timeouts == pytest.approx([0.01, 0.009])
    assert clock.sleeps == [0.001]


def test_dma_wait_channels_free_preserves_full_duplex_batch_poll_sequence() -> None:
    clock = _Clock()
    target = _DmaChannelTarget({1: (False, True), 4: (False, True)})
    driver = DmaDriver(target, clock=clock, sleep=clock.sleep)

    statuses = driver.wait_channels_free((1, 4), timeout_s=0.01, poll_interval_s=0.001)

    assert all(status.is_free for status in statuses.values())
    assert target.commands == [
        (int(DmaCommand.CHANNEL_STATUS_GET), 1),
        (int(DmaCommand.CHANNEL_STATUS_GET), 4),
        (int(DmaCommand.CHANNEL_STATUS_GET), 1),
        (int(DmaCommand.CHANNEL_STATUS_GET), 4),
    ]
    assert target.timeouts == pytest.approx([0.01, 0.01, 0.009, 0.009])
    assert clock.sleeps == [0.001]


def test_uart_capture_wait_preserves_existing_poll_and_fault_query_sequence() -> None:
    clock = _Clock()
    target = _UartCaptureTarget()
    driver = UartDriver(target, instance_id=2, clock=clock, sleep=clock.sleep)

    capture = driver.capture_wait(3, timeout_s=0.01, poll_interval_s=0.001)

    assert capture.data == b"ET!"
    assert capture.received == 3
    assert target.commands == [
        int(UartCommand.CAPTURE_GET),
        int(UartCommand.CAPTURE_GET),
        int(UartCommand.IRQ_STATE_GET),
    ]
    assert target.timeouts == pytest.approx([0.01, 0.009, 0.009])
    assert clock.sleeps == [0.001]
