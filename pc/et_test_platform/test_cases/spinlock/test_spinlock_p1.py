# SPINLOCK P1 Formal Case。
# 职责：验证跨 Flag Bank 独立性、Disable 状态保持和 Clear Key 保护。
# 边界：只通过稳定 Driver API 操作设备，不访问 Codec/Transport/Register。
# 依赖：依赖SPINLOCK Case Fixture、Resource Driver和Canonical Evidence接口。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.resource import ResourceDriver
from ...drivers.spinlock import SpinlockClearScope, SpinlockMode
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import SpinlockCaseSupport

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spinlock")]


# 返回 SPINLOCK Case 的显式恢复动作；不隐藏测试流程和判定。
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


# 根据 Runtime Resource 数量生成首项、Flag Bank 边界和末项的去重集合。
def _boundary_resources(resource_count: int) -> tuple[int, ...]:

    candidates = (0, min(31, resource_count - 1), min(32, resource_count - 1), resource_count - 1)
    return tuple(dict.fromkeys(candidates))


# 测试 Feature：
# 1. 跨 LOW/HIGH Flag Bank 的多 Resource 同时占用。
# 2. 单 Resource 释放不污染其他 Resource 状态。
#
# 测试方法：
# 1. 基线复位后配置 ONE_STEP，并生成 Capability 边界 Resource 集合。
# 2. 不释放地依次获取全部边界 Resource，记录两个 Flag Bank。
# 3. 逆序逐个释放，每轮比较前后 Flag 差值并检查其余 Resource 仍锁定。
#
# 通过条件：
# 1. 全部边界 Resource 可同时锁定，Owner 均为当前 Master。
# 2. 每次释放只改变目标 Resource 位，最终 LOW/HIGH 均为零。
def test_spinlock_p1_001_resource_independence(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：边界集合完全由 Runtime Capability 生成，不绑定目标固定数量。
    support = spinlock_support_for(spinlock_instance_id)
    resources = _boundary_resources(support.runtime.resource_count)
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)
    snapshots: list[dict[str, object]] = []

    record_property("boundary_resource_ids", resources)

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：依次获取边界 Resource，中途不释放以形成组合占用状态。
        for resource_id in resources:
            assert support.spinlock.resource_acquire_try(resource_id)

        acquired = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="flags_low",
            value=acquired.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high",
            value=acquired.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )

        assert all(acquired.is_locked(resource_id) for resource_id in resources)
        snapshots.append({"phase": "acquired", "low": acquired.low, "high": acquired.high})

        # 刺激：逆序释放，每一轮只允许目标位发生变化。
        remaining = set(resources)
        previous = acquired

        # 逐个释放边界Resource，验证每次只有对应Flag位清零且其余锁保持不变。
        for resource_id in reversed(resources):
            support.spinlock.resource_release(resource_id)
            current = support.spinlock.flag_snapshot_get()
            changed = previous.low ^ current.low
            changed |= (previous.high ^ current.high) << 32
            changed_resource_ids = [
                index for index in range(support.runtime.resource_count) if changed & (1 << index)
            ]

            record_property("changed_resource_ids", changed_resource_ids)

            assert changed_resource_ids == [resource_id]
            remaining.remove(resource_id)
            assert all(current.is_locked(item) for item in remaining)
            snapshots.append(
                {
                    "released_resource": resource_id,
                    "low": current.low,
                    "high": current.high,
                    "changed_resource_ids": [resource_id],
                }
            )
            previous = current

        assert previous.low == 0
        assert previous.high == 0

    record_property("flag_transitions", snapshots)
    write_json_result(
        et_artifact_dir / "spinlock_p1_001_resource_independence.json",
        {"measurement_schema": "et.measurement.v1", "resources": resources, "snapshots": snapshots},
    )


# 测试 Feature：
# 1. SPINLOCK Disable/Enable 控制。
# 2. Disable 和同模式 Re-enable 期间锁状态及 Owner 保持。
#
# 测试方法：
# 1. 对 ONE_STEP 和 TWO_STEP 分别建立独立基线并锁定代表 Resource。
# 2. 记录 Disable 前快照，仅关闭模块后再次记录，再以相同模式重新 Enable。
# 3. 比较三个阶段的 Flag、Owner 和 Process 信息，最后由原 Owner 释放。
#
# 通过条件：
# 1. Disable 后 CONFIG.ENABLE 为 False，但锁状态和 Owner 信息不变。
# 2. Re-enable 后 Owner 仍不变，并能由原执行实体正常释放。
@pytest.mark.parametrize("mode", (SpinlockMode.ONE_STEP, SpinlockMode.TWO_STEP), ids=("one", "two"))
def test_spinlock_p1_002_disable_state_hold(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    mode: SpinlockMode,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：两步模式使用合法 Process ID 0，一步模式忽略该公共字段。
    support = spinlock_support_for(spinlock_instance_id)
    resource_id = 0
    process_id = 0
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=mode)

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：锁定代表 Resource，并保存 Disable 前的完整有效快照。
        assert support.spinlock.resource_acquire_try(resource_id, process_id=process_id)
        before = support.spinlock.resource_snapshot_get(resource_id)

        # 刺激：只改变 Enable，不执行 Release/Clear，再读取 Config 和 Resource。
        support.spinlock.configure(enabled=False, mode=mode)
        disabled_config = support.spinlock.config_snapshot_get()
        disabled = support.spinlock.resource_snapshot_get(resource_id)

        # 刺激：按相同模式重新使能，并确认原 Owner 仍可正常释放。
        support.spinlock.configure(enabled=True, mode=mode)
        reenabled = support.spinlock.resource_snapshot_get(resource_id)
        support.spinlock.resource_release(resource_id, process_id=process_id)
        released = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="locked_before_disable",
            value=before.locked,
            source="dut",
            endpoint="RESOURCE_INFO.LOCKED",
        )
        record_observation(
            record_property,
            key="owner_before_disable",
            value=before.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )
        record_observation(
            record_property,
            key="locked_while_disabled",
            value=disabled.locked,
            source="dut",
            endpoint="RESOURCE_INFO.LOCKED",
        )
        record_observation(
            record_property,
            key="owner_after_reenable",
            value=reenabled.master_id,
            source="dut",
            endpoint="RESOURCE_INFO.MASTER_ID",
        )

        assert disabled_config.enabled is False
        assert disabled == before
        assert reenabled == before
        assert released.is_locked(resource_id) is False

    observations = {
        "mode": mode.name,
        "before": asdict(before),
        "disabled": asdict(disabled),
        "reenabled": asdict(reenabled),
        "released": released.is_locked(resource_id),
    }
    record_property("state_hold", observations)
    write_json_result(
        et_artifact_dir / f"spinlock_p1_002_disable_state_hold_{mode.name.lower()}.json",
        {"measurement_schema": "et.measurement.v1", **observations},
    )


# 测试 Feature：
# 1. Batch 与 Global Clear 的授权 Key 保护。
# 2. 正确 Batch 授权清除当前 Master 的全部 Resource。
#
# 测试方法：
# 1. 基线复位后以 ONE_STEP 锁定两个不同 Resource。
# 2. 分别提交错误 Batch 授权和错误 Global 授权，读取 LOW/HIGH Flag。
# 3. 提交正确 Batch 授权并再次读取 Flag，最后执行 Global Release 恢复基线。
#
# 通过条件：
# 1. 两次错误授权均不改变两个 Resource 的锁定状态。
# 2. 正确 Batch 授权后两个 Resource 均清零，判定不依赖命令返回值。
def test_spinlock_p1_003_clear_key_protection(
    spinlock_support_for: Callable[[int], SpinlockCaseSupport],
    spinlock_instance_id: int,
    resource_driver: ResourceDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：从 Capability 选择两个不同 Resource，目标不足两个时明确失败。
    support = spinlock_support_for(spinlock_instance_id)
    assert support.runtime.resource_count >= 2
    resources = (0, support.runtime.resource_count - 1)
    support.spinlock.global_release()
    resource_driver.reset()
    support.spinlock.configure(enabled=True, mode=SpinlockMode.ONE_STEP)

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 刺激：由当前 Master 同时锁定两个 Resource，形成 Clear Key 观测对象。
        for resource_id in resources:
            assert support.spinlock.resource_acquire_try(resource_id)

        before = support.spinlock.flag_snapshot_get()
        assert all(before.is_locked(resource_id) for resource_id in resources)

        # 刺激：错误 Batch 授权不得改变任一锁状态。
        support.spinlock.clear_key_probe(
            SpinlockClearScope.CURRENT_MASTER_ALL,
            authorized=False,
        )
        invalid_batch = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="flags_low_after_invalid_batch",
            value=invalid_batch.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high_after_invalid_batch",
            value=invalid_batch.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )

        assert invalid_batch == before

        # 刺激：错误 Global 授权同样不得改变任一锁状态。
        support.spinlock.clear_key_probe(SpinlockClearScope.GLOBAL_ALL, authorized=False)
        invalid_global = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="flags_low_after_invalid_global",
            value=invalid_global.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high_after_invalid_global",
            value=invalid_global.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )

        assert invalid_global == before

        # 刺激：正确 Batch 授权应清除当前 Master 的两个 Resource。
        support.spinlock.clear_key_probe(
            SpinlockClearScope.CURRENT_MASTER_ALL,
            authorized=True,
        )
        valid_batch = support.spinlock.flag_snapshot_get()

        record_observation(
            record_property,
            key="flags_low_after_valid_batch",
            value=valid_batch.low,
            source="dut",
            endpoint="RESOURCE_FLAGS.LOW",
        )
        record_observation(
            record_property,
            key="flags_high_after_valid_batch",
            value=valid_batch.high,
            source="dut",
            endpoint="RESOURCE_FLAGS.HIGH",
        )

        assert all(not valid_batch.is_locked(resource_id) for resource_id in resources)

    observations = {
        "resources": resources,
        "before": {"low": before.low, "high": before.high},
        "invalid_batch": {"low": invalid_batch.low, "high": invalid_batch.high},
        "invalid_global": {"low": invalid_global.low, "high": invalid_global.high},
        "valid_batch": {"low": valid_batch.low, "high": valid_batch.high},
    }
    record_property("clear_key_observations", observations)
    write_json_result(
        et_artifact_dir / "spinlock_p1_003_clear_key_protection.json",
        {"measurement_schema": "et.measurement.v1", **observations},
    )
