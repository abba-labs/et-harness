# STIMER Wire编解码。
# 职责：固定布局的纯Request/Response转换和严格解码。
# 边界：不执行I/O、等待或测试判断。
# 依赖：仅依赖 STIMER Contract、Model 和公共 ProtocolError。

from ...core.errors import ProtocolError
from .contract import (
    CAPABILITIES_STRUCT,
    COMPARE_STRUCT,
    CONFIG_STRUCT,
    DEBUG_HALT_POLICY_STRUCT,
    EMERGENCY_ROUTE_STRUCT,
    EVENT_PULSE_WIDTH_STRUCT,
    IRQ_SNAPSHOT_STRUCT,
    STIMER_SERVICE_API_VERSION,
    UINT32_STRUCT,
)
from .models import (
    StimerCapabilities,
    StimerConfig,
    StimerDebugHaltPolicy,
    StimerFeature,
    StimerIrqEvent,
    StimerIrqSnapshot,
    StimerRuntimeStatus,
)

_KNOWN_FEATURES = StimerFeature((1 << 16) - 1)


# 按冻结Wire顺序编码Period、Prescaler、Mode和Load Mode完整配置。
def encode_config(config: StimerConfig) -> bytes:

    return CONFIG_STRUCT.pack(
        config.period_ticks,
        config.prescaler_divider,
        int(config.mode),
        int(config.load_mode),
    )


# 按冻结Wire顺序编码CPU Halt期间的STIMER运行策略。
def encode_debug_halt_policy(policy: StimerDebugHaltPolicy) -> bytes:

    return DEBUG_HALT_POLICY_STRUCT.pack(int(policy))


# 严格解码Runtime Capability，并拒绝未知Feature、空拓扑和非法IRQ位。
def decode_capabilities(body: bytes) -> StimerCapabilities:

    if len(body) != CAPABILITIES_STRUCT.size:
        raise ProtocolError("STIMER CAPABILITIES_GET response length is invalid")
    api, size, features, max_period, max_prescaler, channels, instances, irq = (
        CAPABILITIES_STRUCT.unpack(body)
    )
    if api != STIMER_SERVICE_API_VERSION or size != CAPABILITIES_STRUCT.size:
        raise ProtocolError("STIMER CAPABILITIES_GET version or size is incompatible")
    if features & ~int(_KNOWN_FEATURES) or max_period == 0 or max_prescaler == 0:
        raise ProtocolError("STIMER CAPABILITIES_GET contains invalid features or limits")
    if channels == 0 or instances == 0 or irq == 0 or irq & ~int(StimerIrqEvent.ALL):
        raise ProtocolError("STIMER CAPABILITIES_GET contains invalid topology or IRQ bits")
    return StimerCapabilities(
        features=StimerFeature(features),
        maximum_period_ticks=max_period,
        maximum_prescaler_divider=max_prescaler,
        compare_channel_count=channels,
        instance_count=instances,
        irq_events=StimerIrqEvent(irq),
    )


# 严格解码一个固定长度的32-bit实时或锁存计数响应。
def decode_count(body: bytes) -> int:

    if len(body) != UINT32_STRUCT.size:
        raise ProtocolError("STIMER count response length is invalid")
    return UINT32_STRUCT.unpack(body)[0]


# 解码全部STIMER运行时诊断位，并拒绝当前合同未发布的未知位。
def decode_status(body: bytes) -> StimerRuntimeStatus:

    value = decode_count(body)
    if value & ~int(StimerRuntimeStatus.ALL):
        raise ProtocolError("STIMER STATUS_GET contains unknown status bits")
    return StimerRuntimeStatus(value)


# 按冻结Wire顺序编码Compare通道和32-bit硬件门限。
def encode_compare(channel: int, threshold: int) -> bytes:

    return COMPARE_STRUCT.pack(channel, threshold)


# 按冻结Wire顺序编码单一Event Source和公开脉宽周期数。
def encode_event_pulse_width(event: StimerIrqEvent, width_cycles: int) -> bytes:

    return EVENT_PULSE_WIDTH_STRUCT.pack(int(event), width_cycles)


# 按冻结Wire顺序编码逻辑紧急源和触发组；芯片源掩码不出现在PC协议中。
def encode_emergency_route(source_id: int, trigger_group: int) -> bytes:

    return EMERGENCY_ROUTE_STRUCT.pack(source_id, trigger_group)


# 把已经完成公共语义校验的STIMER IRQ掩码编码为固定Wire请求。
def encode_irq(events: StimerIrqEvent) -> bytes:

    return UINT32_STRUCT.pack(int(events))


# 严格解码Raw、Status、ISR计数与最后Source组成的完整IRQ快照。
def decode_irq_snapshot(body: bytes) -> StimerIrqSnapshot:

    if len(body) != IRQ_SNAPSHOT_STRUCT.size:
        raise ProtocolError("STIMER IRQ_SNAPSHOT_GET response length is invalid")
    raw, status, latched, count, last_raw, last_event = IRQ_SNAPSHOT_STRUCT.unpack(body)
    for label, value in (
        ("raw", raw),
        ("status", status),
        ("latched", latched),
        ("last_raw", last_raw),
        ("last_event", last_event),
    ):
        if value & ~int(StimerIrqEvent.ALL):
            raise ProtocolError(f"STIMER IRQ snapshot contains unknown {label} bits")
    return StimerIrqSnapshot(
        raw=StimerIrqEvent(raw),
        status=StimerIrqEvent(status),
        latched=StimerIrqEvent(latched),
        event_count=count,
        last_raw=StimerIrqEvent(last_raw),
        last_event=StimerIrqEvent(last_event),
    )
