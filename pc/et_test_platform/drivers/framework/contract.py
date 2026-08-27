# FRAMEWORK PC Driver Package 的contract层。
#
# 职责：提供 FRAMEWORK 的已发布 Service/Command/Wire 常量。
# 边界：不发送请求、不解析 Capability，也不承载运行时策略。
# 依赖：仅依赖标准库 Enum 与中立 Service ID 定义。

from enum import IntEnum

FRAMEWORK_SERVICE_ID = 0x0000
FRAMEWORK_INSTANCE_ID = 0


# 定义 FrameworkCommand 的已发布 Wire/Command 语义；编号和取值属于兼容合同，不得静默复用或改义。
class FrameworkCommand(IntEnum):
    HELLO = 0x0001
    ECHO = 0x0002
    VERSION_GET = 0x0003
    SERVICE_LIST = 0x0004
    STATISTICS_GET = 0x0005
    RESET_REASON_GET = 0x0006
