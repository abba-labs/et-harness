# STIMER Formal Case pytest Fixture。
# 职责：建立静态Capability与Runtime Service交集并构造Driver。
# 边界：不执行Feature Mutation，不隐藏Case流程。
# 依赖：仅依赖 Framework/STIMER Driver、Chip Capability 和本 IP Support。

import pytest

from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.stimer import STIMER_SERVICE_ID, StimerDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers import resolve_dma_input_route
from ._support import StimerCaseSupport, StimerDmaCaseSupport, StimerSupportFactory


# 把稳定实例名stimer<N>转换成Service Instance ID。
def _stimer_instance_index(instance_name: str) -> int:

    suffix = instance_name.removeprefix("stimer")
    if not instance_name.startswith("stimer") or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid STIMER capability instance name: {instance_name!r}")
    return int(suffix)


# 返回静态Capability与Runtime Registry共有的全部STIMER实例。
@pytest.fixture
def stimer_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(
        _stimer_instance_index(name) for name in target_capabilities.instances("stimer")
    )
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == STIMER_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip(
            "skip_by_runtime_service: no STIMER instance is shared by capability and registry"
        )
    return shared


# 选择交集中的首个实例执行普通单实例Case。
@pytest.fixture(name="stimer_instance_id")
def stimer_representative_instance_id(stimer_instance_ids: tuple[int, ...]) -> int:

    return stimer_instance_ids[0]


# 校验CRG Service已注册，并为Case提供稳定的模块复位入口。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    if not any(
        item.service_id == CRG_SERVICE_ID and item.instance_id == 0
        for item in framework_communication.runtime_services
    ):
        pytest.skip("skip_by_runtime_service: CRG service instance 0 is not registered")
    return CrgDriver(framework_communication.target_client)


# 返回按实例构造STIMER Support的纯准备函数。
@pytest.fixture
def stimer_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> StimerSupportFactory:

    services = framework_communication.runtime_services
    declared = target_capabilities.instances("stimer")

    def build(instance_id: int) -> StimerCaseSupport:

        instance_name = f"stimer{instance_id}"
        if instance_name not in declared:
            pytest.skip(f"skip_by_chip_capability: STIMER instance {instance_name} is absent")
        if not any(
            item.service_id == STIMER_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: STIMER service 0x{STIMER_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        driver = StimerDriver(framework_communication.target_client, instance_id=instance_id)
        return StimerCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            stimer=driver,
            runtime=driver.capabilities_get(),
        )

    return build


# 构造STIMER、DMA、SYSCTRL和Resource单IP Driver及已审核静态Route，不修改硬件。
@pytest.fixture
def stimer_dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
) -> StimerDmaCaseSupport:

    route = resolve_dma_input_route(
        target_capabilities,
        peripheral="stimer",
        instance_id=stimer_instance_id,
    )
    services = framework_communication.runtime_services
    for service_id, label in (
        (DMA_SERVICE_ID, "DMA"),
        (SYSCTRL_SERVICE_ID, "SYSCTRL"),
    ):
        if not any(item.service_id == service_id for item in services):
            pytest.skip(f"skip_by_runtime_service: {label} service is not registered")

    target = framework_communication.target_client
    return StimerDmaCaseSupport(
        stimer_support=stimer_support_for(stimer_instance_id),
        dma=DmaDriver(target, instance_id=route.controller),
        sysctrl=SysctrlDriver(target),
        resource=resource_driver,
        route=route,
    )


__all__ = ("stimer_support_for",)
