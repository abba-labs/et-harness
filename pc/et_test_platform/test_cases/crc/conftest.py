# CRC Formal Case 的 pytest Fixture 入口。
#
# 职责：提供 CRC Capability/Runtime Gate 和 Driver 构造。
# 边界：不隐藏初始化或被测动作；固定收尾与证据发布不产生测试结论。
# 依赖：仅依赖 pytest、Profile、Capability 和稳定 Driver 接口。

from __future__ import annotations

import hashlib

import pytest

from ...core.errors import ConfigurationError
from ...drivers.crc import CRC_SERVICE_ID, CrcDriver
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver, DmaFeature
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.resource.contract import RESOURCE_INSTANCE_ID, RESOURCE_SERVICE_ID
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers.dma_routes import resolve_crc_dma_input_route
from ...results.recorder import write_json_result
from ...scheduling.crc_evidence import RecordedCrcDriver
from ._support import (
    CrcCaseSupport, CrcDmaSupport, CrcSupportFactory,
    calculate_crc_reference, require_crc_runtime_capability,
)


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


__all__ = ("crc_support_for", "crc0", "crc_reference_evidence")


# 明确选择 crc0，不回退到其他实例；初始化必须由 Case 显式 reset。
@pytest.fixture
def crc0(request, framework_communication, target_capabilities, resource_driver, record_property):
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    required = {(CRC_SERVICE_ID, 0), (CRG_SERVICE_ID, 0),
                (RESOURCE_SERVICE_ID, RESOURCE_INSTANCE_ID)}
    if "crc0" not in target_capabilities.instances("crc") or not required <= services:
        raise ConfigurationError("crc0 requires matching CRC0, CRG and Resource services")
    driver = RecordedCrcDriver(framework_communication.target_client, 0, record_property)
    yield driver
    if not driver.reset_attempted:
        return
    if not driver.reset_completed:
        request.session.shouldstop = "CRC reset failed; target isolation is unknown"
    try:
        driver.disable()
        if driver.reset_completed:
            resource_driver.reset()
    except Exception:
        request.session.shouldstop = "CRC cleanup failed; target isolation is unknown"
        raise


# 只读能力核对并发布已有读回和输入元数据；不复位、配置或判定被测功能。
@pytest.fixture
def crc_reference_evidence(crc0, config, payload, fixed_expected, et_artifact_dir, record_property):
    require_crc_runtime_capability(crc0.capabilities_get(), mode=config.mode)
    expected = calculate_crc_reference(config, payload)
    record_property("mode", config.mode.name)
    record_property("expected_crc", expected)
    path = et_artifact_dir / f"crc_p0_002_{config.mode.name.lower()}.json"
    record_property("crc_reference_result", str(path))
    yield
    measured = crc0.calculation
    write_json_result(
        path,
        {
            "measurement_schema": "et.measurement.v1",
            "ip": "crc",
            "case_id": "crc_p0_002",
            "instance": f"crc{crc0.instance_id}",
            "mode": config.mode.name,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "length_bytes": len(payload),
            "fixed_expected": fixed_expected,
            "pc_expected": expected,
            "actual": None if measured is None else measured.result,
            "remaining_input_count": None if measured is None else measured.remaining_input_count,
            "result_readback": crc0.readback,
        },
    )
