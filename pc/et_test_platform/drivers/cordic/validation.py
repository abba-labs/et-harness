# CORDIC PC Driver Package 的 validation 层。
#
# 职责：在 I/O 前校验 CORDIC 公共类型、取值范围和 Runtime Capability。
# 边界：不编码 Wire、不访问 Target/Profile、不修正非法调用参数。
# 依赖：仅依赖本 IP Model。

from __future__ import annotations

from .models import (
    CordicCapabilities,
    CordicConfig,
    CordicFeature,
    CordicFunction,
    CordicInputRange,
    CordicIrqEvent,
    CordicNumericMode,
    CordicResultCount,
    CordicWidth,
    CordicWorkMode,
)

_ENUM_FEATURES = {
    CordicNumericMode.FIXED: CordicFeature.FIXED,
    CordicNumericMode.FLOAT32: CordicFeature.FLOAT32,
    CordicWidth.BITS_16: CordicFeature.WIDTH_16,
    CordicWidth.BITS_32: CordicFeature.WIDTH_32,
    CordicInputRange.NORMALIZED: CordicFeature.NORMALIZED_RANGE,
    CordicInputRange.DIRECT_ANGLE: CordicFeature.DIRECT_ANGLE_RANGE,
    CordicWorkMode.INTERRUPT: CordicFeature.INTERRUPT,
    CordicWorkMode.POLLING: CordicFeature.POLLING,
    CordicWorkMode.ZERO_OVERHEAD: CordicFeature.ZERO_OVERHEAD,
    CordicWorkMode.DMA: CordicFeature.DMA,
}


# 校验一个无符号32位Raw值，禁止Bool借用整数语义。
def validate_raw_word(value: int, label: str) -> int:

    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{label} must be an unsigned 32-bit integer")
    return value


# 校验调用方传入的是稳定 CORDIC 函数枚举，拒绝裸整数冒充协议值。
def validate_function(function: CordicFunction) -> CordicFunction:

    if not isinstance(function, CordicFunction):
        raise TypeError("function must be CordicFunction")
    return function


# 结合Runtime Capability校验完整CORDIC配置。
def validate_config(config: CordicConfig, capabilities: CordicCapabilities) -> CordicConfig:

    if not isinstance(config, CordicConfig):
        raise TypeError("config must be CordicConfig")
    enum_fields = (
        (config.numeric_mode, CordicNumericMode, "numeric_mode"),
        (config.argument_width, CordicWidth, "argument_width"),
        (config.result_width, CordicWidth, "result_width"),
        (config.input_range, CordicInputRange, "input_range"),
        (config.sincos_result_count, CordicResultCount, "sincos_result_count"),
        (
            config.phase_modulus_result_count,
            CordicResultCount,
            "phase_modulus_result_count",
        ),
        (config.hsincos_result_count, CordicResultCount, "hsincos_result_count"),
        (config.work_mode, CordicWorkMode, "work_mode"),
    )

    for value, expected_type, label in enum_fields:
        if not isinstance(value, expected_type):
            raise TypeError(f"{label} must be {expected_type.__name__}")

    for value in (
        config.numeric_mode,
        config.argument_width,
        config.result_width,
        config.input_range,
        config.work_mode,
    ):
        if not capabilities.features & _ENUM_FEATURES[value]:
            raise ValueError(f"{value.name} is outside runtime capability")

    if isinstance(config.scale, bool) or not isinstance(config.scale, int):
        raise TypeError("scale must be an integer")
    if isinstance(config.precision_cycles, bool) or not isinstance(config.precision_cycles, int):
        raise TypeError("precision_cycles must be an integer")
    if not 0 <= config.scale <= capabilities.maximum_scale:
        raise ValueError("scale is outside runtime capability")
    if not 1 <= config.precision_cycles <= capabilities.maximum_precision_cycles:
        raise ValueError("precision_cycles is outside runtime capability")
    return config


# 校验一个非空且仅含已发布Source的IRQ集合。
def validate_irq_events(events: CordicIrqEvent) -> CordicIrqEvent:

    if not isinstance(events, CordicIrqEvent):
        raise TypeError("events must be CordicIrqEvent")
    if events == 0 or int(events) & ~int(CordicIrqEvent.ALL):
        raise ValueError("events must contain only published CORDIC IRQ sources")
    return events


# 按函数元数校验零开销事务的 Raw 参数数量，并逐项限制为 32 位。
def validate_zero_overhead_arguments(
    function: CordicFunction,
    arguments: tuple[int, ...],
) -> tuple[CordicFunction, tuple[int, ...]]:

    normalized_function = validate_function(function)
    expected_count = 2 if normalized_function is CordicFunction.PHASE_MODULUS else 1
    if not isinstance(arguments, tuple) or len(arguments) != expected_count:
        raise ValueError(f"{normalized_function.name} requires {expected_count} raw argument(s)")
    return normalized_function, tuple(
        validate_raw_word(value, f"arguments[{index}]") for index, value in enumerate(arguments)
    )
