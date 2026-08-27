# Framework Validation测试模块。
#
# 职责：验证test_uart_fixtures 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from inspect import Parameter, signature
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.drivers.dma import DMA_SERVICE_ID
from et_test_platform.drivers.framework import ServiceInfo
from et_test_platform.drivers.resource import RESOURCE_SERVICE_ID
from et_test_platform.drivers.sysctrl import SYSCTRL_SERVICE_ID
from et_test_platform.drivers.uart import UART_SERVICE_ID
from et_test_platform.profiles.bench import UartPairConfig
from et_test_platform.scheduling import fixtures as common_fixture_module
from et_test_platform.test_cases.uart import conftest as fixture_module


class _Framework:
    target_client = object()
    runtime_services = (
        ServiceInfo(UART_SERVICE_ID, 4),
        ServiceInfo(UART_SERVICE_ID, 6),
    )


class _FakeUartDriver:
    def __init__(self, target, *, instance_id: int) -> None:
        self.target = target
        self.instance_id = instance_id


class _Capabilities:
    def __init__(self, instances: tuple[str, ...]) -> None:
        self._instances = instances

    def instances(self, ip_id: str) -> tuple[str, ...]:
        assert ip_id == "uart"
        return self._instances


class _DmaCapabilities:
    def __init__(self, *, dma: tuple[str, ...], uart: tuple[str, ...]) -> None:
        self._instances = {"dma": dma, "uart": uart}

    def instances(self, ip_id: str) -> tuple[str, ...]:
        return self._instances[ip_id]


class _FrameworkWithServices:
    target_client = object()

    def __init__(self, services: tuple[ServiceInfo, ...]) -> None:
        self.runtime_services = services


# 验证公共Resource Fixture在Registry未发现时失败，不允许绕过Service门禁。
def test_common_resource_fixture_requires_discovered_registry() -> None:
    framework = SimpleNamespace(target_client=object())

    with pytest.raises(AttributeError, match="runtime_services"):
        common_fixture_module.resource_driver.__wrapped__(framework)


# 验证UART Fixture在Registry未发现时失败，不允许测试假对象改变正式门禁语义。
def test_uart_role_fixture_requires_discovered_registry() -> None:
    pair = UartPairConfig(control_instance=0, dut_instance=4)
    framework = SimpleNamespace(target_client=object())

    with pytest.raises(AttributeError, match="runtime_services"):
        fixture_module.uart_dut_handle.__wrapped__(framework, pair)


def test_evidence_record_property_is_required_pytest_dependency() -> None:
    for fixture in (
        common_fixture_module.framework_communication,
        fixture_module.uart_peer_handle,
    ):
        parameter = signature(fixture.__wrapped__).parameters["record_property"]
        assert parameter.default is Parameter.empty


def test_uart_role_fixtures_create_selected_handles(monkeypatch) -> None:
    monkeypatch.setattr(fixture_module, "UartDriver", _FakeUartDriver)
    pair = UartPairConfig(control_instance=0, dut_instance=4, peer_instance=6)

    dut = fixture_module.uart_dut_handle.__wrapped__(_Framework(), pair)
    peer = fixture_module.uart_peer_handle.__wrapped__(_Framework(), pair, lambda *_: None)

    assert dut.target is _Framework.target_client
    assert peer.target is _Framework.target_client
    assert dut.instance_id == 4
    assert peer.instance_id == 6


def test_uart_peer_fixture_skips_when_peer_is_not_configured() -> None:
    pair = UartPairConfig(control_instance=0, dut_instance=4)

    with pytest.raises(pytest.skip.Exception, match="peer"):
        fixture_module.uart_peer_handle.__wrapped__(_Framework(), pair, lambda *_: None)


def test_uart_role_fixture_requires_runtime_and_profile_instance(monkeypatch) -> None:
    monkeypatch.setattr(fixture_module, "UartDriver", _FakeUartDriver)
    pair = UartPairConfig(control_instance=0, dut_instance=4, peer_instance=6)
    framework = _FrameworkWithServices((ServiceInfo(UART_SERVICE_ID, 4),))
    capabilities = _Capabilities(("uart4",))

    with pytest.raises(
        pytest.skip.Exception,
        match="skip_by_runtime_service: UART Peer.*instance 6",
    ):
        fixture_module.uart_peer_handle.__wrapped__(
            framework,
            pair,
            lambda *_: None,
            capabilities,
        )


def test_uart_role_fixture_reports_missing_runtime_service(monkeypatch) -> None:
    monkeypatch.setattr(fixture_module, "UartDriver", _FakeUartDriver)
    pair = UartPairConfig(control_instance=0, dut_instance=4)
    framework = _FrameworkWithServices(())
    capabilities = _Capabilities(("uart4",))

    with pytest.raises(
        pytest.skip.Exception,
        match="skip_by_runtime_service:.*instance 4",
    ):
        fixture_module.uart_dut_handle.__wrapped__(
            framework,
            pair,
            capabilities,
        )


# Control UART carries ET-Frame and is not a mutable UART test Service.
def test_uart_pair_fixture_keeps_control_route_outside_test_registry(monkeypatch) -> None:

    pair = UartPairConfig(control_instance=0, dut_instance=4, peer_instance=6)

    monkeypatch.setattr(
        fixture_module,
        "load_uart_pair",
        lambda *args, **kwargs: pair,
    )
    config = type(
        "_Config",
        (),
        {
            "getoption": lambda self, name: {
                "et_hardware": True,
                "et_bench": "bench.yaml",
                "et_target": "dut",
            }[name]
        },
    )()

    assert (
        fixture_module.uart_pair_config.__wrapped__(
            config,
        )
        == pair
    )


def test_dma_fixture_uses_configured_controller_not_first_profile_instance() -> None:
    source = Path(fixture_module.__file__).read_text(encoding="utf-8")
    assert "controller_instance" in source
    assert "dma_instances[0]" not in source


def test_dma_fixture_constructs_configured_controller_after_profile_runtime_gate(
    monkeypatch,
) -> None:
    class _FakeDmaDriver:
        def __init__(self, target, *, instance_id: int) -> None:
            self.target = target
            self.instance_id = instance_id

    monkeypatch.setattr(fixture_module, "DmaDriver", _FakeDmaDriver)
    framework = _FrameworkWithServices(
        (
            ServiceInfo(UART_SERVICE_ID, 4),
            ServiceInfo(UART_SERVICE_ID, 6),
            ServiceInfo(DMA_SERVICE_ID, 1),
            ServiceInfo(RESOURCE_SERVICE_ID, 0),
            ServiceInfo(SYSCTRL_SERVICE_ID, 0),
        )
    )
    capabilities = _DmaCapabilities(
        dma=("dma0", "dma1"),
        uart=("uart4", "uart6"),
    )
    pair = SimpleNamespace(
        controller_instance=1,
        dma_port_instance=4,
        peer_port_instance=6,
    )
    dut = SimpleNamespace(instance_id=4)
    peer = SimpleNamespace(instance_id=6)

    support = fixture_module.dma_support.__wrapped__(
        framework,
        capabilities,
        pair,
        dut,
        peer,
        object(),
    )

    assert support.controller == 1
    assert support.dma.instance_id == 1
