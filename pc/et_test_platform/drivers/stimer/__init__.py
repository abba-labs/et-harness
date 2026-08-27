# STIMER PC Driver Package 公开入口。
# 职责：统一导出 STIMER 稳定 Contract、Model 和 Driver API。
# 边界：不执行 I/O、不解析 Capability、不实现 Case 流程。
# 依赖：仅依赖本 IP 的 contract、driver 和 models 模块。

from .contract import STIMER_SERVICE_ID, StimerCommand
from .driver import StimerDriver
from .models import (
    StimerCapabilities,
    StimerConfig,
    StimerDebugHaltPolicy,
    StimerFeature,
    StimerIrqEvent,
    StimerIrqSnapshot,
    StimerLoadMode,
    StimerMode,
    StimerRuntimeStatus,
)

__all__ = (
    "STIMER_SERVICE_ID",
    "StimerCapabilities",
    "StimerCommand",
    "StimerConfig",
    "StimerDebugHaltPolicy",
    "StimerDriver",
    "StimerFeature",
    "StimerIrqEvent",
    "StimerIrqSnapshot",
    "StimerLoadMode",
    "StimerMode",
    "StimerRuntimeStatus",
)
