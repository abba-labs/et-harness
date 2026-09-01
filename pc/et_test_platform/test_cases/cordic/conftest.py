# CORDIC Formal Case pytest Fixture。
#
# 职责：建立静态 Capability 与 Runtime Service 交集，并构造 CORDIC Driver。
# 边界：不修改 Feature、不执行 IRQ 操作、不隐藏 Case 的配置、刺激或断言。
# 依赖：pytest、Framework Registry、Capability 和 CORDIC package API。

from __future__ import annotations

import pytest

from ...core.errors import UnsupportedCapability
from ...drivers.cordic import CORDIC_SERVICE_ID, CordicDriver
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ._support import (
    CordicCaseSupport,
    CordicDmaSupport,
    CordicSupportFactory,
    require_cordic_dma_runtime_capability,
    resolve_cordic_dma_route,
)


# 把平台稳定实例名 cordic<N> 转成 Firmware Service Instance ID。
def _cordic_instance_index(instance_name: str) -> int:

    suffix = instance_name.removeprefix("cordic")
    if not instance_name.startswith("cordic") or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid CORDIC capability instance name: {instance_name!r}")
    return int(suffix)


# 返回静态 Capability 与 Runtime Registry 共有的全部 CORDIC 实例。
@pytest.fixture
def cordic_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(
        _cordic_instance_index(name) for name in target_capabilities.instances("cordic")
    )
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == CORDIC_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip(
            "skip_by_runtime_service: no CORDIC instance is shared by capability and registry"
        )
    return shared


# 选择 Capability/Runtime 交集中的首个实例执行普通单实例 Feature Case。
@pytest.fixture(name="cordic_instance_id")
def cordic_representative_instance_id(cordic_instance_ids: tuple[int, ...]) -> int:

    return cordic_instance_ids[0]


# 返回按实例构造 CORDIC Support 的纯准备函数，不改变设备状态。
@pytest.fixture
def cordic_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> CordicSupportFactory:

    services = framework_communication.runtime_services
    declared = target_capabilities.instances("cordic")

    def build(instance_id: int) -> CordicCaseSupport:

        instance_name = f"cordic{instance_id}"
        if instance_name not in declared:
            pytest.skip(f"skip_by_chip_capability: CORDIC instance {instance_name} is absent")
        if not any(
            item.service_id == CORDIC_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: CORDIC service 0x{CORDIC_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        driver = CordicDriver(framework_communication.target_client, instance_id=instance_id)
        return CordicCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            cordic=driver,
            runtime=driver.capabilities_get(),
        )

    return build


# 校验 CRG Service 已注册后构造 CORDIC 复位 Case 使用的稳定 Driver。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    if not any(
        item.service_id == CRG_SERVICE_ID and item.instance_id == 0
        for item in framework_communication.runtime_services
    ):
        pytest.skip("skip_by_runtime_service: CRG service instance 0 is not registered")
    return CrgDriver(framework_communication.target_client)


# 构造 CORDIC DMA Case 的单 IP Driver 和已审核 Execution Mapping。
#
# 当前目标未发布 CORDIC DMA Execution Mapping 时，这里按内部集成缺口失败关闭；
# 不会从旧版本资料猜写 Request ID、Endpoint 或 DMA Controller，也不会把缺口记为SKIP。
@pytest.fixture
def cordic_dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
) -> CordicDmaSupport:

    try:
        route = resolve_cordic_dma_route(
            target_capabilities,
            instance_id=cordic_instance_id,
        )
    except UnsupportedCapability as error:
        pytest.fail(f"execution_mapping_gap: {error}", pytrace=False)

    services = framework_communication.runtime_services
    for service_id, label in (
        (DMA_SERVICE_ID, "DMA"),
        (SYSCTRL_SERVICE_ID, "SYSCTRL"),
    ):
        if not any(item.service_id == service_id for item in services):
            pytest.skip(f"skip_by_runtime_service: {label} service is not registered")

    cordic_support = cordic_support_for(cordic_instance_id)
    dma = DmaDriver(
        framework_communication.target_client,
        instance_id=route.controller,
    )
    dma_capabilities = dma.capabilities_get()
    try:
        require_cordic_dma_runtime_capability(
            cordic_support.runtime,
            dma_capabilities,
        )
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_runtime_capability: {error}")
    if dma_capabilities.channel_count < 2:
        pytest.skip("skip_by_runtime_capability: CORDIC DMA needs two DMA channels")

    return CordicDmaSupport(
        cordic_support=cordic_support,
        dma=dma,
        dma_capabilities=dma_capabilities,
        resource=resource_driver,
        sysctrl=SysctrlDriver(framework_communication.target_client),
        route=route,
    )


__all__ = ("cordic_support_for", "cordic_dma_support")
