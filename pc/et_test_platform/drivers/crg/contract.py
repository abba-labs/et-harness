# CRG PC Driver Package 的contract层。
#
# 职责：提供 CRG 的已发布 Service/Command/Wire 常量。
# 边界：不发送请求、不解析 Capability，也不承载运行时策略。
# 依赖：仅依赖标准库 Enum。

from enum import IntEnum

CRG_SERVICE_ID = 0x0012


# 定义 CrgCommand 的已发布 Wire/Command 语义；编号和取值属于兼容合同，不得静默复用或改义。
class CrgCommand(IntEnum):
    CLOCK_SET = 0x0001
    RESET = 0x0002
    WDG_CLOCK_SET = 0x0003
    WDG_CLOCK_GET = 0x0004
