# Framework Validation测试模块。
#
# 职责：验证test_lifecycle_scope 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.drivers.resource import RESOURCE_SERVICE_ID, ResourceCommand, ResourceDriver


class _Target:
    def __init__(self, *, fail_reset_call: int | None = None) -> None:
        self.calls: list[int] = []
        self.reset_calls = 0
        self.fail_reset_call = fail_reset_call

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ) -> tuple[ServiceMessage, object]:
        del body
        assert service_id == RESOURCE_SERVICE_ID
        command = int(command_id)
        self.calls.append(command)
        if command == int(ResourceCommand.RESET):
            self.reset_calls += 1
            if self.reset_calls == self.fail_reset_call:
                raise RuntimeError("reset failed")
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=b"",
            ),
            object(),
        )


def test_resource_pool_mode_resets_before_and_after_case() -> None:
    target = _Target()
    resource = ResourceDriver(target)  # type: ignore[arg-type]

    with resource.pool_mode():
        pass

    assert target.calls == [int(ResourceCommand.RESET), int(ResourceCommand.RESET)]


def test_resource_pool_mode_keeps_primary_and_cleanup_failure() -> None:
    target = _Target(fail_reset_call=2)
    resource = ResourceDriver(target)  # type: ignore[arg-type]

    with pytest.raises(OperationCleanupError) as captured, resource.pool_mode():
        raise RuntimeError("case failed")

    assert str(captured.value.primary_error) == "case failed"
    assert [failure.stage for failure in captured.value.cleanup_failures] == ["Resource pool reset"]
    assert target.calls == [int(ResourceCommand.RESET), int(ResourceCommand.RESET)]
