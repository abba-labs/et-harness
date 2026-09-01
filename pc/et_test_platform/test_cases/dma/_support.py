# Formal Case本地Support模块。
#
# 职责：聚合本测试域的只读事实、Driver构造和小粒度复用操作。
# 边界：不隐藏完整Case、不拥有最终断言，也不改变公共Scheduling。
# 依赖：仅依赖本IP Driver、Profile事实和稳定公共工具。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.dma import (
    DMA_SERVICE_ID,
    DmaCapabilities,
    DmaDriver,
    DmaFeature,
    DmaIrqEvent,
    DmaTransferType,
)
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SysctrlDriver
from ...drivers.uart import UartDriver, UartFeature
from ...profiles.bench import DmaPeripheralPairConfig
from ...profiles.capabilities import ChipCapabilities
from ...profiles.chip_execution_mappings import DmaPeripheralDirection
from ...profiles.resolvers.dma_routes import DmaPeripheralRoute, resolve_uart_dma_route

_DMA_IP = "dma"
_TRANSFER_TYPE_OPTION = "transfer_type_and_flow_control"
_MAX_BLOCK_PARAMETER = "max_block_size"
_TRANSFER_DONE_INTERRUPT = "transfer_done"


# 保存一个已 Gate 的 DMA Controller 与共享 Resource Driver；不执行设备操作。
@dataclass(frozen=True, slots=True)
class DmaCaseSupport:
    controller: int
    resource: ResourceDriver
    dma: DmaDriver


# 保存 DMA↔UART Case 已解析的 Route、Driver 与只读能力事实；不执行 Feature 状态变更。
@dataclass(frozen=True, slots=True)
class DmaUartRouteSupport:
    controller: int
    resource: ResourceDriver
    dma: DmaDriver
    dma_capabilities: DmaCapabilities
    sysctrl: SysctrlDriver
    uart_dut: UartDriver
    uart_peer: UartDriver
    pair: DmaPeripheralPairConfig
    route: DmaPeripheralRoute


DmaSupportFactory = Callable[[int], DmaCaseSupport]
DmaUartSupportFactory = Callable[
    [int, DmaPeripheralDirection, UartFeature, UartFeature], DmaUartRouteSupport
]


# 在任何设备动作前核对一个 DMA M2M 向量的静态 Capability，并返回实例名。
def require_dma_m2m_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    channel: int,
    transfer_count: int,
) -> str:

    if instance_id < 0 or channel < 0 or transfer_count <= 0:
        raise ValueError("DMA instance/channel/count is invalid")
    try:
        instances = capabilities.instances(_DMA_IP)
        instance = f"dma{instance_id}"
        if instance not in instances:
            raise UnsupportedCapability(f"DMA instance index {instance_id} is unavailable")
        if "memory_to_memory" not in capabilities.options(
            _DMA_IP,
            _TRANSFER_TYPE_OPTION,
            instance=instance,
        ):
            raise UnsupportedCapability(f"{instance} does not support memory_to_memory")
        member = f"channel_{channel}"
        if member not in capabilities.parameter_members(
            _DMA_IP,
            _MAX_BLOCK_PARAMETER,
            instance=instance,
        ):
            raise UnsupportedCapability(f"{instance}.{member} is unavailable")
        maximum = capabilities.parameter(
            _DMA_IP,
            _MAX_BLOCK_PARAMETER,
            instance=instance,
            member=member,
        )
        if not isinstance(maximum, int) or isinstance(maximum, bool):
            raise UnsupportedCapability(f"{instance}.{member} max_block_size is invalid")
        if transfer_count > maximum:
            raise UnsupportedCapability(f"transfer_count {transfer_count} exceeds {maximum}")
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as exc:
        raise UnsupportedCapability(f"DMA M2M capability is unavailable: {exc}") from exc


# 在访问 DMA 前核对目标 Channel 的 SVD control_writeback Capability，并返回实例名。
def require_dma_control_writeback_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    channel: int,
) -> str:

    if instance_id < 0 or channel < 0:
        raise ValueError("DMA instance and channel must be non-negative")
    try:
        instance = f"dma{instance_id}"
        if instance not in capabilities.instances(_DMA_IP):
            raise UnsupportedCapability(f"DMA instance index {instance_id} is unavailable")
        if not capabilities.has_feature(_DMA_IP, "control_writeback", instance=instance):
            raise UnsupportedCapability(f"{instance} does not support control_writeback")
        enabled = capabilities.parameter(
            _DMA_IP,
            "control_writeback",
            instance=instance,
            member=f"channel_{channel}",
        )
        if enabled is not True:
            raise UnsupportedCapability(
                f"{instance}.channel_{channel} control_writeback is disabled"
            )
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as exc:
        raise UnsupportedCapability(
            f"DMA control_writeback capability is unavailable: {exc}"
        ) from exc


# 在设备动作前核对一个 DMA 传输方向的静态 Capability，并返回已确认的实例名。
def require_dma_transfer_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    transfer_type: int | DmaTransferType,
) -> str:

    transfer = DmaTransferType(transfer_type)
    options = {
        DmaTransferType.MEMORY_TO_MEMORY: "memory_to_memory",
        DmaTransferType.MEMORY_TO_PERIPHERAL: "memory_to_peripheral",
        DmaTransferType.PERIPHERAL_TO_MEMORY: "peripheral_to_memory",
        DmaTransferType.PERIPHERAL_TO_PERIPHERAL: "peripheral_to_peripheral",
    }
    try:
        instances = capabilities.instances(_DMA_IP)
        instance = f"dma{instance_id}"
        if instance not in instances:
            raise UnsupportedCapability(f"DMA instance index {instance_id} is unavailable")
        option = options[transfer]
        if option not in capabilities.options(
            _DMA_IP,
            _TRANSFER_TYPE_OPTION,
            instance=instance,
        ):
            raise UnsupportedCapability(f"{instance} does not support {option}")
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as exc:
        raise UnsupportedCapability(f"DMA transfer capability is unavailable: {exc}") from exc


# 在 Driver 调用前核对 DMA P0 所需的 M2M、Block Size 与 TRANSFER_DONE 静态能力。
def require_dma_transfer_done_capabilities(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    channel: int,
    transfer_count: int,
) -> None:

    if instance_id < 0 or channel < 0 or transfer_count <= 0:
        raise ValueError(
            "instance_id and channel must be non-negative; transfer_count must be positive"
        )
    try:
        instances = capabilities.instances(_DMA_IP)
        instance = f"dma{instance_id}"
        if instance not in instances:
            raise UnsupportedCapability(f"DMA instance index {instance_id} is unavailable")
        transfer_types = capabilities.options(
            _DMA_IP,
            _TRANSFER_TYPE_OPTION,
            instance=instance,
        )
        if "memory_to_memory" not in transfer_types:
            raise UnsupportedCapability(f"{instance} does not support memory_to_memory")
        member = f"channel_{channel}"
        max_block_size = capabilities.parameter(
            _DMA_IP,
            _MAX_BLOCK_PARAMETER,
            instance=instance,
            member=member,
        )
        if (
            isinstance(max_block_size, bool)
            or not isinstance(max_block_size, int)
            or max_block_size <= 0
        ):
            raise UnsupportedCapability(f"{instance}.{member} has invalid max_block_size")
        if transfer_count > max_block_size:
            raise UnsupportedCapability(
                f"transfer_count {transfer_count} exceeds "
                f"{instance}.{member} max_block_size {max_block_size}"
            )
        capabilities.interrupt(
            _DMA_IP,
            _TRANSFER_DONE_INTERRUPT,
            instance=instance,
        )
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as exc:
        raise UnsupportedCapability(
            f"DMA transfer-done P0 capability is unavailable: {exc}"
        ) from exc


# 核对运行中 DMA Service 对 M2M、IRQ、Channel、长度及 TRANSFER_DONE 的只读能力事实。
def require_dma_transfer_done_firmware_capabilities(
    capabilities: DmaCapabilities,
    *,
    channel: int,
    transfer_count: int,
) -> None:

    if channel < 0 or transfer_count <= 0:
        raise ValueError("channel must be non-negative; transfer_count positive")
    if (capabilities.features & DmaFeature.MEMORY_TO_MEMORY) == 0:
        raise UnsupportedCapability("running DMA firmware does not support memory_to_memory")
    if (capabilities.features & DmaFeature.INTERRUPTS) == 0:
        raise UnsupportedCapability("running DMA firmware does not support interrupts")
    if channel >= capabilities.channel_count:
        raise UnsupportedCapability(f"DMA channel {channel} is unavailable in the running firmware")
    if transfer_count > capabilities.max_transfer_count:
        raise UnsupportedCapability(
            f"transfer_count {transfer_count} exceeds running DMA firmware "
            f"limit {capabilities.max_transfer_count}"
        )
    if (capabilities.irq_events & DmaIrqEvent.TRANSFER_DONE) == 0:
        raise UnsupportedCapability("running DMA firmware does not support TRANSFER_DONE interrupt")


# 返回按 Controller 构造 DMA Support 的纯准备函数；失败只产生明确 Skip，不等待硬件。
@pytest.fixture
def dma_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> DmaSupportFactory:

    services = framework_communication.runtime_services
    dma_instances = target_capabilities.instances(_DMA_IP)

    def build(instance_id: int) -> DmaCaseSupport:
        if instance_id < 0:
            raise ValueError("DMA instance ID must be non-negative")
        if not any(
            item.service_id == DMA_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                "skip_by_runtime_service: DMA service "
                f"0x{DMA_SERVICE_ID:04x} instance {instance_id} is not registered"
            )
        instance_name = f"dma{instance_id}"
        if instance_name not in dma_instances:
            pytest.skip(
                "skip_by_chip_capability: DMA instance "
                f"{instance_name} is absent from the profile/runtime intersection"
            )
        return DmaCaseSupport(
            controller=instance_id,
            resource=resource_driver,
            dma=DmaDriver(
                framework_communication.target_client,
                instance_id=instance_id,
            ),
        )

    return build


# 读取并核对 UART Route 对应的 DMA 传输方向；只返回事实，不执行 Feature 动作。
def _require_dma_uart_transfer_capability(
    capabilities: ChipCapabilities,
    dma: DmaDriver,
    direction: DmaPeripheralDirection,
) -> DmaCapabilities:

    instance = f"dma{dma.instance_id}"
    if direction is DmaPeripheralDirection.TX:
        option = "memory_to_peripheral"
        feature = DmaFeature.MEMORY_TO_PERIPHERAL
    else:
        option = "peripheral_to_memory"
        feature = DmaFeature.PERIPHERAL_TO_MEMORY
    try:
        if option not in capabilities.options(
            _DMA_IP,
            _TRANSFER_TYPE_OPTION,
            instance=instance,
        ):
            pytest.skip(f"skip_by_chip_capability: {instance} does not support {option}")
    except CapabilityLookupError as exc:
        pytest.skip(f"skip_by_chip_capability: DMA transfer capability unavailable: {exc}")
    dynamic = dma.capabilities_get()
    if dynamic.features & feature != feature:
        pytest.skip(f"skip_by_runtime_feature: DMA {option} unavailable")
    return dynamic


# 返回 DMA↔UART Route Support 工厂；只查询能力并解析 Route，不修改 UART/DMA/SYSCTRL。
@pytest.fixture
def dma_uart_support_for(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    dma_support_for: DmaSupportFactory,
    sysctrl_driver: SysctrlDriver,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle: UartDriver,
    uart_peer_handle: UartDriver,
) -> DmaUartSupportFactory:

    def build(
        instance_id: int,
        direction: DmaPeripheralDirection,
        dut_feature: UartFeature,
        peer_feature: UartFeature,
    ) -> DmaUartRouteSupport:
        base = dma_support_for(instance_id)
        dma_capabilities = _require_dma_uart_transfer_capability(
            target_capabilities,
            base.dma,
            direction,
        )
        dut_capabilities = uart_dut_handle.capabilities_get()
        peer_capabilities = uart_peer_handle.capabilities_get()
        if dut_capabilities.features & dut_feature != dut_feature:
            pytest.skip(f"skip_by_runtime_feature: UART DUT feature {dut_feature.name} unavailable")
        if peer_capabilities.features & peer_feature != peer_feature:
            pytest.skip(
                f"skip_by_runtime_feature: UART Peer feature {peer_feature.name} unavailable"
            )
        try:
            route = resolve_uart_dma_route(
                target_capabilities,
                dma_peripheral_pair_config,
                direction,
            )
        except UnsupportedCapability as exc:
            pytest.skip(str(exc))
        if route.controller != instance_id:
            pytest.skip(
                "skip_by_execution_mapping: route selects "
                f"DMA{route.controller}, not DMA{instance_id}"
            )
        return DmaUartRouteSupport(
            controller=instance_id,
            resource=base.resource,
            dma=base.dma,
            dma_capabilities=dma_capabilities,
            sysctrl=sysctrl_driver,
            uart_dut=uart_dut_handle,
            uart_peer=uart_peer_handle,
            pair=dma_peripheral_pair_config,
            route=route,
        )

    return build
