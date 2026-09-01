# SPINLOCK PC Driver Package 公开入口。
# 职责：统一导出 SPINLOCK 稳定 Contract、Model 和 Driver API。
# 边界：不执行 I/O、不解析 Capability、不实现 Case 流程。
# 依赖：仅依赖本 IP 的 contract、driver 和 models 模块。

from .contract import SPINLOCK_SERVICE_ID, SpinlockCommand
from .driver import SpinlockDriver
from .models import (
    SpinlockCapabilities,
    SpinlockClearScope,
    SpinlockConfigSnapshot,
    SpinlockFeature,
    SpinlockFlagSnapshot,
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobSnapshot,
    SpinlockPeerJobState,
    SpinlockPeerJobType,
    SpinlockPeerResult,
    SpinlockPeerStatus,
    SpinlockResourceSnapshot,
    SpinlockSharedSnapshot,
)

__all__ = (
    "SPINLOCK_SERVICE_ID",
    "SpinlockCapabilities",
    "SpinlockClearScope",
    "SpinlockCommand",
    "SpinlockConfigSnapshot",
    "SpinlockDriver",
    "SpinlockFeature",
    "SpinlockFlagSnapshot",
    "SpinlockMode",
    "SpinlockPeerControl",
    "SpinlockPeerJobSnapshot",
    "SpinlockPeerJobState",
    "SpinlockPeerJobType",
    "SpinlockPeerResult",
    "SpinlockPeerStatus",
    "SpinlockResourceSnapshot",
    "SpinlockSharedSnapshot",
)
