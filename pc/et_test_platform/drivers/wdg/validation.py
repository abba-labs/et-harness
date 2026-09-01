# WDG PC Driver 参数校验。
# 职责：在 I/O 前拒绝非法公共配置、事件与记录掩码。
# 边界：不读取 Capability，不执行设备操作，不复制芯片寄存器规则。
# 依赖：仅依赖本 IP 模型。

from .models import WdgConfig, WdgIrqEvent, WdgMode, WdgRecord, WdgWorkMode

UINT32_MAX = (1 << 32) - 1


# 校验完整 WDG 配置，不允许 Bool 冒充整数或窗口关系失真。
def validate_config(config: WdgConfig) -> WdgConfig:

    if not isinstance(config, WdgConfig):
        raise TypeError("config must be WdgConfig")
    if not isinstance(config.mode, WdgMode):
        raise ValueError("config.mode must be WdgMode")
    if not isinstance(config.work_mode, WdgWorkMode):
        raise ValueError("config.work_mode must be WdgWorkMode")
    for name, value in (
        ("reload_count", config.reload_count),
        ("window_low_count", config.window_low_count),
        ("window_high_count", config.window_high_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= UINT32_MAX:
            raise ValueError(f"{name} must be an unsigned 32-bit integer")
    if config.reload_count == 0:
        raise ValueError("reload_count must be non-zero")
    if not 0 <= config.window_low_count <= config.window_high_count <= config.reload_count:
        raise ValueError("window thresholds must satisfy low <= high <= reload")
    return config


# 校验非空且只包含已发布 timeout 位的 WDG IRQ 掩码。
def validate_irq_events(events: WdgIrqEvent) -> WdgIrqEvent:

    try:
        normalized = WdgIrqEvent(events)
    except (TypeError, ValueError) as exc:
        raise ValueError("events must be WdgIrqEvent") from exc
    if normalized == WdgIrqEvent.NONE or normalized & ~WdgIrqEvent.ALL:
        raise ValueError("events must contain only published non-zero WDG IRQ bits")
    return normalized


# 校验非空且只包含 reset/interrupt 的持久记录掩码。
def validate_records(records: WdgRecord) -> WdgRecord:

    try:
        normalized = WdgRecord(records)
    except (TypeError, ValueError) as exc:
        raise ValueError("records must be WdgRecord") from exc
    if normalized == WdgRecord.NONE or normalized & ~WdgRecord.ALL:
        raise ValueError("records must contain only published non-zero WDG record bits")
    return normalized
