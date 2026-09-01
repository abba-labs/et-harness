# SYSCTRL PC Driver Package 的__init__层。
#
# 职责：提供 SYSCTRL 的稳定公共导入入口。
# 边界：只导出已批准公共 API，不承载业务逻辑或跨 IP 编排。
# 依赖：仅依赖 sysctrl Driver Package 内部的稳定公共定义。

from .codec import DMA_ROUTE, DMA_ROUTE_RELEASE, DMA_ROUTE_V2
from .contract import SYSCTRL_SERVICE_ID, SysctrlCommand
from .driver import SysctrlDriver
from .models import DmaEndpoint, DmaRequestRoute

__all__ = [
    "DMA_ROUTE",
    "DMA_ROUTE_RELEASE",
    "DMA_ROUTE_V2",
    "SYSCTRL_SERVICE_ID",
    "DmaEndpoint",
    "DmaRequestRoute",
    "SysctrlCommand",
    "SysctrlDriver",
]
