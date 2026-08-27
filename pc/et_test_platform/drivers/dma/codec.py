# DMA PC Driver Package 的codec层。
#
# 职责：提供 DMA 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct

from ...core.errors import ProtocolError
from .models import (
    DmaBurst,
    DmaCapabilities,
    DmaChannelSnapshot,
    DmaChannelStatus,
    DmaComponentSnapshot,
    DmaConfig,
    DmaFeature,
    DmaFifoMode,
    DmaHandshakeTarget,
    DmaInterruptSnapshot,
    DmaIrqEvent,
    DmaIrqResult,
    DmaSoftwareRequestKind,
    DmaTimingSnapshot,
)
from .validation import (
    validate_config_semantics,
    validate_descriptor_address,
)

DMA_CONFIG = struct.Struct("<16BQQIIQIIII")
CHANNEL = struct.Struct("<B3x")
IRQ_ENABLE = struct.Struct("<IBB2x")
IRQ_ENABLE_RESPONSE = struct.Struct("<IB3x")
IRQ_EVENTS = struct.Struct("<I")
IRQ_RESULT = struct.Struct("<IIII")
CHANNEL_STATUS = struct.Struct("<BB2xI")
CAPABILITIES = struct.Struct("<IHHIII")
COMPONENT_SNAPSHOT = struct.Struct("<12I")
INTERRUPT_SNAPSHOT = struct.Struct("<16I")
CHANNEL_SNAPSHOT = struct.Struct("<13I")
LLI_DESCRIPTOR_LOCATION = struct.Struct("<IIB3x")
LLI_DESCRIPTOR_LOCATION_V2 = struct.Struct("<QB7x")
INTERRUPT_CONTROL = struct.Struct("<IB3x")
SOFTWARE_HANDSHAKE_REQUEST = struct.Struct("<4B")
TIMING_SNAPSHOT = struct.Struct("<BB2xI")


# 验证稳定业务枚举后，将 DMA Config 编码为 64-Byte Wire Body。
def encode_config(config: DmaConfig) -> bytes:

    validate_config_semantics(config)
    source_handshake = int(config.source_handshake_mode) | (
        int(config.source_handshake_polarity) << 1
    )
    destination_handshake = int(config.destination_handshake_mode) | (
        int(config.destination_handshake_polarity) << 1
    )
    return DMA_CONFIG.pack(
        config.channel,
        int(config.transfer_type),
        config.priority,
        int(config.source_width),
        int(config.destination_width),
        int(config.source_address_mode),
        int(config.destination_address_mode),
        int(config.source_burst),
        int(config.destination_burst),
        int(config.fifo_mode),
        config.source_interface,
        config.destination_interface,
        int(config.source_update_mode),
        int(config.destination_update_mode),
        source_handshake,
        destination_handshake,
        config.source_address,
        config.destination_address,
        config.transfer_count,
        int(config.flags),
        config.linked_list_address,
        config.source_gather_interval,
        config.source_gather_count,
        config.destination_scatter_interval,
        config.destination_scatter_count,
    )


# 编码一个带三字节保留位的 DMA Channel。
def encode_channel(channel: int) -> bytes:

    return CHANNEL.pack(channel)


# 解码 DMA Start-to-IRQ 的目标 DWT 计时快照。
def decode_timing_snapshot(body: bytes) -> DmaTimingSnapshot:

    if len(body) != TIMING_SNAPSHOT.size:
        raise ProtocolError("DMA timing snapshot response length is invalid")
    complete, channel, elapsed_cycles = TIMING_SNAPSHOT.unpack(body)
    if complete not in (0, 1):
        raise ProtocolError("DMA timing snapshot contains a non-canonical Boolean")
    return DmaTimingSnapshot(
        complete=bool(complete),
        channel=channel,
        elapsed_cycles=elapsed_cycles,
    )


# 解码 FREE_CHANNEL_FIND Response。
def decode_free_channel(body: bytes) -> int:

    if len(body) != CHANNEL.size:
        raise ProtocolError("DMA free-channel response length is invalid")
    return CHANNEL.unpack(body)[0]


# 编码原子启动所用的 32-Bit Channel Mask。
def encode_channel_mask(channel_mask: int) -> bytes:

    return IRQ_EVENTS.pack(channel_mask)


# 解码并验证 CAPABILITIES_GET Response。
def decode_capabilities(body: bytes) -> DmaCapabilities:

    if len(body) != CAPABILITIES.size:
        raise ProtocolError("DMA CAPABILITIES_GET response length is invalid")
    (
        features,
        channel_count,
        max_transfer_count,
        max_gather_scatter_interval,
        max_gather_scatter_count,
        irq_events,
    ) = CAPABILITIES.unpack(body)
    if channel_count == 0 or max_transfer_count == 0:
        raise ProtocolError("DMA CAPABILITIES_GET returned invalid limits")
    return DmaCapabilities(
        features=DmaFeature(features),
        channel_count=channel_count,
        max_transfer_count=max_transfer_count,
        max_gather_scatter_interval=max_gather_scatter_interval,
        max_gather_scatter_count=max_gather_scatter_count,
        irq_events=DmaIrqEvent(irq_events),
    )


# 解码 COMPONENT_SNAPSHOT_GET Response。
def decode_component_snapshot(body: bytes) -> DmaComponentSnapshot:

    if len(body) != COMPONENT_SNAPSHOT.size:
        raise ProtocolError("DMA component snapshot length is invalid")
    values = COMPONENT_SNAPSHOT.unpack(body)
    return DmaComponentSnapshot(
        dma_id=values[0],
        component_id=values[1],
        channel_params=tuple(values[2:10]),
        multi_block_params=values[10],
        max_block_size_params=values[11],
    )


# 解码 INTERRUPT_SNAPSHOT_GET Response。
def decode_interrupt_snapshot(body: bytes) -> DmaInterruptSnapshot:

    if len(body) != INTERRUPT_SNAPSHOT.size:
        raise ProtocolError("DMA interrupt snapshot length is invalid")
    values = INTERRUPT_SNAPSHOT.unpack(body)
    return DmaInterruptSnapshot(
        raw=tuple(values[0:5]),
        status=tuple(values[5:10]),
        mask=tuple(values[10:15]),
        combined_status=values[15],
    )


# 解码 CHANNEL_SNAPSHOT_GET Response；稳定配置字段已由目标侧解码。
def decode_channel_snapshot(body: bytes) -> DmaChannelSnapshot:

    if len(body) != CHANNEL_SNAPSHOT.size:
        raise ProtocolError("DMA channel snapshot length is invalid")
    values = CHANNEL_SNAPSHOT.unpack(body)
    return DmaChannelSnapshot(
        source_address=values[0],
        destination_address=values[1],
        linked_list_address=values[2],
        control_low=values[3],
        control_high=values[4],
        config_low=values[5],
        config_high=values[6],
        source_gather=values[7],
        destination_scatter=values[8],
        source_burst=DmaBurst(values[9]),
        destination_burst=DmaBurst(values[10]),
        block_size=values[11],
        fifo_mode=DmaFifoMode(values[12]),
    )


# 编码旧版 LLI Resource Handle、Offset 与 Last Flag。
def encode_lli_descriptor_location(
    descriptor_handle: int,
    descriptor_offset: int,
    is_last: bool,
) -> bytes:

    return LLI_DESCRIPTOR_LOCATION.pack(
        descriptor_handle,
        descriptor_offset,
        int(is_last),
    )


# 编码 V2 LLI 直接 Descriptor Address 与 Last Flag。
def encode_lli_descriptor_location_v2(
    descriptor_address: int,
    is_last: bool,
) -> bytes:

    address = validate_descriptor_address(descriptor_address)
    return LLI_DESCRIPTOR_LOCATION_V2.pack(address, int(is_last))


# 把 Channel 与具名 IRQ Event Mask 编码为固定 8-Byte 中断控制 Body，不执行 I/O。
def encode_interrupt_control(channel: int, events: DmaIrqEvent) -> bytes:

    return INTERRUPT_CONTROL.pack(int(events), channel)


# 解码 CHANNEL_STATUS_GET Response，保持既有 Bool 转换规则。
def decode_channel_status(body: bytes) -> DmaChannelStatus:

    if len(body) != CHANNEL_STATUS.size:
        raise ProtocolError("DMA channel status response length is invalid")
    is_free, fifo_empty, events = CHANNEL_STATUS.unpack(body)
    return DmaChannelStatus(
        bool(is_free),
        bool(fifo_empty),
        DmaIrqEvent(events),
    )


# 编码 IRQ Enable 或 Combined IRQ Enable Request。
def encode_irq_enable(channel: int, events: DmaIrqEvent, priority: int) -> bytes:

    return IRQ_ENABLE.pack(int(events), channel, priority)


# 解码 IRQ Enable Response，并验证 Firmware 未改变请求。
def decode_irq_enable_response(
    body: bytes,
    requested_events: DmaIrqEvent,
    *,
    combined: bool,
) -> int:

    if len(body) != IRQ_ENABLE_RESPONSE.size:
        command_name = "IRQ_COMBINED_ENABLE" if combined else "IRQ_ENABLE"
        raise ProtocolError(f"DMA {command_name} response length is invalid")
    enabled, route_count = IRQ_ENABLE_RESPONSE.unpack(body)
    if combined:
        if enabled != int(requested_events) or route_count != 1:
            raise ProtocolError("DMA combined IRQ route is inconsistent")
    elif enabled != int(requested_events):
        raise ProtocolError("DMA IRQ_ENABLE changed requested events")
    return route_count


# 编码一个 32-Bit DMA IRQ Event Mask。
def encode_irq_events(events: DmaIrqEvent) -> bytes:

    return IRQ_EVENTS.pack(int(events))


# 解码 IRQ_RESULT_GET Response。
def decode_irq_result(body: bytes) -> DmaIrqResult:

    if len(body) != IRQ_RESULT.size:
        raise ProtocolError("DMA IRQ result response length is invalid")
    events, count, unexpected, overflow = IRQ_RESULT.unpack(body)
    return DmaIrqResult(
        DmaIrqEvent(events),
        count,
        unexpected,
        overflow,
    )


# 把 Channel、端点、请求种类和有效状态编码为固定 4-Byte 软件握手 Body。
def encode_software_handshake_request(
    channel: int,
    target: DmaHandshakeTarget,
    request_kind: DmaSoftwareRequestKind,
    active: bool,
) -> bytes:

    return SOFTWARE_HANDSHAKE_REQUEST.pack(
        channel,
        int(target),
        int(request_kind),
        int(active),
    )
