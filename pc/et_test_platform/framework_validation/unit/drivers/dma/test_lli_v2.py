# Framework Validation测试模块。
#
# 职责：验证test_lli_v2 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.dma import (
    DMA_CONFIG,
    DMA_SERVICE_ID,
    LLI_DESCRIPTOR_LOCATION_V2,
    DmaCommand,
    DmaConfig,
    DmaDriver,
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
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=b"",
            ),
            object(),
        )


def test_lli_v2_appends_direct_address_and_reserved_bytes() -> None:
    target = _Target()
    driver = DmaDriver(target, instance_id=1)  # type: ignore[arg-type]
    config = DmaConfig(
        channel=2,
        source_address=0x20400000,
        destination_address=0x20401000,
        transfer_count=64,
        linked_list_address=0x20402000,
        source_update_mode=2,
        destination_update_mode=2,
    )

    driver.lli_descriptor_init_v2(0x20403000, config, is_last=True)

    assert LLI_DESCRIPTOR_LOCATION_V2.size == 16
    assert len(target.calls) == 1
    service_id, command_id, instance_id, body, retry_safe = target.calls[0]
    assert service_id == DMA_SERVICE_ID
    assert command_id == int(DmaCommand.LLI_DESCRIPTOR_INIT_V2)
    assert instance_id == 1
    assert retry_safe is True
    assert len(body) == DMA_CONFIG.size + LLI_DESCRIPTOR_LOCATION_V2.size == 80
    assert body[: DMA_CONFIG.size] == config.encode()
    assert LLI_DESCRIPTOR_LOCATION_V2.unpack(body[DMA_CONFIG.size :]) == (
        0x20403000,
        1,
    )
    assert body[-7:] == b"\x00" * 7


@pytest.mark.parametrize("address", [0, -1, True, 1 << 64])
def test_lli_v2_rejects_invalid_direct_address(address: object) -> None:
    target = _Target()
    driver = DmaDriver(target)  # type: ignore[arg-type]
    config = DmaConfig(
        channel=0,
        source_address=0x20400000,
        destination_address=0x20401000,
        transfer_count=1,
    )

    with pytest.raises(ValueError, match="descriptor address"):
        driver.lli_descriptor_init_v2(  # type: ignore[arg-type]
            address,
            config,
            is_last=False,
        )

    assert target.calls == []
