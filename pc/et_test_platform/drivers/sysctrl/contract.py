# SYSCTRL PC Driver Package 的contract层。
#
# 职责：提供 SYSCTRL 的已发布 Service/Command/Wire 常量。
# 边界：不发送请求、不解析 Capability，也不承载运行时策略。
# 依赖：仅依赖标准库 Enum。

from enum import IntEnum

SYSCTRL_SERVICE_ID = 0x0011


# SYSCTRL Firmware Service 已发布命令编号。
class SysctrlCommand(IntEnum):
    DMA_REQUEST_CONFIGURE = 0x0001
    DMA_REQUEST_RELEASE = 0x0002
    DMA_REQUEST_CONFIGURE_V2 = 0x0003
