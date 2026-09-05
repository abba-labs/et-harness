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
FRAME_DATA_BYTES = 64
# 固定Wire批大小，不代表芯片RAM容量；最后一批允许少于64个有效word。
RAM_ACCESS_WORDS = 64
CLASSIC_DATA_BYTES = 8
STANDARD_ID_MAX = 0x7FF
EXTENDED_ID_MAX = 0x1FFFFFFF
RX_HEADER_WORDS = 8
TX_HEADER_WORDS = 5
# CAN-FD标准DLC对应的长度，不是芯片的RAM或FIFO容量。
FD_DATA_LENGTHS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)


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
    TX_WRITE = 17
    TX_REQUEST = 18
    TX_STATUS_GET = 19
    RX_FIFO_STATUS_GET = 20
    RX_READ = 21
    RX_FIFO_ACK = 22
    RX_BUFFER_STATUS_GET = 23
    RX_BUFFER_ACK = 24
    FILTER_SET = 25
    FILTER_GET = 26
    EXTENDED_MASK_SET = 27
    EXTENDED_MASK_GET = 28
    PROTOCOL_STATUS_CONSUME = 29
    TIMESTAMP_GET = 30
    TIMESTAMP_RESET = 31
    TIMEOUT_COUNTER_GET = 32
    CLOCK_STOP_SET = 33
    CLOCK_STOP_ACK_GET = 34
    IRQ_MASK_SET = 35
    IRQ_LINE_SELECT_SET = 36
    IRQ_SNAPSHOT_GET = 37
    IRQ_CLEAR = 38
    IRQ_CAPTURE_START = 39
    IRQ_CAPTURE_STOP = 40
    IRQ_EVENT_GET = 41
    IRQ_EVENT_RESET = 42
    HIGH_PRIORITY_STATUS_GET = 43
    TX_EVENT_STATUS_GET = 44
    TX_EVENT_READ = 45
    TX_EVENT_ACK = 46
    TX_READ = 47
    TX_BUFFER_IRQ_SET = 48
    IRQ_CAPTURE_PENDING = 49
    IRQ_LINE_EVENTS_GET = 50
    RAM_WORDS_READ = 51
    RAM_WORDS_WRITE = 52
    RAM_WORDS_EXCHANGE = 53
    CONFIGURATION_WRITE_SET = 54
    CONFIGURATION_WRITE_GET = 55
    NOMINAL_TIMING_WRITE = 56


REQUEST_WORDS = (
    0,
    1,
    0,
    0,
    8,
    0,
    10,
    0,
    0,
    0,
    24,
    0,
    11,
    0,
    1,
    0,
    0,
    21,
    1,
    0,
    1,
    2,
    2,
    0,
    2,
    7,
    2,
    1,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    2,
    2,
    0,
    1,
    2,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    1,  # TX_READ: selected slot.
    2,  # TX_BUFFER_IRQ_SET: selected slot and Boolean enable.
    2,  # IRQ_CAPTURE_PENDING: watched sources and line-1 subset; retain Raw.
    0,  # IRQ_LINE_EVENTS_GET: per-line Service latches.
    3,  # RAM_WORDS_READ: byte offset, valid count, traversal direction.
    3 + RAM_ACCESS_WORDS,
    3 + RAM_ACCESS_WORDS,
    1,
    0,
    4,
)
RESPONSE_WORDS = (
    2,
    0,
    1,
    8,
    0,
    8,
    0,
    10,
    3,
    7,
    0,
    24,
    0,
    11,
    0,
    1,
    2,
    0,
    0,
    7,
    5,
    24,
    0,
    2,
    0,
    0,
    5,
    0,
    1,
    15,
    1,
    0,
    1,
    0,
    1,
    0,
    0,
    4,
    0,
    0,
    0,
    8,
    0,
    4,
    5,
    7,
    0,
    21,  # TX_READ: index + header + padded payload.
    0,  # TX_BUFFER_IRQ_SET: explicit write, no response fields.
    0,  # IRQ_CAPTURE_PENDING: explicit capture setup.
    2,  # IRQ_LINE_EVENTS_GET: line-0 and line-1 source latches.
    RAM_ACCESS_WORDS,
    0,
    RAM_ACCESS_WORDS,
    0,
    1,
    0,
)
# Protocol consume的固定字段顺序；只读清一次，不在READ_ONLY_COMMANDS内。
PROTOCOL_FIELDS = (
    "last_error",
    "activity",
    "error_passive",
    "warning",
    "bus_off",
    "data_last_error",
    "received_esi",
    "received_brs",
    "received_fd",
    "protocol_exception",
    "tdc_position",
    "tx_error_count",
    "rx_error_count",
    "rx_error_passive",
    "error_log_count",
)
PROTOCOL_FLAGS = frozenset(
    {
        "error_passive",
        "warning",
        "bus_off",
        "received_esi",
        "received_brs",
        "received_fd",
        "protocol_exception",
        "rx_error_passive",
    }
)
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
        CanCommand.TX_STATUS_GET,
        CanCommand.RX_FIFO_STATUS_GET,
        CanCommand.RX_READ,
        CanCommand.RX_BUFFER_STATUS_GET,
        CanCommand.FILTER_GET,
        CanCommand.EXTENDED_MASK_GET,
        CanCommand.TIMESTAMP_GET,
        CanCommand.TIMEOUT_COUNTER_GET,
        CanCommand.CLOCK_STOP_ACK_GET,
        CanCommand.IRQ_SNAPSHOT_GET,
        CanCommand.IRQ_EVENT_GET,
        CanCommand.HIGH_PRIORITY_STATUS_GET,
        CanCommand.TX_EVENT_STATUS_GET,
        CanCommand.TX_EVENT_READ,
        CanCommand.TX_READ,
        CanCommand.IRQ_LINE_EVENTS_GET,
        CanCommand.RAM_WORDS_READ,
        CanCommand.CONFIGURATION_WRITE_GET,
    }
)
