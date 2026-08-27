# Reset-aware Target Session 生命周期无硬件测试。
#
# 职责：验证预期断线后的 HELLO/Registry 重建、身份保护和非重放边界。
# 边界：只使用脚本化 Framework/Target 替身，不触发真实复位或串口操作。
# 依赖：pytest、平台异常与 TargetLifecycleController。

from __future__ import annotations

from dataclasses import dataclass

from et_test_platform.core.errors import RequestTimeout
from et_test_platform.scheduling.target_lifecycle import TargetLifecycleController


@dataclass(frozen=True)
class _Hello:
    chip_id: str
    firmware_build_id: str


class _Target:
    def __init__(self) -> None:
        self.session_id = 11
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class _Framework:
    def __init__(self, *, disconnect: bool = True) -> None:
        self.target_client = _Target()
        self.chip_id = "chip"
        self.firmware_build_id = "build"
        self.disconnect = disconnect
        self.version_calls = 0
        self.hello_calls = 0
        self.discover_calls = 0

    def version_get(self) -> object:
        self.version_calls += 1
        if self.disconnect:
            raise RequestTimeout("expected reset")
        return object()

    def hello(self) -> _Hello:
        self.hello_calls += 1
        self.target_client.session_id = 22
        return _Hello(chip_id="chip", firmware_build_id="build")

    def discover_services(self) -> tuple[()]:
        self.discover_calls += 1
        return ()


# 验证控制器只用安全查询观察断线，并在新Session发布后返回完整时间线。
def test_target_lifecycle_reconnects_without_replaying_ip_commands() -> None:
    framework = _Framework()
    now = [0.0]
    controller = TargetLifecycleController(
        framework,  # type: ignore[arg-type]
        clock=lambda: now[0],
        sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
    )

    transition = controller.wait_for_reset_and_reconnect(timeout_s=1.0)

    assert transition.old_session_id == 11
    assert transition.new_session_id == 22
    assert framework.version_calls == 1
    assert framework.hello_calls == 1
    assert framework.discover_calls == 1
    assert framework.target_client.close_calls == 1
    assert framework.target_client.open_calls == 1


# 验证旧Session始终在线时在统一Deadline失败，不伪造复位或主动关闭连接。
def test_target_lifecycle_requires_observed_disconnect() -> None:
    framework = _Framework(disconnect=False)
    now = [0.0]
    controller = TargetLifecycleController(
        framework,  # type: ignore[arg-type]
        clock=lambda: now[0],
        sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
    )

    try:
        controller.wait_for_reset_and_reconnect(timeout_s=0.25, probe_interval_s=0.1)
    except RequestTimeout:
        pass
    else:
        raise AssertionError("missing disconnect must fail closed")

    assert framework.target_client.close_calls == 0
    assert framework.hello_calls == 0
