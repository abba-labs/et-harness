# CRG PC Driver Package 的validation层。
#
# 职责：提供 CRG 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from .models import CrgPeripheral


# 转换合法 CRG Peripheral，并拒绝 bool/未知值。
def peripheral_value(value: object) -> int:

    if isinstance(value, bool):
        raise ValueError("CRG peripheral must not be bool")
    try:
        return int(CrgPeripheral(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("CRG peripheral is invalid") from exc


# 校验 CRG Instance ID。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def instance_value(value: object) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("CRG instance must be an integer")
    if not 0 <= value <= 0xFF:
        raise ValueError("CRG instance must fit uint8")
    return value


# 编码 CRG Clock Enable Bool。
def enabled_value(value: object) -> int:

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise ValueError("CRG enabled must be 0 or 1")
