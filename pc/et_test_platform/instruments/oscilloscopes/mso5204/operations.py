# RIGOL MSO5204 常用多步操作组合。
#
# 职责：提供常用 EDGE 配置、单通道自动测量和 NORMal/BYTE 屏幕波形读取的易用层。
# 边界：只复用本型号公开原子 API，不隐藏测试 PASS/FAIL、不跨仪器编排，也不自动重试失败命令。
# 依赖：运行时仅依赖稳定模型和参数校验；Driver 仅用于类型检查，避免形成循环依赖。

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    Mso5204AcquireType,
    Mso5204AnalogChannel,
    Mso5204BandwidthLimit,
    Mso5204ChannelCoupling,
    Mso5204EdgeCaptureConfig,
    Mso5204MeasurementItem,
    Mso5204SignalMeasurements,
    Mso5204TimebaseMode,
    Mso5204TriggerMode,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
    Mso5204Waveform,
    Mso5204WaveformFormat,
    Mso5204WaveformMode,
    Mso5204WaveformReadConfig,
)
from .validation import (
    _validate_average_count,
    _validate_channel,
    _validate_finite,
    _validate_float_range,
    _validate_int_range,
    _validate_positive_finite,
    _validate_probe_ratio,
    _validate_scpi_token,
)

if TYPE_CHECKING:
    from .driver import Mso5204Driver

_SCREEN_POINT_MAX = 1000


def _analog_source(channel: int | Mso5204AnalogChannel) -> str:
    return f"CHANnel{_validate_channel(int(channel))}"


def _validate_edge_capture_config(config: Mso5204EdgeCaptureConfig) -> None:
    _validate_channel(int(config.channel))
    scale = _validate_positive_finite(config.vertical_scale_v, "vertical scale")
    _validate_float_range(config.time_scale_s, "time scale", 2e-9, 1000.0)
    _validate_scpi_token(
        config.coupling,
        tuple(item.value for item in Mso5204ChannelCoupling),
        "channel coupling",
    )
    _validate_scpi_token(
        config.trigger_slope,
        tuple(item.value for item in Mso5204TriggerSlope),
        "edge trigger slope",
    )
    if config.bandwidth_limit is not None:
        _validate_scpi_token(
            config.bandwidth_limit,
            tuple(item.value for item in Mso5204BandwidthLimit),
            "bandwidth limit",
        )
    offset = 0.0
    if config.vertical_offset_v is not None:
        offset = _validate_float_range(
            config.vertical_offset_v,
            "vertical offset",
            -100.0,
            100.0,
        )
    if config.time_offset_s is not None:
        _validate_finite(config.time_offset_s, "time offset")
    if config.probe_ratio is not None:
        _validate_probe_ratio(config.probe_ratio)
    if config.acquire_type is not None:
        _validate_scpi_token(
            config.acquire_type,
            tuple(item.value for item in Mso5204AcquireType),
            "acquisition type",
        )
    if config.trigger_sweep is not None:
        _validate_scpi_token(
            config.trigger_sweep,
            tuple(item.value for item in Mso5204TriggerSweep),
            "trigger sweep",
        )
    lower = -5.0 * scale - offset
    upper = 5.0 * scale - offset
    _validate_float_range(config.trigger_level_v, "trigger level", lower, upper)
    if config.average_count is not None:
        _validate_average_count(config.average_count)
        if config.acquire_type != Mso5204AcquireType.AVERAGE:
            raise ValueError("average_count requires acquire_type=Mso5204AcquireType.AVERAGE")


def _validate_waveform_read_config(config: Mso5204WaveformReadConfig) -> None:
    _validate_channel(int(config.channel))
    start = _validate_int_range(config.start, "waveform start", 1, _SCREEN_POINT_MAX)
    stop = _validate_int_range(config.stop, "waveform stop", 1, _SCREEN_POINT_MAX)
    if stop < start:
        raise ValueError("waveform range must satisfy start <= stop")
    if config.timeout_s is not None:
        _validate_positive_finite(config.timeout_s, "waveform timeout")


# 提供 MSO5204 高频使用场景的薄易用层；每个方法仍由公开原子 Control 组成，测试判定留给 Case。
class Mso5204Operations:
    def __init__(self, driver: Mso5204Driver) -> None:
        self._driver = driver

    # 按显式 Config 配置单模拟通道 EDGE 捕获；None 可选项保持仪器当前状态不变。
    def configure_edge_capture(self, config: Mso5204EdgeCaptureConfig) -> None:
        _validate_edge_capture_config(config)
        driver = self._driver
        number = _validate_channel(int(config.channel))
        driver.channel.display_set(number, True)
        if config.probe_ratio is not None:
            driver.channel.probe_ratio_set(number, config.probe_ratio)
        driver.channel.coupling_set(number, config.coupling)
        if config.bandwidth_limit is not None:
            driver.channel.bandwidth_limit_set(number, config.bandwidth_limit)
        driver.channel.scale_set(number, config.vertical_scale_v)
        if config.vertical_offset_v is not None:
            driver.channel.offset_set(number, config.vertical_offset_v)
        driver.timebase.mode_set(Mso5204TimebaseMode.YT)
        driver.timebase.main_scale_set(config.time_scale_s)
        if config.time_offset_s is not None:
            driver.timebase.main_offset_set(config.time_offset_s)
        if config.acquire_type is not None:
            driver.acquire.type_set(config.acquire_type)
        if config.average_count is not None:
            driver.acquire.averages_set(config.average_count)
        driver.trigger.mode_set(Mso5204TriggerMode.EDGE)
        driver.trigger.edge_source_set(f"CHANnel{number}")
        driver.trigger.edge_slope_set(config.trigger_slope)
        driver.trigger.edge_level_set(config.trigger_level_v)
        if config.trigger_sweep is not None:
            driver.trigger.sweep_set(config.trigger_sweep)

    # 读取指定模拟通道频率，单位 Hz；只执行一次 MEASure:ITEM? Query。
    def measure_frequency(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.FREQUENCY, channel)

    # 读取指定模拟通道周期，单位 s；只执行一次 MEASure:ITEM? Query。
    def measure_period(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.PERIOD, channel)

    # 读取指定模拟通道正占空比，单位 %；只执行一次 MEASure:ITEM? Query。
    def measure_duty_cycle(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.POSITIVE_DUTY, channel)

    # 读取指定模拟通道峰峰值，单位 V；只执行一次 MEASure:ITEM? Query。
    def measure_vpp(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.VPP, channel)

    # 读取指定模拟通道 RMS，单位 V；只执行一次 MEASure:ITEM? Query。
    def measure_vrms(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.VRMS, channel)

    # 读取指定模拟通道上升时间，单位 s；只执行一次 MEASure:ITEM? Query。
    def measure_rise_time(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.RISE_TIME, channel)

    # 读取指定模拟通道下降时间，单位 s；只执行一次 MEASure:ITEM? Query。
    def measure_fall_time(self, channel: int | Mso5204AnalogChannel) -> float:
        return self._measure(Mso5204MeasurementItem.FALL_TIME, channel)

    # 一次返回频率、周期、占空比、Vpp、Vrms、上升/下降时间；不对结果做阈值判定。
    def measure_signal(self, channel: int | Mso5204AnalogChannel) -> Mso5204SignalMeasurements:
        return Mso5204SignalMeasurements(
            frequency_hz=self.measure_frequency(channel),
            period_s=self.measure_period(channel),
            duty_cycle_percent=self.measure_duty_cycle(channel),
            vpp_v=self.measure_vpp(channel),
            vrms_v=self.measure_vrms(channel),
            rise_time_s=self.measure_rise_time(channel),
            fall_time_s=self.measure_fall_time(channel),
        )

    # 按 NORMal/BYTE 屏幕波形流程读取最多 1000 点，并换算为时间和幅值物理量。
    def read_screen_waveform(self, config: Mso5204WaveformReadConfig) -> Mso5204Waveform:
        _validate_waveform_read_config(config)
        driver = self._driver
        driver.waveform.source_set(_analog_source(config.channel))
        driver.waveform.mode_set(Mso5204WaveformMode.NORMAL)
        driver.waveform.format_set(Mso5204WaveformFormat.BYTE)
        driver.waveform.start_set(config.start)
        driver.waveform.stop_set(config.stop)
        preamble = driver.waveform.preamble_get()
        if preamble.format_code != 0:
            raise ValueError(f"expected BYTE waveform preamble, got format {preamble.format_code}")
        payload = driver.waveform.data_get(timeout_s=config.timeout_s)
        samples = tuple(
            (value - preamble.y_origin - preamble.y_reference) * preamble.y_increment_v
            for value in payload
        )
        times = tuple(
            preamble.x_origin_s + (index - preamble.x_reference) * preamble.x_increment_s
            for index in range(len(payload))
        )
        return Mso5204Waveform(preamble=preamble, samples=samples, times_s=times)

    def _measure(
        self,
        item: Mso5204MeasurementItem,
        channel: int | Mso5204AnalogChannel,
    ) -> float:
        return self._driver.measurement.item_get(item, _analog_source(channel))


# 兼容旧入口：配置最常见的模拟通道 EDGE 捕获链；发送顺序保持原有九条命令不变。
def configure_edge_capture(
    driver: Mso5204Driver,
    channel: int | Mso5204AnalogChannel,
    *,
    vertical_scale_v: float,
    time_scale_s: float,
    trigger_level: float,
    trigger_slope: Mso5204TriggerSlope = Mso5204TriggerSlope.RISING,
) -> None:
    config = Mso5204EdgeCaptureConfig(
        channel=channel,
        vertical_scale_v=vertical_scale_v,
        time_scale_s=time_scale_s,
        trigger_level_v=trigger_level,
        trigger_slope=trigger_slope,
        coupling=Mso5204ChannelCoupling.DC,
    )
    Mso5204Operations(driver).configure_edge_capture(config)


# 兼容函数式入口：读取常用单通道测量快照；不对结果做阈值判定。
def measure_signal(
    driver: Mso5204Driver,
    channel: int | Mso5204AnalogChannel,
) -> Mso5204SignalMeasurements:
    return Mso5204Operations(driver).measure_signal(channel)


# 兼容旧入口：按 NORMal/BYTE 流程读取屏幕波形，并换算为时间和幅值物理量。
def read_screen_waveform(
    driver: Mso5204Driver,
    channel: int | Mso5204AnalogChannel,
    *,
    start: int = 1,
    stop: int = 1000,
    timeout_s: float | None = None,
) -> Mso5204Waveform:
    config = Mso5204WaveformReadConfig(
        channel=channel,
        start=start,
        stop=stop,
        timeout_s=timeout_s,
    )
    return Mso5204Operations(driver).read_screen_waveform(config)
