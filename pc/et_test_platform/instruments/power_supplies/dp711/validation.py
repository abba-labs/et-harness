# RIGOL DP711 参数和响应校验。
#
# 职责：校验 DP711 手册固定范围，并把简单 SCPI 响应转换为稳定业务类型。
# 边界：不发送命令、不等待、不读取设备，也不判断测试 PASS/FAIL。
# 依赖：仅依赖标准库和本型号 Models/InstrumentProtocolError。

from __future__ import annotations

import math

from ...common.errors import InstrumentProtocolError
from .models import (
    Dp711ApplyState,
    Dp711FileType,
    Dp711Identification,
    Dp711Measurement,
    Dp711Options,
    Dp711OutputMode,
    Dp711SystemError,
    Dp711TimerStep,
)

DP711_VOLTAGE_MIN_V = 0.0
DP711_VOLTAGE_MAX_V = 30.0
DP711_APPLY_VOLTAGE_MAX_V = 32.0
DP711_CURRENT_MIN_A = 0.0
DP711_CURRENT_MAX_A = 5.3
DP711_OCP_MIN_A = 0.001
DP711_OCP_MAX_A = 5.5
DP711_OVP_MIN_V = 0.001
DP711_OVP_MAX_V = 33.0
DP711_TIMER_GROUP_MIN = 1
DP711_TIMER_GROUP_MAX = 2048
DP711_TIMER_CYCLE_MAX = 99999
DP711_TIMER_STEP_VOLTAGE_MAX_V = 32.0
DP711_TIMER_STEP_DURATION_MIN_S = 0.01
DP711_TIMER_STEP_DURATION_MAX_S = 99999.0
DP711_RS232_BAUDRATES = frozenset({7200, 9600, 14400, 19200, 38400, 57600, 115200})
DP711_KEYS = frozenset(
    {
        "SYSTEM",
        "MEMORY",
        "TIMER",
        "OUTPUT",
        "NUM0",
        "NUM1",
        "NUM2",
        "NUM3",
        "NUM4",
        "NUM5",
        "NUM6",
        "NUM7",
        "NUM8",
        "NUM9",
        "DOT",
        "BACK",
        "KNOB",
        "LEFT",
        "RIGHT",
        "UP",
        "DOWN",
        "OK",
        "ALL",
    }
)


# 校验一个有限浮点数落在手册固定闭区间内；校验过程不会访问仪器硬件。
def require_range(value: float, minimum: float, maximum: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return converted


# 校验一个整数落在手册固定闭区间内；校验过程不会访问仪器硬件。
def require_integer(value: int, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


# 根据 RSF/RTF 类型校验内部文件位置；校验过程不会访问仪器硬件。
def require_file_position(file_type: Dp711FileType, position: int) -> int:
    maximum = 10 if file_type is Dp711FileType.STATE else 2
    return require_integer(position, 1, maximum, "position")


# 校验并归一化前面板按键名称；校验过程不会访问仪器硬件。
def require_key(key: str) -> str:
    normalized = key.strip().upper()
    if normalized not in DP711_KEYS:
        raise ValueError(f"unsupported DP711 front-panel key: {key}")
    return normalized


# 解析 SCPI ON/OFF 或 1/0 布尔响应。
def parse_bool(response: str) -> bool:
    normalized = response.strip().upper()
    if normalized in {"ON", "1"}:
        return True
    if normalized in {"OFF", "0"}:
        return False
    raise InstrumentProtocolError(f"invalid DP711 boolean response: {response!r}")


# 解析 SCPI YES/NO 布尔响应；解析过程不会访问仪器硬件。
def parse_yes_no(response: str) -> bool:
    normalized = response.strip().upper()
    if normalized == "YES":
        return True
    if normalized == "NO":
        return False
    raise InstrumentProtocolError(f"invalid DP711 YES/NO response: {response!r}")


# 解析 *IDN? 的四段设备标识；解析过程不会访问仪器硬件。
def parse_identification(response: str) -> Dp711Identification:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) != 4:
        raise InstrumentProtocolError(f"invalid DP711 *IDN? response: {response!r}")
    return Dp711Identification(*parts)


# 解析 *OPT? 的 Trigger/Timer/High Resolution 三个选件槽。
def parse_options(response: str) -> Dp711Options:
    parts = [part.strip().upper() for part in response.split(",")]
    if len(parts) != 3:
        raise InstrumentProtocolError(f"invalid DP711 *OPT? response: {response!r}")
    return Dp711Options(
        trigger=parts[0] == "DP7-TRIGGER",
        timer=parts[1] == "DP7-TIMER",
        high_resolution=parts[2] == "DP7-HIRES",
    )


# 解析 APPLy? 的电压和电流设定值；解析过程不会访问仪器硬件。
def parse_apply_state(response: str) -> Dp711ApplyState:
    values = _parse_float_list(response, 2, "APPLY")
    return Dp711ApplyState(voltage_v=values[0], current_a=values[1])


# 解析 MEASure:ALL? 的电压、电流和功率。
def parse_measurement(response: str) -> Dp711Measurement:
    values = _parse_float_list(response, 3, "MEASURE:ALL")
    return Dp711Measurement(voltage_v=values[0], current_a=values[1], power_w=values[2])


# 解析 OUTPut 模式为稳定枚举；解析过程不会访问仪器硬件。
def parse_output_mode(response: str) -> Dp711OutputMode:
    try:
        return Dp711OutputMode(response.strip().upper())
    except ValueError as exc:
        raise InstrumentProtocolError(f"invalid DP711 output mode: {response!r}") from exc


# 解析错误队列的错误码和引号消息；解析过程不会访问仪器硬件。
def parse_system_error(response: str) -> Dp711SystemError:
    code_text, separator, message = response.partition(",")
    if not separator:
        raise InstrumentProtocolError(f"invalid DP711 system error response: {response!r}")
    try:
        code = int(code_text.strip())
    except ValueError as exc:
        raise InstrumentProtocolError(f"invalid DP711 system error code: {response!r}") from exc
    return Dp711SystemError(code=code, message=message.strip().strip('"'))


# 解析去除 IEEE488.2 block header 后的 Timer 组文本。
def parse_timer_steps(payload: bytes) -> tuple[Dp711TimerStep, ...]:
    try:
        text = payload.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise InstrumentProtocolError("DP711 timer response is not ASCII") from exc
    steps: list[Dp711TimerStep] = []
    for item in text.split(";"):
        if not item.strip():
            continue
        fields = [field.strip() for field in item.split(",")]
        if len(fields) != 4:
            raise InstrumentProtocolError(f"invalid DP711 timer step: {item!r}")
        try:
            steps.append(
                Dp711TimerStep(
                    group=int(fields[0]),
                    voltage_v=float(fields[1]),
                    current_a=float(fields[2]),
                    duration_s=float(fields[3]),
                )
            )
        except ValueError as exc:
            raise InstrumentProtocolError(f"invalid DP711 timer step: {item!r}") from exc
    return tuple(steps)


def _parse_float_list(response: str, count: int, label: str) -> tuple[float, ...]:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) != count:
        raise InstrumentProtocolError(f"invalid DP711 {label} response: {response!r}")
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise InstrumentProtocolError(
            f"invalid DP711 {label} numeric response: {response!r}"
        ) from exc
