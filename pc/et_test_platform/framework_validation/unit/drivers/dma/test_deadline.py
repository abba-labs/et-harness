# Framework Validation测试模块。
#
# 职责：验证test_deadline 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.core.errors import RequestTimeout
from et_test_platform.drivers.dma import (
    CHANNEL_STATUS,
    DmaCommand,
    DmaDriver,
    DmaIrqEvent,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _DeadlineTarget:
    def __init__(
        self,
        statuses: tuple[bytes, ...],
        *,
        cleanup_failures: frozenset[DmaCommand] = frozenset(),
    ) -> None:
        self._statuses = deque(statuses)
        self._last_status = statuses[-1]
        self.cleanup_failures = cleanup_failures
        self.commands: list[DmaCommand] = []
        self.timeouts: list[float | None] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
        timeout_s: float | None = None,
    ) -> tuple[ServiceMessage, object]:
        del instance_id, body, retry_safe
        command = DmaCommand(command_id)
        self.commands.append(command)
        self.timeouts.append(timeout_s)
        if command in self.cleanup_failures:
            raise RuntimeError(f"{command.name} cleanup failed")
        response = b""
        if command == DmaCommand.CHANNEL_STATUS_GET:
            response = self._statuses.popleft() if self._statuses else self._last_status
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=0,
                body=response,
            ),
            object(),
        )


def _status(*, free: bool, events: DmaIrqEvent | None = None) -> bytes:
    normalized = DmaIrqEvent(0) if events is None else events
    return CHANNEL_STATUS.pack(int(free), int(free), int(normalized))


def test_wait_complete_passes_one_decreasing_deadline_to_all_primary_requests() -> None:
    clock = _Clock()
    target = _DeadlineTarget(
        (
            _status(free=False),
            _status(free=False),
            _status(free=True),
        )
    )
    driver = DmaDriver(  # type: ignore[arg-type]
        target,
        clock=clock,
        sleep=clock.sleep,
    )

    driver.wait_complete(2, timeout_s=1.0, poll_interval_s=0.2)

    assert target.commands == [
        DmaCommand.CHANNEL_START,
        DmaCommand.CHANNEL_STATUS_GET,
        DmaCommand.CHANNEL_STATUS_GET,
        DmaCommand.CHANNEL_STATUS_GET,
    ]
    assert target.timeouts == pytest.approx([1.0, 1.0, 0.8, 0.6])


def test_wait_complete_timeout_attempts_stop_and_deconfigure() -> None:
    clock = _Clock()
    target = _DeadlineTarget((_status(free=False),))
    driver = DmaDriver(  # type: ignore[arg-type]
        target,
        clock=clock,
        sleep=clock.sleep,
    )

    with pytest.raises(RequestTimeout, match="DMA channel 3 completion"):
        driver.wait_complete(3, timeout_s=0.5, poll_interval_s=0.25)

    assert target.commands[-2:] == [
        DmaCommand.CHANNEL_STOP,
        DmaCommand.CHANNEL_DECONFIGURE,
    ]


def test_wait_complete_keeps_primary_and_all_cleanup_failures() -> None:
    target = _DeadlineTarget(
        (_status(free=False, events=DmaIrqEvent.ERROR),),
        cleanup_failures=frozenset(
            {
                DmaCommand.CHANNEL_STOP,
                DmaCommand.CHANNEL_DECONFIGURE,
            }
        ),
    )
    driver = DmaDriver(target)  # type: ignore[arg-type]

    with pytest.raises(OperationCleanupError) as captured:
        driver.wait_complete(4, timeout_s=1.0)

    error = captured.value
    assert isinstance(error.primary_error, RuntimeError)
    assert "completed with ERROR" in str(error.primary_error)
    assert [item.stage for item in error.cleanup_failures] == [
        "DMA channel stop",
        "DMA channel deconfigure",
    ]
    assert target.commands[-2:] == [
        DmaCommand.CHANNEL_STOP,
        DmaCommand.CHANNEL_DECONFIGURE,
    ]


def test_start_wait_is_a_compatibility_alias_for_total_deadline() -> None:
    clock = _Clock()
    target = _DeadlineTarget((_status(free=False),))
    driver = DmaDriver(  # type: ignore[arg-type]
        target,
        clock=clock,
        sleep=clock.sleep,
    )

    with pytest.raises(RequestTimeout):
        driver.start_wait(1, max_polls=2, poll_interval_s=0.25)

    assert clock.now == pytest.approx(0.5)
    assert target.commands[-2:] == [
        DmaCommand.CHANNEL_STOP,
        DmaCommand.CHANNEL_DECONFIGURE,
    ]
