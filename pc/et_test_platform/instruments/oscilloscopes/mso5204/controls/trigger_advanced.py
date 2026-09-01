# RIGOL MSO5204 高级非协议触发原子控制。
#
# 职责：映射 PULSE、SLOPE、VIDEO、PATTERN、DURATION、TIMEOUT、RUNT、WINDOW、
#       DELAY、SETUP&HOLD 和 Nth EDGE 触发命令，并生成稳定的 set/get 原子 API。
# 边界：每个生成 API 只发送或查询一条 SCPI，不自动切换 TRIGger:MODE 或组合采集流程。
# 依赖：仅依赖公共 ScpiSession、Sequence 和本型号 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_float, _parse_int, _query_command

_ADVANCED_FIELDS = (
    ("pulse_source", ":TRIGger:PULSe:SOURce", "text"),
    ("pulse_condition", ":TRIGger:PULSe:WHEN", "text"),
    ("pulse_upper_width", ":TRIGger:PULSe:UWIDth", "float"),
    ("pulse_lower_width", ":TRIGger:PULSe:LWIDth", "float"),
    ("pulse_level", ":TRIGger:PULSe:LEVel", "float"),
    ("slope_source", ":TRIGger:SLOPe:SOURce", "text"),
    ("slope_condition", ":TRIGger:SLOPe:WHEN", "text"),
    ("slope_upper_time", ":TRIGger:SLOPe:TUPPer", "float"),
    ("slope_lower_time", ":TRIGger:SLOPe:TLOWer", "float"),
    ("slope_window", ":TRIGger:SLOPe:WINDow", "text"),
    ("slope_upper_level", ":TRIGger:SLOPe:ALEVel", "float"),
    ("slope_lower_level", ":TRIGger:SLOPe:BLEVel", "float"),
    ("video_source", ":TRIGger:VIDeo:SOURce", "text"),
    ("video_polarity", ":TRIGger:VIDeo:POLarity", "text"),
    ("video_mode", ":TRIGger:VIDeo:MODE", "text"),
    ("video_line", ":TRIGger:VIDeo:LINE", "int"),
    ("video_standard", ":TRIGger:VIDeo:STANdard", "text"),
    ("video_level", ":TRIGger:VIDeo:LEVel", "float"),
    ("pattern_source", ":TRIGger:PATTern:SOURce", "text"),
    ("duration_source", ":TRIGger:DURation:SOURce", "text"),
    ("duration_condition", ":TRIGger:DURation:WHEN", "text"),
    ("duration_upper_time", ":TRIGger:DURation:TUPPer", "float"),
    ("duration_lower_time", ":TRIGger:DURation:TLOWer", "float"),
    ("timeout_source", ":TRIGger:TIMeout:SOURce", "text"),
    ("timeout_slope", ":TRIGger:TIMeout:SLOPe", "text"),
    ("timeout_time", ":TRIGger:TIMeout:TIME", "float"),
    ("timeout_level", ":TRIGger:TIMeout:LEVel", "float"),
    ("runt_source", ":TRIGger:RUNT:SOURce", "text"),
    ("runt_polarity", ":TRIGger:RUNT:POLarity", "text"),
    ("runt_condition", ":TRIGger:RUNT:WHEN", "text"),
    ("runt_upper_width", ":TRIGger:RUNT:WUPPer", "float"),
    ("runt_lower_width", ":TRIGger:RUNT:WLOWer", "float"),
    ("runt_upper_level", ":TRIGger:RUNT:ALEVel", "float"),
    ("runt_lower_level", ":TRIGger:RUNT:BLEVel", "float"),
    ("window_source", ":TRIGger:WINDows:SOURce", "text"),
    ("window_slope", ":TRIGger:WINDows:SLOPe", "text"),
    ("window_position", ":TRIGger:WINDows:POSition", "text"),
    ("window_time", ":TRIGger:WINDows:TIME", "float"),
    ("window_upper_level", ":TRIGger:WINDows:ALEVel", "float"),
    ("window_lower_level", ":TRIGger:WINDows:BLEVel", "float"),
    ("delay_source_a", ":TRIGger:DELay:SA", "text"),
    ("delay_slope_a", ":TRIGger:DELay:SLOPA", "text"),
    ("delay_source_b", ":TRIGger:DELay:SB", "text"),
    ("delay_slope_b", ":TRIGger:DELay:SLOPB", "text"),
    ("delay_type", ":TRIGger:DELay:TYPE", "text"),
    ("delay_upper_time", ":TRIGger:DELay:TUPPer", "float"),
    ("delay_lower_time", ":TRIGger:DELay:TLOWer", "float"),
    ("delay_upper_level", ":TRIGger:DELay:ALEVel", "float"),
    ("delay_lower_level", ":TRIGger:DELay:BLEVel", "float"),
    ("setup_hold_data_source", ":TRIGger:SHOLd:DSRC", "text"),
    ("setup_hold_clock_source", ":TRIGger:SHOLd:CSRC", "text"),
    ("setup_hold_clock_slope", ":TRIGger:SHOLd:SLOPe", "text"),
    ("setup_hold_pattern", ":TRIGger:SHOLd:PATTern", "text"),
    ("setup_hold_type", ":TRIGger:SHOLd:TYPE", "text"),
    ("setup_hold_setup_time", ":TRIGger:SHOLd:STIMe", "float"),
    ("setup_hold_hold_time", ":TRIGger:SHOLd:HTIMe", "float"),
    ("setup_hold_data_level", ":TRIGger:SHOLd:DLEVel", "float"),
    ("setup_hold_clock_level", ":TRIGger:SHOLd:CLEVel", "float"),
    ("nth_edge_source", ":TRIGger:NEDGe:SOURce", "text"),
    ("nth_edge_slope", ":TRIGger:NEDGe:SLOPe", "text"),
    ("nth_edge_idle_time", ":TRIGger:NEDGe:IDLE", "float"),
    ("nth_edge_count", ":TRIGger:NEDGe:EDGE", "int"),
    ("nth_edge_level", ":TRIGger:NEDGe:LEVel", "float"),
)


def _parse_response(kind: str, value: str) -> str | float | int:
    if kind == "float":
        return _parse_float(value)
    if kind == "int":
        return _parse_int(value)
    return value


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | float | int]:
    def _getter(self: Any) -> str | float | int:
        return _parse_response(kind, self._session.query_text(_query_command(header)))

    return _getter


def _install_scalar_apis() -> None:
    for name, header, kind in _ADVANCED_FIELDS:
        setter = _make_setter(header)
        getter = _make_getter(header, kind)
        setter.__name__ = f"{name}_set"
        getter.__name__ = f"{name}_get"
        setattr(Mso5204AdvancedTriggerControl, setter.__name__, setter)
        setattr(Mso5204AdvancedTriggerControl, getter.__name__, getter)


def _validate_pattern(values: Sequence[str], *, edge_allowed: bool) -> tuple[str, ...]:
    normalized = tuple(str(value).strip().upper() for value in values)
    if not 1 <= len(normalized) <= 20:
        raise ValueError("trigger pattern must contain 1..20 channel states")
    allowed = {"H", "L", "X", "R", "F"} if edge_allowed else {"H", "L", "X"}
    if any(value not in allowed for value in normalized):
        raise ValueError(f"trigger pattern states must be in {sorted(allowed)}")
    if edge_allowed and sum(value in {"R", "F"} for value in normalized) > 1:
        raise ValueError("pattern trigger permits at most one edge state")
    return normalized


# 提供高级模拟/逻辑触发子系统的稳定单命令访问；标量 set/get API 由上方固定注册表生成。
class Mso5204AdvancedTriggerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置 Pattern Trigger 的 CH1..CH4/D0..D15 模式序列；允许 H/L/X 及最多一个 R/F 边沿。
    def pattern_values_set(self, values: Sequence[str]) -> None:
        normalized = _validate_pattern(values, edge_allowed=True)
        self._session.write(_command(":TRIGger:PATTern:PATTern", *normalized))

    # 查询 Pattern Trigger 全部通道模式序列；返回仪器当前二十路状态的字符串元组。
    def pattern_values_get(self) -> tuple[str, ...]:
        response = self._session.query_text(":TRIGger:PATTern:PATTern?")
        return tuple(item.strip() for item in response.split(","))

    # 设置 Pattern Trigger 指定模拟/数字源的门限；只修改该源门限，不改变 Pattern 内容。
    def pattern_level_set(self, source: str, level: float) -> None:
        self._session.write(_command(":TRIGger:PATTern:LEVel", source, level))

    # 查询 Pattern Trigger 指定源的当前门限；只执行一次带 source 参数的 Query。
    def pattern_level_get(self, source: str) -> float:
        return _parse_float(
            self._session.query_text(_query_command(":TRIGger:PATTern:LEVel", source))
        )

    # 设置 Duration Trigger 的 CH1..CH4/D0..D15 高低电平模式；仅允许 H/L/X。
    def duration_pattern_set(self, values: Sequence[str]) -> None:
        normalized = _validate_pattern(values, edge_allowed=False)
        self._session.write(_command(":TRIGger:DURation:TYPE", *normalized))

    # 查询 Duration Trigger 当前二十路高低电平模式；返回仪器原始模式序列。
    def duration_pattern_get(self) -> tuple[str, ...]:
        response = self._session.query_text(":TRIGger:DURation:TYPE?")
        return tuple(item.strip() for item in response.split(","))

    # 设置 Duration Trigger 指定模拟/数字源门限；只修改对应 source 的 level。
    def duration_level_set(self, source: str, level: float) -> None:
        self._session.write(_command(":TRIGger:DURation:LEVel", source, level))

    # 查询 Duration Trigger 指定源门限；只执行一次带 source 参数的 Query。
    def duration_level_get(self, source: str) -> float:
        return _parse_float(
            self._session.query_text(_query_command(":TRIGger:DURation:LEVel", source))
        )


_install_scalar_apis()
