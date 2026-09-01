# B&K Precision 9130B 高频组合操作。
#
# 职责：提供显式通道 Typed 配置、通道/三通道测量和安全关断组合，补足当前通道隐式状态带来的契约风险。
# 边界：组合层不创造新 SCPI 语义，不缓存“当前通道”作为真值，异常直接向上抛出且不吞掉失败。
# 依赖：运行时仅依赖本型号 Models/Validation；Driver 只用于类型检查以避免循环依赖。

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    Bk9130bChannel,
    Bk9130bChannelConfig,
    Bk9130bChannelMeasurement,
    Bk9130bOutputMeasurements,
)
from .validation import (
    BK9130B_CURRENT_MAX_A,
    require_channel_voltage,
    require_range,
)

if TYPE_CHECKING:
    from .driver import Bk9130bDriver


def _validate_channel_config(config: Bk9130bChannelConfig) -> None:
    if not isinstance(config.channel, Bk9130bChannel):
        raise ValueError("channel must be Bk9130bChannel")
    require_channel_voltage(config.channel, config.voltage_v)
    require_range(config.current_a, 0.0, BK9130B_CURRENT_MAX_A, "current_a")
    if not isinstance(config.output_enabled, bool):
        raise ValueError("output_enabled must be bool")
    if not isinstance(config.disable_before_configure, bool):
        raise ValueError("disable_before_configure must be bool")
    if config.ovp_limit_v is not None:
        require_channel_voltage(config.channel, config.ovp_limit_v)
    if config.ovp_enabled is not None and not isinstance(config.ovp_enabled, bool):
        raise ValueError("ovp_enabled must be bool or None")


# 提供 9130B 高频同仪器组合；显式 channel 参数用于避免依赖不可见的当前通道状态。
class Bk9130bOperations:
    def __init__(self, driver: Bk9130bDriver) -> None:
        self._driver = driver

    # 配置指定通道，并在任何写入前完成 CH1/2 30 V、CH3 5 V 和 3 A 上限校验。
    def configure_channel(self, config: Bk9130bChannelConfig) -> None:
        _validate_channel_config(config)
        driver = self._driver
        driver.channel.select_set(config.channel)
        if config.disable_before_configure:
            driver.source.channel_output_enabled_set(False)
        driver.source.voltage_set(config.voltage_v)
        driver.source.current_set(config.current_a)
        if config.ovp_limit_v is not None:
            driver.source.voltage_protection_level_set(config.ovp_limit_v)
        if config.ovp_enabled is not None:
            driver.source.voltage_protection_enabled_set(config.ovp_enabled)
        driver.source.channel_output_enabled_set(config.output_enabled)

    # 兼容旧入口：选择通道、设置电压电流并打开通道；保持原有四条命令顺序。
    def configure_channel_and_enable(
        self,
        channel: Bk9130bChannel,
        voltage_v: float,
        current_a: float,
    ) -> None:
        self.configure_channel(
            Bk9130bChannelConfig(
                channel=channel,
                voltage_v=voltage_v,
                current_a=current_a,
                output_enabled=True,
                disable_before_configure=False,
            )
        )

    # 关闭三个通道输出；使用单条 APPLy:OUTput 0,0,0，不修改电压、电流、保护或通道选择。
    def all_outputs_off(self) -> None:
        self._driver.apply.outputs_set(False, False, False)

    # 一次读取三个通道的电压和电流，返回稳定 Typed Snapshot。
    def read_all_outputs(self) -> Bk9130bOutputMeasurements:
        return Bk9130bOutputMeasurements(
            voltages_v=self._driver.measurement.all_voltages_get(),
            currents_a=self._driver.measurement.all_currents_get(),
        )

    # 显式选择指定通道后读取其电压、电流和功率；不会修改输出设定值。
    def read_channel(self, channel: Bk9130bChannel) -> Bk9130bChannelMeasurement:
        if not isinstance(channel, Bk9130bChannel):
            raise ValueError("channel must be Bk9130bChannel")
        self._driver.channel.select_set(channel)
        return Bk9130bChannelMeasurement(
            channel=channel,
            voltage_v=self._driver.measurement.voltage_get(),
            current_a=self._driver.measurement.current_get(),
            power_w=self._driver.measurement.power_get(),
        )


# 兼容函数式入口：显式选通道后依次设置电压、电流并打开该通道，不改变总输出状态。
def configure_channel_and_enable(
    driver: Bk9130bDriver,
    channel: Bk9130bChannel,
    voltage_v: float,
    current_a: float,
) -> None:
    Bk9130bOperations(driver).configure_channel_and_enable(channel, voltage_v, current_a)


# 兼容函数式入口：用单条 APPLy:OUTput 0,0,0 关闭三路输出，不修改任何电压电流设定。
def all_outputs_off(driver: Bk9130bDriver) -> None:
    Bk9130bOperations(driver).all_outputs_off()


# 兼容旧返回形态：执行两条 ALL 查询并返回电压元组、电流元组，不改变任何输出配置。
def read_all_outputs(
    driver: Bk9130bDriver,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    result = Bk9130bOperations(driver).read_all_outputs()
    return result.voltages_v, result.currents_a
