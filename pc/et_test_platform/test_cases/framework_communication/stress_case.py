# Formal Case辅助模块。
#
# 职责：承载所属测试域的明确辅助职责。
# 边界：不隐藏完整Case、不绕过能力门禁，也不直接访问Transport。
# 依赖：仅依赖稳定公共接口和本测试域模块。

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PayloadClass:
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class CommunicationStressPlan:
    rounds: int
    payload_classes: tuple[PayloadClass, ...]

    def __post_init__(self) -> None:
        if self.rounds <= 0:
            raise ValueError("rounds must be positive")
        if not self.payload_classes:
            raise ValueError("at least one payload class is required")
        names = {item.name for item in self.payload_classes}
        if len(names) != len(self.payload_classes):
            raise ValueError("payload class names must be unique")
        if any(item.size < 8 or item.size > 4088 for item in self.payload_classes):
            raise ValueError("payload sizes must be between 8 and 4088 bytes")


FORMAL_STRESS_PLAN = CommunicationStressPlan(
    rounds=20,
    payload_classes=(
        PayloadClass("small", 16),
        PayloadClass("medium", 256),
        PayloadClass("large", 2048),
    ),
)


# Return one deterministic ECHO payload without performing I/O.
def payload_for_round(round_index: int, class_index: int, size: int) -> bytes:

    prefix = struct.pack("<II", round_index, class_index)
    return prefix + bytes(
        ((round_index * 17 + class_index * 53 + index) & 0xFF)
        for index in range(size - len(prefix))
    )


# Return the nearest-rank-like sample used by the stress measurements.
def percentile(values: list[float], fraction: float) -> float:

    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("percentile fraction must be between zero and one")
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, round((len(ordered) - 1) * fraction)),
    )
    return ordered[index]
