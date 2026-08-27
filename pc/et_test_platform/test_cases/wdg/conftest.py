# WDG Formal Case pytest Fixture。
# 职责：建立静态 Capability 与 Runtime Service 交集并构造 WDG Driver。
# 边界：不执行 Feature Mutation、不隐藏配置、刺激、观测或断言。
# 依赖：pytest、Framework Registry、Capability 和 WDG package API。

import pytest

from ...core.errors import CapabilityLookupError
from ...drivers.cpu import CPU_SERVICE_ID, CpuDriver
from ...drivers.crg import CrgDriver
from ...drivers.framework import FrameworkDriver
from ...drivers.wdg import WDG_SERVICE_ID, WdgDriver
from ...profiles.capabilities import ChipCapabilities
from ._support import (
    CpuNmiCaseSupport,
    CpuNmiSupportFactory,
    WdgCaseSupport,
    WdgSupportFactory,
)


# 把稳定实例名 wdg<N> 转为 Firmware Service Instance ID。
def _wdg_instance_index(instance_name: str) -> int:

    suffix = instance_name.removeprefix("wdg")
    if not instance_name.startswith("wdg") or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid WDG capability instance name: {instance_name!r}")
    return int(suffix)


# 返回静态 Capability 与 Runtime Registry 共有的全部 WDG 实例。
@pytest.fixture
def wdg_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(_wdg_instance_index(name) for name in target_capabilities.instances("wdg"))
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == WDG_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip("skip_by_runtime_service: no WDG instance is shared by capability and registry")
    return shared


# 选择 Capability/Runtime 交集中的首个实例执行普通单实例 Case。
@pytest.fixture(name="wdg_instance_id")
def wdg_representative_instance_id(wdg_instance_ids: tuple[int, ...]) -> int:

    return wdg_instance_ids[0]


# 返回按实例构造 WDG Support 的纯准备函数，不改变设备状态。
@pytest.fixture
def wdg_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> WdgSupportFactory:

    services = framework_communication.runtime_services
    declared = target_capabilities.instances("wdg")

    def build(instance_id: int) -> WdgCaseSupport:

        instance_name = f"wdg{instance_id}"
        if instance_name not in declared:
            pytest.skip(f"skip_by_chip_capability: WDG instance {instance_name} is absent")
        if not any(
            item.service_id == WDG_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: WDG service 0x{WDG_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        driver = WdgDriver(framework_communication.target_client, instance_id=instance_id)
        return WdgCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            wdg=driver,
            runtime=driver.capabilities_get(),
        )

    return build


# 构造CRG Owner Driver；CRG实例选择和时基组合由具体Case负责。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:
    return CrgDriver(framework_communication.target_client)


# 返回静态Capability声明的CPU实例，不在Fixture层做Case跳过或结论判断。
@pytest.fixture
def cpu_nmi_instance_ids(target_capabilities: ChipCapabilities) -> tuple[int, ...]:
    try:
        names = target_capabilities.instances("cpu")
    except CapabilityLookupError:
        names = ()

    instance_ids = []
    for name in names:
        suffix = name.removeprefix("cpu")
        if name.startswith("cpu") and suffix.isdecimal():
            instance_ids.append(int(suffix))
    return tuple(instance_ids)


# 构造CPU Owner Driver并返回可用性事实，具体Skip由Formal Case决定。
@pytest.fixture
def cpu_nmi_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> CpuNmiSupportFactory:
    services = framework_communication.runtime_services
    try:
        declared = target_capabilities.instances("cpu")
    except CapabilityLookupError:
        declared = ()

    def build(instance_id: int) -> CpuNmiCaseSupport:
        instance_name = f"cpu{instance_id}"
        available = instance_name in declared and any(
            item.service_id == CPU_SERVICE_ID and item.instance_id == instance_id
            for item in services
        )
        driver = CpuDriver(framework_communication.target_client, instance_id=instance_id)
        return CpuNmiCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            cpu=driver,
            runtime=driver.capabilities_get() if available else None,
            available=available,
        )

    return build


__all__ = ("wdg_support_for",)
