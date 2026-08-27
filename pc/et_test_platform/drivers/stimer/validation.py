# STIMER PC Driver参数校验。
# 职责：在I/O前拒绝非法公共配置、通道和IRQ掩码。
# 边界：不读取Capability，不执行设备操作。
# 依赖：仅依赖 STIMER 公共 Model 和稳定整数边界。

from .models import StimerConfig, StimerIrqEvent, StimerLoadMode, StimerMode

UINT16_MAX = (1 << 16) - 1
UINT32_MAX = (1 << 32) - 1
EVENT_PULSE_WIDTH_MIN_CYCLES = 1
EVENT_PULSE_WIDTH_MAX_CYCLES = 256


# 校验完整STIMER配置的类型、枚举与32-bit硬件边界，禁止Bool冒充整数。
def validate_config(config: StimerConfig) -> StimerConfig:

    if not isinstance(config, StimerConfig):
        raise TypeError("config must be StimerConfig")
    if not isinstance(config.mode, StimerMode):
        raise ValueError("config.mode must be StimerMode")
    if not isinstance(config.load_mode, StimerLoadMode):
        raise ValueError("config.load_mode must be StimerLoadMode")
    if (
        isinstance(config.period_ticks, bool)
        or not isinstance(config.period_ticks, int)
        or not 1 <= config.period_ticks <= UINT32_MAX
    ):
        raise ValueError("period_ticks must be in range 1..UINT32_MAX")
    if (
        isinstance(config.prescaler_divider, bool)
        or not isinstance(config.prescaler_divider, int)
        or not 1 <= config.prescaler_divider <= UINT16_MAX
    ):
        raise ValueError("prescaler_divider must be in range 1..UINT16_MAX")
    return config


# 校验非空且只包含已发布Source的IRQ掩码。
def validate_irq_events(events: StimerIrqEvent) -> StimerIrqEvent:

    try:
        normalized = StimerIrqEvent(events)
    except (TypeError, ValueError) as exc:
        raise ValueError("events must be StimerIrqEvent") from exc
    if normalized == StimerIrqEvent.NONE or normalized & ~StimerIrqEvent.ALL:
        raise ValueError("events must contain only published non-zero STIMER IRQ bits")
    return normalized


# 校验必须且只能选择一个STIMER事件源；只返回规范化位值，不执行设备I/O。
def validate_single_event(event: StimerIrqEvent) -> StimerIrqEvent:

    normalized = validate_irq_events(event)
    if int(normalized).bit_count() != 1:
        raise ValueError("event must select exactly one STIMER source")
    return normalized


# 根据Runtime发布的通道数量校验公开Compare通道编号。
def validate_compare_channel(channel: int, channel_count: int) -> int:

    if (
        isinstance(channel, bool)
        or not isinstance(channel, int)
        or not 0 <= channel < channel_count
    ):
        raise ValueError("compare channel is outside runtime capability")
    return channel


# 校验单一Event Source和稳定的1到256个STIMER时钟周期范围。
def validate_event_pulse_width(
    event: StimerIrqEvent, width_cycles: int
) -> tuple[StimerIrqEvent, int]:

    normalized_event = validate_single_event(event)
    if (
        isinstance(width_cycles, bool)
        or not isinstance(width_cycles, int)
        or not EVENT_PULSE_WIDTH_MIN_CYCLES <= width_cycles <= EVENT_PULSE_WIDTH_MAX_CYCLES
    ):
        raise ValueError("width_cycles must be in range 1..256")
    return normalized_event, width_cycles
