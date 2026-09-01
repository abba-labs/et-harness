# AES PC Driver Wire 编解码层。
#
# 职责：纯函数编解码 AES Service Body，并校验长度、枚举和保留字段。
# 边界：不访问 TargetClient、Capability、Bench，也不执行等待、重试或设备操作。
# 依赖：仅依赖 struct、本 IP Contract/Model/Validation 和 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .contract import (
    AES_CAPABILITIES_SIZE,
    AES_CONFIGURE_SIZE,
    AES_DATA_LENGTH_SIZE,
    AES_IRQ_SNAPSHOT_SIZE,
    AES_IRQ_TRANSFER_STATUS_SIZE,
    AES_IV_SIZE,
    AES_KEY_SET_SIZE,
    AES_PROCESS_RESULT_SIZE,
    AES_PROCESS_SIZE,
    AES_STATUS_SIZE,
    AES_TIMED_RESULT_SIZE,
)
from .models import (
    AesCapabilities,
    AesConfig,
    AesDirection,
    AesDmaTransferMode,
    AesEndian,
    AesFeature,
    AesIrqEvent,
    AesIrqSnapshot,
    AesIrqTransferState,
    AesIrqTransferStatus,
    AesKeySize,
    AesMode,
    AesPadding,
    AesProcessResult,
    AesStatus,
    AesTimedResult,
)
from .validation import (
    validate_config,
    validate_data_length,
    validate_irq_events,
    validate_key,
    validate_process_length,
    validate_resource_range,
    validate_status_mask,
)

CAPABILITIES = struct.Struct("<HHIIIII8B")
CONFIGURE = struct.Struct("<BBBBBB2xI")
KEY_SET = struct.Struct("<B3x32s")
DATA_LENGTH = struct.Struct("<Q")
PROCESS = struct.Struct("<IIIII")
STATUS = struct.Struct("<BBBBI")
PROCESS_RESULT = struct.Struct("<I4B4x")
IRQ_EVENTS = struct.Struct("<I")
IRQ_SNAPSHOT = struct.Struct("<IIIIIII")
IRQ_TRANSFER_STATUS = struct.Struct("<IIIIII")
TIMED_PROCESS = struct.Struct("<IIIII")
TIMED_RESULT = struct.Struct("<IIII")
BLOCK = struct.Struct("<16s")

_KNOWN_FEATURES = AesFeature(0)
for _feature in AesFeature:
    _KNOWN_FEATURES |= _feature


def _protocol_length(body: bytes, expected: int, label: str) -> None:
    if len(body) != expected:
        raise ProtocolError(f"AES {label} body length is invalid")


def _canonical_bool(value: int, label: str) -> bool:
    if value not in (0, 1):
        raise ProtocolError(f"AES {label} contains a non-canonical Boolean")
    return bool(value)


def _decode_status_fields(busy: int, data_in: int, data_out: int, finish: int) -> AesStatus:
    return AesStatus(
        busy=_canonical_bool(busy, "busy"),
        data_in_request=_canonical_bool(data_in, "data_in_request"),
        data_out_request=_canonical_bool(data_out, "data_out_request"),
        finish=_canonical_bool(finish, "finish"),
    )


def _status_flags(status: AesStatus) -> int:
    return (
        int(status.busy)
        | (int(status.data_in_request) << 1)
        | (int(status.data_out_request) << 2)
        | (int(status.finish) << 3)
    )


def _status_from_flags(flags: int) -> AesStatus:
    if flags & ~0x0F:
        raise ProtocolError("AES status flags contain unknown bits")
    return AesStatus(
        busy=bool(flags & 0x01),
        data_in_request=bool(flags & 0x02),
        data_out_request=bool(flags & 0x04),
        finish=bool(flags & 0x08),
    )


# 解码并校验 AES Service 能力响应，返回结构化能力事实。
def decode_capabilities(body: bytes) -> AesCapabilities:
    _protocol_length(body, AES_CAPABILITIES_SIZE, "CAPABILITIES_GET response")
    (
        api_version,
        struct_size,
        features,
        block_size,
        data_length_bits,
        max_process,
        max_output,
        key_size_mask,
        mode_mask,
        padding_mask,
        endian_mask,
        dma_mode_mask,
        irq_event_mask,
        irq_transfer,
        timed_process,
    ) = CAPABILITIES.unpack(body)
    if api_version == 0 or struct_size != AES_CAPABILITIES_SIZE:
        raise ProtocolError("AES CAPABILITIES_GET version or structure size is incompatible")
    if features & ~int(_KNOWN_FEATURES):
        raise ProtocolError("AES CAPABILITIES_GET contains unknown feature bits")
    if block_size != 16 or not 1 <= data_length_bits <= 64:
        raise ProtocolError("AES CAPABILITIES_GET returned incompatible block/length facts")
    if max_process == 0 or max_output < max_process:
        raise ProtocolError("AES CAPABILITIES_GET returned invalid processing limits")
    if key_size_mask & ~0x03 or mode_mask & ~0x07 or padding_mask & ~0x07:
        raise ProtocolError("AES CAPABILITIES_GET contains unknown algorithm option bits")
    if endian_mask & ~0x03 or dma_mode_mask & ~0x03 or irq_event_mask & ~0x7F:
        raise ProtocolError("AES CAPABILITIES_GET contains unknown transport option bits")
    return AesCapabilities(
        api_version=api_version,
        features=AesFeature(features),
        block_size_bytes=block_size,
        hardware_data_length_bits=data_length_bits,
        max_process_bytes=max_process,
        max_process_output_bytes=max_output,
        key_size_mask=key_size_mask,
        mode_mask=mode_mask,
        padding_mask=padding_mask,
        endian_mask=endian_mask,
        dma_mode_mask=dma_mode_mask,
        irq_event_mask=AesIrqEvent(irq_event_mask),
        irq_transfer_supported=_canonical_bool(irq_transfer, "irq_transfer_supported"),
        timed_process_supported=_canonical_bool(timed_process, "timed_process_supported"),
    )


# 编码 AES 配置请求，确保枚举和计数符合 Wire 合同。
def encode_config(config: AesConfig) -> bytes:
    normalized = validate_config(config)
    return CONFIGURE.pack(
        int(normalized.direction),
        int(normalized.key_size),
        int(normalized.mode),
        int(normalized.padding),
        int(normalized.endian),
        int(normalized.dma_transfer_mode),
        normalized.ctr_counter,
    )


# 解码 AES 配置请求并拒绝未知枚举或非法计数。
def decode_config(body: bytes) -> AesConfig:
    _protocol_length(body, AES_CONFIGURE_SIZE, "CONFIGURE request")
    direction, key_size, mode, padding, endian, dma_mode, counter = CONFIGURE.unpack(body)
    try:
        return validate_config(
            AesConfig(
                direction=AesDirection(direction),
                key_size=AesKeySize(key_size),
                mode=AesMode(mode),
                padding=AesPadding(padding),
                endian=AesEndian(endian),
                dma_transfer_mode=AesDmaTransferMode(dma_mode),
                ctr_counter=counter,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolError("AES CONFIGURE request contains invalid enum or value") from exc


# 编码 AES 密钥请求并按密钥尺寸补齐固定槽位。
def encode_key(key: bytes, key_size: AesKeySize) -> bytes:
    value, normalized_size = validate_key(key, key_size)
    return KEY_SET.pack(int(normalized_size), value + b"\x00" * (32 - len(value)))


# 解码 AES 密钥请求并校验 AES-128 尾部保留字节。
def decode_key(body: bytes) -> tuple[bytes, AesKeySize]:
    _protocol_length(body, AES_KEY_SET_SIZE, "KEY_SET request")
    key_size_raw, slot = KEY_SET.unpack(body)
    try:
        key_size = AesKeySize(key_size_raw)
    except ValueError as exc:
        raise ProtocolError("AES KEY_SET contains an unknown key size") from exc
    key_length = 16 if key_size is AesKeySize.AES128 else 32
    if key_size is AesKeySize.AES128 and slot[16:] != b"\x00" * 16:
        raise ProtocolError("AES AES128 KEY_SET tail must be zero")
    return slot[:key_length], key_size


# 编码固定 16 字节的 AES IV 请求负载。
def encode_iv(iv: bytes) -> bytes:
    value = bytes(iv)
    if len(value) != AES_IV_SIZE:
        raise ValueError("iv must contain exactly 16 bytes")
    return value


# 解码并校验 AES IV_GET 返回的固定字节序列。
def decode_iv(body: bytes) -> bytes:
    _protocol_length(body, AES_IV_SIZE, "IV_GET response")
    return bytes(body)


# 编码 Wire 的 64-bit AES 数据长度字段；芯片位宽由 Driver 的运行时能力约束。
def encode_data_length(length_bytes: int) -> bytes:
    return DATA_LENGTH.pack(validate_data_length(length_bytes))


# 解码精确 8-byte AES 数据长度响应；芯片位宽由 Driver 的运行时能力约束。
def decode_data_length(body: bytes) -> int:
    _protocol_length(body, AES_DATA_LENGTH_SIZE, "DATA_LENGTH_GET response")
    return DATA_LENGTH.unpack(body)[0]


# 编码 Resource-backed AES PROCESS 请求及其范围字段。
def encode_process(
    src_handle: int,
    src_offset: int,
    dst_handle: int,
    dst_offset: int,
    logical_length: int,
) -> bytes:
    validate_process_length(logical_length)
    src, src_off, _ = validate_resource_range(src_handle, src_offset, logical_length, "source")
    dst, dst_off, _ = validate_resource_range(dst_handle, dst_offset, logical_length, "destination")
    return PROCESS.pack(src, src_off, dst, dst_off, logical_length)


# 解码 AES PROCESS 请求并校验源/目标 Resource 范围。
def decode_process(body: bytes) -> tuple[int, int, int, int, int]:
    _protocol_length(body, AES_PROCESS_SIZE, "PROCESS request")
    src, src_off, dst, dst_off, length = PROCESS.unpack(body)
    try:
        validate_process_length(length)
        validate_resource_range(src, src_off, length, "source")
        validate_resource_range(dst, dst_off, length, "destination")
    except ValueError as exc:
        raise ProtocolError("AES PROCESS request contains invalid Resource range") from exc
    return src, src_off, dst, dst_off, length


# 解码 AES STATUS_GET 响应并拒绝非零保留字段。
def decode_status(body: bytes) -> AesStatus:
    _protocol_length(body, AES_STATUS_SIZE, "STATUS_GET response")
    busy, data_in, data_out, finish, reserved = STATUS.unpack(body)
    if reserved != 0:
        raise ProtocolError("AES STATUS_GET reserved field is non-zero")
    return _decode_status_fields(busy, data_in, data_out, finish)


# 编码 AES 状态 W1C 掩码并限制已发布状态位。
def encode_status_mask(mask: int) -> bytes:
    return IRQ_EVENTS.pack(validate_status_mask(mask))


# 解码 PROCESS_RESULT 并返回 produced 与状态快照。
def decode_process_result(body: bytes) -> AesProcessResult:
    _protocol_length(body, AES_PROCESS_RESULT_SIZE, "PROCESS response")
    produced, busy, data_in, data_out, finish = PROCESS_RESULT.unpack(body)
    return AesProcessResult(
        produced_bytes=produced,
        status=_decode_status_fields(busy, data_in, data_out, finish),
    )


# 编码 AES IRQ 事件位并拒绝未知或空事件集合。
def encode_irq_events(events: AesIrqEvent) -> bytes:
    return IRQ_EVENTS.pack(int(validate_irq_events(events)))


# 解码 AES IRQ 事件响应并校验事件位掩码。
def decode_irq_events(body: bytes) -> AesIrqEvent:
    _protocol_length(body, IRQ_EVENTS.size, "IRQ event response")
    value = IRQ_EVENTS.unpack(body)[0]
    try:
        return validate_irq_events(AesIrqEvent(value))
    except ValueError as exc:
        raise ProtocolError("AES IRQ event response contains invalid bits") from exc


# 解码 AES IRQ 原始、屏蔽、锁存和计数快照。
def decode_irq_snapshot(body: bytes) -> AesIrqSnapshot:
    _protocol_length(body, AES_IRQ_SNAPSHOT_SIZE, "IRQ_SNAPSHOT_GET response")
    raw, status, latched, event_count, unexpected, overflow, generation = IRQ_SNAPSHOT.unpack(body)
    for name, value in (("raw", raw), ("status", status), ("latched", latched)):
        if value & ~int(AesIrqEvent.ALL):
            raise ProtocolError(f"AES IRQ snapshot contains unknown {name} bits")
    return AesIrqSnapshot(
        raw=AesIrqEvent(raw),
        status=AesIrqEvent(status),
        latched=AesIrqEvent(latched),
        event_count=event_count,
        unexpected_count=unexpected,
        overflow_count=overflow,
        generation=generation,
    )


# 编码 AES IRQ_TRANSFER_START 的五个 Resource 参数。
def encode_irq_transfer(
    src_handle: int,
    src_offset: int,
    dst_handle: int,
    dst_offset: int,
    logical_length: int,
) -> bytes:
    return encode_process(src_handle, src_offset, dst_handle, dst_offset, logical_length)


# 解码 IRQ transfer 状态、offset、产出和故障计数。
def decode_irq_transfer_status(body: bytes) -> AesIrqTransferStatus:
    _protocol_length(body, AES_IRQ_TRANSFER_STATUS_SIZE, "IRQ_TRANSFER_STATUS_GET response")
    state, input_offset, output_offset, produced, fault_flags, block_count = (
        IRQ_TRANSFER_STATUS.unpack(body)
    )
    try:
        state_value = AesIrqTransferState(state)
    except ValueError as exc:
        raise ProtocolError("AES IRQ transfer status contains an unknown state") from exc
    return AesIrqTransferStatus(
        state=state_value,
        input_offset=input_offset,
        output_offset=output_offset,
        produced_bytes=produced,
        fault_flags=fault_flags,
        block_count=block_count,
    )


# 编码 AES TIMED_PROCESS 的 Resource 参数请求。
def encode_timed_process(
    src_handle: int,
    src_offset: int,
    dst_handle: int,
    dst_offset: int,
    logical_length: int,
) -> bytes:
    return encode_process(src_handle, src_offset, dst_handle, dst_offset, logical_length)


# 解码目标侧 AES 周期数、处理字节数和状态标志，并拒绝未知状态位。
def decode_timed_result(body: bytes) -> AesTimedResult:
    _protocol_length(body, AES_TIMED_RESULT_SIZE, "TIMED_PROCESS response")
    cycles, produced, measured, status_flags = TIMED_RESULT.unpack(body)
    return AesTimedResult(
        elapsed_cycles=cycles,
        produced_bytes=produced,
        measured_bytes=measured,
        status=_status_from_flags(status_flags),
    )


# 编码 CPU block 写入请求并固定为 16 字节。
def encode_block(block: bytes) -> bytes:
    value = bytes(block)
    if len(value) != AES_IV_SIZE:
        raise ValueError("AES block must contain exactly 16 bytes")
    return BLOCK.pack(value)


# 解码 CPU block 读取响应并校验固定长度。
def decode_block(body: bytes) -> bytes:
    _protocol_length(body, AES_IV_SIZE, "BLOCK_READ response")
    return BLOCK.unpack(body)[0]
