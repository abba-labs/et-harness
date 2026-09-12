# ETIM稳定公共入口。
# 职责：导出原子Driver与类型。
# 边界：不公开Codec、Wire常量或芯片事实。
# 依赖：仅本IPDriver和Model。

from .driver import EtimDriver
from .models import (
    EtimCapabilities,
    EtimCount,
    EtimCountObservation,
    EtimEnable,
    EtimIrq,
    EtimIrqSnapshot,
    EtimOperationError,
    EtimTimebase,
)

__all__ = [
    "EtimDriver",
    "EtimCapabilities",
    "EtimCount",
    "EtimCountObservation",
    "EtimEnable",
    "EtimIrq",
    "EtimIrqSnapshot",
    "EtimOperationError",
    "EtimTimebase",
]
