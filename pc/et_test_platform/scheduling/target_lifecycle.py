# Reset-aware Target Session 生命周期控制。
#
# 职责：观察预期复位造成的通信中断，并在同一 Transport 上重新建立 HELLO 与 Service Registry。
# 边界：不触发复位、不解释 IP 事件、不重放业务命令，也不形成测试 PASS/FAIL。
# 依赖：仅依赖 FrameworkDriver、平台异常、单调时钟与有界等待函数。

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ..core.errors import ProtocolError, RequestTimeout, TransportError
from ..drivers.framework import FrameworkDriver


# 表示一次预期复位前后的决定性 Session 时间线；时间字段单位为秒。
@dataclass(frozen=True, slots=True)
class SessionTransition:
    old_session_id: int
    new_session_id: int
    disconnect_elapsed_s: float
    reconnect_elapsed_s: float


# 在显式总期限内观察断线并重建同一 DUT 的 Framework Session；不触发目标复位。
class TargetLifecycleController:
    def __init__(
        self,
        framework: FrameworkDriver,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._framework = framework
        self._clock = clock
        self._sleeper = sleeper

    # 等待预期复位导致的链路中断，再重新HELLO/Discover；业务命令不会被自动重放。
    def wait_for_reset_and_reconnect(
        self,
        *,
        timeout_s: float,
        probe_interval_s: float = 0.1,
    ) -> SessionTransition:
        if timeout_s <= 0 or probe_interval_s <= 0:
            raise ValueError("timeout_s and probe_interval_s must be positive")

        framework = self._framework
        target = framework.target_client
        old_session_id = target.session_id
        expected_chip_id = framework.chip_id
        expected_build_id = framework.firmware_build_id
        started = self._clock()
        deadline = started + timeout_s

        # Phase 1: Use only a retry-safe Framework query to prove the old Session became unusable.
        while self._clock() < deadline:
            try:
                framework.version_get()
            except (ProtocolError, RequestTimeout, TransportError):
                break
            self._sleeper(min(probe_interval_s, max(0.0, deadline - self._clock())))
        else:
            raise RequestTimeout("target did not disconnect before the expected-reset deadline")

        disconnect_elapsed_s = self._clock() - started
        target.close()

        # Phase 2: Reopen the configured Transport until HELLO and Registry both validate.
        last_error: Exception | None = None
        while self._clock() < deadline:
            try:
                target.open()
                hello = framework.hello()
                if hello.chip_id != expected_chip_id:
                    raise ProtocolError(
                        f"reconnected target changed chip identity to {hello.chip_id!r}"
                    )
                if hello.firmware_build_id != expected_build_id:
                    raise ProtocolError(
                        "reconnected target changed firmware build identity to "
                        f"{hello.firmware_build_id!r}"
                    )
                framework.discover_services()
                new_session_id = target.session_id
                if new_session_id == old_session_id:
                    raise ProtocolError("reconnected target reused the pre-reset Session ID")

                return SessionTransition(
                    old_session_id=old_session_id,
                    new_session_id=new_session_id,
                    disconnect_elapsed_s=disconnect_elapsed_s,
                    reconnect_elapsed_s=self._clock() - started,
                )
            except (ProtocolError, RequestTimeout, TransportError) as exc:
                last_error = exc
                target.close()
                self._sleeper(min(probe_interval_s, max(0.0, deadline - self._clock())))

        raise RequestTimeout(
            "target did not re-establish a valid Framework Session before the deadline"
        ) from last_error


__all__ = ["SessionTransition", "TargetLifecycleController"]
