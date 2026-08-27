# CRC PC Driver Package 的 validation 层。
#
# 职责：在发送硬件命令前校验 CRC 公共业务参数。
# 边界：不访问 TargetClient/Profile，不执行设备 I/O，不复制芯片寄存器规则。
# 依赖：仅依赖本 IP Model。

from __future__ import annotations

from .models import CrcConfig, CrcInputAccessWidth, CrcIrqEvent, CrcMode, CrcXorOut

UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1


# 根据 CRC8、CRC16 或 CRC32 模式返回对应自然结果宽度的完整掩码。
def mode_mask(mode: CrcMode) -> int:

    return (1 << int(mode)) - 1


# 拒绝 Bool、非整数和越界值，并返回规范化的无符号 32-Bit 整数。
def require_uint32(value: int, name: str) -> int:

    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= UINT32_MAX:
        raise ValueError(f"{name} must be an unsigned 32-bit integer")
    return value


# 拒绝 Bool、零地址和越界值，并返回规范化的无符号 64-Bit 源地址。
def require_address(value: int, name: str = "source_address") -> int:

    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= UINT64_MAX:
        raise ValueError(f"{name} must be a non-zero unsigned 64-bit integer")
    return value


# 校验 CRC 配置的公共语义和当前模式结果宽度。
def validate_config(config: CrcConfig) -> CrcConfig:

    if not isinstance(config, CrcConfig):
        raise TypeError("config must be CrcConfig")
    if not isinstance(config.mode, CrcMode):
        raise ValueError("config.mode must be CrcMode")
    if not isinstance(config.xor_out, CrcXorOut):
        raise ValueError("config.xor_out must be CrcXorOut")
    if config.mode is CrcMode.CRC8 and config.byte_swap:
        raise ValueError("CRC8 does not support byte swap")
    mask = mode_mask(config.mode)
    for name, value in (
        ("polynomial", config.polynomial),
        ("initial_value", config.initial_value),
    ):
        require_uint32(value, name)
        if value & ~mask:
            raise ValueError(f"{name} exceeds the {int(config.mode)}-bit CRC width")
    if isinstance(config.fifo_threshold, bool) or not isinstance(config.fifo_threshold, int):
        raise ValueError("fifo_threshold must be an integer")
    if not 0 <= config.fifo_threshold <= 0xFF:
        raise ValueError("fifo_threshold must fit in one byte")
    return config


# 校验同步计算的源地址、非零长度、模式对齐、地址溢出和运行时长度上限。
def validate_calculate(
    mode: CrcMode,
    source_address: int,
    length_bytes: int,
    max_calculate_bytes: int,
) -> tuple[int, int]:

    address = require_address(source_address)
    length = require_uint32(length_bytes, "length_bytes")
    maximum = require_uint32(max_calculate_bytes, "max_calculate_bytes")
    if length == 0 or length > maximum:
        raise ValueError(f"length_bytes must be in range 1..{maximum}")
    alignment = int(mode) // 8
    if address % alignment:
        raise ValueError(f"source_address must be {alignment}-byte aligned for {mode.name}")
    if address + length - 1 > UINT64_MAX:
        raise ValueError("source range exceeds unsigned 64-bit address space")
    return address, length


# 校验诊断型 LENGTH 命令的字节长度，并返回可直接进行 Wire 编码的数值。
def validate_data_length(length_bytes: int) -> int:

    return require_uint32(length_bytes, "length_bytes")


# 校验结果或 CHECK 值没有超过当前模式自然宽度。
def validate_mode_value(mode: CrcMode, value: int, name: str) -> int:

    result = require_uint32(value, name)
    if result & ~mode_mask(mode):
        raise ValueError(f"{name} exceeds the {int(mode)}-bit CRC width")
    return result


# 校验非空且只包含已发布 CRC IRQ 位的事件集合。
def validate_irq_events(events: CrcIrqEvent) -> CrcIrqEvent:

    try:
        normalized = CrcIrqEvent(events)
    except (TypeError, ValueError) as exc:
        raise ValueError("events must be CrcIrqEvent") from exc
    if normalized == CrcIrqEvent.NONE or normalized & ~CrcIrqEvent.ALL:
        raise ValueError("events must contain only published non-zero CRC IRQ bits")
    return normalized


# 校验测试输入枚举类型和值域，保证数值能够装入所选的自然访问宽度。
def validate_test_input(width: CrcInputAccessWidth, value: int) -> tuple[CrcInputAccessWidth, int]:

    if not isinstance(width, CrcInputAccessWidth):
        raise ValueError("width must be CrcInputAccessWidth")
    normalized = require_uint32(value, "value")
    if normalized >= 1 << int(width):
        raise ValueError(f"value exceeds the {int(width)}-bit input width")
    return width, normalized


# 校验目标端紧凑 Burst 的固定上限、检查点和每个 32-Bit 输入值。
def validate_test_input_burst(
    values: tuple[int, ...],
    checkpoint_count: int,
) -> tuple[tuple[int, ...], int]:

    if not isinstance(values, tuple) or not 1 <= len(values) <= 9:
        raise ValueError("values must be a tuple containing 1..9 items")
    checkpoint = require_uint32(checkpoint_count, "checkpoint_count")
    if checkpoint > len(values):
        raise ValueError("checkpoint_count must not exceed the input count")
    normalized = tuple(require_uint32(value, "values item") for value in values)
    return normalized, checkpoint
