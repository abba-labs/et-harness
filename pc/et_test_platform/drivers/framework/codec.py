# FRAMEWORK PC Driver Package 的codec层。
#
# 职责：提供 FRAMEWORK 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .models import HelloInfo, ProtocolStatistics, ServiceInfo, VersionInfo

HELLO_PREFIX = struct.Struct("<H")
VERSION_PREFIX = struct.Struct("<H")
COUNT = struct.Struct("<H")
SERVICE_ENTRY = struct.Struct("<HH")
STATISTICS = struct.Struct("<IIII")
RESET_REASON = struct.Struct("<I")


# 从响应 Body 解码 decode hello 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_hello(body: bytes) -> HelloInfo:

    if len(body) < HELLO_PREFIX.size:
        raise ProtocolError("HELLO body is shorter than its prefix")
    protocol_version = HELLO_PREFIX.unpack_from(body)[0]
    offset = HELLO_PREFIX.size
    values: list[str] = []
    for _ in range(3):
        value, offset = _unpack_string(body, offset)
        values.append(value)
    if offset != len(body):
        raise ProtocolError("HELLO body contains trailing bytes")
    return HelloInfo(
        protocol_version=protocol_version,
        chip_id=values[0],
        firmware_build_id=values[1],
        registry_hash=values[2],
    )


# 从响应 Body 解码 decode version 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_version(body: bytes) -> VersionInfo:

    if len(body) < VERSION_PREFIX.size:
        raise ProtocolError("VERSION_GET body is shorter than its prefix")
    protocol_version = VERSION_PREFIX.unpack_from(body)[0]
    firmware_build_id, offset = _unpack_string(body, VERSION_PREFIX.size)
    if offset != len(body):
        raise ProtocolError("VERSION_GET body contains trailing bytes")
    return VersionInfo(protocol_version, firmware_build_id)


# 从响应 Body 解码 decode service list 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_service_list(body: bytes) -> tuple[ServiceInfo, ...]:

    if len(body) < COUNT.size:
        raise ProtocolError("SERVICE_LIST body is shorter than its count")
    count = COUNT.unpack_from(body)[0]
    expected = COUNT.size + count * SERVICE_ENTRY.size
    if len(body) != expected:
        raise ProtocolError("SERVICE_LIST body has an invalid length")
    return tuple(
        ServiceInfo(*SERVICE_ENTRY.unpack_from(body, COUNT.size + index * 4))
        for index in range(count)
    )


# 从响应 Body 解码 decode statistics 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_statistics(body: bytes) -> ProtocolStatistics:

    if len(body) != STATISTICS.size:
        raise ProtocolError("STATISTICS_GET body has an invalid length")
    return ProtocolStatistics(*STATISTICS.unpack(body))


# 从响应 Body 解码 decode reset reason 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_reset_reason(body: bytes) -> int:

    if len(body) != RESET_REASON.size:
        raise ProtocolError("RESET_REASON_GET body has an invalid length")
    return RESET_REASON.unpack(body)[0]


# 处理 registry hash 的纯 Wire 规则；不访问 TargetClient、Capability、Bench 或设备 I/O。
def registry_hash(services: tuple[ServiceInfo, ...]) -> str:

    value = 2166136261
    for service in services:
        for byte in SERVICE_ENTRY.pack(service.service_id, service.instance_id):
            value ^= byte
            value = (value * 16777619) & 0xFFFFFFFF
    return f"{value:08x}"


def _unpack_string(data: bytes, offset: int) -> tuple[str, int]:
    if offset >= len(data):
        raise ProtocolError("missing protocol string length")
    size = data[offset]
    start = offset + 1
    end = start + size
    if end > len(data):
        raise ProtocolError("truncated protocol string")
    try:
        value = data[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("protocol string is not valid UTF-8") from exc
    return value, end
