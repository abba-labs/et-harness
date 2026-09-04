# SPI公共业务入口；Case只依赖稳定类型和Driver动作。
# 职责：导出SPI直接动作、配置与状态类型。
# 边界：导入不执行硬件初始化或测试流程。
# 依赖：仅本IP Driver和Model。
from .contract import SPI_SERVICE_ID
from .driver import SpiCaptureError, SpiDriver
from .models import (
    SpiClockMode,
    SpiConfig,
    SpiCsPolicy,
    SpiErrorStatus,
    SpiFormat,
    SpiIrq,
    SpiIrqEvent,
    SpiLimits,
    SpiRole,
    SpiSnapshot,
    SpiStatusFlag,
    SpiTransferMode,
)

__all__ = [
    "SPI_SERVICE_ID",
    "SpiCaptureError",
    "SpiDriver",
    "SpiRole",
    "SpiFormat",
    "SpiClockMode",
    "SpiTransferMode",
    "SpiCsPolicy",
    "SpiConfig",
    "SpiLimits",
    "SpiSnapshot",
    "SpiIrq",
    "SpiIrqEvent",
    "SpiErrorStatus",
    "SpiStatusFlag",
]
