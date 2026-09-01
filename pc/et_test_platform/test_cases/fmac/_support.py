# FMAC Formal Case 本地Support。
#
# 职责：构造通过静态身份和运行时能力门禁的FMAC/Resource Driver集合。
# 边界：不执行Feature动作、不隐藏完整Case流程、不包含芯片型号分支。
# 依赖：仅依赖公共Driver、Capability、Fixture和Execution Mapping入口。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

import pytest

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.crg import CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver
from ...drivers.fmac import FMAC_SERVICE_ID, FmacCapabilities, FmacDriver, FmacFeature
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities


@dataclass(frozen=True, slots=True)
class FmacCaseSupport:
    instance_id: int
    instance_name: str
    crg: CrgDriver
    fmac: FmacDriver
    resource: ResourceDriver
    runtime: FmacCapabilities


@dataclass(frozen=True, slots=True)
class FmacDmaRoute:
    instance_id: int
    controller: int
    input_interface: int
    output_interface: int
    input_request_id: int
    output_request_id: int
    fifo_address: int
    transfer_width_bits: int
    address_evidence: str
    request_evidence: str


@dataclass(frozen=True, slots=True)
class FmacDmaCaseSupport:
    fmac_support: FmacCaseSupport
    dma: DmaDriver
    sysctrl: SysctrlDriver
    route: FmacDmaRoute


FmacSupportFactory = Callable[[int], FmacCaseSupport]


# 从当前芯片专属执行映射解析FMAC双向DMA路由，不在公共Case保存芯片事实。
def resolve_fmac_dma_route(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> FmacDmaRoute:

    module_name = (
        f"et_test_platform.profiles.chip_execution_mappings.{capabilities.chip_id}.fmac_routes"
    )
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            raise UnsupportedCapability(
                f"FMAC DMA execution mapping is unavailable for chip {capabilities.chip_id!r}"
            ) from error
        raise

    mapping = getattr(module, "FMAC_DMA_MAPPING", None)
    if mapping is None:
        raise UnsupportedCapability("FMAC DMA execution mapping export is unavailable")
    if mapping.instance_id != instance_id:
        raise UnsupportedCapability(
            f"FMAC DMA mapping supports instance {mapping.instance_id}, not {instance_id}"
        )
    if mapping.transfer_width_bits != 16 or len(mapping.allowed_interfaces) < 2:
        raise UnsupportedCapability("FMAC DMA mapping width or interfaces are incompatible")

    instance_name = f"fmac{instance_id}"
    identity = capabilities.identity("fmac", "base_address", instance=instance_name)
    base_address = int(identity, 0) if isinstance(identity, str) else int(identity)
    if not base_address <= mapping.fifo_address < base_address + 0x1000:
        raise UnsupportedCapability("FMAC DMA FIFO endpoint is outside the declared instance")

    available_controllers = {
        int(name.removeprefix("dma"))
        for name in capabilities.instances("dma")
        if name.startswith("dma") and name.removeprefix("dma").isdecimal()
    }
    controller = next(
        (
            candidate
            for candidate in mapping.allowed_controllers
            if candidate in available_controllers
        ),
        None,
    )
    if controller is None:
        raise UnsupportedCapability("no mapped DMA controller is present in capability profile")

    input_interface, output_interface = mapping.allowed_interfaces[:2]
    return FmacDmaRoute(
        instance_id=instance_id,
        controller=controller,
        input_interface=input_interface,
        output_interface=output_interface,
        input_request_id=mapping.input_request_id,
        output_request_id=mapping.output_request_id,
        fifo_address=mapping.fifo_address,
        transfer_width_bits=mapping.transfer_width_bits,
        address_evidence=mapping.address_evidence,
        request_evidence=mapping.request_evidence,
    )


# 核对FMAC实例身份和IRQ映射，不读取任何芯片私有寄存器事实。
def require_fmac_static_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> str:

    instance_name = f"fmac{instance_id}"
    try:
        if instance_name not in capabilities.instances("fmac"):
            raise UnsupportedCapability(f"FMAC instance {instance_name!r} is unavailable")
        identity = capabilities.identity("fmac", "base_address", instance=instance_name)
        irq = capabilities.interrupt("fmac", "irq", instance=instance_name).irqn
        if identity in (None, ""):
            raise UnsupportedCapability("FMAC base address identity is unavailable")
        if isinstance(irq, bool) or not isinstance(irq, int) or irq < 0:
            raise UnsupportedCapability("FMAC IRQ identity is unavailable")
        return instance_name
    except (CapabilityLookupError, UnsupportedCapability) as error:
        raise UnsupportedCapability(f"FMAC static capability gap: {error}") from error


# 核对目标侧Service发布的公共Feature位，不从chip_id推导能力。
def require_fmac_features(support: FmacCaseSupport, features: FmacFeature) -> None:

    if support.runtime.api_version != 1:
        pytest.skip("skip_by_runtime_feature: FMAC API version is incompatible")
    if int(support.runtime.features) & int(features) != int(features):
        pytest.skip(
            "skip_by_runtime_feature: FMAC runtime feature bits are incomplete "
            f"for 0x{int(features):08X}"
        )


# 创建一个只做门禁和Driver构造的FMAC Support Factory。
def build_fmac_support_factory(
    framework_communication,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> FmacSupportFactory:

    runtime_services = framework_communication.runtime_services

    def build(instance_id: int) -> FmacCaseSupport:
        instance_name = require_fmac_static_capability(
            target_capabilities,
            instance_id=instance_id,
        )
        if not any(
            item.service_id == FMAC_SERVICE_ID and item.instance_id == instance_id
            for item in runtime_services
        ):
            pytest.skip(
                f"skip_by_runtime_service: FMAC service 0x{FMAC_SERVICE_ID:04X} "
                f"instance {instance_id} is not registered"
            )
        driver = FmacDriver(framework_communication.target_client, instance_id=instance_id)
        runtime = driver.capabilities_get()
        return FmacCaseSupport(
            instance_id=instance_id,
            instance_name=instance_name,
            crg=CrgDriver(framework_communication.target_client),
            fmac=driver,
            resource=resource_driver,
            runtime=runtime,
        )

    return build


# 在Service注册完整时构造FMAC、DMA和SYSCTRL跨IP编排引用。
def build_fmac_dma_support(
    framework_communication,
    target_capabilities: ChipCapabilities,
    fmac_support_factory: FmacSupportFactory,
    instance_id: int,
    route: FmacDmaRoute,
) -> FmacDmaCaseSupport:

    services = framework_communication.runtime_services
    for service_id, label in ((DMA_SERVICE_ID, "DMA"), (SYSCTRL_SERVICE_ID, "SYSCTRL")):
        if not any(item.service_id == service_id for item in services):
            pytest.skip(f"skip_by_runtime_service: {label} service is not registered")

    target = framework_communication.target_client
    return FmacDmaCaseSupport(
        fmac_support=fmac_support_factory(instance_id),
        dma=DmaDriver(target, instance_id=route.controller),
        sysctrl=SysctrlDriver(target),
        route=route,
    )
