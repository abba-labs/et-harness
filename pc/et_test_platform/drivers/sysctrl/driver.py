# SYSCTRL PC Driver Package 的driver层。
#
# 职责：提供 SYSCTRL 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

from ...clients.target import TargetClient
from .codec import (
    decode_syscnt_routing,
    encode_dma_route_release,
    encode_dma_route_v1,
    encode_dma_route_v2,
    encode_syscnt_routing,
)
from .contract import SYSCTRL_SERVICE_ID, SyscntClockSource, SysctrlCommand
from .models import DmaEndpoint, DmaRequestRoute


# 配置芯片级 DMA Request 路由的单 Service 客户端。
class SysctrlDriver:
    def __init__(self, target: TargetClient) -> None:
        self._target = target

    # 只选择系统计数器时钟源，调用前Case必须停止计数器；不做跨IP动作。
    # 仅等待单次命令，不轮询；通信超时、固件拒绝和非法响应体均上抛。
    def syscnt_source_set(self, instance: int, source: SyscntClockSource) -> None:

        if isinstance(source, bool) or not isinstance(source, (int, SyscntClockSource)):
            raise ValueError("counter source must be INTERNAL or EXTERNAL")
        source = SyscntClockSource(source)
        message, _ = self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.SYSCNT_SOURCE_SET,
            body=encode_syscnt_routing(instance, int(source)),
        )
        if message.body:
            raise ValueError("SYSCTRL source SET returned an unexpected body")

    # 只配置系统Halt路由，不设置计数器HDBG，不控制CPU。
    # 仅等待单次响应，不轮询；超时、固件拒绝及响应错误直接上抛。
    def syscnt_halt_set(self, instance: int, *, enabled: bool) -> None:

        if not isinstance(enabled, bool):
            raise ValueError("counter halt route enabled must be bool")
        message, _ = self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.SYSCNT_HALT_SET,
            body=encode_syscnt_routing(instance, int(enabled)),
        )
        if message.body:
            raise ValueError("SYSCTRL halt SET returned an unexpected body")

    # 返回实际时钟源和Halt路由；不推断实际Hz或CPU是否已停止。
    # 单次只读请求，不等待状态切换；通信超时、固件拒绝及解码错误上抛。
    def syscnt_routing_get(self, instance: int) -> tuple[SyscntClockSource, bool]:

        message, _ = self._target.request(
            SYSCTRL_SERVICE_ID,
            SysctrlCommand.SYSCNT_ROUTING_GET,
            body=encode_syscnt_routing(instance),
            retry_safe=True,
        )
        return decode_syscnt_routing(message.body)

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
