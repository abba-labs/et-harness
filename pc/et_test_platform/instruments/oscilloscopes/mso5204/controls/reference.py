# RIGOL MSO5204 reference waveform atomic controls.
#
# 职责：用稳定命令表生成 REF1..REF10 的显示、源、缩放、标签和动作原子 API。
# 边界：每个生成方法只发送或查询一条 SCPI，不自动保存或显示其他 Reference。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与布尔/浮点解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float

_REFERENCE_FIELDS = (
    ("display", ":REFerence:DISPlay", "bool"),
    ("source", ":REFerence:SOURce", "text"),
    ("vertical_scale", ":REFerence:VSCale", "float"),
    ("vertical_offset", ":REFerence:VOFFset", "float"),
    ("color", ":REFerence:COLor", "text"),
    ("label_enabled", ":REFerence:LABel:ENABle", "bool"),
    ("label_content", ":REFerence:LABel:CONTent", "text"),
)
_REFERENCE_ACTIONS = (
    ("reset", ":REFerence:RESet"),
    ("current_set", ":REFerence:CURRent"),
    ("save", ":REFerence:SAVE"),
)


def _ref(value: int) -> int:
    ref = int(value)
    if not 1 <= ref <= 10:
        raise ValueError("reference channel must be 1..10")
    return ref


def _make_setter(name: str, header: str) -> Callable[[Any, int, Any], None]:
    def _setter(self: Any, ref: int, value: Any) -> None:
        if (
            name == "label_content"
            and isinstance(value, str)
            and ("\r" in value or "\n" in value or "," in value)
        ):
            raise ValueError("reference label must not contain comma or line break")
        self._session.write(_command(header, _ref(ref), value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any, int], str | float | bool]:
    def _getter(self: Any, ref: int) -> str | float | bool:
        value = self._session.query_text(_command(header + "?", _ref(ref)))
        if kind == "bool":
            return _parse_bool(value)
        if kind == "float":
            return _parse_float(value)
        return value

    return _getter


def _make_action(header: str) -> Callable[[Any, int], None]:
    def _action(self: Any, ref: int) -> None:
        self._session.write(_command(header, _ref(ref)))

    return _action


# 提供 REF1..REF10 的单命令显示、源、缩放、标签和动作控制；构造对象时不会保存或显示任何 Reference。
class Mso5204ReferenceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session


for _name, _header, _kind in _REFERENCE_FIELDS:
    setattr(Mso5204ReferenceControl, f"{_name}_set", _make_setter(_name, _header))
    setattr(Mso5204ReferenceControl, f"{_name}_get", _make_getter(_header, _kind))
for _name, _header in _REFERENCE_ACTIONS:
    setattr(Mso5204ReferenceControl, _name, _make_action(_header))
