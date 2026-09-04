# CAN公共命令与固定Wire合同。
# 职责：集中命令编号、小端字段顺序和精确字段数。
# 边界：不包含芯片地址、IO、寄存器位或CAN盒子协议。
# 依赖：标准库。

from enum import IntEnum
from struct import Struct

CAN_SERVICE_ID = 0x010C
WORD = Struct("<I")
INSTANCE = Struct("<B")
POLL_INTERVAL_S = 0.001


# 只追加新命令，不复用已发布ID；与can.md和CAN Service保持一致。
class CanCommand(IntEnum):
    IDENTITY_GET = 0
    INITIALIZING_SET = 1
    INITIALIZING_GET = 2
    TIMING_LIMITS_GET = 3
    TIMING_SET = 4
    TIMING_GET = 5
    OPTIONS_SET = 6
    OPTIONS_GET = 7
    OPTION_LIMITS_GET = 8


REQUEST_WORDS = (0, 1, 0, 0, 8, 0, 10, 0, 0)
RESPONSE_WORDS = (2, 0, 1, 8, 0, 8, 0, 10, 3)
PHASE_FIELDS = ("prescaler", "segment1", "segment2", "sjw")
OPTION_FLAGS = (
    "fd_enabled",
    "brs_enabled",
    "automatic_retry",
    "tx_pause",
    "edge_filter",
    "protocol_exception",
    "tdc_enabled",
)
OPTION_COUNTS = ("tdc_offset_cycles", "tdc_filter_cycles", "ram_watchdog_cycles")
READ_ONLY_COMMANDS = frozenset(
    {
        CanCommand.IDENTITY_GET,
        CanCommand.INITIALIZING_GET,
        CanCommand.TIMING_LIMITS_GET,
        CanCommand.TIMING_GET,
        CanCommand.OPTIONS_GET,
        CanCommand.OPTION_LIMITS_GET,
    }
)
