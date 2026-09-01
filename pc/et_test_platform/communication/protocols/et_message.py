# ServiceMessage 协议的纯 Wire 编解码。
#
# 职责：定义 ServiceMessage 的稳定字段、长度检查和流式解码规则。
# 边界：不访问 Transport、TargetClient、Capability 或任何 IP Driver，不执行设备 I/O。
# 依赖：仅依赖标准库字节/结构处理与平台 ProtocolError。

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

from ...core.errors import ProtocolError
from .et_frame import MAX_PAYLOAD

HEADER = struct.Struct("<HHHH")
MAX_BODY = MAX_PAYLOAD - HEADER.size


# 提供 Status 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class Status(IntEnum):
    OK = 0
    INVALID_SERVICE = 1
    INVALID_COMMAND = 2
    INVALID_PARAM = 3
    NOT_SUPPORTED = 4
    BUSY = 5
    INTERNAL_ERROR = 6


# 提供 ServiceMessage 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True)
class ServiceMessage:
    service_id: int
    command_id: int
    instance_id: int = 0
    status: Status = Status.OK
    body: bytes = b""

    # 提供 encode 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def encode(self) -> bytes:

        body = bytes(self.body)
        for name, value in (
            ("service_id", self.service_id),
            ("command_id", self.command_id),
            ("instance_id", self.instance_id),
        ):
            if not 0 <= value <= 0xFFFF:
                raise ProtocolError(f"{name} must fit uint16")
        if len(body) > MAX_BODY:
            raise ProtocolError(f"message body exceeds {MAX_BODY} bytes")
        return (
            HEADER.pack(
                self.service_id,
                self.command_id,
                self.instance_id,
                int(self.status),
            )
            + body
        )

    # 提供 decode 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @classmethod
    def decode(cls, payload: bytes) -> ServiceMessage:

        if len(payload) < HEADER.size:
            raise ProtocolError("service payload is shorter than its header")
        service_id, command_id, instance_id, status = HEADER.unpack_from(payload)
        try:
            status_value = Status(status)
        except ValueError as exc:
            raise ProtocolError(f"unknown status id {status}") from exc
        return cls(
            service_id=service_id,
            command_id=command_id,
            instance_id=instance_id,
            status=status_value,
            body=payload[HEADER.size :],
        )
