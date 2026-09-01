# UART PC Driver Package 的validation层。
#
# 职责：提供 UART 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from enum import IntEnum
from typing import TypeVar

from ...core.deadline import require_positive_seconds
from .models import UartDmaMode, UartParity, UartStopBits

_EnumT = TypeVar("_EnumT", bound=IntEnum)


# 转换合法枚举值，同时拒绝 bool 和未知值。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def enum_value(value: object, enum_type: type[_EnumT], name: str) -> int:

    if isinstance(value, bool):
        raise ValueError(f"UART {name} must not be bool")
    try:
        return int(enum_type(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"UART {name} is invalid") from exc


# 校验一个无符号整数。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def uint(value: object, bits: int, name: str, *, nonzero: bool = False) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"UART {name} must be an integer")
    maximum = (1 << bits) - 1
    if value < (1 if nonzero else 0) or value > maximum:
        raise ValueError(f"UART {name} is outside uint{bits} range")
    return value


# 将 bool 或 0/1 转换为 Wire Bool。
def bool_byte(value: object, name: str) -> int:

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise ValueError(f"UART {name} must be 0 or 1")


# 返回规范化的 UART Line Config 字段。
def validate_line_config(
    *,
    baudrate: object,
    data_bits: object,
    stop_bits: object,
    parity: object,
) -> tuple[int, int, int, int]:

    baudrate_value = uint(baudrate, 32, "baudrate", nonzero=True)
    data_bits_value = uint(data_bits, 8, "data_bits")
    if not 5 <= data_bits_value <= 8:
        raise ValueError(
            "UART data_bits must be between 5 and 8; use nine_bit_config() for 9-bit mode"
        )

    one_and_half = False
    if isinstance(stop_bits, float):
        if stop_bits != 1.5:
            raise ValueError("UART stop bits is invalid")
        stop_value = int(UartStopBits.ONE_AND_HALF)
        one_and_half = True
    elif isinstance(stop_bits, UartStopBits):
        stop_value = int(stop_bits)
        one_and_half = stop_bits == UartStopBits.ONE_AND_HALF
    else:
        legacy_value = uint(stop_bits, 8, "stop bits")
        if legacy_value == 1:
            stop_value = int(UartStopBits.ONE)
        elif legacy_value in (2, 3):
            stop_value = int(UartStopBits.TWO)
        else:
            raise ValueError("UART stop bits is invalid")
    if one_and_half and data_bits_value != 5:
        raise ValueError("UART 1.5 stop bits is valid only with 5 data bits")
    if stop_value == int(UartStopBits.TWO) and data_bits_value == 5:
        raise ValueError("UART 5 data bits supports 1 or 1.5 stop bits")

    parity_value = enum_value(parity, UartParity, "parity")
    return baudrate_value, data_bits_value, stop_value, parity_value


# 校验兼容 Poll Cap 和严格总 Deadline 参数。
def validate_polling(
    *,
    max_polls: object,
    timeout_s: object,
    poll_interval_s: object,
) -> tuple[int, float, float]:

    return (
        uint(max_polls, 32, "max_polls", nonzero=True),
        require_positive_seconds(timeout_s, "timeout_s"),
        require_positive_seconds(poll_interval_s, "poll_interval_s"),
    )


# 校验 validate fifo thresholds 的本 IP 参数约束；不执行设备 I/O或跨 IP 判断，非法输入以明确配置异常失败。
def validate_fifo_thresholds(tx_threshold: int, rx_threshold: int) -> None:

    if tx_threshold not in (0, 2, 4, 8):
        raise ValueError("UART TX FIFO threshold is invalid")
    if rx_threshold not in (1, 4, 8, 14):
        raise ValueError("UART RX FIFO threshold is invalid")


# 校验 validate dma mode 的本 IP 参数约束；不执行设备 I/O或跨 IP 判断，非法输入以明确配置异常失败。
def validate_dma_mode(mode: object) -> int:

    return enum_value(mode, UartDmaMode, "DMA mode")
