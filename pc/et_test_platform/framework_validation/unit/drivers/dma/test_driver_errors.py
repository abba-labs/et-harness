# Framework Validation测试模块。
#
# 职责：验证test_driver_errors 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.core.errors import RequestTimeout
from et_test_platform.drivers.dma import DmaCommand, DmaConfig, DmaDriver


class _ConfigureTimeoutTarget:
    def __init__(self, *, cleanup_fails: bool) -> None:
        self.cleanup_fails = cleanup_fails
        self.commands: list[int] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ) -> tuple[object, object]:
        del service_id, instance_id, body, retry_safe
        self.commands.append(int(command_id))
        if command_id == DmaCommand.CHANNEL_CONFIGURE:
            raise RequestTimeout("configure response lost")
        if self.cleanup_fails and command_id == DmaCommand.CHANNEL_DECONFIGURE:
            raise RuntimeError("deconfigure failed")
        return object(), object()


def _config() -> DmaConfig:
    return DmaConfig(
        channel=3,
        source_address=0x20400000,
        destination_address=0x20400100,
        transfer_count=4,
    )


def test_configure_timeout_still_attempts_idempotent_deconfigure() -> None:
    target = _ConfigureTimeoutTarget(cleanup_fails=False)
    driver = DmaDriver(target)  # type: ignore[arg-type]

    with pytest.raises(RequestTimeout, match="configure response lost"):
        driver.configure(_config())

    assert target.commands == [
        int(DmaCommand.CHANNEL_CONFIGURE),
        int(DmaCommand.CHANNEL_DECONFIGURE),
    ]


# Preserve the primary timeout and structured deconfigure cleanup failure.
def test_configure_timeout_keeps_cleanup_failure_observable() -> None:

    target = _ConfigureTimeoutTarget(cleanup_fails=True)
    driver = DmaDriver(target)  # type: ignore[arg-type]

    with pytest.raises(OperationCleanupError) as captured:
        driver.configure(_config())

    assert isinstance(captured.value.primary_error, RequestTimeout)
    assert len(captured.value.cleanup_failures) == 1
    cleanup = captured.value.cleanup_failures[0]
    assert cleanup.stage == "DMA channel deconfigure"
    assert isinstance(cleanup.error, RuntimeError)
