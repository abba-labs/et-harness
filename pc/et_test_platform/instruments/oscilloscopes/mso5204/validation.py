# RIGOL MSO5204 SCPI 参数校验和响应解析。
#
# 职责：把 Python 标量安全格式化为单条 SCPI 参数，校验核心手册离散/范围契约并解析常见响应。
# 边界：不发送命令、不决定测试流程，也不把任意原始多行文本透传到仪器。
# 依赖：仅依赖 Python 标准库和 MSO5204 数据模型。

from __future__ import annotations

import math
from enum import Enum

from .models import Mso5204Identification, Mso5204SystemError, Mso5204WaveformPreamble

_MEMORY_DEPTH_BY_POINTS = {
    1_000: "1k",
    10_000: "10k",
    100_000: "100k",
    1_000_000: "1M",
    10_000_000: "10M",
    25_000_000: "25M",
    50_000_000: "50M",
    100_000_000: "100M",
    200_000_000: "200M",
}
_MEMORY_DEPTH_TOKENS = ("AUTO", *_MEMORY_DEPTH_BY_POINTS.values())
_PROBE_RATIOS = (
    0.0001,
    0.0002,
    0.0005,
    0.001,
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.1,
    0.2,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    50.0,
    100.0,
    200.0,
    500.0,
    1000.0,
    2000.0,
    5000.0,
    10000.0,
    20000.0,
    50000.0,
)
_MEASUREMENT_ITEMS = (
    "VMAX",
    "VMIN",
    "VPP",
    "VTOP",
    "VBASe",
    "VAMP",
    "VAVG",
    "VRMS",
    "OVERshoot",
    "PREShoot",
    "MARea",
    "MPARea",
    "PERiod",
    "FREQuency",
    "RTIMe",
    "FTIMe",
    "PWIDth",
    "NWIDth",
    "PDUTy",
    "NDUTy",
    "TVMAX",
    "TVMIN",
    "PSLewrate",
    "NSLewrate",
    "VUPPer",
    "VMID",
    "VLOWer",
    "VARiance",
    "PVRMs",
    "PPULses",
    "NPULses",
    "PEDGes",
    "NEDGes",
    "RRDelay",
    "RFDelay",
    "FRDelay",
    "FFDelay",
    "RRPHase",
    "RFPHase",
    "FRPHase",
    "FFPHase",
)
_MEASUREMENT_STATISTICS = ("MAXimum", "MINimum", "CURRent", "AVERages", "DEViation", "CNT")
_DIGITAL_SOURCES = tuple(f"D{index}" for index in range(16))
_ANALOG_SOURCES = tuple(f"CHANnel{index}" for index in range(1, 5))
_MATH_SOURCES = tuple(f"MATH{index}" for index in range(1, 5))
_MEASUREMENT_SOURCES = _DIGITAL_SOURCES + _ANALOG_SOURCES + _MATH_SOURCES
_MEASUREMENT_THRESHOLD_SOURCES = _ANALOG_SOURCES + _MATH_SOURCES
_EDGE_SOURCES = _DIGITAL_SOURCES + _ANALOG_SOURCES + ("ACLine",)


def _format_number(value: int | float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("numeric SCPI parameter must be finite")
    if isinstance(value, int):
        return str(value)
    return format(number, ".12g")


def _format_arg(value: object) -> str:
    if isinstance(value, Enum):
        return _format_arg(value.value)
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("SCPI string parameter must not be empty")
        if "\r" in text or "\n" in text:
            raise ValueError("SCPI string parameter must not contain line breaks")
        return text
    raise TypeError(f"unsupported SCPI parameter type: {type(value).__name__}")


def _quote_text(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("quoted SCPI text must not contain line breaks")
    return '"' + value.replace('"', '""') + '"'


def _command(header: str, *args: object) -> str:
    normalized = header.strip()
    if not normalized or "\r" in normalized or "\n" in normalized:
        raise ValueError("invalid SCPI command header")
    if not args:
        return normalized
    return normalized + " " + ",".join(_format_arg(value) for value in args)


def _query_command(header: str, *args: object) -> str:
    normalized = header.strip()
    base = normalized if normalized.endswith("?") else normalized + "?"
    return _command(base, *args)


def _validate_channel(channel: int) -> int:
    number = int(channel)
    if number not in {1, 2, 3, 4}:
        raise ValueError("MSO5204 analog channel must be 1..4")
    return number


def _validate_positive_index(value: int, name: str) -> int:
    number = int(value)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _validate_int_range(value: int, name: str, minimum: int, maximum: int) -> int:
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be {minimum}..{maximum}")
    return number


def _validate_finite(value: int | float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _validate_positive_finite(value: int | float, name: str) -> float:
    number = _validate_finite(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _validate_float_range(
    value: int | float,
    name: str,
    minimum: float,
    maximum: float,
) -> float:
    number = _validate_finite(value, name)
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be in range {minimum:g}..{maximum:g}")
    return number


def _scpi_short_form(value: str) -> str:
    return "".join(char for char in value if not char.isalpha() or char.isupper())


def _validate_scpi_token(value: object, choices: tuple[str, ...], name: str) -> str:
    text = _format_arg(value)
    normalized = text.upper()
    for choice in choices:
        if normalized in {choice.upper(), _scpi_short_form(choice).upper()}:
            return choice
    allowed = ", ".join(choices)
    raise ValueError(f"{name} must be one of: {allowed}")


def _validate_average_count(value: int) -> int:
    count = _validate_int_range(value, "acquisition average count", 2, 65536)
    if count & (count - 1):
        raise ValueError("acquisition average count must be a power of two from 2 to 65536")
    return count


def _normalize_memory_depth(value: object) -> str:
    if isinstance(value, int):
        try:
            return _MEMORY_DEPTH_BY_POINTS[value]
        except KeyError as exc:
            raise ValueError("memory depth must match a documented MSO5000 depth") from exc
    return _validate_scpi_token(value, _MEMORY_DEPTH_TOKENS, "memory depth")


def _validate_probe_ratio(value: int | float) -> float:
    ratio = _validate_positive_finite(value, "probe ratio")
    if ratio not in _PROBE_RATIOS:
        raise ValueError("probe ratio must match a documented CHANnel<n>:PROBe value")
    return ratio


def _validate_measurement_item(value: object) -> str:
    return _validate_scpi_token(value, _MEASUREMENT_ITEMS, "measurement item")


def _validate_measurement_statistic(value: object) -> str:
    return _validate_scpi_token(value, _MEASUREMENT_STATISTICS, "measurement statistic")


def _validate_measurement_source(value: object) -> str:
    return _validate_scpi_token(value, _MEASUREMENT_SOURCES, "measurement source")


def _validate_measurement_threshold_source(value: object) -> str:
    return _validate_scpi_token(
        value,
        _MEASUREMENT_THRESHOLD_SOURCES,
        "measurement threshold source",
    )


def _validate_edge_source(value: object) -> str:
    return _validate_scpi_token(value, _EDGE_SOURCES, "edge trigger source")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().upper()
    if normalized in {"1", "ON", "TRUE"}:
        return True
    if normalized in {"0", "OFF", "FALSE"}:
        return False
    raise ValueError(f"invalid boolean response: {value!r}")


def _parse_int(value: str) -> int:
    return int(float(value.strip()))


def _parse_float(value: str) -> float:
    return float(value.strip())


def _parse_csv_ints(value: str) -> tuple[int, ...]:
    fields = [item.strip() for item in value.split(",") if item.strip()]
    if not fields:
        raise ValueError(f"invalid integer list response: {value!r}")
    return tuple(int(item) for item in fields)


def _parse_identification(value: str) -> Mso5204Identification:
    fields = [item.strip() for item in value.split(",", 3)]
    if len(fields) != 4:
        raise ValueError(f"invalid *IDN? response: {value!r}")
    return Mso5204Identification(*fields)


def _parse_system_error(value: str) -> Mso5204SystemError:
    code_text, separator, message_text = value.partition(",")
    if not separator:
        raise ValueError(f"invalid SYSTem:ERRor? response: {value!r}")
    message = message_text.strip()
    if len(message) >= 2 and message.startswith('"') and message.endswith('"'):
        message = message[1:-1]
    return Mso5204SystemError(code=int(code_text.strip()), message=message)


def _parse_preamble(value: str) -> Mso5204WaveformPreamble:
    fields = [item.strip() for item in value.split(",")]
    if len(fields) != 10:
        raise ValueError(f"invalid WAVeform:PREamble? response: {value!r}")
    return Mso5204WaveformPreamble(
        format_code=int(fields[0]),
        type_code=int(fields[1]),
        points=int(fields[2]),
        count=int(fields[3]),
        x_increment_s=float(fields[4]),
        x_origin_s=float(fields[5]),
        x_reference=float(fields[6]),
        y_increment_v=float(fields[7]),
        y_origin=float(fields[8]),
        y_reference=float(fields[9]),
    )
