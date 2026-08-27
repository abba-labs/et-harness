# RESOURCE PC Driver Package 的codec层。
#
# 职责：提供 RESOURCE 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .models import ResourceRef

CREATE_REQUEST = struct.Struct("<II")
RESOURCE_REF = struct.Struct("<IIQ")
RANGE_REQUEST = struct.Struct("<III")
FILL_REQUEST = struct.Struct("<IIIB")
INFO_REQUEST = struct.Struct("<I")
INFO_RESPONSE = struct.Struct("<IIQ")
WRITE_PREFIX = struct.Struct("<II")


# 将 encode create 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_create(size: int, alignment: int) -> bytes:

    return CREATE_REQUEST.pack(size, alignment)


# 从响应 Body 解码 decode created 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_created(body: bytes) -> ResourceRef:

    if len(body) != RESOURCE_REF.size:
        raise ProtocolError("RESOURCE CREATE response length is invalid")
    return ResourceRef(*RESOURCE_REF.unpack(body))


# 将 encode write 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_write(handle: int, offset: int, data: bytes) -> bytes:

    return WRITE_PREFIX.pack(handle, offset) + data


# 将 encode read 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_read(handle: int, offset: int, size: int) -> bytes:

    return RANGE_REQUEST.pack(handle, offset, size)


# 处理 validate read body 的纯 Wire 规则；不访问 TargetClient、Capability、Bench 或设备 I/O。
def validate_read_body(body: bytes, expected: int) -> bytes:

    if len(body) != expected:
        raise ProtocolError("RESOURCE READ returned an unexpected length")
    return bytes(body)


# 将 encode fill 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_fill(handle: int, offset: int, size: int, value: int) -> bytes:

    return FILL_REQUEST.pack(handle, offset, size, value)


# 将 encode info 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_info(handle: int) -> bytes:

    return INFO_REQUEST.pack(handle)


# 从响应 Body 解码 decode info 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_info(handle: int, body: bytes) -> ResourceRef:

    if len(body) != INFO_RESPONSE.size:
        raise ProtocolError("RESOURCE INFO response length is invalid")
    size, _alignment, address = INFO_RESPONSE.unpack(body)
    return ResourceRef(handle, size, address)
