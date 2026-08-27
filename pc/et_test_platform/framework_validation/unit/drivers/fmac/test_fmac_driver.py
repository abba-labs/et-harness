# FMAC PC Driver单元测试。
#
# 职责：验证FMAC Driver公开原子动作的请求映射和本地状态同步。
# 边界：使用本地假Target，不执行Firmware或硬件。
# 依赖：仅依赖FMAC Driver和公开Contract。

from et_test_platform.drivers.fmac.contract import FMAC_SERVICE_ID, FmacCommand
from et_test_platform.drivers.fmac.driver import FmacDriver


class _RecordingTarget:
    def __init__(self) -> None:
        self.requests: list[tuple[int, int, int, bytes, bool]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int,
        body: bytes,
        retry_safe: bool,
    ):
        self.requests.append((service_id, command_id, instance_id, body, retry_safe))
        return object(), object()


# 测试Feature：FMAC Service状态复位使用独立命令且同步清除PC配置标记。
#
# 测试方法：在假Target上调用一次state_reset并检查完整请求字段和Driver状态。
#
# 通过条件：发送STATE_RESET空请求、禁止安全重试，且Driver不再认为FMAC已配置。
def test_fmac_state_reset_request_and_local_state() -> None:

    target = _RecordingTarget()
    driver = FmacDriver(target, instance_id=2)
    driver._configured = True

    driver.state_reset()

    assert target.requests == [
        (FMAC_SERVICE_ID, int(FmacCommand.STATE_RESET), 2, b"", False),
    ]
    assert driver._configured is False
