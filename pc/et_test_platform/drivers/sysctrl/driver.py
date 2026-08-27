# SYSCTRL PC Driver Package 的driver层。
#
# 职责：提供 SYSCTRL 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

from ...clients.target import TargetClient
from .codec import (
    encode_dma_route_release,
    encode_dma_route_v1,
    encode_dma_route_v2,
)
from .contract import SYSCTRL_SERVICE_ID, SysctrlCommand
from .models import DmaEndpoint, DmaRequestRoute


# 配置芯片级 DMA Request 路由的单 Service 客户端。
class SysctrlDriver:
    def __init__(self, target: TargetClient) -> None:
        self._target = target

    # 发送 configure dma request 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def configure_dma_request(
        self,
        controller: int,
        interface: int,
        endpoint: DmaEndpoint,
        instance: int,
        address: int,
    ) -> None:

        self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.DMA_REQUEST_CONFIGURE,
            body=encode_dma_route_v1(
                controller,
                interface,
                endpoint,
                instance,
                address,
            ),
        )

    # 发送 configure dma request v2 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def configure_dma_request_v2(
        self,
        controller: int,
        interface: int,
        request_id: int,
    ) -> None:

        route = DmaRequestRoute(controller, interface, request_id)
        self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.DMA_REQUEST_CONFIGURE_V2,
            body=encode_dma_route_v2(route),
        )

    # 发送 configure route 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def configure_route(self, route: DmaRequestRoute) -> None:

        self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.DMA_REQUEST_CONFIGURE_V2,
            body=encode_dma_route_v2(route),
        )

    # 发送 release dma request 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def release_dma_request(self, controller: int, interface: int) -> None:

        self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.DMA_REQUEST_RELEASE,
            body=encode_dma_route_release(controller, interface),
        )
