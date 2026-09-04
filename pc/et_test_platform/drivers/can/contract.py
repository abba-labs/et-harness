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
    RAM_LIMITS_GET = 9
    RAM_LAYOUT_SET = 10
    RAM_LAYOUT_GET = 11
    BUS_CONFIG_SET = 12
    BUS_CONFIG_GET = 13
    LOOPBACK_SET = 14
    LOOPBACK_GET = 15
    BUS_LIMITS_GET = 16


REQUEST_WORDS = (0, 1, 0, 0, 8, 0, 10, 0, 0, 0, 24, 0, 11, 0, 1, 0, 0)
RESPONSE_WORDS = (2, 0, 1, 8, 0, 8, 0, 10, 3, 7, 0, 24, 0, 11, 0, 1, 2)
BUS_FIELDS = (
    "monitor",
    "restricted",
    "timestamp_divisor",
    "timestamp_source",
    "timeout_source",
    "timeout_period",
    "timeout_enabled",
    "reject_remote_ext",
    "reject_remote_std",
    "unmatched_ext",
    "unmatched_std",
)
BUS_FLAGS = frozenset(
    {"monitor", "restricted", "timeout_enabled", "reject_remote_ext", "reject_remote_std"}
)
RAM_FIELDS = (
    "std_offset",
    "std_count",
    "ext_offset",
    "ext_count",
    "tx_offset",
    "tx_buffer_count",
    "tx_fifo_count",
    "tx_queue",
    "tx_payload_bytes",
    "event_offset",
    "event_count",
    "event_watermark",
    "rx0_offset",
    "rx0_count",
    "rx0_watermark",
    "rx0_overwrite",
    "rx1_offset",
    "rx1_count",
    "rx1_watermark",
    "rx1_overwrite",
    "rx_buffer_offset",
    "rx_buffer_payload_bytes",
    "rx0_payload_bytes",
    "rx1_payload_bytes",
)
RAM_FLAGS = frozenset({"tx_queue", "rx0_overwrite", "rx1_overwrite"})
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
        CanCommand.RAM_LIMITS_GET,
        CanCommand.RAM_LAYOUT_GET,
        CanCommand.BUS_CONFIG_GET,
        CanCommand.LOOPBACK_GET,
        CanCommand.BUS_LIMITS_GET,
    }
)
