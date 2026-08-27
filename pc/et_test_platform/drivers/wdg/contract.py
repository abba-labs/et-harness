# WDG Wire 常量与命令编号。
# 职责：冻结 WDG Service 的公开二进制布局。
# 边界：不执行 I/O，不包含芯片实例、地址或 IRQ 号。
# 依赖：仅依赖标准库。

from enum import IntEnum
from struct import Struct

WDG_SERVICE_ID = 0x0105
WDG_SERVICE_API_VERSION = 1

CAPABILITIES_STRUCT = Struct("<HHIII4B")
CONFIG_STRUCT = Struct("<IIIBBBB")
STATUS_STRUCT = Struct("<B3xI")
MASK_STRUCT = Struct("<I")
IRQ_SNAPSHOT_STRUCT = Struct("<IIIII")
RECORD_STRUCT = Struct("<BB2x")


# WDG Service 公开命令编号，与 Firmware Contract 逐值对应。
class WdgCommand(IntEnum):
    CAPABILITIES_GET = 0x0001
    UNLOCK = 0x0002
    LOCK = 0x0003
    CONFIGURE = 0x0004
    CONFIG_GET = 0x0005
    ENABLE = 0x0006
    DISABLE = 0x0007
    FEED = 0x0008
    STATUS_GET = 0x0009
    MODULE_RESET = 0x000A
    IRQ_ENABLE = 0x000B
    IRQ_DISABLE = 0x000C
    IRQ_MASK = 0x000D
    IRQ_UNMASK = 0x000E
    IRQ_FORCE = 0x000F
    IRQ_CLEAR = 0x0010
    IRQ_SNAPSHOT_GET = 0x0011
    RECORD_GET = 0x0012
    RECORD_CLEAR = 0x0013
