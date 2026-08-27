# Framework Validation测试模块。
#
# 职责：验证test_deadline 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import math

import pytest

from et_test_platform.core.deadline import OperationDeadline
from et_test_platform.core.errors import RequestTimeout


class _FakeClock:
    def __init__(self) -> None:
        self.now = 10.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_deadline_rejects_invalid_time_budgets() -> None:
    for value in (0, -1, True, math.inf, math.nan):
        with pytest.raises(ValueError, match="positive finite"):
            OperationDeadline.start(value)  # type: ignore[arg-type]


def test_deadline_reports_remaining_time_from_one_total_budget() -> None:
    clock = _FakeClock()
    deadline = OperationDeadline.start(
        2.0,
        clock=clock.monotonic,
        sleep=clock.sleep,
        label="uart exchange",
    )

    assert deadline.remaining_s() == pytest.approx(2.0)
    clock.now += 0.75
    assert deadline.remaining_s() == pytest.approx(1.25)
    assert not deadline.expired


def test_deadline_sleep_is_clamped_to_remaining_budget() -> None:
    clock = _FakeClock()
    deadline = OperationDeadline.start(
        0.5,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )

    deadline.sleep(2.0)

    assert clock.sleeps == [pytest.approx(0.5)]
    assert deadline.expired
    with pytest.raises(RequestTimeout, match="deadline expired"):
        deadline.remaining_s()
