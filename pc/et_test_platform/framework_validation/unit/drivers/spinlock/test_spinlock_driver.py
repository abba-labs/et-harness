# SPINLOCK Contract、Codec 和 Driver 单元测试。
# 职责：固定 Wire 布局、严格解码、安全快照和原子 Driver 调用。
# 边界：不访问真实硬件，不替代 Formal HIL Case。
# 依赖：仅依赖SPINLOCK公开Driver模块、协议模型和本文件测试替身。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage, Status
from et_test_platform.core.errors import ProtocolError, TargetRejected
from et_test_platform.drivers.spinlock import (
    SPINLOCK_SERVICE_ID,
    SpinlockClearScope,
    SpinlockCommand,
    SpinlockDriver,
    SpinlockFeature,
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobState,
    SpinlockPeerJobType,
    SpinlockPeerResult,
)
from et_test_platform.drivers.spinlock.codec import (
    decode_capabilities,
    decode_resource_snapshot,
)
from et_test_platform.drivers.spinlock.contract import (
    CAPABILITIES_STRUCT,
    CONFIG_STRUCT,
    FLAG_SNAPSHOT_STRUCT,
    LOCAL_STRESS_RESPONSE_STRUCT,
    MASTER_ID_STRUCT,
    PEER_JOB_SNAPSHOT_STRUCT,
    PEER_STATUS_STRUCT,
    RESOURCE_SNAPSHOT_STRUCT,
    SHARED_SNAPSHOT_STRUCT,
    SPINLOCK_SERVICE_API_VERSION,
)


# 提供可记录 SPINLOCK 原子请求并返回固定硬件事实的 Target 替身。
class _Target:
    def __init__(self) -> None:

        self.calls: list[tuple[int, int, int, bytes, bool]] = []
        self.busy_once = False

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ):

        self.calls.append((service_id, command_id, instance_id, body, retry_safe))
        if command_id == int(SpinlockCommand.RESOURCE_ACQUIRE_TRY) and self.busy_once:
            self.busy_once = False
            raise TargetRejected(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                status=int(Status.BUSY),
            )
        responses = {
            int(SpinlockCommand.CAPABILITIES_GET): CAPABILITIES_STRUCT.pack(
                SPINLOCK_SERVICE_API_VERSION,
                CAPABILITIES_STRUCT.size,
                int(sum(SpinlockFeature)),
                64,
                16,
            ),
            int(SpinlockCommand.CONFIG_SNAPSHOT_GET): CONFIG_STRUCT.pack(1, 0),
            int(SpinlockCommand.LOCAL_MASTER_ID_GET): MASTER_ID_STRUCT.pack(2),
            int(SpinlockCommand.FLAG_SNAPSHOT_GET): FLAG_SNAPSHOT_STRUCT.pack(1, 0),
            int(SpinlockCommand.RESOURCE_SNAPSHOT_GET): RESOURCE_SNAPSHOT_STRUCT.pack(
                1,
                1,
                1,
                0,
                2,
                3,
            ),
            int(SpinlockCommand.PEER_STATUS_GET): PEER_STATUS_STRUCT.pack(1, 0, 3),
            int(SpinlockCommand.PEER_JOB_SNAPSHOT_GET): PEER_JOB_SNAPSHOT_STRUCT.pack(
                int(SpinlockPeerJobState.HOLDING),
                int(SpinlockPeerResult.ACQUIRED),
                3,
                1,
                0,
            ),
            int(SpinlockCommand.LOCAL_STRESS_RUN): LOCAL_STRESS_RESPONSE_STRUCT.pack(100),
            int(SpinlockCommand.SHARED_SNAPSHOT_GET): SHARED_SNAPSHOT_STRUCT.pack(200, 0),
        }
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=responses.get(command_id, b""),
            ),
            object(),
        )


# SPINLOCK 命令、枚举和固定 Wire 尺寸必须与 Firmware 公开合同一致。
def test_spinlock_numeric_and_wire_contract() -> None:

    assert [int(mode) for mode in SpinlockMode] == [0, 1]
    assert [int(scope) for scope in SpinlockClearScope] == [0, 1]
    assert CAPABILITIES_STRUCT.size == 12
    assert CONFIG_STRUCT.size == 4
    assert FLAG_SNAPSHOT_STRUCT.size == 8
    assert RESOURCE_SNAPSHOT_STRUCT.size == 8


# SPINLOCK Capability 与 Resource 快照必须拒绝未知位和无效 Owner 关系。
def test_spinlock_codec_rejects_invalid_semantics() -> None:

    valid = CAPABILITIES_STRUCT.pack(
        SPINLOCK_SERVICE_API_VERSION,
        12,
        int(sum(SpinlockFeature)),
        64,
        16,
    )
    assert decode_capabilities(valid).resource_count == 64

    with pytest.raises(ProtocolError, match="unknown feature"):
        decode_capabilities(
            CAPABILITIES_STRUCT.pack(SPINLOCK_SERVICE_API_VERSION, 12, 1 << 31, 64, 16)
        )
    with pytest.raises(ProtocolError, match="invalid limits"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(SPINLOCK_SERVICE_API_VERSION, 12, 0, 0, 16))
    with pytest.raises(ProtocolError, match="owner semantics"):
        decode_resource_snapshot(RESOURCE_SNAPSHOT_STRUCT.pack(0, 1, 0, 0, 2, 0))


# SPINLOCK Driver 必须保持实例、重试安全和 BUSY 到 False 的稳定语义。
def test_spinlock_driver_atomic_command_flow() -> None:

    target = _Target()
    spinlock = SpinlockDriver(target, instance_id=0)  # type: ignore[arg-type]

    capabilities = spinlock.capabilities_get()
    spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
    assert spinlock.config_snapshot_get().mode is SpinlockMode.ONE_STEP
    assert spinlock.local_master_id_get() == 2
    assert spinlock.resource_acquire_try(0) is True
    assert spinlock.flag_snapshot_get().is_locked(0) is True
    snapshot = spinlock.resource_snapshot_get(0)
    spinlock.resource_release(0)
    spinlock.clear_key_probe(SpinlockClearScope.CURRENT_MASTER_ALL, authorized=False)
    assert spinlock.peer_status_get().master_id == 3
    spinlock.peer_job_start(
        SpinlockPeerJobType.TRY_HOLD,
        mode=SpinlockMode.ONE_STEP,
        resource_id=0,
    )
    assert spinlock.peer_job_snapshot_get().state is SpinlockPeerJobState.HOLDING
    spinlock.peer_job_control(SpinlockPeerControl.RELEASE)
    spinlock.shared_stress_reset()
    assert spinlock.local_stress_run(0, 100) == 100
    assert spinlock.shared_snapshot_get().shared_counter == 200

    assert capabilities.resource_count == 64
    assert snapshot.master_id == 2 and snapshot.process_id == 3
    assert all(call[0] == SPINLOCK_SERVICE_ID and call[2] == 0 for call in target.calls)
    assert target.calls[0][-1] is True
    assert target.calls[1][-1] is False

    target.busy_once = True
    assert spinlock.resource_acquire_try(0) is False


# SPINLOCK Driver 必须在 I/O 前拒绝超出 Runtime Capability 的编号。
def test_spinlock_driver_rejects_invalid_ids_before_io() -> None:

    target = _Target()
    spinlock = SpinlockDriver(target, instance_id=0)  # type: ignore[arg-type]
    spinlock.capabilities_get()
    calls_before = len(target.calls)

    with pytest.raises(ValueError, match="resource_id"):
        spinlock.resource_acquire_try(64)
    with pytest.raises(ValueError, match="process_id"):
        spinlock.resource_acquire_try(0, process_id=16)

    assert len(target.calls) == calls_before
