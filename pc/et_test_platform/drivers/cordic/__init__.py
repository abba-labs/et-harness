# CORDIC PC Driver Package 的公共导出层。
#
# 职责：导出 Case 可依赖的稳定 Driver、Model 和 Service 标识。
# 边界：不实现 Wire 编解码、不访问 Target/Profile、不承载测试流程。
# 依赖：仅依赖本 IP 的 Contract、Driver 和 Model。

from .contract import CORDIC_SERVICE_ID
from .driver import CordicDriver
from .models import (
    CordicCapabilities,
    CordicConfig,
    CordicConversionStatus,
    CordicFeature,
    CordicFunction,
    CordicInputRange,
    CordicIrqEvent,
    CordicIrqSnapshot,
    CordicNumericMode,
    CordicResult,
    CordicResultCount,
    CordicStatus,
    CordicTimedResult,
    CordicWidth,
    CordicWorkMode,
)

__all__ = [
    "CordicCapabilities",
    "CordicConfig",
    "CordicConversionStatus",
    "CordicDriver",
    "CordicFeature",
    "CordicFunction",
    "CordicInputRange",
    "CordicIrqEvent",
    "CordicIrqSnapshot",
    "CordicNumericMode",
    "CordicResult",
    "CordicTimedResult",
    "CordicResultCount",
    "CordicStatus",
    "CordicWidth",
    "CordicWorkMode",
    "CORDIC_SERVICE_ID",
]
