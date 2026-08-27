# RESOURCE PC Driver Package 的contract层。
#
# 职责：提供 RESOURCE 的已发布 Service/Command/Wire 常量。
# 边界：不发送请求、不解析 Capability，也不承载运行时策略。
# 依赖：仅依赖标准库 Enum 与中立 Service ID 定义。

from enum import IntEnum

RESOURCE_SERVICE_ID = 0x0010
RESOURCE_INSTANCE_ID = 0
RESOURCE_TRANSFER_CHUNK = 2048


# 定义 ResourceCommand 的已发布 Wire/Command 语义；编号和取值属于兼容合同，不得静默复用或改义。
class ResourceCommand(IntEnum):
    RESET = 0x0001
    CREATE = 0x0002
    WRITE = 0x0003
    READ = 0x0004
    FILL = 0x0005
    INFO_GET = 0x0006
