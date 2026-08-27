# SPINLOCK Formal Case pytest Fixture。
# 职责：建立静态 Capability 与 Runtime Service 交集并构造 SPINLOCK Driver。
# 边界：不执行 Feature Mutation、不隐藏 Case 配置、刺激、观测或断言。
# 依赖：依赖公共pytest Fixture、Framework Driver、SPINLOCK Driver和Capability模型。

from collections.abc import Callable

import pytest

from ...drivers.framework import FrameworkDriver
from ...drivers.spinlock import SPINLOCK_SERVICE_ID, SpinlockDriver
from ...profiles.capabilities import ChipCapabilities
from ._support import SpinlockCaseSupport


# 把稳定实例名 spinlock<N> 转为 Firmware Service Instance ID。
def _spinlock_instance_index(instance_name: str) -> int:

    suffix = instance_name.removeprefix("spinlock")
    if not instance_name.startswith("spinlock") or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid SPINLOCK capability instance name: {instance_name!r}")
    return int(suffix)


# 返回静态 Capability 与 Runtime Registry 共有的全部 SPINLOCK 实例。
@pytest.fixture
def spinlock_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(
        _spinlock_instance_index(name) for name in target_capabilities.instances("spinlock")
    )
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == SPINLOCK_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip(
            "skip_by_runtime_service: no SPINLOCK instance is shared by capability and registry"
        )
    return shared


# 选择 Capability/Runtime 交集中的首个实例执行普通单实例 Case。
@pytest.fixture(name="spinlock_instance_id")
def spinlock_representative_instance_id(spinlock_instance_ids: tuple[int, ...]) -> int:

    return spinlock_instance_ids[0]


# 返回按实例构造 SPINLOCK Support 的纯准备函数，不改变设备状态。
@pytest.fixture
def spinlock_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> Callable[[int], SpinlockCaseSupport]:

    services = framework_communication.runtime_services
    declared = target_capabilities.instances("spinlock")

    def build(instance_id: int) -> SpinlockCaseSupport:

        instance_name = f"spinlock{instance_id}"
        if instance_name not in declared:
            pytest.skip(f"skip_by_chip_capability: SPINLOCK instance {instance_name} is absent")
        if not any(
            item.service_id == SPINLOCK_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: SPINLOCK service 0x{SPINLOCK_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        driver = SpinlockDriver(framework_communication.target_client, instance_id=instance_id)
        return SpinlockCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            spinlock=driver,
            runtime=driver.capabilities_get(),
        )

    return build


__all__ = ("spinlock_support_for",)
