# DMA PC Driver Package 的validation层。
#
# 职责：提供 DMA 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from enum import IntEnum

from .models import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaConfigFlag,
    DmaFifoMode,
    DmaHandshakeMode,
    DmaHandshakePolarity,
    DmaTransferType,
    DmaUpdateMode,
    DmaWidth,
)


def _require_enum(value: object, enum_type: type[IntEnum], name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"DMA {name} must be an integer enum value")
    try:
        enum_type(value)
    except ValueError as exc:
        raise ValueError(f"DMA {name} is invalid") from exc


# 校验 DMA Config 中所有有限集合字段，拒绝未知 Wire 枚举和 Flag 位。
def validate_config_semantics(config: DmaConfig) -> None:

    enum_fields = (
        (config.transfer_type, DmaTransferType, "transfer_type"),
        (config.source_width, DmaWidth, "source_width"),
        (config.destination_width, DmaWidth, "destination_width"),
        (config.source_address_mode, DmaAddressMode, "source_address_mode"),
        (config.destination_address_mode, DmaAddressMode, "destination_address_mode"),
        (config.source_burst, DmaBurst, "source_burst"),
        (config.destination_burst, DmaBurst, "destination_burst"),
        (config.fifo_mode, DmaFifoMode, "fifo_mode"),
        (config.source_update_mode, DmaUpdateMode, "source_update_mode"),
        (config.destination_update_mode, DmaUpdateMode, "destination_update_mode"),
        (config.source_handshake_mode, DmaHandshakeMode, "source_handshake_mode"),
        (
            config.destination_handshake_mode,
            DmaHandshakeMode,
            "destination_handshake_mode",
        ),
        (
            config.source_handshake_polarity,
            DmaHandshakePolarity,
            "source_handshake_polarity",
        ),
        (
            config.destination_handshake_polarity,
            DmaHandshakePolarity,
            "destination_handshake_polarity",
        ),
    )
    for value, enum_type, name in enum_fields:
        _require_enum(value, enum_type, name)

    if isinstance(config.flags, bool) or not isinstance(config.flags, int):
        raise ValueError("DMA flags must be an integer flag mask")
    known_flags = int(
        DmaConfigFlag.SOURCE_GATHER | DmaConfigFlag.DESTINATION_SCATTER | DmaConfigFlag.INITIAL_DONE
    )
    if int(config.flags) < 0 or int(config.flags) & ~known_flags:
        raise ValueError("DMA flags contain unknown bits")


# 校验旧 Poll-Count 兼容入口的非零计数和正轮询间隔，非法输入立即拒绝。
def validate_start_wait(max_polls: int, poll_interval_s: float) -> None:

    if not 0 < max_polls <= 0xFFFFFFFF:
        raise ValueError("max_polls must be a nonzero uint32")
    if poll_interval_s <= 0:
        raise ValueError("poll_interval_s must be positive")


# 按运行时 Channel Count 校验原子启动掩码；空掩码或越界位立即拒绝。
def validate_channel_mask(channel_mask: int, channel_count: int) -> None:

    limit = (1 << channel_count) - 1
    if channel_mask <= 0 or channel_mask > limit:
        raise ValueError(f"DMA channel mask exceeds {channel_count} runtime channels")


# 校验旧版 LLI Resource Handle 是显式非零 uint32 整数。
def normalize_descriptor_handle(descriptor_handle: int) -> int:

    if isinstance(descriptor_handle, bool) or not isinstance(descriptor_handle, int):
        raise ValueError("DMA LLI descriptor handle must be an integer")
    if not 0 < descriptor_handle <= 0xFFFFFFFF:
        raise ValueError("DMA LLI descriptor handle must be a nonzero uint32")
    return descriptor_handle


# 校验 LLI Descriptor Offset 可以无损编码为 uint32。
def validate_descriptor_offset(descriptor_offset: int) -> None:

    if not 0 <= descriptor_offset <= 0xFFFFFFFF:
        raise ValueError("DMA LLI descriptor offset must fit uint32")


# 校验 V2 LLI Descriptor Address 是非零 uint64。
def validate_descriptor_address(descriptor_address: object) -> int:

    if isinstance(descriptor_address, bool) or not isinstance(descriptor_address, int):
        raise ValueError("DMA LLI descriptor address must be an integer")
    if not 0 < descriptor_address <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("DMA LLI descriptor address must fit nonzero uint64")
    return descriptor_address
