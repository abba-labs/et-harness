# FMAC PC Driver Package的公开入口。
# 职责：统一导出稳定Driver、枚举和结果模型。
# 边界：不执行请求、不读取Profile、不承载Case流程。
# 依赖：仅依赖本FMAC Driver Package内部模块。

from .contract import FMAC_SERVICE_ID, FmacCommand
from .driver import FmacDriver
from .models import (
    FmacCapabilities,
    FmacConfig,
    FmacDataFormat,
    FmacDmaRequest,
    FmacFeature,
    FmacFinalPolicy,
    FmacFunction,
    FmacIrqEvent,
    FmacIrqSnapshot,
    FmacOutputMode,
    FmacProcessResult,
    FmacShift,
    FmacStatus,
    FmacTimedProcessResult,
    FmacWatermark,
)

__all__ = (
    "FMAC_SERVICE_ID",
    "FmacCapabilities",
    "FmacCommand",
    "FmacConfig",
    "FmacDataFormat",
    "FmacDmaRequest",
    "FmacDriver",
    "FmacFeature",
    "FmacFinalPolicy",
    "FmacFunction",
    "FmacIrqEvent",
    "FmacIrqSnapshot",
    "FmacOutputMode",
    "FmacProcessResult",
    "FmacShift",
    "FmacStatus",
    "FmacTimedProcessResult",
    "FmacWatermark",
)
