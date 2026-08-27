# Framework Validation测试模块。
#
# 职责：验证test_dma_support 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.drivers.dma import DMA_SERVICE_ID, DmaFeature
from et_test_platform.drivers.uart import UartFeature
from et_test_platform.profiles.chip_execution_mappings.et6801 import DmaPeripheralDirection
from et_test_platform.profiles.resolvers.dma_routes import DmaPeripheralRoute
from et_test_platform.test_cases.dma import _support as support_module
from et_test_platform.test_cases.dma import conftest as fixture_module

ROOT = Path(__file__).parents[6]
SUPPORT_SOURCE = ROOT / "pc/et_test_platform/test_cases/dma/_support.py"


class _Capabilities:
    def instances(self, ip_name: str) -> tuple[str, ...]:
        assert ip_name == "dma"
        return ("dma0", "dma1")

    def options(self, ip_name: str, feature_name: str, *, instance: str) -> tuple[str, ...]:
        assert ip_name == "dma"
        assert feature_name == "transfer_type_and_flow_control"
        assert instance in {"dma0", "dma1"}
        return (
            "memory_to_memory",
            "memory_to_peripheral",
            "peripheral_to_memory",
            "peripheral_to_peripheral",
        )


class _Framework:
    target_client = object()
    runtime_services = (
        SimpleNamespace(service_id=DMA_SERVICE_ID, instance_id=0),
        SimpleNamespace(service_id=DMA_SERVICE_ID, instance_id=1),
    )


class _Uart:
    def __init__(self, features: UartFeature) -> None:
        self._features = features

    def capabilities_get(self):
        return SimpleNamespace(features=self._features)


# 验证DMA实例选择必须依赖已发现Registry，不允许缺失运行时事实时退回静态Profile。
def test_dma_instance_fixture_requires_discovered_registry() -> None:
    framework = SimpleNamespace(target_client=object())

    with pytest.raises(AttributeError, match="runtime_services"):
        fixture_module.dma_instance_ids.__wrapped__(
            framework,
            _Capabilities(),
        )


def test_dma_support_factory_builds_selected_controller_without_device_io() -> None:
    resource = object()
    factory = support_module.dma_support_for.__wrapped__(
        _Framework(),
        _Capabilities(),
        resource,
    )

    support = factory(1)

    assert support.controller == 1
    assert support.resource is resource
    assert support.dma.instance_id == 1
    assert support.dma._target is _Framework.target_client


def test_dma_local_fixture_derives_instances_from_capability_and_runtime_registry() -> None:
    instance_ids = fixture_module.dma_instance_ids.__wrapped__(
        _Framework(),
        _Capabilities(),
    )

    assert instance_ids == (0, 1)
    assert fixture_module.dma_representative_instance_id.__wrapped__(instance_ids) == 0


def test_dma_local_fixture_uses_capability_and_runtime_intersection() -> None:
    framework = SimpleNamespace(
        runtime_services=(SimpleNamespace(service_id=DMA_SERVICE_ID, instance_id=0),)
    )

    instance_ids = fixture_module.dma_instance_ids.__wrapped__(
        framework,
        _Capabilities(),
    )

    assert instance_ids == (0,)


def test_dma_support_factory_skips_unregistered_controller() -> None:
    resource = object()
    factory = support_module.dma_support_for.__wrapped__(
        _Framework(),
        _Capabilities(),
        resource,
    )

    with pytest.raises(pytest.skip.Exception, match="runtime_service"):
        factory(2)


def test_dma_uart_support_factory_returns_route_and_runtime_facts_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = object()
    dynamic = SimpleNamespace(features=DmaFeature.PERIPHERAL_TO_MEMORY)
    dma = SimpleNamespace(instance_id=1, capabilities_get=lambda: dynamic)
    base_support = SimpleNamespace(controller=1, resource=resource, dma=dma)
    sysctrl = object()
    pair = object()
    dut = _Uart(UartFeature.RX_DMA | UartFeature.TX_DMA)
    peer = _Uart(UartFeature.RX_POLLING | UartFeature.TX_POLLING)
    route = DmaPeripheralRoute(
        peripheral="uart",
        instance_id=1,
        direction=DmaPeripheralDirection.RX,
        peripheral_address=0x40501000,
        request_id=194,
        controller=1,
        interface=2,
        address_evidence="unit:address",
        request_evidence="unit:request",
        bench_evidence="unit:bench",
    )
    resolver_calls: list[DmaPeripheralDirection] = []

    def resolve(*args):
        resolver_calls.append(args[-1])
        return route

    monkeypatch.setattr(support_module, "resolve_uart_dma_route", resolve)
    factory = support_module.dma_uart_support_for.__wrapped__(
        _Framework(),
        _Capabilities(),
        lambda instance_id: base_support if instance_id == 1 else None,
        sysctrl,
        pair,
        dut,
        peer,
    )

    support = factory(
        1,
        DmaPeripheralDirection.RX,
        UartFeature.RX_DMA,
        UartFeature.TX_POLLING,
    )

    assert support.controller == 1
    assert support.resource is resource
    assert support.dma is dma
    assert support.dma_capabilities is dynamic
    assert support.sysctrl is sysctrl
    assert support.uart_dut is dut
    assert support.uart_peer is peer
    assert support.pair is pair
    assert support.route == route
    assert resolver_calls == [DmaPeripheralDirection.RX]


def test_dma_support_source_contains_no_feature_mutation_or_wait() -> None:
    source = SUPPORT_SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        ".controller_enable(",
        ".configure(",
        ".configure_route(",
        ".dma_enable_set(",
        ".initialize(",
        ".start(",
        ".stop(",
        ".deconfigure(",
        ".wait_",
        ".reset(",
        "cleanup_actions",
    ):
        assert forbidden not in source
