# RIGOL MSO5204 waveform record/playback atomic controls.
#
# 职责：用稳定命令表生成 RECord Enable/Start/Play/Current/Frames 的成对原子 API。
# 边界：每个生成方法只发送或查询一条 SCPI，不自动切换采集状态或执行回放流程。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与布尔/整数解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_int

_RECORD_FIELDS = (
    ("enabled", ":RECord:ENABle", "bool"),
    ("recording", ":RECord:STARt", "bool"),
    ("playing", ":RECord:PLAY", "bool"),
    ("current_frame", ":RECord:CURRent", "int"),
    ("frames", ":RECord:FRAMes", "int"),
)


def _make_setter(header: str, kind: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        if kind == "int":
            number = int(value)
            if number < 1:
                raise ValueError("record frame value must be >= 1")
            value = number
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], bool | int]:
    def _getter(self: Any) -> bool | int:
        value = self._session.query_text(header + "?")
        return _parse_bool(value) if kind == "bool" else _parse_int(value)

    return _getter


# 提供 waveform record/playback 的单命令控制；构造对象时不会切换采集状态、开始记录或执行回放流程。
class Mso5204RecordControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session


for _name, _header, _kind in _RECORD_FIELDS:
    setattr(Mso5204RecordControl, f"{_name}_set", _make_setter(_header, _kind))
    setattr(Mso5204RecordControl, f"{_name}_get", _make_getter(_header, _kind))
