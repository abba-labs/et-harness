# MSO5204 台架级便捷接口。
#
# 职责：把连接生命周期、常用配置、测量和波形读取收敛成一个可直接上手的台架对象。
# 边界：不做 PASS/FAIL 判定、不选择物理通道、不隐藏仪器异常，也不替代原子 API。
# 依赖：仅依赖本型号 Driver、连接工厂、稳定模型与 data 目录，不依赖宿主工程代码。

from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path

from .analysis import Wave, dead_time_s, edge_offset_s
from .connection import create_mso5204_visa_driver
from .driver import Mso5204Driver
from .models import (
    Mso5204AcquireConfig,
    Mso5204AnalogChannel,
    Mso5204ChannelCoupling,
    Mso5204EdgeCaptureConfig,
    Mso5204MeasurementItem,
    Mso5204MeasurementStatistic,
    Mso5204RawWaveform,
    Mso5204RawWaveformConfig,
    Mso5204SignalMeasurements,
    Mso5204TriggerConfig,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
    Mso5204Waveform,
    Mso5204WaveformReadConfig,
)
from .operations import Mso5204Operations
from .validation import _validate_channel, _validate_positive_finite

_DEFAULT_TIMEOUT_S = 10.0
_DEFAULT_SCALE_V = 1.0
_DEFAULT_TRIGGER_LEVEL_V = 1.5


# 提供 MSO5204 台架级便捷入口；支持 with 语句自动关闭连接，构造阶段不访问仪器。
class Mso5204Scope:
    def __init__(
        self,
        resource_name: str,
        *,
        visa_library: str | None = "@py",
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        channel: int | Mso5204AnalogChannel = Mso5204AnalogChannel.CH1,
        vertical_scale_v: float = _DEFAULT_SCALE_V,
        trigger_level_v: float = _DEFAULT_TRIGGER_LEVEL_V,
    ) -> None:
        self._driver: Mso5204Driver = create_mso5204_visa_driver(
            resource_name,
            visa_library=visa_library,
            timeout_s=_validate_positive_finite(timeout_s, "timeout_s"),
        )
        self._channel = _validate_channel(int(channel))
        self._vertical_scale_v = _validate_positive_finite(vertical_scale_v, "vertical scale")
        self._trigger_level_v = trigger_level_v

    # 进入 with 语句时打开连接；不执行 autoscale 或修改仪器既有配置。
    def __enter__(self) -> Mso5204Scope:
        self.open()
        return self

    # 退出 with 语句时关闭连接；关闭失败不掩盖 with 代码块中抛出的原始异常。
    def __exit__(self, *exc: object) -> None:
        self.close()

    # 返回底层 Driver，供需要原子 API 的调用方直接使用。
    @property
    def driver(self) -> Mso5204Driver:
        return self._driver

    # 返回稳定 VISA 连接标识；只读本地属性，不发送 SCPI 命令。
    @property
    def identity(self) -> str:
        return self._driver.identity

    # 返回当前观测通道号；该值只影响便捷方法默认通道，不修改仪器通道配置。
    @property
    def channel(self) -> int:
        return self._channel

    # 打开已显式配置的 VISA 资源；连接异常直接向上层传播，不做重试或降级。
    def open(self) -> None:
        self._driver.open()

    # 关闭 VISA 资源；不隐式复位仪器，也不改变 DUT 状态。
    def close(self) -> None:
        self._driver.close()

    # 读取设备标识；执行一次 *IDN? Query，用于确认连到的是预期仪器。
    def identify(self) -> str:
        ident = self._driver.common.identity_get()
        return f"{ident.manufacturer},{ident.model},{ident.serial_number},{ident.software_version}"

    # 按常用默认值配置 EDGE 捕获并启动采集；默认参数可覆盖，等待时间可显式关闭。
    def prepare(
        self,
        *,
        time_scale_s: float,
        channel: int | Mso5204AnalogChannel | None = None,
        vertical_scale_v: float | None = None,
        trigger_level_v: float | None = None,
        trigger_slope: Mso5204TriggerSlope = Mso5204TriggerSlope.RISING,
        settle_s: float = 0.9,
    ) -> None:
        number = self._channel if channel is None else _validate_channel(int(channel))
        self._driver.operations.configure_edge_capture(
            Mso5204EdgeCaptureConfig(
                channel=number,
                vertical_scale_v=(
                    self._vertical_scale_v
                    if vertical_scale_v is None
                    else _validate_positive_finite(vertical_scale_v, "vertical scale")
                ),
                time_scale_s=time_scale_s,
                trigger_level_v=(
                    self._trigger_level_v if trigger_level_v is None else trigger_level_v
                ),
                trigger_slope=trigger_slope,
                coupling=Mso5204ChannelCoupling.DC,
                trigger_sweep=Mso5204TriggerSweep.AUTO,
            )
        )
        self._driver.basic.run()
        if settle_s > 0:
            time.sleep(settle_s)

    # 切换当前观测通道；只改变便捷方法默认值，不修改仪器通道开关或量程。
    def select_channel(self, channel: int | Mso5204AnalogChannel) -> None:
        self._channel = _validate_channel(int(channel))

    # 读取一个测量项；无效响应返回 None，不伪造数值也不重试。
    def measure(
        self,
        item: Mso5204MeasurementItem | str,
        channel: int | Mso5204AnalogChannel | None = None,
    ) -> float | None:
        number = self._channel if channel is None else int(channel)
        return self._driver.operations.measure_item(item, number)

    # 读取跨通道延迟或相位项；源通道必须显式给出，避免隐式配对错误。
    def measure_delay(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: int | Mso5204AnalogChannel,
        source_b: int | Mso5204AnalogChannel,
    ) -> float | None:
        operations = self._driver.operations
        return operations.measure_delay(item, source_a, source_b)

    # 读取统计测量项；不打开统计显示，调用方需自行确保统计已启用。
    def measure_statistic(
        self,
        statistic: Mso5204MeasurementStatistic | str,
        item: Mso5204MeasurementItem | str,
        channel: int | Mso5204AnalogChannel | None = None,
    ) -> float | None:
        number = self._channel if channel is None else int(channel)
        return self._driver.operations.measure_statistic(statistic, item, number)

    # 读取一次常用测量快照；等价于驱动层 measure_signal，保留以便台架代码统一入口。
    def measure_signal(
        self,
        channel: int | Mso5204AnalogChannel | None = None,
    ) -> Mso5204SignalMeasurements:
        number = self._channel if channel is None else int(channel)
        return self._driver.operations.measure_signal(number)

    # 配置触发系统；透传显式 Config，None 字段保持仪器当前状态。
    def configure_trigger(self, config: Mso5204TriggerConfig) -> None:
        self._driver.operations.configure_trigger(config)

    # 配置采集系统；透传显式 Config，None 字段保持仪器当前状态。
    def configure_acquire(self, config: Mso5204AcquireConfig) -> None:
        self._driver.operations.configure_acquire(config)

    # 读取屏幕波形（NORMal/BYTE，最多 1000 点）；返回已换算到物理单位的波形。
    def wave(
        self,
        channel: int | Mso5204AnalogChannel | None = None,
        *,
        start: int = 1,
        stop: int = 1000,
        timeout_s: float | None = None,
    ) -> Mso5204Waveform:
        number = self._channel if channel is None else int(channel)
        return self._driver.operations.read_screen_waveform(
            Mso5204WaveformReadConfig(
                channel=number,
                start=start,
                stop=stop,
                timeout_s=timeout_s,
            )
        )

    # 读取 RAW 深存储波形；停止与恢复采集由 Config 控制，适合 ns 级细节测量。
    def wave_raw(
        self,
        channel: int | Mso5204AnalogChannel | None = None,
        *,
        start: int | None = None,
        stop: int | None = None,
        read_timeout_s: float = 30.0,
    ) -> Mso5204RawWaveform:
        number = self._channel if channel is None else int(channel)
        return self._driver.operations.read_raw_waveform(
            Mso5204RawWaveformConfig(
                channel=number,
                start=start,
                stop=stop,
                read_timeout_s=read_timeout_s,
            )
        )

    # 保存屏幕截图到指定路径；返回写入字节数，目录不存在时自动创建。
    def screenshot(self, path: str | Path, *, timeout_s: float | None = None) -> int:
        return self._driver.operations.save_screenshot(path, timeout_s=timeout_s)

    # 读取屏幕波形并直接返回可分析对象；等价于 wave() 后再做一次纯计算换算。
    def read_wave(
        self,
        channel: int | Mso5204AnalogChannel | None = None,
        *,
        start: int = 1,
        stop: int = 1000,
        timeout_s: float | None = None,
    ) -> Wave:
        return Wave.from_screen(self.wave(channel, start=start, stop=stop, timeout_s=timeout_s))

    # 读取 RAW 深存储波形并直接返回可分析对象；适合 ns 级死区与相位测量。
    def read_wave_raw(
        self,
        channel: int | Mso5204AnalogChannel | None = None,
        *,
        start: int | None = None,
        stop: int | None = None,
        read_timeout_s: float = 30.0,
    ) -> Wave:
        return Wave.from_raw(
            self.wave_raw(
                channel,
                start=start,
                stop=stop,
                read_timeout_s=read_timeout_s,
            )
        )

    # 返回两路已读波形的边沿时间差（B - A）；按周期对齐，避免带上整数个周期。
    def edge_offset_s(
        self,
        wave_a: Wave,
        wave_b: Wave,
        *,
        rising_a: bool = True,
        rising_b: bool = True,
        nth: int = 0,
    ) -> float | None:
        return edge_offset_s(
            wave_a,
            wave_b,
            rising_a=rising_a,
            rising_b=rising_b,
            nth=nth,
        )

    # 返回两路互补 PWM 的死区时间，单位 s；direction 选择测量的边沿组合。
    def dead_time_s(
        self,
        wave_a: Wave,
        wave_b: Wave,
        *,
        direction: str = "a_fall_to_b_rise",
        max_gap_s: float | None = None,
    ) -> float | None:
        return dead_time_s(
            wave_a,
            wave_b,
            direction=direction,
            max_gap_s=max_gap_s,
        )

    # 停止连续采集；只发送一次 :STOP，用于需要稳定画面的读取场景。
    def stop(self) -> None:
        self._driver.basic.stop()

    # 启动连续采集；只发送一次 :RUN，不修改触发条件或通道配置。
    def run(self) -> None:
        self._driver.basic.run()

    # 一次性完成单次采集；不等待触发完成，由调用方决定后续读取时机。
    def single(self) -> None:
        self._driver.basic.single()

    # 强制产生一次触发；不修改触发条件，用于触发迟迟不到的场景。
    def force_trigger(self) -> None:
        self._driver.basic.force_trigger()

    # 读取并弹出仪器错误队列；返回 (code, message)，用于判定命令是否被接受。
    def last_error(self) -> tuple[int, str]:
        error = self._driver.system.error_get()
        return error.code, error.message

    # 关闭并重新打开连接；用于仪器链路异常后的恢复，不改变仪器运行配置。
    def reconnect(self) -> None:
        with suppress(Exception):
            self._driver.close()
        self._driver.open()


# 按显式 VISA 资源创建未打开的台架对象；推荐用 with 语句管理连接生命周期。
def open_scope(
    resource_name: str,
    *,
    visa_library: str | None = "@py",
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    channel: int | Mso5204AnalogChannel = Mso5204AnalogChannel.CH1,
    vertical_scale_v: float = _DEFAULT_SCALE_V,
    trigger_level_v: float = _DEFAULT_TRIGGER_LEVEL_V,
) -> Mso5204Scope:
    return Mso5204Scope(
        resource_name,
        visa_library=visa_library,
        timeout_s=timeout_s,
        channel=channel,
        vertical_scale_v=vertical_scale_v,
        trigger_level_v=trigger_level_v,
    )


__all__ = ["Mso5204Operations", "Mso5204Scope", "open_scope"]
