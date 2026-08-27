# RIGOL DP711 输出与保护控制。
#
# 职责：把 OUTPut 模式、开关、OCP 和 OVP 命令逐项映射为原子 API。
# 边界：不设置 SOURCE 电压/电流，不组合安全上电流程，也不自动清除保护告警。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dp711Limit, Dp711OutputMode
from ..validation import (
    DP711_OCP_MAX_A,
    DP711_OCP_MIN_A,
    DP711_OVP_MAX_V,
    DP711_OVP_MIN_V,
    parse_bool,
    parse_output_mode,
    parse_yes_no,
    require_range,
)


# 提供 DP711 OUTPut 子系统原子控制。
class Dp711OutputControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 使用 OUTPut:CVCC? 查询当前 CV/CC/UR 模式。
    def cvcc_get(self) -> Dp711OutputMode:
        return parse_output_mode(self._session.query_text(":OUTPut:CVCC? CH1"))

    # 使用 OUTPut:MODE? 查询当前 CV/CC/UR 模式。
    def mode_get(self) -> Dp711OutputMode:
        return parse_output_mode(self._session.query_text(":OUTPut:MODE? CH1"))

    # 使用 OCP:ALAR? 查询当前是否已经发生过流保护。
    def ocp_alarm_get(self) -> bool:
        return parse_yes_no(self._session.query_text(":OUTPut:OCP:ALAR? CH1"))

    # 使用 OCP:QUES? 查询当前是否已经发生过流保护。
    def ocp_questionable_get(self) -> bool:
        return parse_yes_no(self._session.query_text(":OUTPut:OCP:QUES? CH1"))

    # 清除 OCP 内部标志和提示；调用方应先消除实际过流原因。
    def ocp_clear(self) -> None:
        self._session.write(":OUTPut:OCP:CLEAR CH1")

    # 打开或关闭 OCP 功能；不修改 OCP 阈值。
    def ocp_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":OUTPut:OCP:STATe CH1,{'ON' if enabled else 'OFF'}")

    # 查询 OCP 功能是否打开；查询或解析过程不会修改仪器配置。
    def ocp_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":OUTPut:OCP:STATe? CH1"))

    # 设置 OCP 阈值；允许手册覆盖的绝对范围，实际分辨率由已安装选件决定。
    def ocp_value_set(self, current_a: float) -> None:
        value = require_range(current_a, DP711_OCP_MIN_A, DP711_OCP_MAX_A, "current_a")
        self._session.write(f":OUTPut:OCP:VALue CH1,{value:g}")

    # 查询当前、最小或最大 OCP 阈值，单位 A；查询或解析过程不会修改仪器配置。
    def ocp_value_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f",{limit.value}"
        return float(self._session.query_text(f":OUTPut:OCP:VALue? CH1{suffix}"))

    # 使用 OVP:ALAR? 查询当前是否已经发生过压保护。
    def ovp_alarm_get(self) -> bool:
        return parse_yes_no(self._session.query_text(":OUTPut:OVP:ALAR? CH1"))

    # 使用 OVP:QUES? 查询当前是否已经发生过压保护。
    def ovp_questionable_get(self) -> bool:
        return parse_yes_no(self._session.query_text(":OUTPut:OVP:QUES? CH1"))

    # 清除 OVP 内部标志和提示；调用方应先消除实际过压原因。
    def ovp_clear(self) -> None:
        self._session.write(":OUTPut:OVP:CLEAR CH1")

    # 打开或关闭 OVP 功能；不修改 OVP 阈值。
    def ovp_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":OUTPut:OVP:STATe CH1,{'ON' if enabled else 'OFF'}")

    # 查询 OVP 功能是否打开；查询或解析过程不会修改仪器配置。
    def ovp_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":OUTPut:OVP:STATe? CH1"))

    # 设置 OVP 阈值；允许手册覆盖的绝对范围，实际分辨率由已安装选件决定。
    def ovp_value_set(self, voltage_v: float) -> None:
        value = require_range(voltage_v, DP711_OVP_MIN_V, DP711_OVP_MAX_V, "voltage_v")
        self._session.write(f":OUTPut:OVP:VALue CH1,{value:g}")

    # 查询当前、最小或最大 OVP 阈值，单位 V；查询或解析过程不会修改仪器配置。
    def ovp_value_get(self, limit: Dp711Limit | None = None) -> float:
        suffix = "" if limit is None else f",{limit.value}"
        return float(self._session.query_text(f":OUTPut:OVP:VALue? CH1{suffix}"))

    # 打开或关闭 CH1 输出；不修改电压、电流或保护设置。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(f":OUTPut:STATe CH1,{'ON' if enabled else 'OFF'}")

    # 查询 CH1 输出是否打开；查询或解析过程不会修改仪器配置。
    def enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":OUTPut:STATe? CH1"))
