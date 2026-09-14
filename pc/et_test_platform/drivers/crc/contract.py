# CRC PC Driver Package 的 contract 层。
#
# 职责：提供 CRC 已发布的 Service、Command 和 Wire 常量。
# 边界：不发送请求、不解析能力、不承载运行时策略。
# 依赖：仅依赖标准库 Enum。

from enum import IntEnum

CRC_SERVICE_ID = 0x0102
CRC_SERVICE_API_VERSION = 1
CRC_CAPABILITIES_SIZE = 16


# CRC Firmware Service 已发布命令编号。
class CrcCommand(IntEnum):
    CAPABILITIES_GET = 0x0001
    ENABLE = 0x0002
    DISABLE = 0x0003
    CONFIGURE = 0x0004
    CALCULATE = 0x0005
    DATA_LENGTH_SET = 0x0006
    DATA_LENGTH_GET = 0x0007
    RESULT_GET = 0x0008
    CHECK_VALUE_SET = 0x0009
    FIFO_STATUS_GET = 0x000A
    IRQ_ENABLE = 0x000B
    IRQ_DISABLE = 0x000C
    IRQ_MASK = 0x000D
    IRQ_UNMASK = 0x000E
    IRQ_FORCE = 0x000F
    IRQ_CLEAR = 0x0010
    IRQ_SNAPSHOT_GET = 0x0011
    TEST_INPUT_WRITE = 0x0012
    TEST_CALCULATE_TIMED = 0x0013
    TEST_INPUT_BURST_32 = 0x0014
    CONTEXT_RESET = 0x0015
