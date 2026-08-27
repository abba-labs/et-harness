# Formal Case的pytest Fixture入口。
#
# 职责：提供运行时事实门禁和Driver构造。
# 边界：不执行Feature动作、不拥有最终断言，也不隐藏完整Case。
# 依赖：仅依赖pytest、Profile、Capability和稳定Driver接口。

from __future__ import annotations

from collections.abc import Callable

import pytest

from ...core.errors import CapabilityLookupError, ConfigurationError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver, DmaFeature
from ...drivers.framework import FrameworkDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...drivers.uart import UART_SERVICE_ID, UartDriver, UartFeature
from ...profiles.bench import (
    DmaPeripheralPairConfig,
    UartPairConfig,
    load_dma_peripheral_pair,
    load_uart_pair,
)
from ...profiles.capabilities import ChipCapabilities
from ...profiles.chip_execution_mappings import DmaPeripheralDirection
from ...profiles.resolvers.dma_routes import resolve_uart_dma_route
from ...scheduling.run_context import record_evidence, require_evidence
from ._support import DmaExecutionSupport, UartDmaFullDuplexSupport, UartDmaSupport


# 校验 CRG Service 已注册，并为 Case 提供稳定的模块复位入口。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    if not any(
        item.service_id == CRG_SERVICE_ID and item.instance_id == 0
        for item in framework_communication.runtime_services
    ):
        pytest.skip("skip_by_runtime_service: CRG service instance 0 is not registered")
    return CrgDriver(framework_communication.target_client)


# 读取已发现的 Service；保留直接调用 Fixture 的轻量 Unit Test 兼容。
# 在任何 Feature Mutation 前校验本 IP 所需的 Firmware Service。
def _require_runtime_service(
    framework_communication: FrameworkDriver,
    service_id: int,
    instance_id: int,
    label: str,
) -> None:
    services = framework_communication.runtime_services
    if not any(
        item.service_id == service_id and item.instance_id == instance_id for item in services
    ):
        pytest.skip(
            f"skip_by_runtime_service: {label} service 0x{service_id:04x} "
            f"instance {instance_id} is not registered"
        )


# 校验 UART 实例同时存在于 Runtime Registry 和静态 Chip Capability。
def _require_uart_runtime_instance(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities | None,
    instance_id: int,
    role: str,
) -> None:

    _require_runtime_service(framework_communication, UART_SERVICE_ID, instance_id, f"UART {role}")
    if target_capabilities is None:
        return
    instance_name = f"uart{instance_id}"
    try:
        uart_instances = target_capabilities.instances("uart")
    except CapabilityLookupError:
        pytest.skip("skip_by_chip_capability: UART is absent from the generated profile")
    if instance_name not in uart_instances:
        pytest.skip(
            f"skip_by_chip_capability: UART {role} instance {instance_name} "
            "is absent from the generated profile"
        )


# 读取 UART Runtime Capability；不执行 Feature Mutation。
def _require_uart_feature(uart: UartDriver, feature: UartFeature) -> None:

    capabilities = uart.capabilities_get()
    if capabilities.features & feature != feature:
        pytest.skip(f"skip_by_runtime_feature: UART DUT feature {feature.name} unavailable")


# 在 Feature Gate 后解析一条不可变 UART DMA Route。
def _resolve_uart_dma_support(
    *,
    target_capabilities: ChipCapabilities,
    dma_support: DmaExecutionSupport,
    pair: DmaPeripheralPairConfig,
    uart_dut: UartDriver,
    uart_peer: UartDriver,
    direction: DmaPeripheralDirection,
) -> UartDmaSupport:

    feature = UartFeature.TX_DMA if direction is DmaPeripheralDirection.TX else UartFeature.RX_DMA
    _require_uart_feature(uart_dut, feature)
    route = resolve_uart_dma_route(
        target_capabilities,
        pair,
        direction,
    )
    if route.controller != dma_support.controller:
        raise ConfigurationError(
            f"UART {direction.value.upper()} DMA route controller does not match prepared "
            f"DMA support: route={route.controller}, support={dma_support.controller}"
        )
    return UartDmaSupport(
        resource=dma_support.resource,
        dma=dma_support.dma,
        sysctrl=dma_support.sysctrl,
        uart_dut=uart_dut,
        uart_peer=uart_peer,
        pair=pair,
        route=route,
    )


# 加载 UART DUT/Peer/Control 角色，只解析 Bench 拓扑。
@pytest.fixture
def uart_pair_config(pytestconfig: pytest.Config) -> UartPairConfig:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for hardware Cases")
    return load_uart_pair(bench, pytestconfig.getoption("et_target"))


# 校验 DUT UART 后构造对应 Instance Driver。
@pytest.fixture
def uart_dut_handle(
    framework_communication: FrameworkDriver,
    uart_pair_config: UartPairConfig,
    target_capabilities: ChipCapabilities | None = None,
) -> UartDriver:

    _require_uart_runtime_instance(
        framework_communication,
        target_capabilities,
        uart_pair_config.dut_instance,
        "DUT",
    )
    return UartDriver(
        framework_communication.target_client,
        instance_id=uart_pair_config.dut_instance,
    )


# 校验并构造 UART Peer Driver，同时登记 Peer Evidence。
@pytest.fixture
def uart_peer_handle(
    framework_communication: FrameworkDriver,
    uart_pair_config: UartPairConfig,
    record_property: Callable[[str, object], None],
    target_capabilities: ChipCapabilities | None = None,
) -> UartDriver:

    if uart_pair_config.peer_instance is None:
        pytest.skip("UART peer role is not configured")
    _require_uart_runtime_instance(
        framework_communication,
        target_capabilities,
        uart_pair_config.peer_instance,
        "Peer",
    )
    driver = UartDriver(
        framework_communication.target_client,
        instance_id=uart_pair_config.peer_instance,
    )
    require_evidence(record_property, "peer")
    record_evidence(record_property, "peer")
    return driver


# 加载 UART DMA Case 使用的 Bench 配测关系。
@pytest.fixture
def dma_peripheral_pair_config(pytestconfig: pytest.Config) -> DmaPeripheralPairConfig:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for hardware Cases")
    return load_dma_peripheral_pair(bench, pytestconfig.getoption("et_target"))


# 为 UART DMA Case 构造经 Gate 的 DMA/SYSCTRL Driver 聚合。
@pytest.fixture
def dma_support(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle: UartDriver,
    uart_peer_handle: UartDriver,
    resource_driver: ResourceDriver,
) -> DmaExecutionSupport:

    controller = dma_peripheral_pair_config.controller_instance
    _require_runtime_service(framework_communication, DMA_SERVICE_ID, controller, "DMA")
    _require_runtime_service(framework_communication, SYSCTRL_SERVICE_ID, 0, "SYSCTRL")
    try:
        dma_instances = target_capabilities.instances("dma")
    except CapabilityLookupError:
        pytest.skip("skip_by_capability: no DMA instance in generated profile")
    controller_name = f"dma{controller}"
    if controller_name not in dma_instances:
        pytest.skip(
            f"skip_by_capability: configured DMA controller {controller_name} "
            "is absent from the generated profile"
        )
    if dma_peripheral_pair_config.dma_port_instance != uart_dut_handle.instance_id:
        pytest.skip("skip_by_bench: DMA port does not match UART DUT instance")
    if dma_peripheral_pair_config.peer_port_instance != uart_peer_handle.instance_id:
        pytest.skip("skip_by_bench: peer port does not match UART Peer instance")
    return DmaExecutionSupport(
        controller=controller,
        resource=resource_driver,
        dma=DmaDriver(framework_communication.target_client, instance_id=controller),
        sysctrl=SysctrlDriver(framework_communication.target_client),
    )


# 提供 UART TX DMA Case 已 Gate/Resolve 的环境事实。
@pytest.fixture
def uart_dma_tx_support(
    target_capabilities: ChipCapabilities,
    dma_support: DmaExecutionSupport,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle: UartDriver,
    uart_peer_handle: UartDriver,
) -> UartDmaSupport:

    return _resolve_uart_dma_support(
        target_capabilities=target_capabilities,
        dma_support=dma_support,
        pair=dma_peripheral_pair_config,
        uart_dut=uart_dut_handle,
        uart_peer=uart_peer_handle,
        direction=DmaPeripheralDirection.TX,
    )


# 提供 UART RX DMA Case 已 Gate/Resolve 的环境事实。
@pytest.fixture
def uart_dma_rx_support(
    target_capabilities: ChipCapabilities,
    dma_support: DmaExecutionSupport,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle: UartDriver,
    uart_peer_handle: UartDriver,
) -> UartDmaSupport:

    return _resolve_uart_dma_support(
        target_capabilities=target_capabilities,
        dma_support=dma_support,
        pair=dma_peripheral_pair_config,
        uart_dut=uart_dut_handle,
        uart_peer=uart_peer_handle,
        direction=DmaPeripheralDirection.RX,
    )


# 提供 UART 双向 DMA Case 的两条 Route 和只读 Runtime Capability。
@pytest.fixture
def uart_dma_full_duplex_support(
    target_capabilities: ChipCapabilities,
    dma_support: DmaExecutionSupport,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle: UartDriver,
    uart_peer_handle: UartDriver,
) -> UartDmaFullDuplexSupport:

    _require_uart_feature(uart_dut_handle, UartFeature.TX_DMA)
    _require_uart_feature(uart_dut_handle, UartFeature.RX_DMA)
    tx_route = resolve_uart_dma_route(
        target_capabilities,
        dma_peripheral_pair_config,
        DmaPeripheralDirection.TX,
    )
    rx_route = resolve_uart_dma_route(
        target_capabilities,
        dma_peripheral_pair_config,
        DmaPeripheralDirection.RX,
    )
    if tx_route.controller != rx_route.controller or tx_route.controller != dma_support.controller:
        raise ConfigurationError(
            "UART full-duplex DMA routes must use the prepared controller: "
            f"tx={tx_route.controller}, rx={rx_route.controller}, "
            f"support={dma_support.controller}"
        )
    if tx_route.interface == rx_route.interface:
        raise ConfigurationError("UART full-duplex DMA requires distinct TX/RX interfaces")
    dma_capabilities = dma_support.dma.capabilities_get()
    if (
        not dma_capabilities.features & DmaFeature.ATOMIC_CHANNEL_MASK_START
        or dma_capabilities.channel_count < 2
    ):
        pytest.skip(
            "skip_by_runtime_feature: DMA full duplex requires atomic start and two channels"
        )
    return UartDmaFullDuplexSupport(
        resource=dma_support.resource,
        dma=dma_support.dma,
        sysctrl=dma_support.sysctrl,
        uart_dut=uart_dut_handle,
        uart_peer=uart_peer_handle,
        pair=dma_peripheral_pair_config,
        tx_route=tx_route,
        rx_route=rx_route,
        dma_capabilities=dma_capabilities,
    )
