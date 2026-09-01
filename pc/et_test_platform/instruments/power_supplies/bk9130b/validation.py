# B&K Precision 9130B 参数与简单响应校验。
#
# 职责：校验手册明确的固定范围、通道和接口，并把简单 SCPI 响应转换为稳定业务类型。
# 边界：不发送命令、不等待设备，也不替仪器推断手册未明确给出的状态相关限制。
# 依赖：仅依赖标准库、本型号 Models 和公共仪器协议异常。

from __future__ import annotations

import math
from collections.abc import Iterable

from ...common.errors import InstrumentProtocolError
from .models import Bk9130bApplyState, Bk9130bChannel, Bk9130bIdentification, Bk9130bSystemError

BK9130B_VOLTAGE_MAX_V = 30.0
BK9130B_CH3_VOLTAGE_MAX_V = 5.0
BK9130B_CURRENT_MAX_A = 3.0
BK9130B_STORAGE_MIN = 1
BK9130B_STORAGE_MAX = 36
BK9130B_MEMORY_GROUP_MIN = 1
BK9130B_MEMORY_GROUP_MAX = 4
BK9130B_GPIB_ADDRESS_MIN = 0
BK9130B_GPIB_ADDRESS_MAX = 30
BK9130B_TRIGGER_DELAY_MIN_S = 0.1
BK9130B_TRIGGER_DELAY_MAX_S = 99999.9
_SCPI_NUMERIC_KEYWORDS = frozenset({"MIN", "MAX", "UP", "DOWN", "DEF"})


# 校验一个有限浮点数落在给定闭区间内；校验过程不会访问仪器硬件。
def require_range(value: float, minimum: float, maximum: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return converted


# 校验整数落在给定闭区间内；校验过程不会访问仪器硬件。
def require_integer(value: int, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


# 校验状态寄存器值为无符号 16 位整数；只做本地参数检查。
def require_register_value(value: int, name: str = "value") -> int:
    return require_integer(value, 0, 0xFFFF, name)


# 把布尔值转换为手册通用的 ON/OFF SCPI 参数；不执行仪器 I/O。
def format_bool(enabled: bool) -> str:
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be bool")
    return "ON" if enabled else "OFF"


# 校验并格式化数值或 MIN/MAX/UP/DOWN/DEF 关键字；不访问仪器状态。
def format_numeric_or_keyword(
    value: float | str,
    minimum: float,
    maximum: float,
    name: str,
) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized not in _SCPI_NUMERIC_KEYWORDS:
            raise ValueError(f"unsupported {name} keyword: {value}")
        return normalized
    return f"{require_range(value, minimum, maximum, name):g}"


# 校验 APPLy 的通道特定电压范围；数据表规定 CH1/2 为 30 V、CH3 为 5 V。
def require_channel_voltage(channel: Bk9130bChannel, voltage_v: float) -> float:
    maximum = BK9130B_CH3_VOLTAGE_MAX_V if channel is Bk9130bChannel.CH3 else BK9130B_VOLTAGE_MAX_V
    return require_range(voltage_v, 0.0, maximum, "voltage_v")


# 校验通道列表不为空、不重复且只包含 CH1/CH2/CH3；不执行任何仪器动作。
def format_channels(channels: Iterable[Bk9130bChannel]) -> str:
    normalized = tuple(channels)
    if not normalized:
        raise ValueError("channels must not be empty")
    if any(not isinstance(channel, Bk9130bChannel) for channel in normalized):
        raise ValueError("channels must contain Bk9130bChannel values")
    if len(set(normalized)) != len(normalized):
        raise ValueError("channels must not contain duplicates")
    return ",".join(channel.value for channel in normalized)


# 校验显示字符串可安全放入一条 ASCII SCPI 命令；不允许换行或未转义双引号。
def format_display_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("text must be str")
    normalized = text.strip()
    if not normalized:
        raise ValueError("text must not be empty")
    if "\r" in normalized or "\n" in normalized or '"' in normalized:
        raise ValueError("text must be a single line without double quotes")
    try:
        normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("text must be ASCII") from exc
    return normalized


# 解析 SCPI ON/OFF 或 1/0 布尔响应；解析过程不会修改仪器配置。
def parse_bool(response: str) -> bool:
    normalized = response.strip().upper()
    if normalized in {"ON", "1"}:
        return True
    if normalized in {"OFF", "0"}:
        return False
    raise InstrumentProtocolError(f"invalid 9130B boolean response: {response!r}")


# 解析 *IDN? 四段设备标识；解析失败时抛出明确协议异常。
def parse_identification(response: str) -> Bk9130bIdentification:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) != 4:
        raise InstrumentProtocolError(f"invalid 9130B *IDN? response: {response!r}")
    return Bk9130bIdentification(*parts)


# 解析 SYSTem:ERRor? 的错误码和消息；解析过程不会读取额外错误项。
def parse_system_error(response: str) -> Bk9130bSystemError:
    code_text, separator, message = response.partition(",")
    if not separator:
        raise InstrumentProtocolError(f"invalid 9130B system error response: {response!r}")
    try:
        code = int(code_text.strip())
    except ValueError as exc:
        raise InstrumentProtocolError(f"invalid 9130B system error code: {response!r}") from exc
    return Bk9130bSystemError(code=code, message=message.strip().strip('"'))


# 解析固定数量的逗号分隔浮点响应；数量或数值非法时抛出协议异常。
def parse_float_tuple(response: str, count: int, label: str) -> tuple[float, ...]:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) != count:
        raise InstrumentProtocolError(f"invalid 9130B {label} response: {response!r}")
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise InstrumentProtocolError(
            f"invalid 9130B {label} numeric response: {response!r}"
        ) from exc


# 解析 APPLy? 返回的电压和电流；只转换本次查询响应。
def parse_apply_state(response: str) -> Bk9130bApplyState:
    voltage, current = parse_float_tuple(response, 2, "APPLY")
    return Bk9130bApplyState(voltage_v=voltage, current_a=current)
