# SYSCTRL PC Driver Package 的validation层。
#
# 职责：提供 SYSCTRL 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from .models import DmaRequestRoute


# 校验一个明确拒绝 bool 的 uint8。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def require_uint8(value: object, name: str) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"SYSCTRL {name} must be an integer")
    if not 0 <= value <= 0xFF:
        raise ValueError(f"SYSCTRL {name} must fit uint8")
    return value


# 校验一个非零 uint64。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def require_nonzero_uint64(value: object, name: str) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"SYSCTRL {name} must be an integer")
    if not 0 < value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"SYSCTRL {name} must fit nonzero uint64")
    return value


# 校验 PC 已解析的直接 DMAMUX Route。
def validate_request_route(route: DmaRequestRoute) -> None:

    require_uint8(route.controller, "controller")
    require_uint8(route.interface, "interface")
    require_uint8(route.request_id, "request_id")
