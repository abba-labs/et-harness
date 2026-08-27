# WDG PC Driver Package 公开入口。
# 职责：统一导出 WDG 稳定 Contract、Model 和 Driver API。
# 边界：不执行 I/O、不解析 Capability、不实现 Case 流程。
# 依赖：仅依赖本 IP 的 contract、driver 和 models 模块。

from .contract import WDG_SERVICE_ID, WdgCommand
from .driver import WdgDriver
from .models import (
    WdgCapabilities,
    WdgConfig,
    WdgFeature,
    WdgIrqEvent,
    WdgIrqSnapshot,
    WdgMode,
    WdgRecord,
    WdgRecordSnapshot,
    WdgStatus,
    WdgWorkMode,
)

__all__ = (
    "WDG_SERVICE_ID",
    "WdgCapabilities",
    "WdgCommand",
    "WdgConfig",
    "WdgDriver",
    "WdgFeature",
    "WdgIrqEvent",
    "WdgIrqSnapshot",
    "WdgMode",
    "WdgRecord",
    "WdgRecordSnapshot",
    "WdgStatus",
    "WdgWorkMode",
)
