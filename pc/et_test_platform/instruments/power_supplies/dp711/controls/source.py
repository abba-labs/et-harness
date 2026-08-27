# RIGOL DP711 SOURCE 电压、电流和保护控制。
#
# 职责：把 SOURce 的电压、电流、OCP、OVP 命令逐项映射为原子 API。
# 边界：不打开输出、不执行测量，不把 SOURCE 与 OUTPut 命令组合成测试流程。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dp711Limit
from ..validation import (
    DP711_CURRENT_MAX_A,
    DP711_CURRENT_MIN_A,
    DP711_OCP_MAX_A,
    DP711_OCP_MIN_A,
    DP711_OVP_MAX_V,
    DP711_OVP_MIN_V,
    DP711_VOLTAGE_MAX_V,
    DP711_VOLTAGE_MIN_V,
    parse_bool,
    parse_yes_no,
    require_range,
)


# 提供 DP711 SOURce 子系统原子控制。
class Dp711SourceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置 CH1 电流设定值；不打开输出；只修改该配置项，不执行额外仪器动作。
    def current_set(self, current_a: float) -> None:
        value = require_range(
            current_a,
            DP711_CURRENT_MIN_A,
            DP711_CURRENT_MAX_A,
            "current_a",
        )
        self._session.write(f":SOURce1:CURRent {value:g}")

    # 查询当前、最小或最大 CH1 电流设定值，单位 A。
    def current_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f" {limit.value}"
        return float(self._session.query_text(f":SOURce1:CURRent?{suffix}"))

    # 清除 SOURCE 路径的 OCP 标志和提示。
    def current_protection_clear(self) -> None:
        self._session.write(":SOURce1:CURRent:PROTection:CLEar")

    # 设置 SOURCE 路径的 OCP 阈值；只修改该配置项，不执行额外仪器动作。
    def current_protection_value_set(self, current_a: float) -> None:
        value = require_range(current_a, DP711_OCP_MIN_A, DP711_OCP_MAX_A, "current_a")
        self._session.write(f":SOURce1:CURRent:PROTection {value:g}")

    # 查询 SOURCE 路径当前、最小或最大 OCP 阈值，单位 A。
    def current_protection_value_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f" {limit.value}"
        return float(self._session.query_text(f":SOURce1:CURRent:PROTection?{suffix}"))

    # 打开或关闭 SOURCE 路径 OCP；不修改阈值。
    def current_protection_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SOURce1:CURRent:PROTection:STATe {'ON' if enabled else 'OFF'}")

    # 查询 SOURCE 路径 OCP 是否打开；查询或解析过程不会修改仪器配置。
    def current_protection_enabled_get(self) -> bool:
        response = self._session.query_text(":SOURce1:CURRent:PROTection:STATe?")
        return parse_bool(response)

    # 查询 SOURCE 路径是否已经发生 OCP；查询或解析过程不会修改仪器配置。
    def current_protection_tripped_get(self) -> bool:
        response = self._session.query_text(":SOURce1:CURRent:PROTection:TRIPped?")
        return parse_yes_no(response)

    # 设置 CH1 电压设定值；不打开输出；只修改该配置项，不执行额外仪器动作。
    def voltage_set(self, voltage_v: float) -> None:
        value = require_range(
            voltage_v,
            DP711_VOLTAGE_MIN_V,
            DP711_VOLTAGE_MAX_V,
            "voltage_v",
        )
        self._session.write(f":SOURce1:VOLTage {value:g}")

    # 查询当前、最小或最大 CH1 电压设定值，单位 V。
    def voltage_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f" {limit.value}"
        return float(self._session.query_text(f":SOURce1:VOLTage?{suffix}"))

    # 清除 SOURCE 路径的 OVP 标志和提示。
    def voltage_protection_clear(self) -> None:
        self._session.write(":SOURce1:VOLTage:PROTection:CLEar")

    # 设置 SOURCE 路径的 OVP 阈值；只修改该配置项，不执行额外仪器动作。
    def voltage_protection_value_set(self, voltage_v: float) -> None:
        value = require_range(voltage_v, DP711_OVP_MIN_V, DP711_OVP_MAX_V, "voltage_v")
        self._session.write(f":SOURce1:VOLTage:PROTection {value:g}")

    # 查询 SOURCE 路径当前、最小或最大 OVP 阈值，单位 V。
    def voltage_protection_value_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f" {limit.value}"
        return float(self._session.query_text(f":SOURce1:VOLTage:PROTection?{suffix}"))

    # 打开或关闭 SOURCE 路径 OVP；不修改阈值。
    def voltage_protection_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SOURce1:VOLTage:PROTection:STATe {'ON' if enabled else 'OFF'}")

    # 查询 SOURCE 路径 OVP 是否打开；查询或解析过程不会修改仪器配置。
    def voltage_protection_enabled_get(self) -> bool:
        response = self._session.query_text(":SOURce1:VOLTage:PROTection:STATe?")
        return parse_bool(response)

    # 查询 SOURCE 路径是否已经发生 OVP；查询或解析过程不会修改仪器配置。
    def voltage_protection_tripped_get(self) -> bool:
        response = self._session.query_text(":SOURce1:VOLTage:PROTection:TRIPped?")
        return parse_yes_no(response)
