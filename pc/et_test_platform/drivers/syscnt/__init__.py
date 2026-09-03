# SYSCNT Driver公开入口。
# 职责：导出稳定动作与语义类型。
# 边界：导入不访问硬件。
# 依赖：本IP实现。

from .contract import SYSCNT_SERVICE_ID
from .driver import SyscntDriver
from .models import (
    SyscntCapabilities,
    SyscntControl,
    SyscntFeature,
    SyscntHaltPolicy,
    SyscntReferenceSample,
    SyscntView,
)

__all__ = [
    "SYSCNT_SERVICE_ID",
    "SyscntDriver",
    "SyscntCapabilities",
    "SyscntControl",
    "SyscntFeature",
    "SyscntHaltPolicy",
    "SyscntReferenceSample",
    "SyscntView",
]
