# ET-Frame 协议的纯 Wire 编解码。
#
# 职责：定义 ET-Frame 的稳定字段、长度检查和流式解码规则。
# 边界：不访问 Transport、TargetClient、Capability 或任何 IP Driver，不执行设备 I/O。
# 依赖：仅依赖标准库字节/结构处理与平台 ProtocolError。

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum

from ...core.errors import ProtocolError

MAGIC = b"ET"
VERSION = 1
HEADER = struct.Struct("<2sBBHHII")
TRAILER = struct.Struct("<I")
MAX_PAYLOAD = 4096


# 提供 MessageType 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class MessageType(IntEnum):
    REQUEST = 1
    RESPONSE = 2
    EVENT = 3


# 提供 Frame 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True)
class Frame:
    message_type: MessageType
    flags: int
    sequence: int
    session_id: int
    payload: bytes


# 提供 FrameCodec 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class FrameCodec:
    # 提供 encode 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @staticmethod
    def encode(frame: Frame) -> bytes:

        payload = bytes(frame.payload)
        if len(payload) > MAX_PAYLOAD:
            raise ProtocolError(f"payload exceeds {MAX_PAYLOAD} bytes")
        if not 0 <= frame.flags <= 0xFFFF:
            raise ProtocolError("flags must fit uint16")
        header = HEADER.pack(
            MAGIC,
            VERSION,
            int(frame.message_type),
            frame.flags,
            len(payload),
            frame.sequence,
            frame.session_id,
        )
        content = header + payload
        return content + TRAILER.pack(zlib.crc32(content) & 0xFFFFFFFF)

    # 提供 decode 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @staticmethod
    def decode(data: bytes) -> Frame:

        if len(data) < HEADER.size + TRAILER.size:
            raise ProtocolError("frame is shorter than the minimum size")
        magic, version, message_type, flags, payload_len, sequence, session_id = HEADER.unpack_from(
            data
        )
        if magic != MAGIC:
            raise ProtocolError("invalid frame magic")
        if version != VERSION:
            raise ProtocolError(f"unsupported frame version {version}")
        if payload_len > MAX_PAYLOAD:
            raise ProtocolError("declared payload exceeds protocol maximum")
        expected_size = HEADER.size + payload_len + TRAILER.size
        if len(data) != expected_size:
            raise ProtocolError(f"frame length mismatch: expected {expected_size}, got {len(data)}")
        expected_crc = TRAILER.unpack_from(data, expected_size - TRAILER.size)[0]
        actual_crc = zlib.crc32(data[: -TRAILER.size]) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ProtocolError("frame CRC mismatch")
        try:
            message_type_value = MessageType(message_type)
        except ValueError as exc:
            raise ProtocolError(f"unknown message type {message_type}") from exc
        return Frame(
            message_type=message_type_value,
            flags=flags,
            sequence=sequence,
            session_id=session_id,
            payload=data[HEADER.size : HEADER.size + payload_len],
        )


# 提供 FrameDecoder 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class FrameDecoder:
    def __init__(self) -> None:
        self._buffer = bytearray()

    # 提供 reset 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def reset(self) -> None:

        self._buffer.clear()

    # 提供 feed 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def feed(self, data: bytes) -> list[Frame]:

        self._buffer.extend(data)
        frames: list[Frame] = []
        minimum = HEADER.size + TRAILER.size

        while True:
            magic_at = self._buffer.find(MAGIC)
            if magic_at < 0:
                if self._buffer[-1:] == MAGIC[:1]:
                    del self._buffer[:-1]
                else:
                    self._buffer.clear()
                break
            if magic_at:
                del self._buffer[:magic_at]
            if len(self._buffer) < HEADER.size:
                break

            _, version, message_type, _, payload_len, _, _ = HEADER.unpack_from(self._buffer)
            if (
                version != VERSION
                or message_type not in MessageType._value2member_map_
                or payload_len > MAX_PAYLOAD
            ):
                del self._buffer[0]
                continue

            frame_size = HEADER.size + payload_len + TRAILER.size
            if frame_size < minimum or len(self._buffer) < frame_size:
                break
            candidate = bytes(self._buffer[:frame_size])
            try:
                frames.append(FrameCodec.decode(candidate))
            except ProtocolError:
                del self._buffer[0]
                continue
            del self._buffer[:frame_size]

        return frames
