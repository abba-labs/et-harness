# AES 正式测试用例 pytest Fixture。
#
# 职责：只暴露 AES 静态/运行时门禁和 Driver 构造。
# 边界：不修改 Feature，不隐藏等待、清理、断言或完整 Case 流程。
# 依赖：pytest、Framework、Resource、Capability 和 AES package API。

from __future__ import annotations

import pytest

from ...drivers.aes import AES_SERVICE_ID
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers.dma_routes import resolve_aes_dma_route
from ._support import (
    AesCaseSupport,
    AesDmaCaseSupport,
    AesSupportFactory,
    build_aes_dma_support,
)
from ._support import (
    aes_support_for as build_aes_support_factory,
)


@pytest.fixture
def aes_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:
    declared = tuple(
        int(name.removeprefix("aes"))
        for name in target_capabilities.instances("aes")
        if name.startswith("aes") and name.removeprefix("aes").isdigit()
    )
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == AES_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip("skip_by_runtime_service: no AES instance is shared by capability and registry")
    return shared


@pytest.fixture(name="aes_instance_id")
def aes_representative_instance_id(aes_instance_ids: tuple[int, ...]) -> int:
    return aes_instance_ids[0]


@pytest.fixture
def aes_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> AesSupportFactory:
    return build_aes_support_factory(
        framework_communication,
        target_capabilities,
        resource_driver,
    )


@pytest.fixture
def aes_support(
    aes_support_for: AesSupportFactory,
    aes_instance_id: int,
) -> AesCaseSupport:
    return aes_support_for(aes_instance_id)


# 校验 CRG Service 已注册后构造 AES 错误注入 Case 使用的稳定 Driver。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    if not any(
        item.service_id == CRG_SERVICE_ID and item.instance_id == 0
        for item in framework_communication.runtime_services
    ):
        pytest.skip("skip_by_runtime_service: CRG service instance 0 is not registered")
    return CrgDriver(framework_communication.target_client)


@pytest.fixture
def aes_dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
    aes_support_for: AesSupportFactory,
    aes_instance_id: int,
) -> AesDmaCaseSupport:

    # Resolver 只核对静态 Capability 与芯片映射，不在 Fixture 中修改硬件状态。
    route = resolve_aes_dma_route(
        target_capabilities,
        instance_id=aes_instance_id,
    )
    return build_aes_dma_support(
        framework_communication,
        target_capabilities,
        resource_driver,
        aes_support_for,
        aes_instance_id,
        route,
    )
