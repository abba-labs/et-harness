# Framework Validation测试模块。
#
# 职责：验证test_driver_commands 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.dma import (
    CAPABILITIES,
    DMA_SERVICE_ID,
    DmaCommand,
    DmaConfig,
    DmaDriver,
    DmaFeature,
    DmaIrqEvent,
)


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes, bool]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ) -> tuple[ServiceMessage, object]:
        self.calls.append((service_id, int(command_id), instance_id, body, retry_safe))
        response_body = b""
        if command_id == DmaCommand.CAPABILITIES_GET:
            response_body = CAPABILITIES.pack(
                int(DmaFeature.MEMORY_TO_MEMORY),
                4,
                1024,
                0,
                0,
                int(DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.ERROR),
            )
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response_body,
            ),
            object(),
        )


def test_configure_keeps_service_command_instance_and_64_byte_body() -> None:
    target = _Target()
    driver = DmaDriver(target, instance_id=2)  # type: ignore[arg-type]
    config = DmaConfig(
        channel=1,
        source_address=0x20400000,
        destination_address=0x20400100,
        transfer_count=16,
    )

    driver.configure(config)

    assert target.calls == [
        (
            DMA_SERVICE_ID,
            int(DmaCommand.CHANNEL_CONFIGURE),
            2,
            config.encode(),
            False,
        )
    ]


def test_runtime_capability_cache_limits_atomic_channel_mask() -> None:
    target = _Target()
    driver = DmaDriver(target)  # type: ignore[arg-type]

    capabilities = driver.capabilities_get()
    driver.start_channels(0b1111)

    assert capabilities.channel_count == 4
    assert target.calls[0][1] == int(DmaCommand.CAPABILITIES_GET)
    assert target.calls[0][4] is True
    assert target.calls[1] == (
        DMA_SERVICE_ID,
        int(DmaCommand.CHANNELS_START),
        0,
        b"\x0f\x00\x00\x00",
        False,
    )
