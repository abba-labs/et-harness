# RESOURCE PC Driver Package 的validation层。
#
# 职责：提供 RESOURCE 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from .models import ResourceRef


# 校验明确拒绝 bool 的 uint32。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def require_uint32(value: object, name: str, *, nonzero: bool = False) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Resource {name} must be an integer")
    minimum = 1 if nonzero else 0
    if not minimum <= value <= 0xFFFFFFFF:
        raise ValueError(f"Resource {name} must fit uint32")
    return value


# 校验一个资源内的 Offset/Size 范围。
def validate_range(
    resource: ResourceRef,
    *,
    offset: object,
    size: object,
    operation: str,
) -> tuple[int, int]:

    offset_value = require_uint32(offset, f"{operation} offset")
    size_value = require_uint32(size, f"{operation} size")
    if offset_value > resource.size or size_value > resource.size - offset_value:
        raise ValueError(f"resource {operation} is outside the allocated range")
    return offset_value, size_value


# 校验 Fill Byte。
#
# 该 API 只校验本层参数语义；非法值在发送 Target 请求前被显式拒绝。
def validate_fill_value(value: object) -> int:

    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise ValueError("Resource fill value must fit uint8")
    return value
