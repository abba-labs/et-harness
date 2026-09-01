# SYSCTRL PC Driver Package 的codec层。
#
# 职责：提供 SYSCTRL 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct

from .models import DmaEndpoint, DmaRequestRoute
from .validation import (
    require_nonzero_uint64,
    require_uint8,
    validate_request_route,
)

DMA_ROUTE = struct.Struct("<4BQ")
DMA_ROUTE_RELEASE = struct.Struct("<2B2x")
DMA_ROUTE_V2 = struct.Struct("<4B")


# 编码旧版 Endpoint/Instance/Address 请求，不改变既有 Wire。
def encode_dma_route_v1(
    controller: int,
    interface: int,
    endpoint: DmaEndpoint,
    instance: int,
    address: int,
) -> bytes:

    return DMA_ROUTE.pack(
        require_uint8(controller, "controller"),
        require_uint8(interface, "interface"),
        require_uint8(int(endpoint), "endpoint"),
        require_uint8(instance, "instance"),
        require_nonzero_uint64(address, "DMA endpoint address"),
    )


# 编码直接 Controller/Interface/Request ID 请求。
def encode_dma_route_v2(route: DmaRequestRoute) -> bytes:

    validate_request_route(route)
    return DMA_ROUTE_V2.pack(
        route.controller,
        route.interface,
        route.request_id,
        0,
    )


# 编码 DMAMUX Interface Release 请求。
def encode_dma_route_release(controller: int, interface: int) -> bytes:

    return DMA_ROUTE_RELEASE.pack(
        require_uint8(controller, "controller"),
        require_uint8(interface, "interface"),
    )
