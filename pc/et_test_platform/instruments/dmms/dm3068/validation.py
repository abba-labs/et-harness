# RIGOL DM3068 SCPI 参数格式化和响应解析。
#
# 职责：校验已由官方资料确认的有限参数，并把文本响应转换为稳定 Python 类型。
# 边界：不发送 SCPI、不访问 Transport，不为 CHM 正文无法确认的参数范围编造限制。
# 依赖：仅依赖本型号 models 和公共 InstrumentProtocolError。

from __future__ import annotations

import csv
from io import StringIO
from math import isfinite
from typing import TypeVar

from ...common.errors import InstrumentProtocolError
from .models import (
    Dm3068Identification,
    Dm3068RangeKeyword,
    Dm3068SystemError,
)

_ALLOWED_BAUDRATES = {4800, 9600, 19200, 38400, 57600, 115200}
_EnumT = TypeVar("_EnumT")


def _format_number(value: float | int) -> str:
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError("SCPI numeric value must be finite")
    return format(numeric, ".12g")


def _nonempty_token(value: str, name: str) -> str:
    token = value.strip()
    if not token:
        raise ValueError(f"{name} must not be empty")
    if any(character in token for character in "\r\n;"):
        raise ValueError(f"{name} contains forbidden SCPI separator")
    return token


def _range_token(value: int | Dm3068RangeKeyword) -> str:
    if isinstance(value, Dm3068RangeKeyword):
        return value.value
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("range index must be a non-negative integer or MIN/MAX/DEF")
    return str(value)


def _bool_token(enabled: bool) -> str:
    if not isinstance(enabled, bool):
        raise TypeError("enabled must be bool")
    return "ON" if enabled else "OFF"


def _parse_bool(text: str) -> bool:
    token = text.strip().upper()
    if token in {"1", "ON", "TRUE"}:
        return True
    if token in {"0", "OFF", "FALSE"}:
        return False
    raise InstrumentProtocolError(f"cannot parse boolean response: {text!r}")


def _parse_float(text: str) -> float:
    try:
        return float(text.strip())
    except ValueError as exc:
        raise InstrumentProtocolError(f"cannot parse numeric response: {text!r}") from exc


def _parse_int(text: str) -> int:
    try:
        return int(text.strip(), 10)
    except ValueError as exc:
        raise InstrumentProtocolError(f"cannot parse integer response: {text!r}") from exc


def _parse_identification(text: str) -> Dm3068Identification:
    fields = [field.strip() for field in text.strip().split(",", 3)]
    if len(fields) != 4:
        raise InstrumentProtocolError(f"invalid *IDN? response: {text!r}")
    return Dm3068Identification(*fields)


def _parse_error(text: str) -> Dm3068SystemError:
    try:
        fields = next(csv.reader(StringIO(text.strip()), skipinitialspace=True))
    except (csv.Error, StopIteration) as exc:
        raise InstrumentProtocolError(f"invalid SYSTem:ERRor? response: {text!r}") from exc
    if len(fields) < 2:
        raise InstrumentProtocolError(f"invalid SYSTem:ERRor? response: {text!r}")
    try:
        code = int(fields[0].strip(), 10)
    except ValueError as exc:
        raise InstrumentProtocolError(f"invalid system error code: {text!r}") from exc
    return Dm3068SystemError(code=code, message=",".join(fields[1:]).strip())


def _require_baudrate(value: int) -> int:
    if value not in _ALLOWED_BAUDRATES:
        allowed = ", ".join(str(item) for item in sorted(_ALLOWED_BAUDRATES))
        raise ValueError(f"baudrate must be one of: {allowed}")
    return value
