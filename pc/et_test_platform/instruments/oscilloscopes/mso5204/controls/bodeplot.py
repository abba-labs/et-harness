# RIGOL MSO5204 Bode Plot 原子控制。
#
# 职责：用命令表生成 Bode 扫频的常规 set/get API，并保留带特殊参数的独立接口。
# 边界：每个 API 只发送或查询一条 SCPI，不自动配置 AWG、模拟通道或测试判定。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int, _query_command

_BODE_FIELDS = (
    ("enabled", ":BODeplot:ENABle", "bool"),
    ("display_type", ":BODeplot:DISPtype", "text"),
    ("source", ":BODeplot:SOURce", "text"),
    ("sweep_type", ":BODeplot:SWEeptype", "text"),
    ("input_source", ":BODeplot:REFin", "text"),
    ("output_source", ":BODeplot:REFout", "text"),
    ("impedance", ":BODeplot:IMPedance", "text"),
    ("start_frequency", ":BODeplot:STARt", "float"),
    ("stop_frequency", ":BODeplot:STOP", "float"),
    ("voltage_profile", ":BODeplot:VOLTage:PROFile", "bool"),
)


def _parse(kind: str, value: str) -> str | float | bool:
    if kind == "bool":
        return _parse_bool(value)
    if kind == "float":
        return _parse_float(value)
    return value


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | float | bool]:
    def _getter(self: Any) -> str | float | bool:
        return _parse(kind, self._session.query_text(header + "?"))

    return _getter


# 提供 Bode Plot 扫频、激励幅度与 Margin 查询；构造对象时不会配置 AWG 或启动扫频。
class Mso5204BodePlotControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置每十倍频程的扫频点数并执行 10..300 范围校验，只发送 POINT 命令。
    def points_per_decade_set(self, points: int) -> None:
        value = int(points)
        if not 10 <= value <= 300:
            raise ValueError("Bode points per decade must be 10..300")
        self._session.write(_command(":BODeplot:POINT", value))

    # 查询每十倍频程的扫频点数，只读取 POINT 当前值，不改变扫频设置。
    def points_per_decade_get(self) -> int:
        return _parse_int(self._session.query_text(":BODeplot:POINT?"))

    # 设置指定频段的 Bode 激励幅度，只发送一次 VOLTage 命令，不自动打开 Profile。
    def voltage_set(self, amplitude_v: float, frequency_range: str) -> None:
        self._session.write(_command(":BODeplot:VOLTage", amplitude_v, frequency_range))

    # 查询指定频段的 Bode 激励幅度，只读取该频段当前配置值。
    def voltage_get(self, frequency_range: str) -> float:
        return _parse_float(
            self._session.query_text(_query_command(":BODeplot:VOLTage", frequency_range))
        )

    # 查询当前 Gain Margin 数值，只读取分析结果，不重新执行 Bode 扫频。
    def gain_margin_get(self) -> float:
        return _parse_float(self._session.query_text(":BODeplot:GMARgin?"))

    # 查询 Gain Margin 对应频率，只读取分析结果，不改变显示或扫频参数。
    def gain_margin_frequency_get(self) -> float:
        return _parse_float(self._session.query_text(":BODeplot:GMARgin:FREQuency?"))

    # 查询当前 Phase Margin 数值，只读取分析结果，不重新执行 Bode 扫频。
    def phase_margin_get(self) -> float:
        return _parse_float(self._session.query_text(":BODeplot:PMARgin?"))

    # 查询 Phase Margin 对应频率，只读取分析结果，不改变显示或扫频参数。
    def phase_margin_frequency_get(self) -> float:
        return _parse_float(self._session.query_text(":BODeplot:PMARgin:FREQuency?"))


for _name, _header, _kind in _BODE_FIELDS:
    setattr(Mso5204BodePlotControl, f"{_name}_set", _make_setter(_header))
    setattr(Mso5204BodePlotControl, f"{_name}_get", _make_getter(_header, _kind))
