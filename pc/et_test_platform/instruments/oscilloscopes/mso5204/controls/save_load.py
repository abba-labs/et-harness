# RIGOL MSO5204 save/load atomic controls.
#
# 职责：用稳定命令表生成 CSV/Image 参数 API，并提供单命令 Save/Load 文件动作。
# 边界：只操作仪器端存储命令，不访问 PC 文件系统，也不自动覆盖其他配置。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与布尔解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool

_SAVE_FIELDS = (
    ("csv_length", ":SAVE:CSV:LENGth", "text"),
    ("csv_channel", ":SAVE:CSV:CHANnel", "text"),
    ("image_type", ":SAVE:IMAGe:TYPE", "text"),
    ("image_invert", ":SAVE:IMAGe:INVert", "bool"),
    ("image_color", ":SAVE:IMAGe:COLor", "bool"),
)
_SAVE_ACTIONS = (
    ("csv_save", ":SAVE:CSV"),
    ("image_save", ":SAVE:IMAGe"),
    ("setup_save", ":SAVE:SETup"),
    ("waveform_save", ":SAVE:WAVeform"),
    ("setup_load", ":LOAD:SETup"),
)


def _path(path: str) -> str:
    value = path.strip()
    if not value or "\r" in value or "\n" in value:
        raise ValueError("storage path must be non-empty and single-line")
    return value


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | bool]:
    def _getter(self: Any) -> str | bool:
        value = self._session.query_text(header + "?")
        return _parse_bool(value) if kind == "bool" else value

    return _getter


def _make_path_action(header: str) -> Callable[[Any, str], None]:
    def _action(self: Any, path: str) -> None:
        self._session.write(_command(header, _path(path)))

    return _action


# 提供仪器端 CSV/Image/Setup/Waveform Save/Load 原子接口；构造对象时不会访问 PC 文件系统或执行文件动作。
class Mso5204SaveLoadControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询最近一次 Save 操作状态；只读取 STATus，不发起新的保存或加载动作。
    def status_get(self) -> str:
        return self._session.query_text(":SAVE:STATus?")


for _name, _header, _kind in _SAVE_FIELDS:
    setattr(Mso5204SaveLoadControl, f"{_name}_set", _make_setter(_header))
    setattr(Mso5204SaveLoadControl, f"{_name}_get", _make_getter(_header, _kind))
for _name, _header in _SAVE_ACTIONS:
    setattr(Mso5204SaveLoadControl, _name, _make_path_action(_header))
