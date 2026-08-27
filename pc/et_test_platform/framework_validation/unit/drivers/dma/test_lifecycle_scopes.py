# Framework Validation测试模块。
#
# 职责：验证test_lifecycle_scopes 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.drivers.dma import DMA_SERVICE_ID, DmaCommand, DmaConfig, DmaDriver


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes]] = []
        self.failures: dict[int, Exception] = {}

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
        timeout_s: float | None = None,
    ) -> tuple[ServiceMessage, object]:
        del retry_safe, timeout_s
        assert service_id == DMA_SERVICE_ID
        command = int(command_id)
        self.calls.append((command, body))
        failure = self.failures.get(command)
        if failure is not None:
            raise failure
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=b"",
            ),
            object(),
        )


def _config(channel: int = 3) -> DmaConfig:
    return DmaConfig(
        channel=channel,
        source_address=0x20400000,
        destination_address=0x20401000,
        transfer_count=4,
    )


def test_dma_lifecycle_scopes_preserve_m2m_command_order() -> None:
    target = _Target()
    dma = DmaDriver(target, instance_id=1)  # type: ignore[arg-type]
    config = _config()

    with dma.controller_mode(), dma.configured_channel(config):
        dma.start(config.channel)

    assert [command for command, _ in target.calls] == [
        int(DmaCommand.CONTROLLER_ENABLE),
        int(DmaCommand.CHANNEL_CONFIGURE),
        int(DmaCommand.CHANNEL_START),
        int(DmaCommand.CHANNEL_STOP),
        int(DmaCommand.CHANNEL_DECONFIGURE),
        int(DmaCommand.CONTROLLER_DISABLE),
    ]


def test_dma_nested_scopes_keep_primary_and_all_cleanup_failures() -> None:
    target = _Target()
    target.failures[int(DmaCommand.CHANNEL_STOP)] = RuntimeError("stop failed")
    target.failures[int(DmaCommand.CONTROLLER_DISABLE)] = RuntimeError("disable failed")
    dma = DmaDriver(target)  # type: ignore[arg-type]
    config = _config(channel=0)

    with (
        pytest.raises(OperationCleanupError) as captured,
        dma.controller_mode(),
        dma.configured_channel(config),
    ):
        raise RuntimeError("case failed")

    assert str(captured.value.primary_error) == "case failed"
    assert [failure.stage for failure in captured.value.cleanup_failures] == [
        "DMA channel stop",
        "DMA controller disable",
    ]
    assert [command for command, _ in target.calls] == [
        int(DmaCommand.CONTROLLER_ENABLE),
        int(DmaCommand.CHANNEL_CONFIGURE),
        int(DmaCommand.CHANNEL_STOP),
        int(DmaCommand.CHANNEL_DECONFIGURE),
        int(DmaCommand.CONTROLLER_DISABLE),
    ]
