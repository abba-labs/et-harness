# SPI命令及固定Wire布局。
# 职责：集中Service身份、命令编号和u32字段数。
# 边界：不访问Profile或设备；不引入第二套帧协议。
# 依赖：仅标准库。

from enum import IntEnum
from struct import Struct

SPI_SERVICE_ID = 0x010B
WORD = Struct("<I")
INSTANCE = Struct("<B")
DEFAULT_TIMEOUT_S = 1.0
POLL_INTERVAL_S = 0.001


# 每个命令只触发一种原子SPI动作；配置顺序留给Case。
class SpiCommand(IntEnum):
    LIMITS_GET = 0
    CONFIGURE = 1
    CONFIG_GET = 2
    ENABLE_SET = 3
    FIFO_RESET = 4
    DIVIDER_SET = 5
    FRAME_COUNT_SET = 6
    CS_SET = 7
    LOOPBACK_SET = 8
    FIFO_THRESHOLDS_SET = 9
    SNAPSHOT_GET = 10
    ERROR_STATUS_READ = 11
    WRITE_FRAME = 12
    READ_FRAME = 13
    TEST_FIFO_WRITE_ONCE = 14
    TEST_FIFO_READ_ONCE = 15
    DMA_CONFIGURE = 16
    DMA_ENDPOINT_GET = 17
    IRQ_MASK_SET = 18
    IRQ_CLEAR = 19
    IRQ_CAPTURE_START = 20
    IRQ_CAPTURE_STOP = 21
    IRQ_EVENT_GET = 22
    IRQ_EVENT_RESET = 23


# 与公共文档同序，单位是u32字段数；响应不带实例前缀。
REQUEST_WORDS = (0, 16, 0, 1, 0, 1, 1, 1, 1, 3, 0, 0, 1, 0, 1, 0, 4, 0, 2, 1, 1, 0, 0, 0)
RESPONSE_WORDS = (7, 0, 16, 0, 0, 0, 0, 0, 0, 0, 14, 2, 1, 2, 0, 1, 0, 2, 0, 0, 0, 0, 8, 0)
CONFIG_FIELDS = (
    "role",
    "frame_format",
    "clock_mode",
    "transfer_mode",
    "cs_policy",
    "frame_bits",
    "frame_count",
    "divider",
    "target_output_enabled",
    "loopback",
    "rx_sample_delay",
    "control_bits",
    "sequential",
    "transmit",
    "handshake",
    "reserved",
)
