# RIGOL MSO5204 waveform search atomic controls.
#
# 职责：用稳定命令表生成 Edge/Pulse/Runt/Slope Search 的 set/get 原子 API。
# 边界：生成 API 每次只发送或查询一条 SCPI，不自动启动采集或改变 Trigger 配置。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与常用响应解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int, _query_command

_SEARCH_FIELDS = (
    ("enabled", ":SEARch:STATe", "bool"),
    ("mode", ":SEARch:MODE", "text"),
    ("event", ":SEARch:EVENt", "int"),
    ("edge_slope", ":SEARch:EDGE:SLOPe", "text"),
    ("edge_source", ":SEARch:EDGE:SOURce", "text"),
    ("edge_threshold", ":SEARch:EDGE:THReshold", "float"),
    ("pulse_polarity", ":SEARch:PULSe:POLarity", "text"),
    ("pulse_qualifier", ":SEARch:PULSe:QUALifier", "text"),
    ("pulse_source", ":SEARch:PULSe:SOURce", "text"),
    ("pulse_upper_width", ":SEARch:PULSe:UWIDth", "float"),
    ("pulse_lower_width", ":SEARch:PULSe:LWIDth", "float"),
    ("pulse_threshold", ":SEARch:PULSe:THReshold", "float"),
    ("runt_polarity", ":SEARch:RUNT:POLarity", "text"),
    ("runt_qualifier", ":SEARch:RUNT:QUALifier", "text"),
    ("runt_source", ":SEARch:RUNT:SOURce", "text"),
    ("runt_upper_width", ":SEARch:RUNT:WUPPer", "float"),
    ("runt_lower_width", ":SEARch:RUNT:WLOWer", "float"),
    ("runt_threshold_a", ":SEARch:RUNT:THReshold1", "float"),
    ("runt_threshold_b", ":SEARch:RUNT:THReshold2", "float"),
    ("slope_polarity", ":SEARch:SLOPe:POLarity", "text"),
    ("slope_qualifier", ":SEARch:SLOPe:QUALifier", "text"),
    ("slope_source", ":SEARch:SLOPe:SOURce", "text"),
    ("slope_upper_time", ":SEARch:SLOPe:TUPPer", "float"),
    ("slope_lower_time", ":SEARch:SLOPe:TLOWer", "float"),
    ("slope_threshold_a", ":SEARch:SLOPe:THReshold1", "float"),
    ("slope_threshold_b", ":SEARch:SLOPe:THReshold2", "float"),
)


def _parse(kind: str, value: str) -> str | float | int | bool:
    if kind == "bool":
        return _parse_bool(value)
    if kind == "float":
        return _parse_float(value)
    if kind == "int":
        return _parse_int(value)
    return value


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | float | int | bool]:
    def _getter(self: Any) -> str | float | int | bool:
        return _parse(kind, self._session.query_text(_query_command(header)))

    return _getter


# 提供 Edge/Pulse/Runt/Slope Search 的单命令参数和查询接口；构造对象时不会启动采集或修改 Trigger。
class Mso5204SearchControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询当前 Search 命中事件总数；只读取 COUNt，不改变搜索条件或采集状态。
    def count_get(self) -> int:
        return _parse_int(self._session.query_text(":SEARch:COUNt?"))

    # 查询当前选中 Search 事件的水平位置；只读取 VALue，不移动事件游标。
    def value_get(self) -> float:
        return _parse_float(self._session.query_text(":SEARch:VALue?"))


for _name, _header, _kind in _SEARCH_FIELDS:
    setattr(Mso5204SearchControl, f"{_name}_set", _make_setter(_header))
    setattr(Mso5204SearchControl, f"{_name}_get", _make_getter(_header, _kind))
