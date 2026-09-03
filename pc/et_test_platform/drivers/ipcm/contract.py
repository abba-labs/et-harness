# IPCM V1 Wire 契约。
# 职责：集中命令编号和固定布局，与 et_ipcm_service.h 对齐。
# 边界：不执行 I/O，不含芯片地址或 Core 拓扑。
# 依赖：标准库。

from enum import IntEnum
from struct import Struct

IPCM_SERVICE_ID = 0x0109
IPCM_SERVICE_API_VERSION = 1
LOGICAL_SET_BITS = 32
DATA_WORD_BYTES = 4
CAPABILITIES = Struct("<8H")
CONFIG = Struct("<HHIIIBBH")
IDENTIFIER = Struct("<H")
PAIR = Struct("<HH")
MAILBOX = Struct("<IIIBBH")
PENDING = Struct("<II")
WRITE_HEADER = Struct("<HHH")
CAPTURE_ARM = Struct("<HHHHBB")
EVENT_HEADER = Struct("<8I5H")


# 所有动作均使用同一 IPCM Service，保留现有 ET-Frame。
class IpcmCommand(IntEnum):
    CAPABILITIES_GET = 0x0001
    CONFIGURE = 0x0002
    MAILBOX_RELEASE = 0x0003
    MAILBOX_SNAPSHOT_GET = 0x0004
    PENDING_SNAPSHOT_GET = 0x0005
    PAYLOAD_WRITE = 0x0006
    PAYLOAD_READ = 0x0007
    MESSAGE_SEND = 0x0008
    ACK_SEND = 0x0009
    INTERRUPT_CLEAR = 0x000A
    DESTINATION_RELEASE = 0x000B
    CAPTURE_ARM = 0x0010
    CAPTURE_GET = 0x0011
    CAPTURE_ABORT = 0x0012
    STATE_RESET = 0x0013
