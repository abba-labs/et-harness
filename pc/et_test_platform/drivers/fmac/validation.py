# FMAC PC Driver Package 的 validation 层。
#
# 职责：校验公共参数和 Runtime Capability，不截断或猜测芯片事实。
# 边界：不执行I/O、不修改配置、不读取芯片Profile。
# 依赖：仅依赖FMAC公共Model。

from __future__ import annotations

from .models import (
    FmacCapabilities,
    FmacConfig,
    FmacDataFormat,
    FmacDmaRequest,
    FmacFunction,
    FmacIrqEvent,
)


# 校验公共无符号整数的类型和闭区间，禁止bool混入整数参数。
def require_uint(value: int, label: str, maximum: int, *, nonzero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    minimum = 1 if nonzero else 0
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be in range {minimum}..{maximum}")
    return value


# 按Runtime Capability校验完整FMAC配置，不截断或补写默认字段。
def validate_config(config: FmacConfig, capabilities: FmacCapabilities) -> FmacConfig:
    if not isinstance(config, FmacConfig):
        raise TypeError("config must be FmacConfig")
    logical_limit = 1 << capabilities.logical_address_bits
    for label, start, size in (
        ("x1", config.x1_start, config.x1_size),
        ("x2", config.x2_start, config.x2_size),
        ("y", config.y_start, config.y_size),
    ):
        require_uint(start, f"{label}_start", logical_limit - 1)
        require_uint(size, f"{label}_size", logical_limit - 1, nonzero=True)
        if start + size > logical_limit:
            raise ValueError(f"{label} region exceeds the published logical address limit")
    if config.x1_full_watermark not in capabilities.watermarks:
        raise ValueError("x1_full_watermark is not supported by runtime capability")
    if config.y_empty_watermark not in capabilities.watermarks:
        raise ValueError("y_empty_watermark is not supported by runtime capability")
    if config.output_mode not in capabilities.output_modes:
        raise ValueError("output_mode is not supported by runtime capability")
    if int(config.output_shift) >= capabilities.shift_count:
        raise ValueError("output_shift is not supported by runtime capability")
    require_uint(config.output_offset, "output_offset", 0xFFFF)
    return config


# 校验FMAC功能和P/Q抽头数量，并限制反馈抽头只用于IIR。
def validate_function(
    function: FmacFunction,
    feedforward_taps: int,
    feedback_taps: int,
    capabilities: FmacCapabilities,
) -> tuple[FmacFunction, int, int]:
    if not isinstance(function, FmacFunction):
        raise TypeError("function must be FmacFunction")
    feedforward = require_uint(
        feedforward_taps,
        "feedforward_taps",
        capabilities.max_feedforward_taps,
        nonzero=True,
    )
    feedback = require_uint(
        feedback_taps,
        "feedback_taps",
        capabilities.max_feedback_taps,
    )
    if function is not FmacFunction.IIR and feedback != 0:
        raise ValueError("feedback_taps is valid only for IIR")
    return function, feedforward, feedback


# 校验Resource数据动作的句柄、偏移、数量和公共数据格式。
def validate_data_action(
    handle: int,
    offset: int,
    count: int,
    format_: FmacDataFormat,
    capabilities: FmacCapabilities,
) -> tuple[int, int, int, FmacDataFormat]:
    if not isinstance(format_, FmacDataFormat):
        raise TypeError("format must be FmacDataFormat")
    return (
        require_uint(handle, "handle", 0xFFFFFFFF, nonzero=True),
        require_uint(offset, "offset", 0xFFFFFFFF),
        require_uint(count, "count", capabilities.max_transfer_items, nonzero=True),
        format_,
    )


# 按Runtime Capability校验非空IRQ Source集合，拒绝未知Source位。
def validate_irq_events(events: FmacIrqEvent, capabilities: FmacCapabilities) -> FmacIrqEvent:
    if not isinstance(events, FmacIrqEvent) or events == 0:
        raise ValueError("events must be a nonempty FmacIrqEvent")
    if int(events) & ~int(capabilities.irq_events):
        raise ValueError("events contain bits absent from runtime capability")
    return events


# 校验FMAC自身DMA Request Gate位；NONE用于显式关闭全部Gate。
def validate_dma_requests(requests: FmacDmaRequest) -> FmacDmaRequest:
    if not isinstance(requests, FmacDmaRequest) or int(requests) & ~int(FmacDmaRequest.ALL):
        raise ValueError("requests contain unknown FMAC DMA request bits")
    return requests
