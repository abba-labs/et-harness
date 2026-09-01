# RESOURCE PC Driver Package 的__init__层。
#
# 职责：提供 RESOURCE 的稳定公共导入入口。
# 边界：只导出已批准公共 API，不承载业务逻辑或跨 IP 编排。
# 依赖：仅依赖 resource Driver Package 内部的稳定公共定义。

from .codec import (
    CREATE_REQUEST,
    FILL_REQUEST,
    INFO_RESPONSE,
    RANGE_REQUEST,
    RESOURCE_REF,
)
from .contract import (
    RESOURCE_INSTANCE_ID,
    RESOURCE_SERVICE_ID,
    RESOURCE_TRANSFER_CHUNK,
    ResourceCommand,
)
from .driver import ResourceDriver
from .models import ResourceRef

__all__ = [
    "CREATE_REQUEST",
    "FILL_REQUEST",
    "INFO_RESPONSE",
    "RANGE_REQUEST",
    "RESOURCE_INSTANCE_ID",
    "RESOURCE_REF",
    "RESOURCE_SERVICE_ID",
    "RESOURCE_TRANSFER_CHUNK",
    "ResourceCommand",
    "ResourceDriver",
    "ResourceRef",
]
