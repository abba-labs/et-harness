# FMAC PC Driver Package 的 codec 层。
#
# 职责：执行 FMAC Wire Body 的确定性编码和严格解码。
# 边界：不发送请求、不读取 Profile、不产生 Case 结论。
# 依赖：仅依赖FMAC Contract、Model和标准库。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .contract import (
    FMAC_CAPABILITIES_SIZE,
    FMAC_SERVICE_API_VERSION,
    FMAC_SHIFT_ENCODING_COUNT,
)
from .models import (
    FmacCapabilities,
    FmacConfig,
    FmacDataFormat,
    FmacFeature,
    FmacFinalPolicy,
    FmacFunction,
    FmacIrqEvent,
    FmacIrqSnapshot,
    FmacOutputMode,
    FmacProcessResult,
    FmacShift,
    FmacStatus,
    FmacTimedProcessResult,
    FmacWatermark,
)

CAPABILITIES = struct.Struct("<HHIH6BH2B")
CONFIG = struct.Struct("<14BH8x")
CONFIG_SNAPSHOT = struct.Struct("<14BH")
START = struct.Struct("<4B")
RESOURCE = struct.Struct("<IIHBB")
COEFFICIENTS = struct.Struct("<IIB3xIIB3x")
PROCESS = struct.Struct("<4BIIIIH2x")
COUNT = struct.Struct("<I")
PROCESS_RESULT = struct.Struct("<II")
TIMED_PROCESS_RESULT = struct.Struct("<III")
STATUS = struct.Struct("<10B2x")
IRQ_SNAPSHOT = struct.Struct("<IIIIII")
UINT32 = struct.Struct("<I")

_KNOWN_FEATURES = (1 << 13) - 1
_KNOWN_IRQ_BITS = int(FmacIrqEvent.ALL)
_ALIGNMENT_UNKNOWN = 0xFF


# 严格解码FMAC Runtime Capability，未知或非法事实直接拒绝。
def decode_capabilities(body: bytes) -> FmacCapabilities:

    if len(body) != FMAC_CAPABILITIES_SIZE:
        raise ProtocolError("FMAC CAPABILITIES_GET response length is invalid")
    (
        api_version,
        struct_size,
        features,
        max_transfer_items,
        logical_address_bits,
        max_feedforward_taps,
        max_feedback_taps,
        watermark_mask,
        output_mode_mask,
        shift_count,
        irq_events,
        fir_alignment,
        iir_alignment,
    ) = CAPABILITIES.unpack(body)
    if api_version != FMAC_SERVICE_API_VERSION or struct_size != FMAC_CAPABILITIES_SIZE:
        raise ProtocolError("FMAC CAPABILITIES_GET version or size is incompatible")
    if features & ~_KNOWN_FEATURES or max_transfer_items == 0 or logical_address_bits == 0:
        raise ProtocolError("FMAC CAPABILITIES_GET contains invalid limits or feature bits")
    if watermark_mask == 0 or watermark_mask & ~0x0F:
        raise ProtocolError("FMAC CAPABILITIES_GET contains invalid watermark bits")
    if (
        output_mode_mask == 0
        or output_mode_mask & ~0x07
        or shift_count != FMAC_SHIFT_ENCODING_COUNT
    ):
        raise ProtocolError("FMAC CAPABILITIES_GET contains invalid output options")
    if irq_events == 0 or irq_events & ~_KNOWN_IRQ_BITS:
        raise ProtocolError("FMAC CAPABILITIES_GET contains invalid IRQ bits")
    return FmacCapabilities(
        api_version=api_version,
        features=FmacFeature(features),
        max_transfer_items=max_transfer_items,
        logical_address_bits=logical_address_bits,
        max_feedforward_taps=max_feedforward_taps,
        max_feedback_taps=max_feedback_taps,
        watermarks=tuple(
            watermark
            for index, watermark in enumerate(FmacWatermark)
            if watermark_mask & (1 << index)
        ),
        output_modes=tuple(mode for mode in FmacOutputMode if output_mode_mask & (1 << int(mode))),
        shift_count=shift_count,
        irq_events=FmacIrqEvent(irq_events),
        fir_first_valid_output_index=(
            None if fir_alignment == _ALIGNMENT_UNKNOWN else fir_alignment
        ),
        iir_first_valid_output_index=(
            None if iir_alignment == _ALIGNMENT_UNKNOWN else iir_alignment
        ),
    )


# 编码一份已经完成Runtime Capability校验的完整FMAC配置。
def encode_config(config: FmacConfig) -> bytes:

    return CONFIG.pack(
        config.x1_start,
        config.x1_size,
        int(config.x1_full_watermark),
        config.x2_start,
        config.x2_size,
        config.y_start,
        config.y_size,
        int(config.y_empty_watermark),
        int(config.final_policy),
        int(config.output_mode),
        int(config.internal_clip),
        int(config.float_input),
        int(config.float_output),
        int(config.output_shift),
        config.output_offset,
    )


# 解码FMAC配置读回，严格转换公共枚举并拒绝未知硬件编码。
def decode_config_snapshot(body: bytes) -> FmacConfig:

    if len(body) != CONFIG_SNAPSHOT.size:
        raise ProtocolError("FMAC CONFIG_SNAPSHOT_GET response length is invalid")
    values = CONFIG_SNAPSHOT.unpack(body)
    try:
        return FmacConfig(
            x1_start=values[0],
            x1_size=values[1],
            x1_full_watermark=FmacWatermark(values[2]),
            x2_start=values[3],
            x2_size=values[4],
            y_start=values[5],
            y_size=values[6],
            y_empty_watermark=FmacWatermark(values[7]),
            final_policy=FmacFinalPolicy(values[8]),
            output_mode=FmacOutputMode(values[9]),
            internal_clip=bool(values[10]),
            float_input=bool(values[11]),
            float_output=bool(values[12]),
            output_shift=FmacShift(values[13]),
            output_offset=values[14],
        )
    except ValueError as error:
        raise ProtocolError("FMAC config snapshot contains unknown enum values") from error


# 编码FMAC功能选择和P/Q抽头数量；保留字固定写零。
def encode_start(function: FmacFunction, feedforward_taps: int, feedback_taps: int) -> bytes:
    return START.pack(int(function), feedforward_taps, feedback_taps, 0)


# 编码Resource句柄、偏移、数量和数据格式，不传递目标裸地址。
def encode_resource(handle: int, offset: int, count: int, format_: FmacDataFormat) -> bytes:
    return RESOURCE.pack(handle, offset, count, int(format_), 0)


# 编码前馈与反馈两段独立Resource引用；两个保留区固定写零。
def encode_coefficients(
    feedforward_handle: int,
    feedforward_offset: int,
    feedforward_count: int,
    feedback_handle: int,
    feedback_offset: int,
    feedback_count: int,
) -> bytes:
    return COEFFICIENTS.pack(
        feedforward_handle,
        feedforward_offset,
        feedforward_count,
        feedback_handle,
        feedback_offset,
        feedback_count,
    )


# 编码一笔目标端有界PROCESS事务，不在PC端隐藏轮询或重试。
def encode_process(
    function: FmacFunction,
    feedforward_taps: int,
    feedback_taps: int,
    format_: FmacDataFormat,
    source_handle: int,
    source_offset: int,
    destination_handle: int,
    destination_offset: int,
    count: int,
) -> bytes:
    return PROCESS.pack(
        int(function),
        feedforward_taps,
        feedback_taps,
        int(format_),
        source_handle,
        source_offset,
        destination_handle,
        destination_offset,
        count,
    )


# 解码单一传输数量响应，并通过命令标签给出准确协议错误。
def decode_count(body: bytes, label: str) -> int:
    if len(body) != COUNT.size:
        raise ProtocolError(f"FMAC {label} response length is invalid")
    return COUNT.unpack(body)[0]


# 解码PROCESS实际接受和读取数量，保留两个独立硬件事实。
def decode_process_result(body: bytes) -> FmacProcessResult:
    if len(body) != PROCESS_RESULT.size:
        raise ProtocolError("FMAC PROCESS response length is invalid")
    return FmacProcessResult(*PROCESS_RESULT.unpack(body))


# 校验PROCESS_TIMED固定响应长度，并按接受数、读取数、DWT周期顺序解码原始事实。
def decode_timed_process_result(body: bytes) -> FmacTimedProcessResult:
    if len(body) != TIMED_PROCESS_RESULT.size:
        raise ProtocolError("FMAC PROCESS_TIMED response length is invalid")
    return FmacTimedProcessResult(*TIMED_PROCESS_RESULT.unpack(body))


# 解码FMAC状态快照，并拒绝非0/1的布尔硬件编码。
def decode_status(body: bytes) -> FmacStatus:
    if len(body) != STATUS.size:
        raise ProtocolError("FMAC STATUS_GET response length is invalid")
    values = STATUS.unpack(body)
    if any(value not in (0, 1) for value in (*values[0:1], *values[3:10])):
        raise ProtocolError("FMAC status contains noncanonical Boolean values")
    return FmacStatus(
        active=bool(values[0]),
        x1_spare_count=values[1],
        y_unread_count=values[2],
        x1_full=bool(values[3]),
        y_empty=bool(values[4]),
        x1_overflow=bool(values[5]),
        y_underflow=bool(values[6]),
        accumulator_saturation=bool(values[7]),
        negative_after_offset=bool(values[8]),
        float_to_q15_overflow=bool(values[9]),
    )


# 解码硬件Raw/Status和Service投递证据，并拒绝未知Source位。
def decode_irq_snapshot(body: bytes) -> FmacIrqSnapshot:
    if len(body) != IRQ_SNAPSHOT.size:
        raise ProtocolError("FMAC IRQ_SNAPSHOT_GET response length is invalid")
    raw, status, latched, event_count, enabled, masked = IRQ_SNAPSHOT.unpack(body)
    if any(value & ~_KNOWN_IRQ_BITS for value in (raw, status, latched, enabled, masked)):
        raise ProtocolError("FMAC IRQ snapshot contains unknown source bits")
    return FmacIrqSnapshot(
        raw=FmacIrqEvent(raw),
        status=FmacIrqEvent(status),
        latched=FmacIrqEvent(latched),
        event_count=event_count,
        enabled=FmacIrqEvent(enabled),
        masked=FmacIrqEvent(masked),
    )


# 编码一个无符号32-bit FMAC命令字段，字节序固定为小端。
def encode_uint32(value: int) -> bytes:
    return UINT32.pack(value)


# 解码一个无符号32-bit FMAC响应字段，并严格校验响应长度。
def decode_uint32(body: bytes, label: str) -> int:
    if len(body) != UINT32.size:
        raise ProtocolError(f"FMAC {label} response length is invalid")
    return UINT32.unpack(body)[0]
