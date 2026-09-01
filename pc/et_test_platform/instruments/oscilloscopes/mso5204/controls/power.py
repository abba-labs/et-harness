# RIGOL MSO5204 Power Analysis 原子控制。
#
# 职责：用稳定命令表生成分析类型、源、频率参考和参考电平百分比的 set/get API。
# 边界：不自动打开通道、不采集波形，也不把分析结果解释成测试判定。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与整数解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_int

_POWER_FIELDS = (
    ("analysis_type", ":POWer:TYPE", "text"),
    ("current_source", ":POWer:CURRentsource", "text"),
    ("voltage_source", ":POWer:VOLTagesource", "text"),
    ("quality_frequency_reference", ":POWer:QUALity:FREQreference", "text"),
    ("reference_level_method", ":POWer:REFLevel:METHod", "text"),
    ("reference_percent_high", ":POWer:REFLevel:PERCent:HIGH", "int"),
    ("reference_percent_low", ":POWer:REFLevel:PERCent:LOW", "int"),
    ("reference_percent_mid", ":POWer:REFLevel:PERCent:MID", "int"),
)


def _make_setter(header: str, kind: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, int(value) if kind == "int" else value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | int]:
    def _getter(self: Any) -> str | int:
        value = self._session.query_text(header + "?")
        return _parse_int(value) if kind == "int" else value

    return _getter


# 提供 Power Analysis 参数的单命令 set/get；构造对象时不会打开通道、采集波形或执行分析判定。
class Mso5204PowerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session


for _name, _header, _kind in _POWER_FIELDS:
    setattr(Mso5204PowerControl, f"{_name}_set", _make_setter(_header, _kind))
    setattr(Mso5204PowerControl, f"{_name}_get", _make_getter(_header, _kind))
