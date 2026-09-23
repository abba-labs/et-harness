# RIGOL MSO5204 常用多步操作组合。
#
# 职责：提供常用 EDGE 配置、测量读取、触发/采集配置、波形读取和截图的易用层。
# 边界：只复用本型号公开原子 API，不隐藏测试 PASS/FAIL、不跨仪器编排，也不自动重试失败命令。
# 依赖：运行时仅依赖稳定模型和参数校验；Driver 仅用于类型检查，避免形成循环依赖。

from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from .._internal.errors import InstrumentProtocolError
from .models import (
    Mso5204AcquireConfig,
    Mso5204AcquireType,
    Mso5204AnalogChannel,
    Mso5204BandwidthLimit,
    Mso5204ChannelCoupling,
    Mso5204EdgeCaptureConfig,
    Mso5204MeasurementItem,
    Mso5204MeasurementStatistic,
    Mso5204RawWaveform,
    Mso5204RawWaveformConfig,
    Mso5204SignalMeasurements,
    Mso5204TimebaseMode,
    Mso5204TriggerConfig,
    Mso5204TriggerCoupling,
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
    _validate_positive_index,
    _validate_probe_ratio,
    _validate_scpi_token,
)

if TYPE_CHECKING:
    from .driver import Mso5204Driver

_SCREEN_POINT_MAX = 1000

# 仪器在无法给出有效测量时返回 9.9E+37；该量级远高于任何真实物理量，用于识别无效结果。
_INVALID_MEASUREMENT_THRESHOLD = 1e30


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


def _validate_trigger_config(config: Mso5204TriggerConfig) -> None:
    if config.mode is not None:
        _validate_scpi_token(
            config.mode,
            tuple(item.value for item in Mso5204TriggerMode),
            "trigger mode",
        )
    if config.sweep is not None:
        _validate_scpi_token(
            config.sweep,
            tuple(item.value for item in Mso5204TriggerSweep),
            "trigger sweep",
        )
    if config.coupling is not None:
        _validate_scpi_token(
            config.coupling,
            tuple(item.value for item in Mso5204TriggerCoupling),
            "trigger coupling",
        )
    if config.edge_slope is not None:
        _validate_scpi_token(
            config.edge_slope,
            tuple(item.value for item in Mso5204TriggerSlope),
            "edge trigger slope",
        )
    if config.edge_source is not None:
        _validate_channel(int(config.edge_source))
    if config.edge_level_v is not None:
        _validate_finite(config.edge_level_v, "edge trigger level")
    if config.holdoff_s is not None:
        _validate_float_range(config.holdoff_s, "trigger holdoff", 8e-9, 10.0)


def _validate_acquire_config(config: Mso5204AcquireConfig) -> None:
    if config.acquire_type is not None:
        _validate_scpi_token(
            config.acquire_type,
            tuple(item.value for item in Mso5204AcquireType),
            "acquisition type",
        )
    if config.average_count is not None:
        _validate_average_count(config.average_count)
        # 与 EDGE 捕获配置保持同一语义：平均次数只在显式声明 AVERage 类型时才有意义，
        # 否则会向处于 NORM/PEAK 模式的仪器下发自相矛盾的平均命令。
        if config.acquire_type != Mso5204AcquireType.AVERAGE:
            raise ValueError("average_count requires acquire_type=Mso5204AcquireType.AVERAGE")


def _validate_raw_waveform_config(config: Mso5204RawWaveformConfig) -> None:
    _validate_channel(int(config.channel))
    _validate_positive_finite(config.read_timeout_s, "waveform read timeout")
    _validate_positive_finite(config.acquire_timeout_s, "acquire timeout")
    if config.start is not None:
        _validate_positive_index(config.start, "waveform start")
    if config.stop is not None:
        _validate_positive_index(config.stop, "waveform stop")
    if config.start is not None and config.stop is not None and config.stop < config.start:
        raise ValueError("waveform range must satisfy start <= stop")


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

    # 读取单个测量项并过滤仪器无效值；无效或越界响应返回 None，由调用方决定是否重试。
    def measure_item(
        self,
        item: Mso5204MeasurementItem | str,
        channel: int | Mso5204AnalogChannel,
    ) -> float | None:
        value = self._driver.measurement.item_get(item, _analog_source(channel))
        if value is None or abs(value) >= _INVALID_MEASUREMENT_THRESHOLD:
            return None
        return value

    # 配置跨通道延迟/相位测量的 A/B 源；延迟项和相位项都不接受单通道源。
    def configure_delay_sources(
        self,
        source_a: int | Mso5204AnalogChannel,
        source_b: int | Mso5204AnalogChannel,
    ) -> None:
        a = _analog_source(source_a)
        b = _analog_source(source_b)
        driver = self._driver
        driver.measurement.delay_source_a_set(a)
        driver.measurement.delay_source_b_set(b)
        driver.measurement.phase_source_a_set(a)
        driver.measurement.phase_source_b_set(b)

    # 读取跨通道延迟或相位测量项；先配置 A/B 源再查询，无效响应返回 None。
    def measure_delay(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: int | Mso5204AnalogChannel,
        source_b: int | Mso5204AnalogChannel,
    ) -> float | None:
        # 实测结论：跨通道延迟/相位项不会沿用单通道源，必须先显式设置 A/B 源，
        # 否则仪器返回的是上一次遗留的源组合，测量值会静默错配。
        self.configure_delay_sources(source_a, source_b)
        value = self._driver.measurement.item_get(
            item,
            _analog_source(source_a),
            _analog_source(source_b),
        )
        if value is None or abs(value) >= _INVALID_MEASUREMENT_THRESHOLD:
            return None
        return value

    # 读取统计测量项；无效响应返回 None，不触发统计复位或显示开关。
    def measure_statistic(
        self,
        statistic: Mso5204MeasurementStatistic | str,
        item: Mso5204MeasurementItem | str,
        channel: int | Mso5204AnalogChannel,
    ) -> float | None:
        value = self._driver.measurement.statistics_item_get(
            statistic,
            item,
            _analog_source(channel),
        )
        if value is None or abs(value) >= _INVALID_MEASUREMENT_THRESHOLD:
            return None
        return value

    # 按显式 Config 配置触发系统；None 字段保持仪器当前状态不变。
    def configure_trigger(self, config: Mso5204TriggerConfig) -> None:
        _validate_trigger_config(config)
        driver = self._driver
        if config.mode is not None:
            driver.trigger.mode_set(config.mode)
        if config.coupling is not None:
            driver.trigger.coupling_set(config.coupling)
        if config.holdoff_s is not None:
            driver.trigger.holdoff_set(config.holdoff_s)
        if config.noise_reject is not None:
            driver.trigger.noise_reject_set(config.noise_reject)
        if config.edge_source is not None:
            driver.trigger.edge_source_set(_analog_source(config.edge_source))
        if config.edge_slope is not None:
            driver.trigger.edge_slope_set(config.edge_slope)
        if config.edge_level_v is not None:
            driver.trigger.edge_level_set(config.edge_level_v)
        # 扫描方式最后设置：SINGle 会立即武装单次采集，提前设置会被后续触发参数覆盖。
        if config.sweep is not None:
            driver.trigger.sweep_set(config.sweep)

    # 按显式 Config 配置采集系统；average_count 只在 AVERage 类型下允许。
    def configure_acquire(self, config: Mso5204AcquireConfig) -> None:
        _validate_acquire_config(config)
        driver = self._driver
        if config.acquire_type is not None:
            driver.acquire.type_set(config.acquire_type)
        if config.average_count is not None:
            driver.acquire.averages_set(config.average_count)
        if config.memory_depth is not None:
            driver.acquire.memory_depth_set(config.memory_depth)
        if config.anti_alias is not None:
            driver.acquire.anti_alias_set(config.anti_alias)

    # 等待一次采集进入可读状态；超时返回 False，不抛异常也不强制触发。
    def wait_acquired(self, *, timeout_s: float = 6.0) -> bool:
        checked = _validate_positive_finite(timeout_s, "acquire timeout")
        deadline = time.monotonic() + checked
        while time.monotonic() < deadline:
            try:
                status = self._driver.trigger.status_get().upper()
            except Exception:
                return False
            if status not in ("WAIT", "RUN", ""):
                return True
            time.sleep(0.2)
        return False

    # 读取 RAW 深存储波形；按实测要求先停止采集再读，读后可恢复连续运行。
    def read_raw_waveform(self, config: Mso5204RawWaveformConfig) -> Mso5204RawWaveform:
        _validate_raw_waveform_config(config)
        driver = self._driver
        channel = _validate_channel(int(config.channel))

        driver.channel.display_set(channel, True)
        driver.waveform.source_set(_analog_source(channel))
        driver.waveform.format_set(Mso5204WaveformFormat.BYTE)
        driver.waveform.mode_set(Mso5204WaveformMode.RAW)

        if config.stop_first:
            # 深存储填充需要时间：等待采集就绪后再 STOP，否则会读到未完成的数据。
            self.wait_acquired(timeout_s=config.acquire_timeout_s)
            with suppress(Exception):
                driver.basic.stop()
            self._await_stopped()

        try:
            payload = driver.waveform.data_get(timeout_s=config.read_timeout_s)
            # 空负载说明仪器没有给出可用数据（常见于采集未就绪或链路异常）；
            # 此处失败关闭，避免把空波形当成"测到 0 个点"的正常结果传给调用方。
            if not payload:
                raise InstrumentProtocolError(
                    f"empty RAW waveform payload on CHANnel{channel}; acquisition may not be ready"
                )
            # preamble 必须在恢复 RUN 之前读取：它描述的是刚读出的这批数据，
            # 若先重启采集，换算系数可能已经对应到下一次采集。
            preamble = driver.waveform.preamble_get()
        finally:
            # 无论读取成败都恢复连续采集，避免把示波器留在 STOP 状态影响后续用例。
            if config.stop_first and config.restart_run:
                with suppress(Exception):
                    driver.basic.run()

        samples = tuple(
            (value - preamble.y_origin - preamble.y_reference) * preamble.y_increment_v
            for value in payload
        )
        return Mso5204RawWaveform(
            channel=channel,
            samples=samples,
            x_increment_s=preamble.x_increment_s,
            x_origin_s=preamble.x_origin_s,
        )

    # 等待示波器真正离开采集状态；只读触发状态，超时后直接返回而不阻塞调用方。
    def _await_stopped(self, *, attempts: int = 20) -> None:
        for _ in range(attempts):
            time.sleep(0.15)
            try:
                status = self._driver.trigger.status_get()
            except Exception:
                continue
            if status.upper() in ("TD", "STOP", "STOPPED", "AUTO"):
                return

    # 保存一次屏幕截图；返回写入的字节数，BMP 数据由仪器直接给出。
    def save_screenshot(self, path: str | Path, *, timeout_s: float | None = None) -> int:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self._driver.display.screenshot_get(timeout_s=timeout_s)
        if not payload:
            raise ValueError("instrument returned an empty screenshot payload")
        target.write_bytes(payload)
        return len(payload)

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
