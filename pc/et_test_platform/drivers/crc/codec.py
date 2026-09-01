# CRC PC Driver Package 的 codec 层。
#
# 职责：提供 CRC Wire Body 的纯编码和严格解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 和 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .contract import CRC_CAPABILITIES_SIZE, CRC_SERVICE_API_VERSION
from .models import (
    CrcCalculateResult,
    CrcCapabilities,
    CrcConfig,
    CrcFeature,
    CrcFifoStatus,
    CrcInputAccessWidth,
    CrcInputBurstResult,
    CrcIrqEvent,
    CrcIrqSnapshot,
    CrcMode,
    CrcTimedResult,
)

CAPABILITIES = struct.Struct("<HHIBBBBI")
CONFIG = struct.Struct("<BBBBII")
CALCULATE = struct.Struct("<QI")
CALCULATE_RESULT = struct.Struct("<II")
UINT32 = struct.Struct("<I")
FIFO_STATUS = struct.Struct("<B3x")
IRQ_SNAPSHOT = struct.Struct("<IIIII")
TEST_INPUT = struct.Struct("<B3xI")
TIMED_CALCULATE = struct.Struct("<QII")
TIMED_RESULT = struct.Struct("<IIII")
TEST_INPUT_BURST = struct.Struct("<BBH9I")
TEST_INPUT_BURST_RESULT = struct.Struct("<BBHIIB3s")

_KNOWN_FEATURES = CrcFeature((1 << 22) - 1)
_KNOWN_MODE_BITS = 0x07
_KNOWN_IRQ_BITS = int(CrcIrqEvent.ALL)


# 解码并严格验证 CRC Runtime Capability。
def decode_capabilities(body: bytes) -> CrcCapabilities:

    if len(body) != CRC_CAPABILITIES_SIZE:
        raise ProtocolError("CRC CAPABILITIES_GET response length is invalid")
    api_version, struct_size, features, modes, irq_bits, threshold, flags, maximum = (
        CAPABILITIES.unpack(body)
    )
    if api_version != CRC_SERVICE_API_VERSION or struct_size != CRC_CAPABILITIES_SIZE:
        raise ProtocolError("CRC CAPABILITIES_GET version or structure size is incompatible")
    if features & ~int(_KNOWN_FEATURES):
        raise ProtocolError("CRC CAPABILITIES_GET contains unknown feature bits")
    if modes == 0 or modes & ~_KNOWN_MODE_BITS:
        raise ProtocolError("CRC CAPABILITIES_GET contains invalid mode bits")
    if irq_bits & ~_KNOWN_IRQ_BITS or flags & ~0x01:
        raise ProtocolError("CRC CAPABILITIES_GET contains unknown IRQ or flag bits")
    if threshold == 0 or maximum == 0:
        raise ProtocolError("CRC CAPABILITIES_GET contains invalid limits")
    supported_modes = tuple(
        mode
        for bit, mode in enumerate((CrcMode.CRC8, CrcMode.CRC16, CrcMode.CRC32))
        if modes & (1 << bit)
    )
    return CrcCapabilities(
        api_version=api_version,
        features=CrcFeature(features),
        modes=supported_modes,
        irq_events=CrcIrqEvent(irq_bits),
        fifo_threshold_max=threshold,
        bounded_synchronous_calculate=bool(flags & 0x01),
        max_calculate_bytes=maximum,
    )


# 按 CRC Wire Contract 编码一份已经完成业务校验的完整配置请求体。
def encode_config(config: CrcConfig) -> bytes:

    flags = (
        int(config.ref_in)
        | (int(config.ref_out) << 1)
        | (int(config.byte_swap) << 2)
        | (int(config.auto_length_reload) << 3)
        | (int(config.result_check) << 4)
    )
    return CONFIG.pack(
        int(config.mode),
        flags,
        int(config.xor_out),
        config.fifo_threshold,
        config.polynomial,
        config.initial_value,
    )


# 编码 Resource 地址和待计算 Byte 数。
def encode_calculate(source_address: int, length_bytes: int) -> bytes:

    return CALCULATE.pack(source_address, length_bytes)


# 严格校验响应长度并解码一次 CRC 计算结果及剩余输入计数。
def decode_calculate_result(body: bytes) -> CrcCalculateResult:

    if len(body) != CALCULATE_RESULT.size:
        raise ProtocolError("CRC CALCULATE response length is invalid")
    result, remaining = CALCULATE_RESULT.unpack(body)
    return CrcCalculateResult(result=result, remaining_input_count=remaining)


# 按小端 Wire Contract 编码一个已经完成范围校验的无符号 32-Bit 字段。
def encode_uint32(value: int) -> bytes:

    return UINT32.pack(value)


# 严格校验响应长度并按小端顺序解码一个无符号 32-Bit 字段。
def decode_uint32(body: bytes, label: str) -> int:

    if len(body) != UINT32.size:
        raise ProtocolError(f"CRC {label} response length is invalid")
    return UINT32.unpack(body)[0]


# 解码 CRC FIFO 状态，并拒绝非规范 Bool。
def decode_fifo_status(body: bytes) -> CrcFifoStatus:

    if len(body) != FIFO_STATUS.size:
        raise ProtocolError("CRC FIFO_STATUS_GET response length is invalid")
    overflow = FIFO_STATUS.unpack(body)[0]
    if overflow not in (0, 1):
        raise ProtocolError("CRC FIFO_STATUS_GET returned a non-canonical Boolean")
    return CrcFifoStatus(overflow=bool(overflow))


# 按 CRC Wire Contract 编码已经完成合法性校验的非空 IRQ 事件集合。
def encode_irq_events(events: CrcIrqEvent) -> bytes:

    return UINT32.pack(int(events))


# 解码同一次 CRC IRQ 硬件状态和回调证据。
def decode_irq_snapshot(body: bytes) -> CrcIrqSnapshot:

    if len(body) != IRQ_SNAPSHOT.size:
        raise ProtocolError("CRC IRQ_SNAPSHOT_GET response length is invalid")
    raw, status, event_count, last_event, last_raw = IRQ_SNAPSHOT.unpack(body)
    for label, value in (
        ("raw", raw),
        ("status", status),
        ("last_event", last_event),
        ("last_raw", last_raw),
    ):
        if value & ~_KNOWN_IRQ_BITS:
            raise ProtocolError(f"CRC IRQ snapshot contains unknown {label} bits")
    return CrcIrqSnapshot(
        raw=CrcIrqEvent(raw),
        status=CrcIrqEvent(status),
        event_count=event_count,
        last_event=CrcIrqEvent(last_event),
        last_raw=CrcIrqEvent(last_raw),
    )


# 编码一次已经完成宽度和值域校验的 CRC 测试输入寄存器写入请求。
def encode_test_input(width: CrcInputAccessWidth, value: int) -> bytes:

    return TEST_INPUT.pack(int(width), value)


# 编码固定九槽的目标端紧凑 Burst；未使用槽清零以保持 Wire 唯一表示。
def encode_test_input_burst(values: tuple[int, ...], checkpoint_count: int) -> bytes:

    padded = values + (0,) * (9 - len(values))
    return TEST_INPUT_BURST.pack(len(values), checkpoint_count, 0, *padded)


# 解码目标端紧凑 Burst 事实，并拒绝非规范保留字段和 Bool。
def decode_test_input_burst_result(body: bytes) -> CrcInputBurstResult:

    if len(body) != TEST_INPUT_BURST_RESULT.size:
        raise ProtocolError("CRC TEST_INPUT_BURST_32 response length is invalid")
    count, checkpoint, reserved, checkpoint_result, final_result, overflow, tail = (
        TEST_INPUT_BURST_RESULT.unpack(body)
    )
    if reserved != 0 or tail != b"\x00\x00\x00":
        raise ProtocolError("CRC TEST_INPUT_BURST_32 response reserved field is non-zero")
    if not 1 <= count <= 9 or checkpoint > count:
        raise ProtocolError("CRC TEST_INPUT_BURST_32 returned invalid counts")
    if overflow not in (0, 1):
        raise ProtocolError("CRC TEST_INPUT_BURST_32 returned a non-canonical Boolean")
    return CrcInputBurstResult(
        count=count,
        checkpoint_count=checkpoint,
        checkpoint_result=checkpoint_result,
        final_result=final_result,
        overflow=bool(overflow),
    )


# 编码包含源地址、字节数和冻结保留字段的目标侧 CRC DWT 计时请求。
def encode_timed_calculate(source_address: int, length_bytes: int) -> bytes:

    return TIMED_CALCULATE.pack(source_address, length_bytes, 0)


# 解码目标侧 CRC DWT 计时事实并校验保留位。
def decode_timed_result(body: bytes) -> CrcTimedResult:

    if len(body) != TIMED_RESULT.size:
        raise ProtocolError("CRC TEST_CALCULATE_TIMED response length is invalid")
    result, elapsed_cycles, measured_bytes, reserved = TIMED_RESULT.unpack(body)
    if reserved != 0:
        raise ProtocolError("CRC TEST_CALCULATE_TIMED response reserved field is non-zero")
    return CrcTimedResult(
        result=result,
        elapsed_cycles=elapsed_cycles,
        measured_bytes=measured_bytes,
    )
