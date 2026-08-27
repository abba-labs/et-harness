# DMA PC Driver Package 的__init__层。
#
# 职责：提供 DMA 的稳定公共导入入口。
# 边界：只导出已批准公共 API，不承载业务逻辑或跨 IP 编排。
# 依赖：仅依赖 dma Driver Package 内部的稳定公共定义。

from __future__ import annotations

from .codec import (
    CAPABILITIES,
    CHANNEL,
    CHANNEL_SNAPSHOT,
    CHANNEL_STATUS,
    COMPONENT_SNAPSHOT,
    DMA_CONFIG,
    INTERRUPT_CONTROL,
    INTERRUPT_SNAPSHOT,
    IRQ_ENABLE,
    IRQ_ENABLE_RESPONSE,
    IRQ_EVENTS,
    IRQ_RESULT,
    LLI_DESCRIPTOR_LOCATION,
    LLI_DESCRIPTOR_LOCATION_V2,
    SOFTWARE_HANDSHAKE_REQUEST,
    TIMING_SNAPSHOT,
)
from .codec import encode_config as _encode_config
from .contract import DMA_SERVICE_ID, DmaCommand
from .driver import DmaDriver
from .models import (
    DmaAccessView,
    DmaAddressMode,
    DmaBurst,
    DmaCapabilities,
    DmaChannelSnapshot,
    DmaChannelStatus,
    DmaComponentSnapshot,
    DmaConfigFlag,
    DmaFeature,
    DmaFifoMode,
    DmaHandshakeMode,
    DmaHandshakePolarity,
    DmaHandshakeTarget,
    DmaInterruptSnapshot,
    DmaIrqEvent,
    DmaIrqResult,
    DmaSoftwareRequestKind,
    DmaTimingSnapshot,
    DmaTransferType,
    DmaUpdateMode,
    DmaWidth,
)
from .models import DmaConfig as _DmaConfigModel


# 兼容旧公开 API 的 DMA 配置对象。
#
# 稳定字段定义位于 ``models.py``；旧版 ``encode()`` 入口保留在 Package
# Facade，并委托给纯 Codec，以保证现有调用方与 Golden Bytes 不变。
class DmaConfig(_DmaConfigModel):
    __slots__ = ()

    # 按已发布 64-Byte Wire Contract 编码当前配置。
    def encode(self) -> bytes:

        return _encode_config(self)


__all__ = [
    "CAPABILITIES",
    "CHANNEL",
    "CHANNEL_SNAPSHOT",
    "CHANNEL_STATUS",
    "COMPONENT_SNAPSHOT",
    "DMA_CONFIG",
    "DMA_SERVICE_ID",
    "INTERRUPT_CONTROL",
    "INTERRUPT_SNAPSHOT",
    "IRQ_ENABLE",
    "IRQ_ENABLE_RESPONSE",
    "IRQ_EVENTS",
    "IRQ_RESULT",
    "LLI_DESCRIPTOR_LOCATION",
    "LLI_DESCRIPTOR_LOCATION_V2",
    "SOFTWARE_HANDSHAKE_REQUEST",
    "TIMING_SNAPSHOT",
    "DmaAccessView",
    "DmaAddressMode",
    "DmaBurst",
    "DmaCapabilities",
    "DmaChannelSnapshot",
    "DmaChannelStatus",
    "DmaCommand",
    "DmaComponentSnapshot",
    "DmaConfig",
    "DmaConfigFlag",
    "DmaDriver",
    "DmaFeature",
    "DmaFifoMode",
    "DmaHandshakeMode",
    "DmaHandshakePolarity",
    "DmaHandshakeTarget",
    "DmaInterruptSnapshot",
    "DmaIrqEvent",
    "DmaIrqResult",
    "DmaSoftwareRequestKind",
    "DmaTransferType",
    "DmaTimingSnapshot",
    "DmaUpdateMode",
    "DmaWidth",
]
