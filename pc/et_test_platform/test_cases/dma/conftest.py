# Formal Case的pytest Fixture入口。
#
# 职责：提供运行时事实门禁和Driver构造。
# 边界：不执行Feature动作、不拥有最终断言，也不隐藏完整Case。
# 依赖：仅依赖pytest、Profile、Capability和稳定Driver接口。

from __future__ import annotations

from collections.abc import Callable

import pytest

from ...core.errors import CapabilityLookupError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID
from ...drivers.framework import FrameworkDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...drivers.uart import UART_SERVICE_ID, UartDriver
from ...profiles.bench import (
    DmaPeripheralPairConfig,
    UartPairConfig,
    load_dma_peripheral_pair,
    load_uart_pair,
)
from ...profiles.capabilities import ChipCapabilities
from ...scheduling.run_context import record_evidence, require_evidence
from ._support import dma_support_for, dma_uart_support_for


# 把平台稳定实例名 ``dma<N>`` 转为 Firmware Service Instance ID。
def _dma_instance_index(instance_name: str) -> int:

    prefix = "dma"
    suffix = instance_name.removeprefix(prefix)
    if not instance_name.startswith(prefix) or not suffix.isdecimal():
        raise pytest.UsageError(f"invalid DMA capability instance name: {instance_name!r}")
    return int(suffix)


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


# 校验作为 DMA 外设端点的 UART 实例，不改变 UART 状态。
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


# 返回静态 Capability 声明且运行时已注册的全部 DMA 实例。
@pytest.fixture
def dma_instance_ids(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
) -> tuple[int, ...]:

    declared_ids = tuple(_dma_instance_index(name) for name in target_capabilities.instances("dma"))
    if not declared_ids:
        pytest.skip("skip_by_chip_capability: DMA has no declared instance")
    services = framework_communication.runtime_services
    runtime_ids = {item.instance_id for item in services if item.service_id == DMA_SERVICE_ID}
    instance_ids = tuple(instance_id for instance_id in declared_ids if instance_id in runtime_ids)
    if not instance_ids:
        pytest.skip("skip_by_runtime_service: no DMA instance is shared by capability and registry")
    return instance_ids


# 选择 Capability/Runtime 交集中的首个 DMA 实例执行普通 Feature Case。
@pytest.fixture(name="instance_id")
def dma_representative_instance_id(dma_instance_ids: tuple[int, ...]) -> int:

    return dma_instance_ids[0]


# 选择运行时报告的首个有效 Channel 执行普通 Feature Case。
@pytest.fixture(name="channel")
def dma_representative_channel(
    dma_support_for,
    instance_id: int,
) -> int:

    channel_count = dma_support_for(instance_id).dma.capabilities_get().channel_count
    if channel_count <= 0:
        pytest.skip("skip_by_runtime_feature: DMA has no channel")
    return 0


# 为明确的 Channel 边界 Feature 动态选择首、末通道；不会展开中间通道或 Controller 笛卡尔积。
@pytest.fixture(params=("first", "last"), ids=("first-channel", "last-channel"))
def dma_boundary_channel(
    request: pytest.FixtureRequest,
    dma_support_for,
    instance_id: int,
) -> int:

    channel_count = dma_support_for(instance_id).dma.capabilities_get().channel_count
    if channel_count <= 0:
        pytest.skip("skip_by_runtime_feature: DMA has no channel")
    if request.param == "first":
        return 0
    return channel_count - 1


# 校验 SYSCTRL Service 后构造 DMA Case 使用的 Driver。
@pytest.fixture
def sysctrl_driver(framework_communication: FrameworkDriver) -> SysctrlDriver:

    _require_runtime_service(framework_communication, SYSCTRL_SERVICE_ID, 0, "SYSCTRL")
    return SysctrlDriver(framework_communication.target_client)


# 校验 CRG Service 后构造 DMA Reset/Clock Case 使用的 Driver。
@pytest.fixture
def crg_driver(framework_communication: FrameworkDriver) -> CrgDriver:

    _require_runtime_service(framework_communication, CRG_SERVICE_ID, 0, "CRG")
    return CrgDriver(framework_communication.target_client)


# 加载 DMA 外设 Case 的 Bench 关系，不解析 Request ID 或发送命令。
@pytest.fixture
def dma_peripheral_pair_config(pytestconfig: pytest.Config) -> DmaPeripheralPairConfig:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for hardware Cases")
    return load_dma_peripheral_pair(bench, pytestconfig.getoption("et_target"))


# 加载 DMA 外设端点使用的 UART DUT/Peer 角色。
@pytest.fixture
def uart_pair_config(pytestconfig: pytest.Config) -> UartPairConfig:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for hardware Cases")
    return load_uart_pair(bench, pytestconfig.getoption("et_target"))


# 构造 DMA 外设 Case 使用的 UART DUT Driver。
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


# 构造 DMA 外设 Case 使用的 UART Peer Driver，并登记 Peer Evidence。
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


__all__ = ("dma_support_for", "dma_uart_support_for")
