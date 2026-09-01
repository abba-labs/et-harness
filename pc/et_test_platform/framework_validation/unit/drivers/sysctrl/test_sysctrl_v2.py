# Framework Validation测试模块。
#
# 职责：验证test_sysctrl_v2 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.sysctrl import (
    DMA_ROUTE,
    DMA_ROUTE_RELEASE,
    DMA_ROUTE_V2,
    SYSCTRL_SERVICE_ID,
    DmaEndpoint,
    DmaRequestRoute,
    SysctrlCommand,
    SysctrlDriver,
)


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, bytes]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ) -> tuple[ServiceMessage, object]:
        del instance_id, retry_safe
        self.calls.append((service_id, int(command_id), body))
        return ServiceMessage(service_id, command_id, 0, body=b""), object()


def test_sysctrl_v2_uses_new_command_and_four_byte_body() -> None:
    target = _Target()
    driver = SysctrlDriver(target)  # type: ignore[arg-type]

    driver.configure_dma_request_v2(0, 1, 194)
    driver.configure_route(DmaRequestRoute(1, 2, 197))

    assert DMA_ROUTE_V2.size == 4
    assert target.calls == [
        (
            SYSCTRL_SERVICE_ID,
            int(SysctrlCommand.DMA_REQUEST_CONFIGURE_V2),
            b"\x00\x01\xc2\x00",
        ),
        (
            SYSCTRL_SERVICE_ID,
            int(SysctrlCommand.DMA_REQUEST_CONFIGURE_V2),
            b"\x01\x02\xc5\x00",
        ),
    ]


def test_sysctrl_v1_and_release_wire_remain_stable() -> None:
    target = _Target()
    driver = SysctrlDriver(target)  # type: ignore[arg-type]

    driver.configure_dma_request(1, 2, DmaEndpoint.UART_RX, 3, 0x40502000)
    driver.release_dma_request(1, 2)

    assert DMA_ROUTE.size == 12
    assert DMA_ROUTE_RELEASE.size == 4
    assert target.calls == [
        (
            SYSCTRL_SERVICE_ID,
            int(SysctrlCommand.DMA_REQUEST_CONFIGURE),
            b"\x01\x02\x01\x03" + (0x40502000).to_bytes(8, "little"),
        ),
        (
            SYSCTRL_SERVICE_ID,
            int(SysctrlCommand.DMA_REQUEST_RELEASE),
            b"\x01\x02\x00\x00",
        ),
    ]
