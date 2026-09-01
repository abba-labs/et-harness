# SPINLOCK P2 Formal Case。
# 职责：验证两个硬件 Master 的竞争、交接、Owner 保护和 Release 作用域。
# 边界：只调用稳定 SPINLOCK Driver，不访问芯片 Core 编号、Mailbox 或寄存器。
# 依赖：需要部署已验证的片内 Peer，并由 Runtime Capability 发布 Peer 能力。

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.resource import ResourceDriver
from ...drivers.spinlock import (
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobSnapshot,
    SpinlockPeerJobState,
    SpinlockPeerJobType,
    SpinlockPeerResult,
)
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import SpinlockCaseSupport

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spinlock")]

PEER_STATE_TIMEOUT_S = 5.0
PEER_STATE_POLL_INTERVAL_S = 0.005


# 等待 Peer 到达指定状态；固定间隔只用于轮询让步，最终同步依据始终是硬件状态。
def _wait_peer_state(
    support: SpinlockCaseSupport,
    expected_states: Iterable[SpinlockPeerJobState],
) -> SpinlockPeerJobSnapshot:

    expected = frozenset(expected_states)
    deadline = time.monotonic() + PEER_STATE_TIMEOUT_S
    snapshot = support.spinlock.peer_job_snapshot_get()

    while snapshot.state not in expected and time.monotonic() < deadline:
        time.sleep(PEER_STATE_POLL_INTERVAL_S)
        snapshot = support.spinlock.peer_job_snapshot_get()

    return snapshot


# 仅在 Peer Job 仍活动时请求中止，避免清理阶段覆盖已经完成的结果。
def _abort_peer_if_active(support: SpinlockCaseSupport) -> None:

    snapshot = support.spinlock.peer_job_snapshot_get()
    if snapshot.state in {
        SpinlockPeerJobState.STARTED,
        SpinlockPeerJobState.WAITING,
        SpinlockPeerJobState.HOLDING,
    }:
        support.spinlock.peer_job_control(SpinlockPeerControl.ABORT)


# 返回本组双 Master Case 的显式恢复动作。
def _cleanup_actions(
    support: SpinlockCaseSupport,
    resource_driver: ResourceDriver,
) -> tuple[CleanupAction, ...]:

    return (
        ("SPINLOCK peer abort", lambda: _abort_peer_if_active(support)),
        ("SPINLOCK global release", support.spinlock.global_release),
        (
            "SPINLOCK disable",
            lambda: support.spinlock.configure(enabled=False, mode=SpinlockMode.ONE_STEP),
        ),
        ("Resource pool reset", resource_driver.reset),
    )


# 读取Peer就绪状态及双方Master ID，最终身份结论由Case显式断言。
def _master_pair_snapshot(support: SpinlockCaseSupport) -> tuple[int, int, bool]:

    peer = support.spinlock.peer_status_get()
    local_master = support.spinlock.local_master_id_get()

    return local_master, peer.master_id, peer.ready


# 测试 Feature：
# 1. SPINLOCK ONE_STEP/TWO_STEP Try 竞争。
# 2. Master Owner 保护及 Owner 释放后的恢复获取。
#
# 测试方法：
# 1. 本地 Master 获取 Resource，Peer 对同一 Resource 执行有界 TRY。
# 2. 确认 Peer 返回 BUSY 且 Owner 不变，再由本地 Master 释放。
# 3. Peer 再次 TRY 并保持持锁，确认 Owner 切换后命令 Peer 释放。
#
# 通过条件：
# 1. 两种模式下，竞争期间 Peer 均不能接管本地 Master 的 Resource。
# 2. 原 Owner 释放后 Peer 均能获取，Owner 为已验证的 Peer Master。
@pytest.mark.parametrize("mode", (SpinlockMode.ONE_STEP, SpinlockMode.TWO_STEP), ids=("one", "two"))
def test_spinlock_p2_001_try_contention_and_recovery(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    mode: SpinlockMode,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：在首次配置前建立 SPINLOCK 和 Resource Pool 的独立基线。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    process_id = 1
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=mode)
    local_master, peer_master, peer_ready = _master_pair_snapshot(support)
    assert peer_ready is True
    assert peer_master != local_master

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：本地 Master 先持锁，再让 Peer 对同一 Resource 执行一次 TRY。
        assert support.spinlock.resource_acquire_try(resource_id, process_id=process_id)
        support.spinlock.peer_job_start(
            SpinlockPeerJobType.TRY_HOLD,
            mode=mode,
            resource_id=resource_id,
            process_id=process_id + 1,
        )
        contended = _wait_peer_state(support, {SpinlockPeerJobState.DONE})
        contended_owner = support.spinlock.resource_snapshot_get(resource_id)

        record_observation(
            record_property,
            key="peer_try_while_owned",
            value=contended.result.name,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.RESULT",
        )
        record_observation(
            record_property,
            key="owner_while_contended",
            value=contended_owner.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )

        assert contended.state is SpinlockPeerJobState.DONE
        assert contended.result is SpinlockPeerResult.BUSY
        assert contended_owner.locked is True
        assert contended_owner.master_id == local_master

        # 刺激：原 Owner 释放后，Peer 再次 TRY 并保持持锁供主核读取 Owner。
        support.spinlock.resource_release(resource_id, process_id=process_id)
        support.spinlock.peer_job_start(
            SpinlockPeerJobType.TRY_HOLD,
            mode=mode,
            resource_id=resource_id,
            process_id=process_id + 1,
        )
        recovered = _wait_peer_state(support, {SpinlockPeerJobState.HOLDING})
        recovered_owner = support.spinlock.resource_snapshot_get(resource_id)

        record_observation(
            record_property,
            key="peer_try_after_release",
            value=recovered.result.name,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.RESULT",
        )
        record_observation(
            record_property,
            key="owner_after_handoff",
            value=recovered_owner.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )

        assert recovered.state is SpinlockPeerJobState.HOLDING
        assert recovered.result is SpinlockPeerResult.ACQUIRED
        assert recovered_owner.locked is True
        assert recovered_owner.master_id == peer_master

        # 恢复：命令 Peer 由原执行实体释放 Resource，并等待 Job 完整结束。
        support.spinlock.peer_job_control(SpinlockPeerControl.RELEASE)
        released = _wait_peer_state(support, {SpinlockPeerJobState.DONE})
        assert released.state is SpinlockPeerJobState.DONE
        assert released.result is SpinlockPeerResult.RELEASED
        assert support.spinlock.flag_snapshot_get().is_locked(resource_id) is False

    write_json_result(
        et_artifact_dir / f"spinlock_p2_001_try_contention_and_recovery_{mode.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "mode": mode.name,
            "local_master": local_master,
            "peer_master": peer_master,
            "contended_result": contended.result.name,
            "recovered_result": recovered.result.name,
        },
    )


# 测试 Feature：
# 1. SPINLOCK ONE_STEP/TWO_STEP 等待获取。
# 2. Owner 释放后的单次所有权交接。
#
# 测试方法：
# 1. 本地 Master 持锁后启动 Peer BLOCKING_HOLD Job。
# 2. 读取 WAITING 和 ENTER_COUNT=0，证明 Peer 尚未进入临界区。
# 3. 本地 Master 释放后等待 Peer 进入 HOLDING，再确认 Owner 和进入次数。
#
# 通过条件：
# 1. 原 Owner 释放前 Peer 保持 WAITING，Resource Owner 不变。
# 2. 释放后 Peer 只进入一次，Owner 切换为 Peer Master。
@pytest.mark.parametrize("mode", (SpinlockMode.ONE_STEP, SpinlockMode.TWO_STEP), ids=("one", "two"))
def test_spinlock_p2_002_blocking_handoff(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    mode: SpinlockMode,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：选择一个代表 Resource，并验证两个执行实体的硬件 Master 映射。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    process_id = 3
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=mode)
    local_master, peer_master, peer_ready = _master_pair_snapshot(support)
    assert peer_ready is True
    assert peer_master != local_master

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：本地 Master 持锁，Peer 进入可查询且可终止的等待状态。
        assert support.spinlock.resource_acquire_try(resource_id, process_id=process_id)
        support.spinlock.peer_job_start(
            SpinlockPeerJobType.BLOCKING_HOLD,
            mode=mode,
            resource_id=resource_id,
            process_id=process_id + 1,
        )
        waiting = _wait_peer_state(support, {SpinlockPeerJobState.WAITING})
        owner_before = support.spinlock.resource_snapshot_get(resource_id)

        record_observation(
            record_property,
            key="peer_state_before_release",
            value=waiting.state.name,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.STATE",
        )
        record_observation(
            record_property,
            key="peer_enter_count_before_release",
            value=waiting.enter_count,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.ENTER_COUNT",
        )

        assert waiting.state is SpinlockPeerJobState.WAITING
        assert waiting.enter_count == 0
        assert owner_before.master_id == local_master

        # 刺激：原 Owner 释放后，等待 Peer 完成一次且仅一次的所有权交接。
        support.spinlock.resource_release(resource_id, process_id=process_id)
        holding = _wait_peer_state(support, {SpinlockPeerJobState.HOLDING})
        owner_after = support.spinlock.resource_snapshot_get(resource_id)

        record_observation(
            record_property,
            key="peer_enter_count_after_release",
            value=holding.enter_count,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.ENTER_COUNT",
        )
        record_observation(
            record_property,
            key="owner_after_handoff",
            value=owner_after.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )

        assert holding.state is SpinlockPeerJobState.HOLDING
        assert holding.enter_count == 1
        assert owner_after.master_id == peer_master

        # 恢复：由 Peer 释放其持有的 Resource。
        support.spinlock.peer_job_control(SpinlockPeerControl.RELEASE)
        released = _wait_peer_state(support, {SpinlockPeerJobState.DONE})
        assert released.state is SpinlockPeerJobState.DONE
        assert support.spinlock.flag_snapshot_get().is_locked(resource_id) is False

    write_json_result(
        et_artifact_dir / f"spinlock_p2_002_blocking_handoff_{mode.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "mode": mode.name,
            "local_master": local_master,
            "peer_master": peer_master,
            "enter_count": holding.enter_count,
        },
    )


# 测试 Feature：
# 1. SPINLOCK Master Owner 释放保护。
#
# 测试方法：
# 1. 本地 Master 在 ONE_STEP/TWO_STEP 下获取同一代表 Resource。
# 2. 命令非 Owner Peer 对该 Resource 执行 RELEASE_ONCE。
# 3. 比较释放前后 Flag、Master 和 Process 信息，再由原 Owner 正常释放。
#
# 通过条件：
# 1. Peer Release 后 Resource 仍锁定，Owner 信息逐项不变。
# 2. 原 Owner Release 后对应 Flag 清零。
@pytest.mark.parametrize("mode", (SpinlockMode.ONE_STEP, SpinlockMode.TWO_STEP), ids=("one", "two"))
def test_spinlock_p2_003_non_owner_release_protection(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    mode: SpinlockMode,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：本地 Master 成为明确 Owner，Peer 仅执行一次非 Owner Release。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    process_id = 5
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=mode)
    local_master, peer_master, peer_ready = _master_pair_snapshot(support)
    assert peer_ready is True
    assert peer_master != local_master

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：获取并记录完整 Owner 快照。
        assert support.spinlock.resource_acquire_try(resource_id, process_id=process_id)
        before = support.spinlock.resource_snapshot_get(resource_id)

        # 刺激：由非 Owner Peer 提交相同 Resource/Process 的 Release。
        support.spinlock.peer_job_start(
            SpinlockPeerJobType.RELEASE_ONCE,
            mode=mode,
            resource_id=resource_id,
            process_id=process_id,
        )
        peer_release = _wait_peer_state(support, {SpinlockPeerJobState.DONE})
        after = support.spinlock.resource_snapshot_get(resource_id)

        record_observation(
            record_property,
            key="owner_before_peer_release",
            value=before.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )
        record_observation(
            record_property,
            key="owner_after_peer_release",
            value=after.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )
        record_observation(
            record_property,
            key="locked_after_peer_release",
            value=after.locked,
            source="dut",
            endpoint="RESOURCE_INFO.LOCKED",
        )

        assert peer_release.state is SpinlockPeerJobState.DONE
        assert peer_release.result is SpinlockPeerResult.RELEASED
        assert before.master_id == local_master
        assert after == before

        # 恢复：只有原 Owner 的 Release 应使对应 Flag 清零。
        support.spinlock.resource_release(resource_id, process_id=process_id)
        released = support.spinlock.flag_snapshot_get().is_locked(resource_id)
        record_observation(
            record_property,
            key="flag_after_owner_release",
            value=released,
            source="dut",
            endpoint="RESOURCE_FLAGS[RESOURCE_ID]",
        )
        assert released is False

    write_json_result(
        et_artifact_dir / f"spinlock_p2_003_non_owner_release_protection_{mode.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "mode": mode.name,
            "before_master": before.master_id,
            "after_master": after.master_id,
            "locked_after_peer_release": after.locked,
        },
    )


# 测试 Feature：
# 1. 当前 Master Batch Release 范围。
# 2. 全 Master Global Release 范围。
#
# 测试方法：
# 1. 本地 Master 获取两个 Resource，Peer 获取第三个 Resource 并保持 HOLDING。
# 2. 本地执行 Batch Release，确认只清除本地两个 Resource。
# 3. 执行 Global Release，确认三个 Resource 全部清零。
#
# 通过条件：
# 1. Batch 不影响 Peer 持有的 Resource 和 Owner。
# 2. Global 能清除两个 Master 的全部测试 Resource。
def test_spinlock_p2_004_batch_and_global_scope(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：至少三个 Resource 才能形成两个 Master 的独立占用分组。
    support = spinlock_support_for(spinlock_instance_id)
    assert support.runtime.resource_count >= 3
    local_resources = (0, 1)
    peer_resource = 2
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
    local_master, peer_master, peer_ready = _master_pair_snapshot(support)
    assert peer_ready is True
    assert peer_master != local_master

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：本地占用两个 Resource，Peer 独立占用第三个并保持持锁。
        for resource_id in local_resources:
            assert support.spinlock.resource_acquire_try(resource_id)

        support.spinlock.peer_job_start(
            SpinlockPeerJobType.HOLD,
            mode=SpinlockMode.ONE_STEP,
            resource_id=peer_resource,
        )
        holding = _wait_peer_state(support, {SpinlockPeerJobState.HOLDING})
        assert holding.state is SpinlockPeerJobState.HOLDING
        peer_before = support.spinlock.resource_snapshot_get(peer_resource)
        assert peer_before.master_id == peer_master

        # 刺激：当前 Master 的 Batch Release 只能清除本地分组。
        support.spinlock.batch_release()
        after_batch = support.spinlock.flag_snapshot_get()
        peer_state = support.spinlock.peer_job_snapshot_get()
        peer_after_batch = support.spinlock.resource_snapshot_get(peer_resource)

        record_observation(
            record_property,
            key="flags_low_after_batch",
            value=after_batch.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high_after_batch",
            value=after_batch.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )
        record_observation(
            record_property,
            key="peer_job_state_after_batch",
            value=peer_state.state.name,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.STATE",
        )
        record_observation(
            record_property,
            key="peer_owner_after_batch",
            value=peer_after_batch.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )

        assert all(not after_batch.is_locked(item) for item in local_resources)
        assert after_batch.is_locked(peer_resource) is True
        assert peer_state.state is SpinlockPeerJobState.HOLDING
        assert peer_after_batch.master_id == peer_master

        # 刺激：Global Release 应清除包括 Peer Owner 在内的全部 Resource。
        support.spinlock.global_release()
        after_global = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="flags_low_after_global",
            value=after_global.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high_after_global",
            value=after_global.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )

        assert after_global.low == 0
        assert after_global.high == 0

        # 恢复：中止仍在等待控制的 Peer Job，使下一 Case 从 IDLE 语义重新开始。
        support.spinlock.peer_job_control(SpinlockPeerControl.ABORT)
        aborted = _wait_peer_state(support, {SpinlockPeerJobState.ABORTED})
        assert aborted.state is SpinlockPeerJobState.ABORTED

    write_json_result(
        et_artifact_dir / "spinlock_p2_004_batch_and_global_scope.json",
        {
            "measurement_schema": "et.measurement.v1",
            "local_resources": local_resources,
            "peer_resource": peer_resource,
            "peer_master": peer_master,
            "flags_after_batch": {"low": after_batch.low, "high": after_batch.high},
            "flags_after_global": {"low": after_global.low, "high": after_global.high},
        },
    )
