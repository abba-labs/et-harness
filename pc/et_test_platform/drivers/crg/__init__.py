# CRG PC Driver Package 的__init__层。
#
# 职责：提供 CRG 的稳定公共导入入口。
# 边界：只导出已批准公共 API，不承载业务逻辑或跨 IP 编排。
# 依赖：仅依赖 crg Driver Package 内部的稳定公共定义。

from .codec import CRG_CONTROL
from .contract import CRG_SERVICE_ID, CrgCommand
from .driver import CrgDriver
from .models import CrgPeripheral, CrgWdgClockConfig, CrgWdgClockSource

__all__ = [
    "CRG_CONTROL",
    "CRG_SERVICE_ID",
    "CrgCommand",
    "CrgDriver",
    "CrgPeripheral",
    "CrgWdgClockConfig",
    "CrgWdgClockSource",
]
