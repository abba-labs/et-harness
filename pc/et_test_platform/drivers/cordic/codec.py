# CORDIC PC Driver Package 的 codec 层。
#
# 职责：执行 CORDIC Wire Body 的确定性编码和严格解码。
# 边界：不发送请求、不读取 Profile、不解释数学 Codec 或测试结论。
# 依赖：仅依赖本 IP Contract、Model 和公共 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .contract import (
    CORDIC_CAPABILITIES_SIZE,
    CORDIC_SERVICE_API_VERSION,
    CORDIC_TIMED_RESPONSE_SIZE,
)
from .models import (
    CordicCapabilities,
    CordicConfig,
    CordicFeature,
    CordicFunction,
    CordicIrqEvent,
    CordicIrqSnapshot,
    CordicResult,
    CordicTimedResult,
)

CAPABILITIES = struct.Struct("<HHIHBBB3x")
CONFIG = struct.Struct("<10B2x")
ARGUMENT = struct.Struct("<B3xI")
RESULT = struct.Struct("<II")
UINT32 = struct.Struct("<I")
IRQ_SNAPSHOT = struct.Struct("<IIIII")
ZERO_OVERHEAD = struct.Struct("<BB2xII")
TIMED_EXECUTE = struct.Struct("<BB2xIII")
TIMED_RESULT = struct.Struct("<III")

_KNOWN_FEATURES = CordicFeature((1 << 12) - 1)
_KNOWN_FUNCTION_MASK = (1 << len(CordicFunction)) - 1
_KNOWN_IRQ_BITS = int(CordicIrqEvent.ALL)


# 严格解码CORDIC Runtime Capability，并拒绝未知位和非零保留字段。
def decode_capabilities(body: bytes) -> CordicCapabilities:

    if len(body) != CORDIC_CAPABILITIES_SIZE:
        raise ProtocolError("CORDIC CAPABILITIES_GET response length is invalid")
    api_version, struct_size, features, functions, scale, precision, irq_events = (
        CAPABILITIES.unpack(body)
    )
    if api_version != CORDIC_SERVICE_API_VERSION or struct_size != CORDIC_CAPABILITIES_SIZE:
        raise ProtocolError("CORDIC CAPABILITIES_GET version or size is incompatible")
    if features & ~int(_KNOWN_FEATURES):
        raise ProtocolError("CORDIC CAPABILITIES_GET contains unknown feature bits")
    if functions == 0 or functions & ~_KNOWN_FUNCTION_MASK:
        raise ProtocolError("CORDIC CAPABILITIES_GET contains invalid function bits")
    if scale > 7 or precision == 0 or irq_events & ~_KNOWN_IRQ_BITS:
        raise ProtocolError("CORDIC CAPABILITIES_GET contains invalid limits or IRQ bits")
    return CordicCapabilities(
        api_version=api_version,
        features=CordicFeature(features),
        functions=tuple(
            function for function in CordicFunction if functions & (1 << int(function))
        ),
        maximum_scale=scale,
        maximum_precision_cycles=precision,
        irq_events=CordicIrqEvent(irq_events),
    )


# 编码一份已经完成Runtime Capability校验的完整配置。
def encode_config(config: CordicConfig) -> bytes:

    return CONFIG.pack(
        int(config.numeric_mode),
        int(config.argument_width),
        int(config.result_width),
        int(config.input_range),
        config.scale,
        config.precision_cycles,
        int(config.sincos_result_count),
        int(config.phase_modulus_result_count),
        int(config.hsincos_result_count),
        int(config.work_mode),
    )


# 将函数编号与一个 Raw 参数编码为固定 8 字节请求体。
def encode_argument(function: CordicFunction, raw_value: int) -> bytes:

    return ARGUMENT.pack(int(function), raw_value)


# 解码两个不解释Codec的CORDIC Raw结果字。
def decode_result(body: bytes) -> CordicResult:

    if len(body) != RESULT.size:
        raise ProtocolError("CORDIC RESULT response length is invalid")
    return CordicResult(*RESULT.unpack(body))


# 将已校验的无符号 32 位值编码为固定 4 字节请求体。
def encode_uint32(value: int) -> bytes:

    return UINT32.pack(value)


# 严格校验 4 字节响应长度并解码无符号 32 位值。
def decode_uint32(body: bytes, label: str) -> int:

    if len(body) != UINT32.size:
        raise ProtocolError(f"CORDIC {label} response length is invalid")
    return UINT32.unpack(body)[0]


# 解码 IRQ Raw/Mask 后状态及 ISR 回调证据，并拒绝未知事件位。
def decode_irq_snapshot(body: bytes) -> CordicIrqSnapshot:

    if len(body) != IRQ_SNAPSHOT.size:
        raise ProtocolError("CORDIC IRQ_SNAPSHOT_GET response length is invalid")
    raw, status, event_count, last_event, last_raw = IRQ_SNAPSHOT.unpack(body)
    for label, value in (
        ("raw", raw),
        ("status", status),
        ("last_event", last_event),
        ("last_raw", last_raw),
    ):
        if value & ~_KNOWN_IRQ_BITS:
            raise ProtocolError(f"CORDIC IRQ snapshot contains unknown {label} bits")
    return CordicIrqSnapshot(
        raw=CordicIrqEvent(raw),
        status=CordicIrqEvent(status),
        event_count=event_count,
        last_event=CordicIrqEvent(last_event),
        last_raw=CordicIrqEvent(last_raw),
    )


# 编码一笔固定两槽的零开销Raw事务，未使用槽保持零。
def encode_zero_overhead(function: CordicFunction, arguments: tuple[int, ...]) -> bytes:

    second = arguments[1] if len(arguments) == 2 else 0
    return ZERO_OVERHEAD.pack(int(function), len(arguments), arguments[0], second)


# 编码一笔固定16字节的目标侧CORDIC计时事务，保留字段和超时预算均显式传输。
def encode_timed(
    function: CordicFunction,
    arguments: tuple[int, ...],
    timeout_polls: int,
) -> bytes:

    second = arguments[1] if len(arguments) == 2 else 0
    return TIMED_EXECUTE.pack(int(function), len(arguments), arguments[0], second, timeout_polls)


# 严格解码目标侧CORDIC计时结果，保留Raw结果并返回目标周期数。
def decode_timed_result(body: bytes) -> CordicTimedResult:

    if len(body) != CORDIC_TIMED_RESPONSE_SIZE or len(body) != TIMED_RESULT.size:
        raise ProtocolError("CORDIC TEST_EXECUTE_TIMED response length is invalid")
    return CordicTimedResult(*TIMED_RESULT.unpack(body))
