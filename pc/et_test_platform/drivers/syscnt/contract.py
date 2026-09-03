# SYSCNT命令与固定Wire布局。
# 职责：与固件公开Service头文件保持一一对应。
# 边界：不包含芯片地址，不执行I/O。
# 依赖：标准库。

from enum import IntEnum
from struct import Struct

SYSCNT_SERVICE_ID = 0x010A
BYTE = Struct("<B")
WORD = Struct("<I")
COUNT = Struct("<Q")
CAPABILITIES = Struct("<IBBBB")
CONTROL = Struct("<BBBBI")
REFERENCE = Struct("<QQQ")


# 编号归本IP所有，公共ET-Frame保持不变。
class SyscntCommand(IntEnum):
    CAPABILITIES_GET = 0
    ENABLE_SET = 1
    VALUE_LOAD = 2
    COUNT_GET = 3
    CONTROL_GET = 4
    HALT_POLICY_SET = 5
    FREQUENCY_ID_SET = 6
    REFERENCE_SAMPLE_GET = 7
    REFERENCE_ENABLE_SET = 8
