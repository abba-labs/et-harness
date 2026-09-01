# 总 Deadline 的跨 IP 公共基础实现。
#
# 职责：提供芯片无关的总 Deadline语义，供 Driver、Case 和通信层复用。
# 边界：不包含任何 IP Command、Wire 字段、Bench 事实或设备 I/O。
# 依赖：仅依赖 Python 标准库和 core 层内部稳定类型。

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from .errors import RequestTimeout

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


# 提供 OperationDeadline 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True, slots=True)
class OperationDeadline:
    _expires_at: float
    _clock: Clock
    _sleep: Sleeper
    _label: str

    # 从当前单调时钟创建 Deadline，并拒绝无效时间预算。
    @classmethod
    def start(
        cls,
        timeout_s: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleeper = time.sleep,
        label: str = "operation",
    ) -> OperationDeadline:

        checked_timeout = require_positive_seconds(timeout_s, "timeout_s")
        if not label:
            raise ValueError("deadline label must not be empty")
        return cls(
            _expires_at=clock() + checked_timeout,
            _clock=clock,
            _sleep=sleep,
            _label=label,
        )

    # 返回当前时刻是否已经耗尽总时间预算。
    #
    # 该 API 提供平台级公共语义，不引入具体 IP 的业务策略或跨层硬件编排。
    @property
    def expired(self) -> bool:

        return self._clock() >= self._expires_at

    # 返回剩余时间；Deadline 耗尽时立即抛出明确异常。
    def remaining_s(self) -> float:

        remaining = self._expires_at - self._clock()
        if remaining <= 0:
            raise RequestTimeout(f"{self._label} deadline expired")
        return remaining

    # 在剩余预算内休眠，不允许一次休眠越过总 Deadline。
    def sleep(self, interval_s: float) -> None:

        checked_interval = require_positive_seconds(interval_s, "interval_s")
        self._sleep(min(checked_interval, self.remaining_s()))


# 校验一个正、有限且不能为 bool 的秒数。
#
# 该 API 提供平台级公共语义，不引入具体 IP 的业务策略或跨层硬件编排。
def require_positive_seconds(value: float, name: str) -> float:

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return converted
