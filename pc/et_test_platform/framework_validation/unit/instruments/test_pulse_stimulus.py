# 公共脉冲激励 Adapter 单元测试。
#
# 职责：验证单次脉冲调用顺序、时间证据和非法输入失败关闭。
# 边界：仅使用内存替身，不连接真实仪器。
# 依赖：仅依赖 pytest 和被测 MSO5204 Pulse Adapter。

from __future__ import annotations

from types import SimpleNamespace

import pytest

from et_test_platform.instruments.signal_generators.mso5204 import (
    Mso5204PulseBinding,
    Mso5204PulseStimulus,
)


class _FakeSource:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def output_enabled_set(self, channel: int, enabled: bool) -> None:
        self.calls.append(("output", channel, enabled))

    def apply_pulse(self, channel: int, *values: float) -> None:
        self.calls.append(("apply_pulse", channel, *values))

    def pulse_duty_cycle_set(self, channel: int, duty_percent: float) -> None:
        self.calls.append(("duty", channel, duty_percent))


class _FakeDriver:
    def __init__(self) -> None:
        self.source = _FakeSource()
        self.identity = "fake-scope"
        self.opened = False
        self.closed = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True


# 验证Adapter先配置后使能，且在返回前关闭输出并保留时间窗。
def test_emit_pulse_has_bounded_output_and_timeline(monkeypatch) -> None:
    driver = _FakeDriver()
    stimulus = Mso5204PulseStimulus(
        driver,  # type: ignore[arg-type]
        Mso5204PulseBinding(output_channel=2, amplitude_vpp=3.0, offset_v=1.5),
    )
    timeline = iter((10.0, 10.002))
    monkeypatch.setattr(
        "et_test_platform.instruments.signal_generators.mso5204.time.monotonic",
        lambda: next(timeline),
    )
    sleep_call = SimpleNamespace(width_s=None)
    monkeypatch.setattr(
        "et_test_platform.instruments.signal_generators.mso5204.time.sleep",
        lambda width_s: setattr(sleep_call, "width_s", width_s),
    )

    event = stimulus.emit_pulse(width_s=0.001)

    assert event.started_s == 10.0
    assert event.completed_s == 10.002
    assert sleep_call.width_s == 0.001
    assert driver.source.calls == [
        ("output", 2, False),
        ("apply_pulse", 2, 500.0, 3.0, 1.5, 0.0),
        ("duty", 2, 50.0),
        ("output", 2, True),
        ("output", 2, False),
    ]


# 验证非正脉宽在任何仪器调用前被拒绝。
@pytest.mark.parametrize("width_s", [0.0, -0.001])
def test_emit_pulse_rejects_non_positive_width(width_s: float) -> None:
    driver = _FakeDriver()
    stimulus = Mso5204PulseStimulus(
        driver,  # type: ignore[arg-type]
        Mso5204PulseBinding(output_channel=1, amplitude_vpp=1.8, offset_v=0.9),
    )

    with pytest.raises(ValueError, match="must be positive"):
        stimulus.emit_pulse(width_s=width_s)

    assert driver.source.calls == []


# 验证脉宽等待异常时仍执行输出关闭，不把高电平泄漏到下一Case。
def test_emit_pulse_disables_output_when_wait_fails(monkeypatch) -> None:
    driver = _FakeDriver()
    stimulus = Mso5204PulseStimulus(
        driver,  # type: ignore[arg-type]
        Mso5204PulseBinding(output_channel=1, amplitude_vpp=1.8, offset_v=0.9),
    )
    monkeypatch.setattr(
        "et_test_platform.instruments.signal_generators.mso5204.time.sleep",
        lambda _width_s: (_ for _ in ()).throw(RuntimeError("wait failed")),
    )

    with pytest.raises(RuntimeError, match="wait failed"):
        stimulus.emit_pulse(width_s=0.001)

    assert driver.source.calls[-2:] == [("output", 1, True), ("output", 1, False)]
