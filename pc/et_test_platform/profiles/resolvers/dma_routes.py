# 跨 IP 执行事实 Resolver。
#
# 职责：组合 Chip Capability、Bench 与芯片执行映射，返回强类型事实。
# 边界：不导入具体芯片模块、不导入 Driver/TargetClient、不发送硬件命令、不等待设备，也不执行最终断言。
# 依赖：仅依赖 Profile/Capability Model 和芯片无关的执行映射加载入口。

from __future__ import annotations

from dataclasses import dataclass

from ...core.errors import ConfigurationError, UnsupportedCapability
from ..bench import DmaPeripheralPairConfig
from ..capabilities import ChipCapabilities
from ..chip_execution_mappings import (
    DmaPeripheralDirection,
    load_aes_dma_mapping,
    load_crc_dma_mapping,
    load_dma_input_mappings,
    load_uart_dma_mappings,
)


# PC 完成全部核对后可直接下发的 DMA 外设路由事实。
@dataclass(frozen=True, slots=True)
class DmaPeripheralRoute:
    peripheral: str
    instance_id: int
    direction: DmaPeripheralDirection
    peripheral_address: int
    request_id: int
    controller: int
    interface: int
    address_evidence: str
    request_evidence: str
    bench_evidence: str


# PC 完成 Capability 与芯片映射核对后可执行的 CRC DMA 输入事实。
@dataclass(frozen=True, slots=True)
class CrcDmaInputRoute:
    instance_id: int
    peripheral_address: int
    request_id: int
    controller: int
    interface: int
    address_evidence: str
    request_evidence: str


# 表达经过 Capability 与芯片映射核对的单向外设到内存 DMA 公共执行事实。
@dataclass(frozen=True, slots=True)
class DmaInputRoute:
    peripheral: str
    instance_id: int
    peripheral_address: int
    request_id: int
    controller: int
    interface: int
    address_evidence: str
    request_evidence: str


# AES 双向 DMA 路径的最终执行事实；输入和输出使用不同 DMAMUX Interface。
@dataclass(frozen=True, slots=True)
class AesDmaRoute:
    instance_id: int
    controller: int
    input_interface: int
    output_interface: int
    input_request_id: int
    output_request_id: int
    input_fifo_address: int
    output_fifo_address: int
    input_register_address: int
    output_register_address: int
    address_evidence: str
    request_evidence: str


# 核对当前芯片 UART DMA 静态 Capability、执行映射与 Bench 事实。
def resolve_uart_dma_route(
    capabilities: ChipCapabilities,
    bench: DmaPeripheralPairConfig,
    direction: DmaPeripheralDirection,
) -> DmaPeripheralRoute:

    if not bench.provider.startswith("uart"):
        raise ConfigurationError(f"DMA peripheral provider {bench.provider!r} is not UART")
    mappings = load_uart_dma_mappings(capabilities.chip_id)
    key = (bench.dma_port_instance, direction)
    mapping = mappings.get(key)
    if mapping is None:
        raise UnsupportedCapability(
            f"chip {capabilities.chip_id!r} has no reviewed UART DMA mapping for "
            f"uart{bench.dma_port_instance}.{direction.value}"
        )

    instance = f"uart{bench.dma_port_instance}"
    if instance not in capabilities.instances("uart"):
        raise UnsupportedCapability(f"capability profile has no UART instance {instance!r}")
    identity = capabilities.identity("uart", "base_address", instance=instance)
    try:
        capability_address = int(identity, 0) if isinstance(identity, str) else int(identity)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"UART base address for {instance!r} is not an integer identity"
        ) from exc
    if capability_address != mapping.peripheral_address:
        raise ConfigurationError(
            f"UART address conflict for {instance}: capability=0x{capability_address:x}, "
            f"mapping=0x{mapping.peripheral_address:x}"
        )

    controller = bench.controller_instance
    interface = (
        bench.destination_interface
        if direction is DmaPeripheralDirection.TX
        else bench.source_interface
    )
    if controller not in mapping.allowed_controllers:
        raise UnsupportedCapability(
            f"DMA controller {controller} is not allowed for {instance}.{direction.value}"
        )
    if interface not in mapping.allowed_interfaces:
        raise UnsupportedCapability(
            f"DMA interface {interface} is not allowed for {instance}.{direction.value}"
        )
    dma_instance = f"dma{controller}"
    if dma_instance not in capabilities.instances("dma"):
        raise UnsupportedCapability(f"capability profile has no DMA instance {dma_instance!r}")

    return DmaPeripheralRoute(
        peripheral=mapping.peripheral,
        instance_id=mapping.instance_id,
        direction=mapping.direction,
        peripheral_address=mapping.peripheral_address,
        request_id=mapping.request_id,
        controller=controller,
        interface=interface,
        address_evidence=mapping.address_evidence,
        request_evidence=mapping.request_evidence,
        bench_evidence=(
            f"bench:{bench.provider}:dma{controller}:uart{bench.dma_port_instance}:"
            f"interface{interface}"
        ),
    )


# 核对当前芯片 CRC/DMA Capability 与已审核执行映射，返回首个稳定 Route。
def resolve_crc_dma_input_route(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> CrcDmaInputRoute:

    mapping = load_crc_dma_mapping(capabilities.chip_id)
    instance = f"crc{instance_id}"
    if instance not in capabilities.instances("crc"):
        raise UnsupportedCapability(f"capability profile has no CRC instance {instance!r}")
    if mapping.instance_id != instance_id:
        raise UnsupportedCapability(
            f"chip mapping supports crc{mapping.instance_id}, not {instance}"
        )
    identity = capabilities.identity("crc", "base_address", instance=instance)
    try:
        base_address = int(identity, 0) if isinstance(identity, str) else int(identity)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"CRC base address for {instance!r} is not an integer identity"
        ) from exc
    if not base_address <= mapping.peripheral_address < base_address + 0x1000:
        raise ConfigurationError(
            f"CRC DMA endpoint 0x{mapping.peripheral_address:x} is outside {instance}"
        )
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
    return CrcDmaInputRoute(
        instance_id=instance_id,
        peripheral_address=mapping.peripheral_address,
        request_id=mapping.request_id,
        controller=controller,
        interface=mapping.allowed_interfaces[0],
        address_evidence=mapping.address_evidence,
        request_evidence=mapping.request_evidence,
    )


# 核对单向外设 DMA Endpoint、静态 Capability 与芯片执行映射。
def resolve_dma_input_route(
    capabilities: ChipCapabilities,
    *,
    peripheral: str,
    instance_id: int,
    register_span: int = 0x1000,
) -> DmaInputRoute:

    mappings = load_dma_input_mappings(capabilities.chip_id, peripheral)
    mapping = mappings.get(instance_id)
    instance = f"{peripheral}{instance_id}"
    if mapping is None:
        raise UnsupportedCapability(
            f"chip {capabilities.chip_id!r} has no reviewed DMA input mapping for {instance}"
        )
    if instance not in capabilities.instances(peripheral):
        raise UnsupportedCapability(f"capability profile has no {peripheral.upper()} {instance!r}")

    identity = capabilities.identity(peripheral, "base_address", instance=instance)
    try:
        base_address = int(identity, 0) if isinstance(identity, str) else int(identity)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"{peripheral.upper()} base address for {instance!r} is not an integer identity"
        ) from exc
    if not base_address <= mapping.peripheral_address < base_address + register_span:
        raise ConfigurationError(
            f"{peripheral.upper()} DMA endpoint 0x{mapping.peripheral_address:x} is outside "
            f"{instance}"
        )

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

    return DmaInputRoute(
        peripheral=mapping.peripheral,
        instance_id=mapping.instance_id,
        peripheral_address=mapping.peripheral_address,
        request_id=mapping.request_id,
        controller=controller,
        interface=mapping.allowed_interfaces[0],
        address_evidence=mapping.address_evidence,
        request_evidence=mapping.request_evidence,
    )


# 核对 AES/DMA Capability 与芯片执行映射，选择两个互不冲突的接口。
def resolve_aes_dma_route(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> AesDmaRoute:

    mapping = load_aes_dma_mapping(capabilities.chip_id)
    instance = f"aes{instance_id}"
    if instance not in capabilities.instances("aes"):
        raise UnsupportedCapability(f"capability profile has no AES instance {instance!r}")
    if mapping.instance_id != instance_id:
        raise UnsupportedCapability(
            f"chip mapping supports aes{mapping.instance_id}, not {instance}"
        )
    identity = capabilities.identity("aes", "base_address", instance=instance)
    try:
        base_address = int(identity, 0) if isinstance(identity, str) else int(identity)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"AES base address for {instance!r} is not an integer identity"
        ) from exc
    endpoints = (
        mapping.input_fifo_address,
        mapping.output_fifo_address,
        mapping.input_register_address,
        mapping.output_register_address,
    )
    if any(not base_address <= endpoint < base_address + 0x1000 for endpoint in endpoints):
        raise ConfigurationError(f"AES DMA endpoint is outside {instance}")

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
    return AesDmaRoute(
        instance_id=instance_id,
        controller=controller,
        input_interface=input_interface,
        output_interface=output_interface,
        input_request_id=mapping.input_request_id,
        output_request_id=mapping.output_request_id,
        input_fifo_address=mapping.input_fifo_address,
        output_fifo_address=mapping.output_fifo_address,
        input_register_address=mapping.input_register_address,
        output_register_address=mapping.output_register_address,
        address_evidence=mapping.address_evidence,
        request_evidence=mapping.request_evidence,
    )
