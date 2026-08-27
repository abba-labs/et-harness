# 逻辑脉冲激励公共接口。
#
# 职责：为 Formal Case 提供仪器型号中立的单次脉冲激励和真实时间窗。
# 边界：不选择物理输出、不固定接线、不定义 DUT 电平也不实现 Case 断言。
# 依赖：仅依赖 Python 标准库的 Protocol 和 dataclass。

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# 记录一次真实脉冲的主机单调时间窗，供 Case 作为外部激励证据。
@dataclass(frozen=True, slots=True)
class PulseEvent:
    started_s: float
    completed_s: float


# 定义 Formal Case 可依赖的最小单次脉冲行为。
@runtime_checkable
class PulseStimulus(Protocol):
    # 返回稳定连接身份；读取属性不得触发设备 I/O。
    @property
    def identity(self) -> str: ...

    # 打开已显式配置的仪器连接；不得扫描或选择其他设备。
    def open(self) -> None: ...

    # 关闭当前连接，并在设备支持时保持激励输出为关闭状态。
    def close(self) -> None: ...

    # 发出一个有界高电平脉冲并在返回前关闭输出，同时返回真实执行时间窗。
    def emit_pulse(self, *, width_s: float) -> PulseEvent: ...


__all__ = ["PulseEvent", "PulseStimulus"]
