# ETIM基础Wire常量。
# 职责：集中Service身份、Command和定长小端布局。
# 边界：只定义本IP Body，不定义第二份ET-Frame。
# 依赖：仅标准库。

from enum import IntEnum
from struct import Struct

ETIM_SERVICE_ID = 0x010D
ETIM_API_VERSION = 1
DETAIL = Struct("<i")
CAPABILITIES = Struct("<iHHIQII")
TIMEBASE = Struct("<IQ")
TIMEBASE_RESPONSE = Struct("<iIQ")
ENABLE = Struct("<BB2x")
ENABLE_RESPONSE = Struct("<iI")
COUNT = Struct("<iII")
OBSERVATION = Struct("<iIIIII")
IRQ_CONFIG = Struct("<II")
IRQ_SNAPSHOT = Struct("<iIIII")
WORD = Struct("<I")


# 每个稳定命令只表达一个本IP动作；公共ET-Frame身份与事务由通信层负责。
class EtimCommand(IntEnum):
    CAPABILITIES_GET = 1
    TIMEBASE_CONFIGURE = 2
    TIMEBASE_GET = 3
    ENABLE_SET = 4
    ENABLE_GET = 5
    COUNT_GET = 6
    COUNT_LATCH = 7
    COUNT_CLEAR = 8
    IRQ_CONFIGURE = 9
    IRQ_SNAPSHOT_GET = 10
    IRQ_FORCE = 11
    IRQ_CLEAR = 12
