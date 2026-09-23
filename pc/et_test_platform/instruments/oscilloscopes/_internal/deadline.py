# 示波器库自包含操作 Deadline。
#
# 职责：提供一次顶层操作的总时间预算，供 SCPI 会话和 VISA Transport 复用剩余时间。
# 边界：不包含型号命令、测试期望值，也不自行决定重试策略。
# 依赖：仅依赖 Python 标准库与本库异常。

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from .errors import OscilloscopeTimeout

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


# 校验一个正、有限且不能为 bool 的秒数；非法输入在触达设备前立即拒绝。
def require_positive_seconds(value: float, name: str) -> float:

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return converted


# 表示一次操作的总时间预算；嵌套调用只消耗剩余时间，不重新获得完整超时。
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

    # 返回当前时刻是否已经耗尽总时间预算；只读单调时钟，不触达设备。
    @property
    def expired(self) -> bool:

        return self._clock() >= self._expires_at

    # 返回剩余秒数；预算耗尽时立即抛出超时异常，供上层失败关闭。
    def remaining_s(self) -> float:

        remaining = self._expires_at - self._clock()
        if remaining <= 0:
            raise OscilloscopeTimeout(f"{self._label} deadline expired")
        return remaining

    # 在剩余预算内休眠；单次休眠不允许越过总 Deadline。
    def sleep(self, interval_s: float) -> None:

        checked_interval = require_positive_seconds(interval_s, "interval_s")
        self._sleep(min(checked_interval, self.remaining_s()))


__all__ = ["OperationDeadline", "require_positive_seconds"]
