# SPINLOCK P3 Formal Case。
# 职责：验证两个硬件 Master 对片内共享计数的长期互斥保护。
# 边界：只调用稳定 SPINLOCK Driver，不访问芯片共享地址或 Cache 控制。
# 依赖：需要目标适配提供双 Master Peer Job 和共享可见内存策略。

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.resource import ResourceDriver
from ...drivers.spinlock import (
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobState,
    SpinlockPeerJobType,
    SpinlockPeerResult,
)
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import SpinlockCaseSupport

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spinlock")]

SPINLOCK_STRESS_LOOP_COUNT = 10000
SPINLOCK_STRESS_TIMEOUT_S = 20.0
SPINLOCK_STRESS_POLL_INTERVAL_S = 0.005


# 等待 Peer 压力 Job 完成，以状态而不是固定延时作为同步依据。
def _wait_peer_done(support: SpinlockCaseSupport):

    deadline = time.monotonic() + SPINLOCK_STRESS_TIMEOUT_S
    snapshot = support.spinlock.peer_job_snapshot_get()

    while (
        snapshot.state
        not in {
            SpinlockPeerJobState.DONE,
            SpinlockPeerJobState.ABORTED,
            SpinlockPeerJobState.ERROR,
        }
        and time.monotonic() < deadline
    ):
        time.sleep(SPINLOCK_STRESS_POLL_INTERVAL_S)
        snapshot = support.spinlock.peer_job_snapshot_get()

    return snapshot


# 返回压力 Case 的显式恢复动作。
def _cleanup_actions(
    support: SpinlockCaseSupport,
    resource_driver: ResourceDriver,
) -> tuple[CleanupAction, ...]:

    def abort_if_active() -> None:
        snapshot = support.spinlock.peer_job_snapshot_get()
        if snapshot.state in {
            SpinlockPeerJobState.STARTED,
            SpinlockPeerJobState.WAITING,
            SpinlockPeerJobState.HOLDING,
        }:
            support.spinlock.peer_job_control(SpinlockPeerControl.ABORT)

    return (
        ("SPINLOCK peer abort", abort_if_active),
        ("SPINLOCK global release", support.spinlock.global_release),
        (
            "SPINLOCK disable",
            lambda: support.spinlock.configure(enabled=False, mode=SpinlockMode.ONE_STEP),
        ),
        ("Resource pool reset", resource_driver.reset),
    )


# 测试 Feature：
# 1. SPINLOCK 双 Master 临界区互斥。
#
# 测试方法：
# 1. 清零芯片适配提供的共享计数和违规计数，启动 Peer 压力 Job。
# 2. 本地 Master 使用同一 ONE_STEP Resource 执行相同循环次数。
# 3. 等待 Peer 完成后读取双方完成次数、共享计数和违规计数。
#
# 通过条件：
# 1. 两个 Master 都完成全部循环，共享计数等于两倍计划循环次数。
# 2. 临界区违规计数为零，最终 Resource 为空闲。
def test_spinlock_p3_001_dual_master_shared_counter_stress(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：验证 Peer 就绪和双 Master 映射，再建立共享压力基线。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
    peer = support.spinlock.peer_status_get()
    local_master = support.spinlock.local_master_id_get()
    assert peer.ready is True
    assert peer.master_id != local_master
    support.spinlock.shared_stress_reset()

    record_property("loop_count", SPINLOCK_STRESS_LOOP_COUNT)

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：先启动 Peer，再立即让本地 Master 运行同一 Resource 的压力循环。
        support.spinlock.peer_job_start(
            SpinlockPeerJobType.STRESS,
            mode=SpinlockMode.ONE_STEP,
            resource_id=resource_id,
            loop_count=SPINLOCK_STRESS_LOOP_COUNT,
        )
        local_completed = support.spinlock.local_stress_run(
            resource_id,
            SPINLOCK_STRESS_LOOP_COUNT,
        )
        peer_result = _wait_peer_done(support)
        shared = support.spinlock.shared_snapshot_get()
        final_flags = support.spinlock.flag_snapshot_get()

        # 观测：在断言前记录两端进度和共享硬件事实，失败时仍能回溯。
        record_property("dut_completed_count", local_completed)
        record_observation(
            record_property,
            key="peer_completed_count",
            value=peer_result.completed_count,
            source="peer",
            device_id="core1_peer",
            endpoint="PEER_JOB.COMPLETED_COUNT",
        )
        record_observation(
            record_property,
            key="shared_counter",
            value=shared.shared_counter,
            source="dut",
            endpoint="SHARED_STRESS.SHARED_COUNTER",
        )
        record_observation(
            record_property,
            key="violation_count",
            value=shared.violation_count,
            source="dut",
            endpoint="SHARED_STRESS.VIOLATION_COUNT",
        )

        assert peer_result.state is SpinlockPeerJobState.DONE
        assert peer_result.result is SpinlockPeerResult.COMPLETED
        assert local_completed == SPINLOCK_STRESS_LOOP_COUNT
        assert peer_result.completed_count == SPINLOCK_STRESS_LOOP_COUNT
        assert shared.shared_counter == 2 * SPINLOCK_STRESS_LOOP_COUNT
        assert shared.violation_count == 0
        assert final_flags.is_locked(resource_id) is False

    write_json_result(
        et_artifact_dir / "spinlock_p3_001_dual_master_shared_counter_stress.json",
        {
            "measurement_schema": "et.measurement.v1",
            "loop_count": SPINLOCK_STRESS_LOOP_COUNT,
            "local_master": local_master,
            "peer_master": peer.master_id,
            "local_completed": local_completed,
            "peer_completed": peer_result.completed_count,
            "shared_counter": shared.shared_counter,
            "violation_count": shared.violation_count,
        },
    )
