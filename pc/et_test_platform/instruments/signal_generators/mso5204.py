# MSO5204 内置波形源的公共脉冲激励 Adapter。
#
# 职责：把 PulseStimulus 映射到 MSO5204 AWG 原子 API，并记录真实执行时间窗。
# 边界：输出通道和模拟参数由 Bench 注入，不包含 DUT/IP 语义或断言。
# 依赖：仅依赖公共脉冲接口与现有 MSO5204 Driver。

from __future__ import annotations

import time
from dataclasses import dataclass

from ..oscilloscopes.mso5204.connection import create_mso5204_visa_driver
from ..oscilloscopes.mso5204.driver import Mso5204Driver
from .interface import PulseEvent

_HALF_PERIODS_PER_PULSE = 2.0
_DEFAULT_DUTY_PERCENT = 50.0


# 保存 Bench 声明的 AWG 输出事实；不包含 Case 脉宽或测试期望。
@dataclass(frozen=True, slots=True)
class Mso5204PulseBinding:
    output_channel: int
    amplitude_vpp: float
    offset_v: float


# 将型号无关的单次脉冲接口映射为 MSO5204 AWG 的安全输出生命周期。
class Mso5204PulseStimulus:
    def __init__(self, driver: Mso5204Driver, binding: Mso5204PulseBinding) -> None:
        self._driver = driver
        self._binding = binding

    # 返回底层 VISA 连接身份；不发送 SCPI。
    @property
    def identity(self) -> str:
        return self._driver.identity

    # 打开已配置的 VISA 资源；不使能 AWG 输出。
    def open(self) -> None:
        self._driver.open()

    # 先关闭 AWG 输出再释放连接，防止 Case 结束后保留激励。
    def close(self) -> None:
        self._driver.source.output_enabled_set(self._binding.output_channel, False)
        self._driver.close()

    # 配置对称脉冲并使能一个高电平窗；无效脉宽在任何设备 I/O 前拒绝。
    def emit_pulse(self, *, width_s: float) -> PulseEvent:
        if width_s <= 0.0:
            raise ValueError("pulse width_s must be positive")

        channel = self._binding.output_channel
        frequency_hz = 1.0 / (_HALF_PERIODS_PER_PULSE * width_s)
        self._driver.source.output_enabled_set(channel, False)
        self._driver.source.apply_pulse(
            channel,
            frequency_hz,
            self._binding.amplitude_vpp,
            self._binding.offset_v,
            0.0,
        )
        self._driver.source.pulse_duty_cycle_set(channel, _DEFAULT_DUTY_PERCENT)

        started_s = time.monotonic()
        self._driver.source.output_enabled_set(channel, True)
        try:
            time.sleep(width_s)
        finally:
            self._driver.source.output_enabled_set(channel, False)
        completed_s = time.monotonic()

        return PulseEvent(started_s=started_s, completed_s=completed_s)


# 根据显式 VISA 资源和 Bench AWG 事实构造未打开的公共激励器。
def create_mso5204_pulse_stimulus(
    resource_name: str,
    binding: Mso5204PulseBinding,
    *,
    visa_library: str | None = None,
    timeout_s: float = 5.0,
) -> Mso5204PulseStimulus:
    driver = create_mso5204_visa_driver(
        resource_name,
        visa_library=visa_library,
        timeout_s=timeout_s,
    )
    return Mso5204PulseStimulus(driver, binding)


__all__ = [
    "Mso5204PulseBinding",
    "Mso5204PulseStimulus",
    "create_mso5204_pulse_stimulus",
]
