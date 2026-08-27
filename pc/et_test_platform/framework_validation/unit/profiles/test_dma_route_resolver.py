# Framework Validation测试模块。
#
# 职责：验证test_dma_route_resolver 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from dataclasses import replace

import pytest

from et_test_platform.core.errors import ConfigurationError, UnsupportedCapability
from et_test_platform.profiles.bench import DmaPeripheralPairConfig
from et_test_platform.profiles.capabilities import load_packaged_chip_capabilities
from et_test_platform.profiles.chip_execution_mappings.et6801 import (
    ET6801_UART_DMA_MAPPINGS,
    DmaPeripheralDirection,
)
from et_test_platform.profiles.resolvers.dma_routes import (
    resolve_aes_dma_route,
    resolve_dma_input_route,
    resolve_uart_dma_route,
)


def _bench(**changes: object) -> DmaPeripheralPairConfig:
    base = DmaPeripheralPairConfig(
        provider="uart_loopback",
        controller_instance=0,
        dma_port_instance=1,
        peer_port_instance=2,
        source_interface=0,
        destination_interface=1,
        baudrate=115200,
        data_bits=8,
        parity=0,
        stop_bits=1,
    )
    return replace(base, **changes)


def test_et6801_uart0_to_uart2_mapping_matches_reviewed_sources() -> None:
    expected = {
        (0, DmaPeripheralDirection.TX): (0x40500000, 192),
        (0, DmaPeripheralDirection.RX): (0x40500000, 193),
        (1, DmaPeripheralDirection.TX): (0x40501000, 194),
        (1, DmaPeripheralDirection.RX): (0x40501000, 195),
        (2, DmaPeripheralDirection.TX): (0x40502000, 196),
        (2, DmaPeripheralDirection.RX): (0x40502000, 197),
    }

    assert {
        key: (item.peripheral_address, item.request_id)
        for key, item in ET6801_UART_DMA_MAPPINGS.items()
    } == expected
    assert all(item.address_evidence for item in ET6801_UART_DMA_MAPPINGS.values())
    assert all(item.request_evidence for item in ET6801_UART_DMA_MAPPINGS.values())


def test_resolver_selects_destination_interface_for_uart_tx() -> None:
    route = resolve_uart_dma_route(
        load_packaged_chip_capabilities("et6801"),
        _bench(),
        DmaPeripheralDirection.TX,
    )

    assert route.instance_id == 1
    assert route.peripheral_address == 0x40501000
    assert route.request_id == 194
    assert route.controller == 0
    assert route.interface == 1


def test_resolver_selects_source_interface_for_uart_rx() -> None:
    route = resolve_uart_dma_route(
        load_packaged_chip_capabilities("et6801"),
        _bench(),
        DmaPeripheralDirection.RX,
    )

    assert route.request_id == 195
    assert route.interface == 0


def test_resolver_selects_distinct_interfaces_for_et6801_aes() -> None:
    route = resolve_aes_dma_route(
        load_packaged_chip_capabilities("et6801"),
        instance_id=0,
    )

    assert route.controller == 0
    assert route.input_interface != route.output_interface
    assert route.input_request_id == 112
    assert route.output_request_id == 113
    assert route.input_fifo_address == 0x4020505C
    assert route.output_register_address == 0x40205064


def test_resolver_selects_reviewed_stimer_dma_input_route() -> None:
    route = resolve_dma_input_route(
        load_packaged_chip_capabilities("et6801"),
        peripheral="stimer",
        instance_id=0,
    )

    assert route.peripheral == "stimer"
    assert route.instance_id == 0
    assert route.peripheral_address == 0x4040600C
    assert route.request_id == 104
    assert route.controller == 0
    assert route.interface == 0


def test_resolver_selects_last_reviewed_stimer_instance() -> None:
    route = resolve_dma_input_route(
        load_packaged_chip_capabilities("et6801"),
        peripheral="stimer",
        instance_id=5,
    )

    assert route.instance_id == 5
    assert route.peripheral_address == 0x4040B00C
    assert route.request_id == 109


def test_resolver_rejects_unreviewed_uart_mapping() -> None:
    with pytest.raises(UnsupportedCapability, match="no reviewed UART DMA mapping"):
        resolve_uart_dma_route(
            load_packaged_chip_capabilities("et6801"),
            _bench(dma_port_instance=3),
            DmaPeripheralDirection.TX,
        )


def test_resolver_rejects_non_uart_bench_provider() -> None:
    with pytest.raises(ConfigurationError, match="not UART"):
        resolve_uart_dma_route(
            load_packaged_chip_capabilities("et6801"),
            _bench(provider="spi_loopback"),
            DmaPeripheralDirection.TX,
        )
