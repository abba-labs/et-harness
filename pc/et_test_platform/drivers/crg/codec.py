# CRG PC Driver Package 的codec层。
#
# 职责：提供 CRG 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct

CRG_CONTROL = struct.Struct("<4B")


# 将 encode clock set 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_clock_set(peripheral: int, instance: int, enabled: int) -> bytes:

    return CRG_CONTROL.pack(peripheral, instance, enabled, 0)


# 将 encode reset 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_reset(peripheral: int, instance: int) -> bytes:

    return CRG_CONTROL.pack(peripheral, instance, 0, 0)


# 将 WDG clock set 对应字段编码为固定四字节 Wire Body。
def encode_wdg_clock_set(wdg_id: int, source: int, divider: int) -> bytes:

    return CRG_CONTROL.pack(wdg_id, source, divider, 0)


# 将 WDG clock get 请求编码为固定四字节 Wire Body；其余字段必须为零。
def encode_wdg_clock_get(wdg_id: int) -> bytes:

    return CRG_CONTROL.pack(wdg_id, 0, 0, 0)


# 解码 CRG Service 的 WDG clock readback，不访问 Target 或执行策略。
def decode_wdg_clock(body: bytes) -> tuple[int, int]:

    if len(body) != CRG_CONTROL.size:
        raise ValueError("invalid CRG WDG clock response length")

    source, divider, reserved0, reserved1 = CRG_CONTROL.unpack(body)
    if reserved0 != 0 or reserved1 != 0:
        raise ValueError("CRG WDG clock response contains non-zero reserved bytes")

    return source, divider


# 编码独立的系统计数器时钟命令；GET把enabled保留字段置零。
def encode_syscnt_clock(instance: int, enabled: int = 0) -> bytes:

    return CRG_CONTROL.pack(instance, enabled, 0, 0)


# 精确校验时钟门控读回，拒绝非Boolean和非零保留字段。
def decode_syscnt_clock(body: bytes) -> bool:

    if len(body) != CRG_CONTROL.size:
        raise ValueError("invalid CRG SYSCNT clock response length")

    enabled, *reserved = CRG_CONTROL.unpack(body)
    if enabled not in (0, 1) or any(reserved):
        raise ValueError("invalid CRG SYSCNT clock response fields")

    return bool(enabled)
