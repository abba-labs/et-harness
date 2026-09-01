# CRC Formal Case 的 pytest Fixture 入口。
#
# 职责：提供 CRC Capability/Runtime Gate 和 Driver 构造。
# 边界：不执行 Feature Mutation、不拥有最终断言、不隐藏完整 Case。
# 依赖：仅依赖 pytest、Profile、Capability 和稳定 Driver 接口。

from __future__ import annotations

import pytest

from ...drivers.crc import CRC_SERVICE_ID, CrcDriver
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver, DmaFeature
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers.dma_routes import resolve_crc_dma_input_route
from ._support import CrcCaseSupport, CrcDmaSupport, CrcSupportFactory


# 把平台稳定实例名 crc<N> 转为 Firmware Service Instance ID。
def _crc_instance_index(instance_name: str) -> int:

    suffix = instance_name.removeprefix("crc")
    if not instance_name.startswith("crc") or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid CRC capability instance name: {instance_name!r}")
    return int(suffix)


# 返回静态 Capability 与 Runtime Registry 共有的全部 CRC 实例。
@pytest.fixture
def crc_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(_crc_instance_index(name) for name in target_capabilities.instances("crc"))
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == CRC_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip("skip_by_runtime_service: no CRC instance is shared by capability and registry")
    return shared


# 选择 Capability/Runtime 交集中的首个 CRC 实例执行普通 Feature Case。
@pytest.fixture(name="crc_instance_id")
def crc_representative_instance_id(crc_instance_ids: tuple[int, ...]) -> int:

    return crc_instance_ids[0]


# 校验 CRG Service 已注册，并为 Case 提供稳定的模块复位入口。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    if not any(
        item.service_id == CRG_SERVICE_ID and item.instance_id == 0
        for item in framework_communication.runtime_services
    ):
        pytest.skip("skip_by_runtime_service: CRG service instance 0 is not registered")
    return CrgDriver(framework_communication.target_client)


# 返回按实例构造 CRC Support 的纯准备函数；不改变 CRC/Resource 状态。
@pytest.fixture
def crc_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> CrcSupportFactory:

    services = framework_communication.runtime_services
    declared = target_capabilities.instances("crc")

    def build(instance_id: int) -> CrcCaseSupport:
        if instance_id < 0:
            raise ValueError("CRC instance ID must be non-negative")
        if not any(
            item.service_id == CRC_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: CRC service 0x{CRC_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        instance_name = f"crc{instance_id}"
        if instance_name not in declared:
            pytest.skip(f"skip_by_chip_capability: CRC instance {instance_name} is absent")
        driver = CrcDriver(
            framework_communication.target_client,
            instance_id=instance_id,
        )
        return CrcCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            resource=resource_driver,
            crc=driver,
            runtime=driver.capabilities_get(),
        )

    return build


# 构造 CRC DMA Case 的 Driver 和已审核 Route 事实；不修改任何 IP 状态。
@pytest.fixture
def crc_dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
) -> CrcDmaSupport:

    route = resolve_crc_dma_input_route(
        target_capabilities,
        instance_id=crc_instance_id,
    )
    services = framework_communication.runtime_services
    for service_id, instance_id, label in (
        (DMA_SERVICE_ID, route.controller, "DMA"),
        (SYSCTRL_SERVICE_ID, 0, "SYSCTRL"),
    ):
        if not any(
            item.service_id == service_id and item.instance_id == instance_id for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: {label} service 0x{service_id:04x} "
                f"instance {instance_id} is not registered"
            )
    dma = DmaDriver(
        framework_communication.target_client,
        instance_id=route.controller,
    )
    dma_capabilities = dma.capabilities_get()
    if dma_capabilities.features & DmaFeature.MEMORY_TO_PERIPHERAL == 0:
        pytest.skip("skip_by_runtime_feature: DMA memory_to_peripheral is unavailable")
    return CrcDmaSupport(
        crc_support=crc_support_for(crc_instance_id),
        dma=dma,
        dma_capabilities=dma_capabilities,
        sysctrl=SysctrlDriver(framework_communication.target_client),
        route=route,
    )


__all__ = ("crc_support_for",)
