# SPINLOCK P0 Formal Case。
# 职责：验证配置、一步锁和两步 Process ID 的基础硬件链路。
# 边界：只通过稳定 Driver API 操作设备，不访问 Codec/Transport/Register。
# 依赖：依赖SPINLOCK Case Fixture、Resource Driver和Canonical Evidence接口。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.resource import ResourceDriver
from ...drivers.spinlock import SpinlockFeature, SpinlockMode
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import SpinlockCaseSupport

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spinlock")]


# 返回 SPINLOCK Case 的显式恢复动作；不隐藏配置、刺激、观测或断言。
def _cleanup_actions(
    support: SpinlockCaseSupport,
    resource_driver: ResourceDriver,
) -> tuple[CleanupAction, ...]:

    return (
        ("SPINLOCK global release", support.spinlock.global_release),
        (
            "SPINLOCK disable",
            lambda: support.spinlock.configure(enabled=False, mode=SpinlockMode.ONE_STEP),
        ),
        ("Resource pool reset", resource_driver.reset),
    )


# 测试 Feature：
# 1. SPINLOCK 模块 Enable/Disable 控制。
# 2. SPINLOCK ONE_STEP 与 TWO_STEP 模式配置读回。
#
# 测试方法：
# 1. 执行 Global Release 和 Resource Pool Reset，建立独立基线。
# 2. 依次配置 ONE_STEP、TWO_STEP 和 Disable，并读取 CONFIG 快照。
# 3. 保存每轮期望值和硬件读回值，不以命令成功代替配置证据。
#
# 通过条件：
# 1. 两种模式 Enable 后均准确读回，Disable 后 Enable 为 False。
# 2. Runtime Capability 明确发布两种模式和完整数量限制。
def test_spinlock_p0_001_config_modes(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：获取运行时能力，只使用能力发布的实例和限制。
    support = spinlock_support_for(spinlock_instance_id)
    required = SpinlockFeature.ONE_STEP | SpinlockFeature.TWO_STEP
    assert support.runtime.features & required == required
    assert support.runtime.resource_count > 0
    assert support.runtime.process_id_count > 0

    # 隔离：第一次 Feature 配置前释放全部锁并复位公共 Resource Pool。
    support.spinlock.global_release()
    resource_driver.reset()
    snapshots: list[dict[str, object]] = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：配置 ONE_STEP，并读取硬件实际接受的 Enable 和 Mode。
        support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
        one_step = support.spinlock.config_snapshot_get()
        snapshots.append({"expected": "ONE_STEP", "actual": one_step.mode.name})

        record_property("expected_enable", True)
        record_observation(
            record_property,
            key="actual_enable",
            value=one_step.enabled,
            source="dut",
            endpoint="CONFIG.ENABLE",
        )
        record_property("expected_mode", "ONE_STEP")
        record_observation(
            record_property,
            key="actual_mode",
            value=one_step.mode.name,
            source="dut",
            endpoint="CONFIG.MODE",
        )

        assert one_step.enabled is True
        assert one_step.mode is SpinlockMode.ONE_STEP

        # 刺激：切换 TWO_STEP，确认配置变化未依赖本地缓存。
        support.spinlock.configure(enabled=True, mode=SpinlockMode.TWO_STEP)
        two_step = support.spinlock.config_snapshot_get()
        snapshots.append({"expected": "TWO_STEP", "actual": two_step.mode.name})

        record_property("expected_enable", True)
        record_observation(
            record_property,
            key="actual_enable",
            value=two_step.enabled,
            source="dut",
            endpoint="CONFIG.ENABLE",
        )
        record_property("expected_mode", "TWO_STEP")
        record_observation(
            record_property,
            key="actual_mode",
            value=two_step.mode.name,
            source="dut",
            endpoint="CONFIG.MODE",
        )

        assert two_step.enabled is True
        assert two_step.mode is SpinlockMode.TWO_STEP

        # 刺激：仅关闭模块，确认硬件 Enable 读回为 False。
        support.spinlock.configure(enabled=False, mode=SpinlockMode.TWO_STEP)
        disabled = support.spinlock.config_snapshot_get()
        snapshots.append({"expected": "DISABLED", "actual": disabled.enabled})

        record_property("expected_enable", False)
        record_observation(
            record_property,
            key="actual_enable",
            value=disabled.enabled,
            source="dut",
            endpoint="CONFIG.ENABLE",
        )
        record_property("expected_mode", "TWO_STEP")
        record_observation(
            record_property,
            key="actual_mode",
            value=disabled.mode.name,
            source="dut",
            endpoint="CONFIG.MODE",
        )

        assert disabled.enabled is False

    record_property("config_snapshots", snapshots)
    write_json_result(
        et_artifact_dir / "spinlock_p0_001_config_modes.json",
        {"measurement_schema": "et.measurement.v1", "snapshots": snapshots},
    )


# 测试 Feature：
# 1. SPINLOCK ONE_STEP 模式全 Resource 获取和释放。
# 2. Resource Flag 与硬件 Owner 读回。
#
# 测试方法：
# 1. 基线复位后配置 ONE_STEP，并读取当前执行实体的 Master ID。
# 2. 遍历 Runtime Capability 发布的每个 Resource，逐项 Try 获取。
# 3. 获取后先读无副作用 Flag，再读 Owner；释放后只读 Flag，不读取空闲 Owner。
#
# 通过条件：
# 1. 每个 Resource 恰好成功获取一次，Locked 和 Owner 均正确。
# 2. 每个 Resource 释放后对应 Flag 清零，最终两个 Flag Bank 均为零。
def test_spinlock_p0_002_one_step_all_resources(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：使用运行时数量生成全 Resource 矩阵，不写死目标最大编号。
    support = spinlock_support_for(spinlock_instance_id)
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
    expected_master_id = support.spinlock.local_master_id_get()
    measurements: list[dict[str, object]] = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 循环：每一轮只获取、观测并释放一个 Resource，避免组合状态遮蔽故障。
        for resource_id in range(support.runtime.resource_count):
            acquired = support.spinlock.resource_acquire_try(resource_id)
            acquired_flags = support.spinlock.flag_snapshot_get()
            acquired_snapshot = support.spinlock.resource_snapshot_get(resource_id)

            record_property("resource_id", resource_id)
            record_observation(
                record_property,
                key="locked_after_acquire",
                value=acquired_snapshot.locked,
                source="dut",
                endpoint="RESOURCE_INFO.LOCKED",
            )
            record_observation(
                record_property,
                key="owner_after_acquire",
                value=acquired_snapshot.master_id,
                source="dut",
                endpoint="RESOURCE_INFO.MASTER_ID",
            )

            assert acquired is True
            assert acquired_flags.is_locked(resource_id) is True
            assert acquired_snapshot.locked is True
            assert acquired_snapshot.owner_valid is True
            assert acquired_snapshot.master_id == expected_master_id

            support.spinlock.resource_release(resource_id)
            released_flags = support.spinlock.flag_snapshot_get()

            record_observation(
                record_property,
                key="flag_after_release",
                value=released_flags.is_locked(resource_id),
                source="dut",
                endpoint="RESOURCE_FLAGS[RESOURCE_ID]",
            )

            assert released_flags.is_locked(resource_id) is False

            measurements.append(
                {
                    "resource_id": resource_id,
                    "owner": acquired_snapshot.master_id,
                    "locked_after_acquire": acquired_snapshot.locked,
                    "locked_after_release": released_flags.is_locked(resource_id),
                }
            )

        # 观测：全矩阵结束后确认两个 Flag Bank 都返回空闲基线。
        final_flags = support.spinlock.flag_snapshot_get()
        assert final_flags.low == 0
        assert final_flags.high == 0

    record_property("resource_measurements", measurements)
    write_json_result(
        et_artifact_dir / "spinlock_p0_002_one_step_all_resources.json",
        {"measurement_schema": "et.measurement.v1", "resources": measurements},
    )


# 测试 Feature：
# 1. SPINLOCK TWO_STEP 模式。
# 2. 全 Process ID 登记、Owner 读回和同 Process 释放。
#
# 测试方法：
# 1. 基线复位后配置 TWO_STEP，并选择 Capability 内的代表 Resource。
# 2. 遍历全部 Process ID，逐项获取并读取 Locked、Owner、Valid 和 Process ID。
# 3. 使用同一 Process ID 释放后检查无副作用 Flag 清零。
#
# 通过条件：
# 1. 每个 Process ID 均被硬件准确记录，Owner 等于当前 Master。
# 2. 每轮释放后 Resource 恢复空闲，不读取空闲 Owner 端点。
def test_spinlock_p0_003_two_step_process_ids(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：全部范围来自 Runtime Capability，代表 Resource 使用首个合法编号。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.TWO_STEP)
    expected_master_id = support.spinlock.local_master_id_get()
    measurements: list[dict[str, object]] = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 循环：每个 Process ID 独立获取、观测和释放同一代表 Resource。
        for process_id in range(support.runtime.process_id_count):
            record_property("expected_process_id", process_id)

            assert support.spinlock.resource_acquire_try(
                resource_id,
                process_id=process_id,
            )
            snapshot = support.spinlock.resource_snapshot_get(resource_id)

            record_observation(
                record_property,
                key="actual_process_id",
                value=snapshot.process_id,
                source="dut",
                endpoint="RESOURCE_INFO.PROCESS_ID",
            )
            record_observation(
                record_property,
                key="process_id_valid",
                value=snapshot.process_id_valid,
                source="dut",
                endpoint="RESOURCE_INFO.PROCESS_ID_VALID",
            )
            record_observation(
                record_property,
                key="actual_master_id",
                value=snapshot.master_id,
                source="dut",
                endpoint="RESOURCE_INFO.MASTER_ID",
            )

            assert snapshot.locked is True
            assert snapshot.owner_valid is True
            assert snapshot.master_id == expected_master_id
            assert snapshot.process_id_valid is True
            assert snapshot.process_id == process_id

            support.spinlock.resource_release(resource_id, process_id=process_id)
            released_flags = support.spinlock.flag_snapshot_get()
            assert released_flags.is_locked(resource_id) is False

            measurements.append(
                {
                    "expected_process_id": process_id,
                    "actual_process_id": snapshot.process_id,
                    "master_id": snapshot.master_id,
                    "process_id_valid": snapshot.process_id_valid,
                }
            )

    record_property("process_measurements", measurements)
    write_json_result(
        et_artifact_dir / "spinlock_p0_003_two_step_process_ids.json",
        {"measurement_schema": "et.measurement.v1", "process_ids": measurements},
    )
