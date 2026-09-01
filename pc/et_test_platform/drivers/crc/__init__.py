# CRC PC Driver Package 的稳定公共导出。
#
# 职责：集中暴露 Case 允许使用的 CRC Model、Contract 和 Driver API。
# 边界：不执行设备 I/O、不导出内部 Validation 实现。
# 依赖：仅依赖本 Package 模块。

from .codec import (
    CALCULATE,
    CALCULATE_RESULT,
    CAPABILITIES,
    CONFIG,
    FIFO_STATUS,
    IRQ_SNAPSHOT,
    TEST_INPUT,
    TEST_INPUT_BURST,
    TEST_INPUT_BURST_RESULT,
    TIMED_CALCULATE,
    TIMED_RESULT,
)
from .contract import CRC_SERVICE_API_VERSION, CRC_SERVICE_ID, CrcCommand
from .driver import CrcDriver
from .models import (
    CrcCalculateResult,
    CrcCapabilities,
    CrcConfig,
    CrcFeature,
    CrcFifoStatus,
    CrcInputAccessWidth,
    CrcInputBurstResult,
    CrcIrqEvent,
    CrcIrqSnapshot,
    CrcMode,
    CrcTimedResult,
    CrcXorOut,
)

__all__ = [
    "CALCULATE",
    "CALCULATE_RESULT",
    "CAPABILITIES",
    "CONFIG",
    "CRC_SERVICE_API_VERSION",
    "CRC_SERVICE_ID",
    "FIFO_STATUS",
    "IRQ_SNAPSHOT",
    "TEST_INPUT",
    "TEST_INPUT_BURST",
    "TEST_INPUT_BURST_RESULT",
    "TIMED_CALCULATE",
    "TIMED_RESULT",
    "CrcCalculateResult",
    "CrcCapabilities",
    "CrcCommand",
    "CrcConfig",
    "CrcDriver",
    "CrcFeature",
    "CrcFifoStatus",
    "CrcInputAccessWidth",
    "CrcInputBurstResult",
    "CrcIrqEvent",
    "CrcIrqSnapshot",
    "CrcMode",
    "CrcTimedResult",
    "CrcXorOut",
]
