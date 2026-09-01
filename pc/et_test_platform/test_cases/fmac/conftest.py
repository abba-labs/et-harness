# FMAC Formal Case pytest Fixture。
#
# 职责：提供Capability/Runtime交集中的FMAC实例和Driver Support。
# 边界：不执行配置、启动、数据写入或最终断言。
# 依赖：仅依赖pytest、公共Fixture和FMAC本地Support。

from __future__ import annotations

import pytest

from ...drivers.fmac import FMAC_SERVICE_ID
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...profiles.capabilities import ChipCapabilities
from ._support import (
    FmacCaseSupport,
    FmacDmaCaseSupport,
    FmacSupportFactory,
    build_fmac_dma_support,
    build_fmac_support_factory,
    resolve_fmac_dma_route,
)


@pytest.fixture
def fmac_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared = tuple(
        int(name.removeprefix("fmac"))
        for name in target_capabilities.instances("fmac")
        if name.startswith("fmac") and name.removeprefix("fmac").isdigit()
    )
    runtime = {
        item.instance_id
        for item in framework_communication.runtime_services
        if item.service_id == FMAC_SERVICE_ID
    }
    shared = tuple(instance_id for instance_id in declared if instance_id in runtime)
    if not shared:
        pytest.skip(
            "skip_by_runtime_service: no FMAC instance is shared by capability and registry"
        )
    return shared


@pytest.fixture(name="fmac_instance_id")
def fmac_representative_instance_id(fmac_instance_ids: tuple[int, ...]) -> int:

    return fmac_instance_ids[0]


@pytest.fixture
def fmac_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> FmacSupportFactory:

    return build_fmac_support_factory(
        framework_communication,
        target_capabilities,
        resource_driver,
    )


@pytest.fixture
def fmac_support(
    fmac_support_for: FmacSupportFactory,
    fmac_instance_id: int,
) -> FmacCaseSupport:

    return fmac_support_for(fmac_instance_id)


@pytest.fixture
def fmac_dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    fmac_support_for: FmacSupportFactory,
    fmac_instance_id: int,
) -> FmacDmaCaseSupport:

    route = resolve_fmac_dma_route(
        target_capabilities,
        instance_id=fmac_instance_id,
    )
    return build_fmac_dma_support(
        framework_communication,
        target_capabilities,
        fmac_support_for,
        fmac_instance_id,
        route,
    )
