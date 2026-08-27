# FRAMEWORK PC Driver Package 的__init__层。
#
# 职责：提供 FRAMEWORK 的稳定公共导入入口。
# 边界：只导出已批准公共 API，不承载业务逻辑或跨 IP 编排。
# 依赖：仅依赖 framework Driver Package 内部的稳定公共定义。

from __future__ import annotations

from .codec import (
    COUNT,
    HELLO_PREFIX,
    RESET_REASON,
    SERVICE_ENTRY,
    STATISTICS,
    VERSION_PREFIX,
    decode_hello,
    decode_statistics,
    decode_version,
    registry_hash,
)
from .contract import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
)
from .driver import FrameworkDriver
from .models import (
    EchoExchange,
    HelloInfo,
    ProtocolStatistics,
    ServiceInfo,
    VersionInfo,
)


def _hello_decode(cls: type[HelloInfo], body: bytes) -> HelloInfo:
    del cls
    return decode_hello(body)


def _version_decode(cls: type[VersionInfo], body: bytes) -> VersionInfo:
    del cls
    return decode_version(body)


def _statistics_decode(
    cls: type[ProtocolStatistics],
    body: bytes,
) -> ProtocolStatistics:
    del cls
    return decode_statistics(body)


# Compatibility for callers of the historical Model.decode() entry points.
HelloInfo.decode = classmethod(_hello_decode)
VersionInfo.decode = classmethod(_version_decode)
ProtocolStatistics.decode = classmethod(_statistics_decode)

_registry_hash = registry_hash

__all__ = [
    "COUNT",
    "FRAMEWORK_INSTANCE_ID",
    "FRAMEWORK_SERVICE_ID",
    "HELLO_PREFIX",
    "RESET_REASON",
    "SERVICE_ENTRY",
    "STATISTICS",
    "VERSION_PREFIX",
    "EchoExchange",
    "FrameworkCommand",
    "FrameworkDriver",
    "HelloInfo",
    "ProtocolStatistics",
    "ServiceInfo",
    "VersionInfo",
]
