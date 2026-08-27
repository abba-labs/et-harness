# RIGOL DP711 高频组合操作。
#
# 职责：在原子 Driver 之上提供 Typed 输出配置、安全关断和输出测量组合，减少 Case 重复样板代码。
# 边界：不隐藏测试断言、不访问其他仪器，也不把组合操作冒充底层原子命令。
# 依赖：运行时仅依赖本型号 Models/Validation；Driver 只用于类型检查以避免循环依赖。

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Dp711Measurement, Dp711OutputConfig
from .validation import (
    DP711_CURRENT_MAX_A,
    DP711_CURRENT_MIN_A,
    DP711_OCP_MAX_A,
    DP711_OCP_MIN_A,
    DP711_OVP_MAX_V,
    DP711_OVP_MIN_V,
    DP711_VOLTAGE_MAX_V,
    DP711_VOLTAGE_MIN_V,
    require_range,
)

if TYPE_CHECKING:
    from .driver import Dp711Driver


def _validate_output_config(config: Dp711OutputConfig) -> None:
    require_range(
        config.voltage_v,
        DP711_VOLTAGE_MIN_V,
        DP711_VOLTAGE_MAX_V,
        "voltage_v",
    )
    require_range(
        config.current_a,
        DP711_CURRENT_MIN_A,
        DP711_CURRENT_MAX_A,
        "current_a",
    )
    if not isinstance(config.enabled, bool):
        raise ValueError("enabled must be bool")
    if not isinstance(config.disable_before_configure, bool):
        raise ValueError("disable_before_configure must be bool")
    if config.ocp_limit_a is not None:
        require_range(config.ocp_limit_a, DP711_OCP_MIN_A, DP711_OCP_MAX_A, "ocp_limit_a")
    if config.ovp_limit_v is not None:
        require_range(config.ovp_limit_v, DP711_OVP_MIN_V, DP711_OVP_MAX_V, "ovp_limit_v")


# 提供 DP711 高频同仪器组合；构造对象时不访问硬件，所有组合仍调用公开原子 API。
class Dp711Operations:
    def __init__(self, driver: Dp711Driver) -> None:
        self._driver = driver

    # 按 Typed Config 完成可选预关断、保护阈值、电压电流和最终输出状态配置。
    def configure_output(self, config: Dp711OutputConfig) -> None:
        _validate_output_config(config)
        driver = self._driver
        if config.disable_before_configure:
            driver.output.enabled_set(False)
        if config.ocp_limit_a is not None:
            driver.source.current_protection_value_set(config.ocp_limit_a)
            driver.source.current_protection_enabled_set(True)
        if config.ovp_limit_v is not None:
            driver.source.voltage_protection_value_set(config.ovp_limit_v)
            driver.source.voltage_protection_enabled_set(True)
        driver.source.voltage_set(config.voltage_v)
        driver.source.current_set(config.current_a)
        driver.output.enabled_set(config.enabled)

    # 兼容旧入口：设置电压、电流后打开输出；保持原有三条命令顺序，不追加预关断。
    def configure_and_enable(self, voltage_v: float, current_a: float) -> None:
        self.configure_output(
            Dp711OutputConfig(
                voltage_v=voltage_v,
                current_a=current_a,
                enabled=True,
                disable_before_configure=False,
            )
        )

    # 关闭输出，并可选清除已记录的 OCP/OVP 标志。
    def safe_output_off(self, *, clear_protection: bool = False) -> None:
        self._driver.output.enabled_set(False)
        if clear_protection:
            self._driver.output.ocp_clear()
            self._driver.output.ovp_clear()

    # 一次读取实际电压、电流和功率；不改变仪器配置，也不执行阈值判断。
    def read_output(self) -> Dp711Measurement:
        return self._driver.measurement.all_get()
