# MSO5204 逻辑信号观测 Adapter。
#
# 职责：把公共 SignalObserver 语义映射到现有 MSO5204 Driver 原子 API。
# 边界：物理通道和模拟前端参数由 Bench 注入，不包含 DUT/IP 语义或测试断言。
# 依赖：仅依赖公共示波器接口、MSO5204 Driver、连接工厂和稳定数据模型。

from __future__ import annotations

from dataclasses import dataclass

from ..interface import SignalEdge, SignalObservation
from .connection import create_mso5204_visa_driver
from .driver import Mso5204Driver
from .models import (
    Mso5204ChannelCoupling,
    Mso5204EdgeCaptureConfig,
    Mso5204MeasurementItem,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
)

_EDGE_MAP = {
    SignalEdge.RISING: Mso5204TriggerSlope.RISING,
    SignalEdge.FALLING: Mso5204TriggerSlope.FALLING,
    SignalEdge.EITHER: Mso5204TriggerSlope.EITHER,
}


# 保存由 Bench 提供的 MSO5204 模拟前端事实；不包含时基或测试期望值。
@dataclass(frozen=True, slots=True)
class Mso5204ObserverBinding:
    channel: int
    vertical_scale_v: float
    trigger_level_v: float
    probe_ratio: float | None = None


# 实现公共 SignalObserver；每个方法只组合本型号公开 Driver API。
class Mso5204SignalObserver:
    def __init__(self, driver: Mso5204Driver, binding: Mso5204ObserverBinding) -> None:
        self._driver = driver
        self._binding = binding

    # 返回底层 VISA 连接身份；只读本地属性，不发送 SCPI。
    @property
    def identity(self) -> str:
        return self._driver.identity

    # 打开已指定的 VISA 资源；不扫描仪器或自动选择通道。
    def open(self) -> None:
        self._driver.open()

    # 关闭底层 VISA 资源；不隐式复位示波器或 DUT。
    def close(self) -> None:
        self._driver.close()

    # 把公共边沿捕获参数与 Bench 模拟前端事实映射到 MSO5204 Typed Config。
    def configure_edge_capture(self, *, time_scale_s: float, edge: SignalEdge) -> None:
        self._driver.operations.configure_edge_capture(
            Mso5204EdgeCaptureConfig(
                channel=self._binding.channel,
                vertical_scale_v=self._binding.vertical_scale_v,
                time_scale_s=time_scale_s,
                trigger_level_v=self._binding.trigger_level_v,
                trigger_slope=_EDGE_MAP[edge],
                coupling=Mso5204ChannelCoupling.DC,
                probe_ratio=self._binding.probe_ratio,
                trigger_sweep=Mso5204TriggerSweep.NORMAL,
            )
        )

    # 向 MSO5204 发送一次单次采集命令并保持既有触发配置；不等待触发或读取结果。
    def arm_single(self) -> None:
        self._driver.basic.single()

    # 向 MSO5204 启动连续采集；不改变 Bench 已配置的通道、探头和触发条件。
    def run(self) -> None:
        self._driver.basic.run()

    # 向 MSO5204 停止当前采集以稳定后续读取；不清除已采集波形或测量配置。
    def stop(self) -> None:
        self._driver.basic.stop()

    # 读取公共契约要求的五个物理量，并保留仪器原始异常和超时。
    def measure(self) -> SignalObservation:
        channel = self._binding.channel
        operations = self._driver.operations

        return SignalObservation(
            frequency_hz=operations.measure_frequency(channel),
            period_s=operations.measure_period(channel),
            positive_width_s=self._driver.measurement.item_get(
                Mso5204MeasurementItem.POSITIVE_WIDTH,
                f"CHANnel{channel}",
            ),
            duty_cycle_percent=operations.measure_duty_cycle(channel),
            vpp_v=operations.measure_vpp(channel),
        )


# 根据显式 VISA 资源和 Bench 模拟前端事实构造未打开的公共观测器。
def create_mso5204_signal_observer(
    resource_name: str,
    binding: Mso5204ObserverBinding,
    *,
    visa_library: str | None = None,
    timeout_s: float = 5.0,
) -> Mso5204SignalObserver:
    driver = create_mso5204_visa_driver(
        resource_name,
        visa_library=visa_library,
        timeout_s=timeout_s,
    )
    return Mso5204SignalObserver(driver, binding)


__all__ = [
    "Mso5204ObserverBinding",
    "Mso5204SignalObserver",
    "create_mso5204_signal_observer",
]
