# RIGOL DM3068 高频同仪器组合操作。
#
# 职责：提供 Typed Function/Range/Rate 配置、基础测量读取和外部触发组合，减少 Case 重复样板代码。
# 边界：不增加隐藏 SCPI、不跨仪器编排，也不执行期望值比较或 PASS/FAIL 判定。
# 依赖：运行时仅依赖本型号 Models/Validation；Driver 只用于类型检查以避免循环依赖。

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    Dm3068BasicMeasurementFunction,
    Dm3068MeasurementConfig,
    Dm3068RangeKeyword,
    Dm3068Rate,
    Dm3068Reading,
    Dm3068TriggerSource,
)
from .validation import _nonempty_token, _range_token

if TYPE_CHECKING:
    from .driver import Dm3068Driver

RangeValue = int | Dm3068RangeKeyword


def _validate_measurement_config(config: Dm3068MeasurementConfig) -> None:
    if not isinstance(config.function, Dm3068BasicMeasurementFunction):
        raise ValueError("function must be Dm3068BasicMeasurementFunction")
    _range_token(config.range_value)
    if not isinstance(config.rate, Dm3068Rate):
        raise ValueError("rate must be Dm3068Rate")


# 提供 DM3068 高频基础测量和触发组合；构造对象时不会切换 Function 或访问仪器。
class Dm3068Operations:
    def __init__(self, driver: Dm3068Driver) -> None:
        self._driver = driver

    # 按 Typed Config 依次设置 Function、Range、Rate；所有参数在第一条写入前完成校验。
    def configure_measurement(self, config: Dm3068MeasurementConfig) -> None:
        _validate_measurement_config(config)
        function = config.function
        driver = self._driver
        if function is Dm3068BasicMeasurementFunction.VOLTAGE_DC:
            driver.function.voltage_dc_select()
            driver.measurement.voltage_dc_range_set(config.range_value)
            driver.rate.voltage_dc_set(config.rate)
        elif function is Dm3068BasicMeasurementFunction.VOLTAGE_AC:
            driver.function.voltage_ac_select()
            driver.measurement.voltage_ac_range_set(config.range_value)
            driver.rate.voltage_ac_set(config.rate)
        elif function is Dm3068BasicMeasurementFunction.CURRENT_DC:
            driver.function.current_dc_select()
            driver.measurement.current_dc_range_set(config.range_value)
            driver.rate.current_dc_set(config.rate)
        elif function is Dm3068BasicMeasurementFunction.CURRENT_AC:
            driver.function.current_ac_select()
            driver.measurement.current_ac_range_set(config.range_value)
            driver.rate.current_ac_set(config.rate)
        elif function is Dm3068BasicMeasurementFunction.RESISTANCE_2WIRE:
            driver.function.resistance_2wire_select()
            driver.measurement.resistance_2wire_range_set(config.range_value)
            driver.rate.resistance_2wire_set(config.rate)
        else:
            driver.function.resistance_4wire_select()
            driver.measurement.resistance_4wire_range_set(config.range_value)
            driver.rate.resistance_4wire_set(config.rate)

    # 读取已经配置好的基础测量值；每次只执行对应 Function 的一条 MEASure Query。
    def read_measurement(self, function: Dm3068BasicMeasurementFunction) -> Dm3068Reading:
        if not isinstance(function, Dm3068BasicMeasurementFunction):
            raise ValueError("function must be Dm3068BasicMeasurementFunction")
        measurement = self._driver.measurement
        if function is Dm3068BasicMeasurementFunction.VOLTAGE_DC:
            value = measurement.voltage_dc_get()
        elif function is Dm3068BasicMeasurementFunction.VOLTAGE_AC:
            value = measurement.voltage_ac_get()
        elif function is Dm3068BasicMeasurementFunction.CURRENT_DC:
            value = measurement.current_dc_get()
        elif function is Dm3068BasicMeasurementFunction.CURRENT_AC:
            value = measurement.current_ac_get()
        elif function is Dm3068BasicMeasurementFunction.RESISTANCE_2WIRE:
            value = measurement.resistance_2wire_get()
        else:
            value = measurement.resistance_4wire_get()
        return Dm3068Reading(function=function, value=value)

    # 配置后立即读取一次基础测量值；不改变 Trigger，也不对读取结果做判定。
    def configure_and_read(self, config: Dm3068MeasurementConfig) -> Dm3068Reading:
        self.configure_measurement(config)
        return self.read_measurement(config.function)

    # 配置外部触发；先校验模式为单行安全 Token，再选择 EXT 触发源并写入模式。
    def configure_external_trigger(self, mode: str) -> None:
        normalized = _nonempty_token(mode, "mode")
        self._driver.trigger.source_set(Dm3068TriggerSource.EXTERNAL)
        self._driver.trigger.external_mode_set(normalized)


# 兼容函数式入口：按 Function -> Range -> Rate 三条原子命令配置直流电压，不读取测量值。
def configure_dc_voltage(
    driver: Dm3068Driver,
    *,
    range_value: RangeValue = Dm3068RangeKeyword.DEFAULT,
    rate: Dm3068Rate = Dm3068Rate.MEDIUM,
) -> None:
    Dm3068Operations(driver).configure_measurement(
        Dm3068MeasurementConfig(
            function=Dm3068BasicMeasurementFunction.VOLTAGE_DC,
            range_value=range_value,
            rate=rate,
        )
    )


# 兼容函数式入口：按 Function -> Range -> Rate 三条原子命令配置直流电流，不读取测量值。
def configure_dc_current(
    driver: Dm3068Driver,
    *,
    range_value: RangeValue = Dm3068RangeKeyword.DEFAULT,
    rate: Dm3068Rate = Dm3068Rate.MEDIUM,
) -> None:
    Dm3068Operations(driver).configure_measurement(
        Dm3068MeasurementConfig(
            function=Dm3068BasicMeasurementFunction.CURRENT_DC,
            range_value=range_value,
            rate=rate,
        )
    )


# 兼容函数式入口：按 Function -> Range -> Rate 三条原子命令配置四线电阻，不读取测量值。
def configure_resistance_4wire(
    driver: Dm3068Driver,
    *,
    range_value: RangeValue = Dm3068RangeKeyword.DEFAULT,
    rate: Dm3068Rate = Dm3068Rate.MEDIUM,
) -> None:
    Dm3068Operations(driver).configure_measurement(
        Dm3068MeasurementConfig(
            function=Dm3068BasicMeasurementFunction.RESISTANCE_4WIRE,
            range_value=range_value,
            rate=rate,
        )
    )


# 兼容函数式入口：先校验 mode，再依次设置 EXT 触发源和外部触发模式，不等待触发完成。
def configure_external_trigger(driver: Dm3068Driver, mode: str) -> None:
    Dm3068Operations(driver).configure_external_trigger(mode)
