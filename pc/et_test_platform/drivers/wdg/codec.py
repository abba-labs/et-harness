# WDG Wire 编解码。
# 职责：提供固定布局的纯 Request/Response 转换和严格解码。
# 边界：不执行 I/O、等待、Capability 查询或测试判断。
# 依赖：仅依赖本 IP Contract/Model 和公共 ProtocolError。

from ...core.errors import ProtocolError
from .contract import (
    CAPABILITIES_STRUCT,
    CONFIG_STRUCT,
    IRQ_SNAPSHOT_STRUCT,
    MASK_STRUCT,
    RECORD_STRUCT,
    STATUS_STRUCT,
    WDG_SERVICE_API_VERSION,
)
from .models import (
    WdgCapabilities,
    WdgConfig,
    WdgFeature,
    WdgIrqEvent,
    WdgIrqSnapshot,
    WdgMode,
    WdgRecord,
    WdgRecordSnapshot,
    WdgStatus,
    WdgWorkMode,
)

_KNOWN_FEATURES = WdgFeature((1 << 11) - 1)


# 严格解码 Runtime Capability 并拒绝未知位、空模式和非法实例数。
def decode_capabilities(body: bytes) -> WdgCapabilities:

    if len(body) != CAPABILITIES_STRUCT.size:
        raise ProtocolError("WDG CAPABILITIES_GET response length is invalid")
    api, size, features, maximum_reload, maximum_window, modes, work_modes, irq, count = (
        CAPABILITIES_STRUCT.unpack(body)
    )
    if api != WDG_SERVICE_API_VERSION or size != CAPABILITIES_STRUCT.size:
        raise ProtocolError("WDG CAPABILITIES_GET version or size is incompatible")
    if features & ~int(_KNOWN_FEATURES) or maximum_reload == 0 or maximum_window == 0:
        raise ProtocolError("WDG CAPABILITIES_GET contains invalid features or limits")
    known_modes = sum(1 << int(mode) for mode in WdgMode)
    known_work_modes = sum(1 << int(mode) for mode in WdgWorkMode)
    if modes == 0 or modes & ~known_modes or work_modes == 0 or work_modes & ~known_work_modes:
        raise ProtocolError("WDG CAPABILITIES_GET contains invalid mode bits")
    if irq == 0 or irq & ~int(WdgIrqEvent.ALL) or count == 0:
        raise ProtocolError("WDG CAPABILITIES_GET contains invalid IRQ or instance facts")
    return WdgCapabilities(
        features=WdgFeature(features),
        maximum_reload_count=maximum_reload,
        maximum_window_count=maximum_window,
        modes=tuple(mode for mode in WdgMode if modes & (1 << int(mode))),
        work_modes=tuple(mode for mode in WdgWorkMode if work_modes & (1 << int(mode))),
        irq_events=WdgIrqEvent(irq),
        instance_count=count,
    )


# 编码一份已经完成公共语义校验的完整 WDG 配置。
def encode_config(config: WdgConfig) -> bytes:

    return CONFIG_STRUCT.pack(
        config.reload_count,
        config.window_low_count,
        config.window_high_count,
        int(config.mode),
        int(config.work_mode),
        int(config.reset_enable),
        int(config.halt_pause_enable),
    )


# 严格解码目标实际配置读回值，并拒绝非规范布尔值和未知模式。
def decode_config(body: bytes) -> WdgConfig:

    if len(body) != CONFIG_STRUCT.size:
        raise ProtocolError("WDG CONFIG_GET response length is invalid")
    reload_count, low, high, mode, work_mode, reset_enable, halt_pause = CONFIG_STRUCT.unpack(body)
    if reset_enable not in (0, 1) or halt_pause not in (0, 1):
        raise ProtocolError("WDG CONFIG_GET contains noncanonical boolean values")
    try:
        return WdgConfig(
            reload_count=reload_count,
            window_low_count=low,
            window_high_count=high,
            mode=WdgMode(mode),
            work_mode=WdgWorkMode(work_mode),
            reset_enable=bool(reset_enable),
            halt_pause_enable=bool(halt_pause),
        )
    except ValueError as exc:
        raise ProtocolError("WDG CONFIG_GET contains unknown mode values") from exc


# 严格解码使能状态和当前计数，并拒绝非规范使能字段。
def decode_status(body: bytes) -> WdgStatus:

    if len(body) != STATUS_STRUCT.size:
        raise ProtocolError("WDG STATUS_GET response length is invalid")
    enabled, counter = STATUS_STRUCT.unpack(body)
    if enabled not in (0, 1):
        raise ProtocolError("WDG STATUS_GET contains a noncanonical enabled value")
    return WdgStatus(enabled=bool(enabled), counter=counter)


# 编码一个已校验的 WDG IRQ 或 Record 位掩码。
def encode_mask(value: WdgIrqEvent | WdgRecord) -> bytes:

    return MASK_STRUCT.pack(int(value))


# 解码 Raw、Status、ISR latch/count 与最后 Raw 的同一快照。
def decode_irq_snapshot(body: bytes) -> WdgIrqSnapshot:

    if len(body) != IRQ_SNAPSHOT_STRUCT.size:
        raise ProtocolError("WDG IRQ_SNAPSHOT_GET response length is invalid")
    raw, status, latched, event_count, last_raw = IRQ_SNAPSHOT_STRUCT.unpack(body)
    for label, value in (
        ("raw", raw),
        ("status", status),
        ("latched", latched),
        ("last_raw", last_raw),
    ):
        if value & ~int(WdgIrqEvent.ALL):
            raise ProtocolError(f"WDG IRQ snapshot contains unknown {label} bits")
    return WdgIrqSnapshot(
        raw=WdgIrqEvent(raw),
        status=WdgIrqEvent(status),
        latched=WdgIrqEvent(latched),
        event_count=event_count,
        last_raw=WdgIrqEvent(last_raw),
    )


# 解码彼此独立的 reset 与 interrupt 持久记录。
def decode_records(body: bytes) -> WdgRecordSnapshot:

    if len(body) != RECORD_STRUCT.size:
        raise ProtocolError("WDG RECORD_GET response length is invalid")
    reset, interrupt = RECORD_STRUCT.unpack(body)
    if reset not in (0, 1) or interrupt not in (0, 1):
        raise ProtocolError("WDG RECORD_GET contains noncanonical record values")
    return WdgRecordSnapshot(reset=bool(reset), interrupt=bool(interrupt))
