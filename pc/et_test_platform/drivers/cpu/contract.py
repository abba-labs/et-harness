# CPU Owner Wire Contract。
# 职责：冻结 CPU/NMI Owner 的 Service ID、命令号和二进制布局。
# 边界：不包含芯片地址、IRQn、寄存器位或 Case 流程。
# 依赖：仅依赖 Python 标准库的枚举与二进制结构定义。

from enum import IntEnum
from struct import Struct

CPU_SERVICE_ID = 0x0013
CPU_SERVICE_API_VERSION = 1

CAPABILITIES_STRUCT = Struct("<HHI")
CONFIG_STRUCT = Struct("<B3x")
SNAPSHOT_STRUCT = Struct("<IIIII")


# CPU Owner Service 公开命令，与 Firmware Contract 逐值对应。
class CpuCommand(IntEnum):
    CAPABILITIES_GET = 0x0001
    NMI_CONFIGURE = 0x0002
    NMI_SNAPSHOT_GET = 0x0003
    NMI_EVENT_CLEAR = 0x0004
