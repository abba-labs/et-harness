# DMA P2 Formal Case。
#
# 职责：验证 LLI、Combined IRQ、UART外设DMA、Software Handshake、Alias和CRG恢复路径。
# 边界：只通过公共 Driver/Resolver/Bench 操作，不直接访问寄存器或芯片地址。
# 依赖：仅依赖 DMA/UART/SYSCTRL/CRG公共接口与Canonical Evidence接口。

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...core.errors import UnsupportedCapability
from ...drivers.crg import CrgDriver, CrgPeripheral
from ...drivers.dma import (
    DmaAccessView,
    DmaAddressMode,
    DmaConfig,
    DmaFeature,
    DmaHandshakeMode,
    DmaHandshakeTarget,
    DmaIrqEvent,
    DmaSoftwareRequestKind,
    DmaTransferType,
    DmaUpdateMode,
)
from ...drivers.framework import FrameworkDriver
from ...drivers.sysctrl import DmaRequestRoute, SysctrlDriver
from ...drivers.uart import UartFeature
from ...profiles.bench import DmaPeripheralPairConfig
from ...profiles.capabilities import ChipCapabilities
from ...profiles.chip_execution_mappings import DmaPeripheralDirection
from ...profiles.resolvers.dma_routes import resolve_uart_dma_route
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    DmaSupportFactory,
    DmaUartSupportFactory,
    require_dma_m2m_capability,
    require_dma_transfer_capability,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("dma")]

DMA_LLI_DESCRIPTOR_SIZE = 28


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _descriptor_words(raw: bytes) -> list[int]:
    return [
        int.from_bytes(raw[offset : offset + 4], "little")
        for offset in range(0, DMA_LLI_DESCRIPTOR_SIZE, 4)
    ]


def _descriptor_chain_valid(
    descriptor_words: list[list[int]],
    descriptor_addresses: list[int],
) -> bool:
    if len(descriptor_words) != len(descriptor_addresses):
        return False
    for index, words in enumerate(descriptor_words):
        if len(words) != 7:
            return False
        expected_next = (
            descriptor_addresses[index + 1] & 0xFFFFFFFF
            if index + 1 < len(descriptor_addresses)
            else 0
        )
        if words[2] != expected_next:
            return False
    return True


def _uart_init_kwargs(config: DmaPeripheralPairConfig) -> dict[str, int]:
    return {
        "baudrate": config.baudrate,
        "data_bits": config.data_bits,
        "parity": config.parity,
        "stop_bits": config.stop_bits,
    }


def _require_route_controller(route, instance_id: int) -> None:
    if route.controller != instance_id:
        raise UnsupportedCapability(
            f"UART DMA route selects controller {route.controller}, not requested DMA{instance_id}"
        )


def _software_handshake_features(handshake_mode: DmaHandshakeMode) -> DmaFeature:
    return (
        DmaFeature.SOFTWARE_HANDSHAKE
        if handshake_mode is DmaHandshakeMode.SOFTWARE
        else DmaFeature(0)
    )


# =============================================================================
# Linked List
# =============================================================================


# 测试 Feature：
# 1. 双端 LLI 的 2/3/4 节点有限 Descriptor Chain。
#
# 测试方法：
# 1. 构造分离 Source/Destination 与真实 Next Address 链，执行后读取全部数据与 Descriptor。
#
# 通过条件：
# 1. Descriptor 链结构正确、全部目标块数据一致且 Channel Free。
@pytest.mark.parametrize("block_count", [2, 3, 4])
def test_dma_p2_001_finite_lli_chain(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    block_count: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：双端 LLI 的 2/3/4 节点有限 Descriptor Chain。
    # 测试方法：构造分离 Source/Destination 与真实 Next Address 链，执行后读取全部数据与 Descriptor。
    # 通过条件：Descriptor 链结构正确、全部目标块数据一致且 Channel Free。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    block_size = 32
    patterns = [
        bytes(((block * 53) + (index * 17) + 3) & 0xFF for index in range(block_size))
        for block in range(block_count)
    ]
    controller_enabled = False
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source_blocks = [resource.create(block_size + 4) for _ in patterns]
        destination_blocks = [resource.create(block_size + 4) for _ in patterns]
        descriptors = [resource.create(DMA_LLI_DESCRIPTOR_SIZE, alignment=4) for _ in patterns]
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for source, destination, data in zip(
            source_blocks, destination_blocks, patterns, strict=True
        ):
            resource.write(source, data)
            resource.fill(destination, 0xA5)
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for index, descriptor in enumerate(descriptors):
            next_address = descriptors[index + 1].address if index + 1 < block_count else 0
            dma.lli_descriptor_init_v2(
                descriptor.address,
                DmaConfig(
                    channel=0,
                    source_address=source_blocks[index].address,
                    destination_address=destination_blocks[index].address,
                    transfer_count=block_size,
                    source_update_mode=DmaUpdateMode.LINKED_LIST,
                    destination_update_mode=DmaUpdateMode.LINKED_LIST,
                    linked_list_address=next_address,
                ),
                is_last=index == block_count - 1,
            )

        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source_blocks[0].address,
                destination_address=destination_blocks[0].address,
                transfer_count=block_size,
                source_update_mode=DmaUpdateMode.LINKED_LIST,
                destination_update_mode=DmaUpdateMode.LINKED_LIST,
                linked_list_address=descriptors[0].address,
            )
        )
        configured = True
        dma.start(0)
        dma.wait_channel_free(0, timeout_s=2.0)
        actual = b"".join(resource.read(item, block_size) for item in destination_blocks)
        expected = b"".join(patterns)
        words = [_descriptor_words(resource.read(item)) for item in descriptors]
        descriptor_addresses = [item.address for item in descriptors]
        chain_valid = _descriptor_chain_valid(words, descriptor_addresses)
        status = dma.channel_status(0)

        record_property("block_count", block_count)
        record_property("data_match", actual == expected)
        record_property("descriptor_chain_valid", chain_valid)
        record_observation(
            record_property,
            key="descriptor_words",
            value=words,
            source="dut",
            endpoint="LLI_DESCRIPTOR.NEXT_ADDRESS",
        )
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_001_lli_dma{instance_id}_{block_count}_blocks.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "block_count": block_count,
                "block_size": block_size,
                "source_lli": True,
                "destination_lli": True,
                "descriptor_addresses": descriptor_addresses,
                "descriptor_words": words,
                "descriptor_chain_valid": chain_valid,
                "expected_sha256": _digest(expected),
                "actual_sha256": _digest(actual),
                "data_match": actual == expected,
                "channel_free": status.is_free,
            },
        )

        assert actual == expected
        assert chain_valid
        assert status.is_free


# 测试 Feature：
# 1. 仅 Source 或仅 Destination 采用 LLI 的地址更新。
#
# 测试方法：
# 1. LLI侧使用分离Buffer，另一侧使用连续Buffer，建立3节点有限链后执行。
#
# 通过条件：
# 1. 两种单侧模式的链结构、重建目标数据和Channel Free均正确。
@pytest.mark.parametrize(
    ("source_lli", "destination_lli", "label"),
    [(True, False, "source"), (False, True, "destination")],
)
def test_dma_p2_002_one_sided_lli_update(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    source_lli: bool,
    destination_lli: bool,
    label: str,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：仅 Source 或仅 Destination 采用 LLI 的地址更新。
    # 测试方法：LLI侧使用分离Buffer，另一侧使用连续Buffer，建立3节点有限链后执行。
    # 通过条件：两种单侧模式的链结构、重建目标数据和Channel Free均正确。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    block_count = 3
    block_size = 32
    patterns = [
        bytes(((block * 53) + (index * 17) + 3) & 0xFF for index in range(block_size))
        for block in range(block_count)
    ]
    controller_enabled = False
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        if source_lli:
            source_blocks = [resource.create(block_size + 4) for _ in patterns]
            # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
            for item, data in zip(source_blocks, patterns, strict=True):
                resource.write(item, data)
        else:
            combined_source = resource.create(block_count * block_size)
            resource.write(combined_source, b"".join(patterns))
            source_blocks = [combined_source] * block_count

        if destination_lli:
            destination_blocks = [resource.create(block_size + 4) for _ in patterns]
            # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
            for item in destination_blocks:
                resource.fill(item, 0xA5)
        else:
            combined_destination = resource.create(block_count * block_size)
            resource.fill(combined_destination, 0xA5)
            destination_blocks = [combined_destination] * block_count

        descriptors = [resource.create(DMA_LLI_DESCRIPTOR_SIZE, alignment=4) for _ in patterns]
        source_update = DmaUpdateMode.LINKED_LIST if source_lli else DmaUpdateMode.CONTIGUOUS
        destination_update = (
            DmaUpdateMode.LINKED_LIST if destination_lli else DmaUpdateMode.CONTIGUOUS
        )
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for index, descriptor in enumerate(descriptors):
            next_address = descriptors[index + 1].address if index + 1 < block_count else 0
            source_address = (
                source_blocks[index].address
                if source_lli
                else source_blocks[index].address + index * block_size
            )
            destination_address = (
                destination_blocks[index].address
                if destination_lli
                else destination_blocks[index].address + index * block_size
            )
            dma.lli_descriptor_init_v2(
                descriptor.address,
                DmaConfig(
                    channel=0,
                    source_address=source_address,
                    destination_address=destination_address,
                    transfer_count=block_size,
                    source_update_mode=source_update,
                    destination_update_mode=destination_update,
                    linked_list_address=next_address,
                ),
                is_last=index == block_count - 1,
            )

        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source_blocks[0].address,
                destination_address=destination_blocks[0].address,
                transfer_count=block_size,
                source_update_mode=source_update,
                destination_update_mode=destination_update,
                linked_list_address=descriptors[0].address,
            )
        )
        configured = True
        dma.start(0)
        dma.wait_channel_free(0, timeout_s=2.0)
        actual = (
            b"".join(resource.read(item, block_size) for item in destination_blocks)
            if destination_lli
            else resource.read(destination_blocks[0], block_count * block_size)
        )
        expected = b"".join(patterns)
        words = [_descriptor_words(resource.read(item)) for item in descriptors]
        chain_valid = _descriptor_chain_valid(words, [item.address for item in descriptors])
        status = dma.channel_status(0)

        record_property("lli_direction", label)
        record_property("descriptor_chain_valid", chain_valid)
        record_property("data_match", actual == expected)
        record_observation(
            record_property,
            key="descriptor_words",
            value=words,
            source="dut",
            endpoint="LLI_DESCRIPTOR.NEXT_ADDRESS",
        )
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_002_one_sided_{label}_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "lli_direction": label,
                "block_count": block_count,
                "block_size": block_size,
                "source_lli": source_lli,
                "destination_lli": destination_lli,
                "descriptor_chain_valid": chain_valid,
                "descriptor_words": words,
                "data_match": actual == expected,
                "channel_free": status.is_free,
            },
        )

        assert actual == expected
        assert chain_valid
        assert status.is_free


# =============================================================================
# 高级中断与外设 Transaction IRQ
# =============================================================================


# 测试 Feature：
# 1. Combined物理IRQ路由下的TRANSFER_DONE交付与M2M数据。
#
# 测试方法：
# 1. 建立Combined Route，Start后等待ISR Event与Free并读取目标数据。
#
# 通过条件：
# 1. route_count=1、TRANSFER_DONE锁存、数据正确、异常计数为0且Free。
def test_dma_p2_004_combined_irq(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：Combined物理IRQ路由下的TRANSFER_DONE交付与M2M数据。
    # 测试方法：建立Combined Route，Start后等待ISR Event与Free并读取目标数据。
    # 通过条件：route_count=1、TRANSFER_DONE锁存、数据正确、异常计数为0且Free。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    source_data = bytes((index * 29 + 7) & 0xFF for index in range(64))
    events = DmaIrqEvent.TRANSFER_DONE
    controller_enabled = False
    configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA combined IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(source_data), alignment=4)
        destination = resource.create(len(source_data), alignment=4)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=len(source_data),
            )
        )
        configured = True
        route_count = dma.irq_enable_combined(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(0)
        irq = dma.wait_irq_count(minimum_count=1, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        actual = resource.read(destination)
        status = dma.channel_status(0)

        record_property("combined_route_count", route_count)
        record_property("data_match", actual == source_data)
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(irq.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_004_combined_irq_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "combined_route_count": route_count,
                "irq_count": irq.irq_count,
                "latched_events": int(irq.latched_events),
                "unexpected_count": irq.unexpected_count,
                "overflow_count": irq.overflow_count,
                "data_match": actual == source_data,
                "channel_free": status.is_free,
            },
        )

        assert route_count == 1
        assert actual == source_data
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert status.is_free


# 测试 Feature：
# 1. UART RX P2M的SOURCE_TRANSACTION + TRANSFER_DONE。
#
# 测试方法：
# 1. Peer发送31 Byte，DMA写入Memory并等待两类IRQ。
#
# 通过条件：
# 1. Destination等于Peer Payload，两类ISR Latch均成立且Free。
def test_dma_p2_005_source_transaction_irq(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：UART RX P2M的SOURCE_TRANSACTION + TRANSFER_DONE。
    # 测试方法：Peer发送31 Byte，DMA写入Memory并等待两类IRQ。
    # 通过条件：Destination等于Peer Payload，两类ISR Latch均成立且Free。

    support = dma_uart_support_for(
        instance_id,
        DmaPeripheralDirection.RX,
        UartFeature.RX_DMA,
        UartFeature.TX_POLLING,
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource = support.resource
    dma = support.dma
    sysctrl = support.sysctrl
    uart_dut = support.uart_dut
    uart_peer = support.uart_peer
    pair = support.pair
    route = support.route
    events = DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.SOURCE_TRANSACTION
    if support.dma_capabilities.irq_events & events != events:
        pytest.skip("skip_by_runtime_feature: SOURCE_TRANSACTION or TRANSFER_DONE IRQ unavailable")
    payload = bytes((index * 19 + 5) & 0xFF for index in range(31))
    dut_initialized = peer_initialized = uart_dma_enabled = route_configured = False
    controller_enabled = configured = irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.extend(
                (
                    ("DMA channel stop", lambda: dma.stop(0)),
                    ("DMA channel deconfigure", lambda: dma.deconfigure(0)),
                )
            )
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART RX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART RX DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        destination = resource.create(len(payload), alignment=4)
        resource.fill(destination, 0xA5)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=route.peripheral_address,
                destination_address=destination.address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_address_mode=DmaAddressMode.FIXED,
                source_interface=route.interface,
            )
        )
        configured = True
        route_count = dma.irq_enable(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(0)
        transferred = uart_peer.write(payload, timeout_s=2.0)
        irq = dma.wait_irq_count(minimum_count=1, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        actual = resource.read(destination, len(payload))
        status = dma.channel_status(0)

        record_property("expected_payload", payload)
        record_property("request_id", route.request_id)
        record_property("transferred_bytes", transferred)
        record_property("data_match", actual == payload)
        record_property("actual_data_digest", _digest(actual))
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="isr_latched_source_transaction",
            value=bool(irq.latched_events & DmaIrqEvent.SOURCE_TRANSACTION),
            source="dut",
            endpoint="ISR.LATCHED.SOURCE_TRANSACTION",
        )
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(irq.latched_events & DmaIrqEvent.TRANSFER_DONE),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_005_source_transaction_irq_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "request_id": route.request_id,
                "route_count": route_count,
                "transferred_bytes": transferred,
                "actual_data_digest": _digest(actual),
                "irq_count": irq.irq_count,
                "latched_events": int(irq.latched_events),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )

        assert transferred == len(payload)
        assert actual == payload
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert status.is_free


# 测试 Feature：
# 1. UART TX M2P的DESTINATION_TRANSACTION + TRANSFER_DONE。
#
# 测试方法：
# 1. Peer先Capture，DMA发送31 Byte并等待Capture/IRQ/Free。
#
# 通过条件：
# 1. Peer数据正确，两类ISR Latch均成立且Free。
def test_dma_p2_006_destination_transaction_irq(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：UART TX M2P的DESTINATION_TRANSACTION + TRANSFER_DONE。
    # 测试方法：Peer先Capture，DMA发送31 Byte并等待Capture/IRQ/Free。
    # 通过条件：Peer数据正确，两类ISR Latch均成立且Free。

    support = dma_uart_support_for(
        instance_id, DmaPeripheralDirection.TX, UartFeature.TX_DMA, UartFeature.RX_POLLING
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource, dma, sysctrl = support.resource, support.dma, support.sysctrl
    uart_dut, uart_peer, pair, route = (
        support.uart_dut,
        support.uart_peer,
        support.pair,
        support.route,
    )
    events = DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.DESTINATION_TRANSACTION
    if support.dma_capabilities.irq_events & events != events:
        pytest.skip(
            "skip_by_runtime_feature: DESTINATION_TRANSACTION or TRANSFER_DONE IRQ unavailable"
        )
    payload = bytes((index * 23 + 7) & 0xFF for index in range(31))
    dut_initialized = peer_initialized = capture_started = uart_dma_enabled = route_configured = (
        False
    )
    controller_enabled = configured = irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.extend(
                (
                    ("DMA channel stop", lambda: dma.stop(0)),
                    ("DMA channel deconfigure", lambda: dma.deconfigure(0)),
                )
            )
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART TX DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.interface,
            )
        )
        configured = True
        route_count = dma.irq_enable(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        uart_peer.capture_start(len(payload))
        capture_started = True
        dma.start(0)
        actual = uart_peer.capture_wait(len(payload)).data
        irq = dma.wait_irq_count(minimum_count=1, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        status = dma.channel_status(0)

        record_property("expected_payload", payload)
        record_property("request_id", route.request_id)
        record_property("peer_capture_digest", _digest(actual))
        record_property("data_match", actual == payload)
        record_observation(
            record_property,
            key="peer_capture",
            value=actual,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="isr_latched_destination_transaction",
            value=bool(irq.latched_events & DmaIrqEvent.DESTINATION_TRANSACTION),
            source="dut",
            endpoint="ISR.LATCHED.DESTINATION_TRANSACTION",
        )
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(irq.latched_events & DmaIrqEvent.TRANSFER_DONE),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_006_destination_transaction_irq_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "request_id": route.request_id,
                "route_count": route_count,
                "peer_capture_digest": _digest(actual),
                "irq_count": irq.irq_count,
                "latched_events": int(irq.latched_events),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )

        assert actual == payload
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert status.is_free


# =============================================================================
# NORMAL / ACC Access View
# =============================================================================


# 测试 Feature：
# 1. 同一逻辑DMA的NORMAL与ACC组件访问别名一致。
#
# 测试方法：
# 1. 分别读取两套Component Snapshot并比较全部字段。
#
# 通过条件：
# 1. 身份和全部组件参数完全一致；公共Feature身份仍保留Mapping Gap。
def test_dma_p2_013_normal_and_acc_alias(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：同一逻辑DMA的NORMAL与ACC组件访问别名一致。
    # 测试方法：分别读取两套Component Snapshot并比较全部字段。
    # 通过条件：身份和全部组件参数完全一致；公共Feature身份仍保留Mapping Gap。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    dma = dma_support_for(instance_id).dma
    normal = dma.component_snapshot_get(DmaAccessView.NORMAL)
    acc = dma.component_snapshot_get(DmaAccessView.ACC)
    snapshots_equal = normal == acc

    record_observation(
        record_property,
        key="normal_component_id",
        value=normal.component_id,
        source="dut",
        endpoint="DMA_COMPONENT.COMPONENT_ID.NORMAL",
    )
    record_observation(
        record_property,
        key="acc_component_id",
        value=acc.component_id,
        source="dut",
        endpoint="DMA_COMPONENT.COMPONENT_ID.ACC",
    )
    record_property("snapshots_equal", snapshots_equal)
    record_observation(
        record_property,
        key="normal_channel_params",
        value=list(normal.channel_params),
        source="dut",
        endpoint="DMA_COMPONENT.CHANNEL_PARAMS.NORMAL",
    )
    record_observation(
        record_property,
        key="acc_channel_params",
        value=list(acc.channel_params),
        source="dut",
        endpoint="DMA_COMPONENT.CHANNEL_PARAMS.ACC",
    )
    write_json_result(
        et_artifact_dir / f"dma_p2_013_normal_and_acc_alias_dma{instance_id}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "controller": instance_id,
            "normal": {
                "dma_id": normal.dma_id,
                "component_id": normal.component_id,
                "channel_params": list(normal.channel_params),
                "multi_block_params": normal.multi_block_params,
                "max_block_size_params": normal.max_block_size_params,
            },
            "acc": {
                "dma_id": acc.dma_id,
                "component_id": acc.component_id,
                "channel_params": list(acc.channel_params),
                "multi_block_params": acc.multi_block_params,
                "max_block_size_params": acc.max_block_size_params,
            },
            "snapshots_equal": snapshots_equal,
        },
    )
    assert snapshots_equal


# =============================================================================
# Clock Gate / Reset 恢复
# =============================================================================


# 测试 Feature：
# 1. DMA经CRG Clock Gate/Reset扰动后的M2M恢复。
#
# 测试方法：
# 1. 先baseline M2M，再Clock Disable/Enable+Reset后执行不同Payload recovery。
#
# 通过条件：
# 1. 两阶段数据均正确，恢复阶段Free且CRG序列完整。
def test_dma_p2_015_reset_clock_recovery(
    dma_support_for: DmaSupportFactory,
    crg_driver: CrgDriver,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 测试 Feature：DMA经CRG Clock Gate/Reset扰动后的M2M恢复。
    # 测试方法：先baseline M2M，再Clock Disable/Enable+Reset后执行不同Payload recovery。
    # 通过条件：两阶段数据均正确，恢复阶段Free且CRG序列完整。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource, dma, crg = support.resource, support.dma, crg_driver
    results: dict[str, dict[str, object]] = {}
    actual_data: dict[str, bytes] = {}
    clock_disabled = False
    cleanup_state = {"configured": False, "controller_enabled": False}

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if cleanup_state["configured"]:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if cleanup_state["controller_enabled"]:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        if clock_disabled:
            actions.append(
                (
                    "DMA clock enable",
                    lambda: crg.clock_set(CrgPeripheral.DMA, instance=instance_id, enabled=True),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for label, seed in (("baseline", 0x21), ("recovery", 0x91)):
            if label == "recovery":
                crg.clock_set(CrgPeripheral.DMA, instance=instance_id, enabled=False)
                clock_disabled = True
                crg.clock_set(CrgPeripheral.DMA, instance=instance_id, enabled=True)
                clock_disabled = False
                crg.reset(CrgPeripheral.DMA, instance=instance_id)
            payload = bytes((seed + index * 13) & 0xFF for index in range(32))
            require_dma_m2m_capability(
                target_capabilities, instance_id=instance_id, channel=0, transfer_count=len(payload)
            )
            resource.reset()
            source = resource.create(len(payload), alignment=4)
            destination = resource.create(len(payload), alignment=4)
            resource.write(source, payload)
            resource.fill(destination, 0xA5)
            dma.controller_enable()
            cleanup_state["controller_enabled"] = True
            dma.configure(
                DmaConfig(
                    channel=0,
                    source_address=source.address,
                    destination_address=destination.address,
                    transfer_count=len(payload),
                )
            )
            cleanup_state["configured"] = True
            dma.start(0)
            dma.wait_channel_free(0, timeout_s=2.0)
            actual = resource.read(destination)
            actual_data[label] = actual
            status = dma.channel_status(0)
            results[label] = {
                "bytes": len(payload),
                "expected_sha256": _digest(payload),
                "actual_sha256": _digest(actual),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            }
            dma.stop(0)
            dma.deconfigure(0)
            cleanup_state["configured"] = False
            dma.controller_disable()
            cleanup_state["controller_enabled"] = False
            resource.reset()

        record_property("clock_reset_sequence", "clock_disable->clock_enable->reset")
        record_property("baseline_data_match", bool(results["baseline"]["data_match"]))
        record_property("recovery_data_match", bool(results["recovery"]["data_match"]))
        record_observation(
            record_property,
            key="baseline_actual_data",
            value=actual_data["baseline"],
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="baseline_channel_free",
            value=bool(results["baseline"]["channel_free"]),
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_observation(
            record_property,
            key="recovery_actual_data",
            value=actual_data["recovery"],
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="recovery_channel_free",
            value=bool(results["recovery"]["channel_free"]),
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_015_reset_clock_recovery_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "clock_reset_sequence": "clock_disable->clock_enable->reset",
                "baseline": results["baseline"],
                "recovery": results["recovery"],
            },
        )

        assert results["baseline"]["data_match"] is True
        assert results["baseline"]["channel_free"] is True
        assert results["recovery"]["data_match"] is True
        assert results["recovery"]["channel_free"] is True


# =============================================================================
# Peripheral Handshake
# =============================================================================


# 测试 Feature：
# 1. UART TX硬件握手M2P的1/17/257 Byte数据路径。
#
# 测试方法：
# 1. 配置TX Route，Peer先Capture后启动DMA并等待Free。
#
# 通过条件：
# 1. 三个长度的Peer Capture均等于Source且Free。
@pytest.mark.parametrize("length", [1, 17, 257])
def test_dma_p2_008_memory_to_peripheral(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    length: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：UART TX硬件握手M2P的1/17/257 Byte数据路径。
    # 测试方法：配置TX Route，Peer先Capture后启动DMA并等待Free。
    # 通过条件：三个长度的Peer Capture均等于Source且Free。

    support = dma_uart_support_for(
        instance_id, DmaPeripheralDirection.TX, UartFeature.TX_DMA, UartFeature.RX_POLLING
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource, dma, sysctrl = support.resource, support.dma, support.sysctrl
    uart_dut, uart_peer, pair, route = (
        support.uart_dut,
        support.uart_peer,
        support.pair,
        support.route,
    )
    payload = bytes((index * 29 + 11) & 0xFF for index in range(length))
    dut_initialized = peer_initialized = capture_started = uart_dma_enabled = route_configured = (
        False
    )
    controller_enabled = configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.interface,
            )
        )
        configured = True
        uart_peer.capture_start(len(payload))
        capture_started = True
        dma.start(0)
        actual = uart_peer.capture_wait(len(payload)).data
        dma.wait_channel_free(0, timeout_s=2.0)
        status = dma.channel_status(0)

        record_property("expected_payload", payload)
        record_property("length_bytes", length)
        record_property("request_id", route.request_id)
        record_property("peer_capture_digest", _digest(actual))
        record_observation(
            record_property,
            key="peer_capture",
            value=actual,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_008_m2p_dma{instance_id}_{length}_bytes.json",
            {
                "measurement_schema": "et.measurement.v1",
                "length_bytes": length,
                "request_id": route.request_id,
                "peer_capture_digest": _digest(actual),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )
        assert actual == payload
        assert status.is_free


# 测试 Feature：
# 1. UART RX硬件握手P2M的1/17/257 Byte数据路径。
#
# 测试方法：
# 1. 配置RX Route，Start后Peer发送Payload，Wait Free并读Destination。
#
# 通过条件：
# 1. Peer发送完整、Destination正确且Free。
@pytest.mark.parametrize("length", [1, 17, 257])
def test_dma_p2_009_peripheral_to_memory(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    length: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：UART RX硬件握手P2M的1/17/257 Byte数据路径。
    # 测试方法：配置RX Route，Start后Peer发送Payload，Wait Free并读Destination。
    # 通过条件：Peer发送完整、Destination正确且Free。

    support = dma_uart_support_for(
        instance_id, DmaPeripheralDirection.RX, UartFeature.RX_DMA, UartFeature.TX_POLLING
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource, dma, sysctrl = support.resource, support.dma, support.sysctrl
    uart_dut, uart_peer, pair, route = (
        support.uart_dut,
        support.uart_peer,
        support.pair,
        support.route,
    )
    payload = bytes((index * 31 + 13) & 0xFF for index in range(length))
    dut_initialized = peer_initialized = uart_dma_enabled = route_configured = False
    controller_enabled = configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART RX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        destination = resource.create(len(payload), alignment=4)
        resource.fill(destination, 0xA5)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=route.peripheral_address,
                destination_address=destination.address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_address_mode=DmaAddressMode.FIXED,
                source_interface=route.interface,
            )
        )
        configured = True
        dma.start(0)
        transferred = uart_peer.write(payload, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        actual = resource.read(destination, len(payload))
        status = dma.channel_status(0)

        record_property("expected_payload", payload)
        record_property("length_bytes", length)
        record_property("transferred_bytes", transferred)
        record_property("actual_data_digest", _digest(actual))
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_009_p2m_dma{instance_id}_{length}_bytes.json",
            {
                "measurement_schema": "et.measurement.v1",
                "length_bytes": length,
                "transferred_bytes": transferred,
                "actual_data_digest": _digest(actual),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )
        assert transferred == len(payload)
        assert actual == payload
        assert status.is_free


# 测试 Feature：
# 1. 双UART Route的1/17/257 Byte P2P数据路径。
#
# 测试方法：
# 1. 解析RX/TX两条Route，Peer Exchange提供外设两端刺激与最终Observer。
#
# 通过条件：
# 1. 三长度Peer最终数据等于输入，Route正确且Channel Free。
@pytest.mark.parametrize("length", [1, 17, 257])
def test_dma_p2_010_peripheral_to_peripheral(
    framework_communication: FrameworkDriver,
    target_capabilities: ChipCapabilities,
    dma_support_for: DmaSupportFactory,
    sysctrl_driver: SysctrlDriver,
    dma_peripheral_pair_config: DmaPeripheralPairConfig,
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    instance_id: int,
    length: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：双UART Route的1/17/257 Byte P2P数据路径。
    # 测试方法：解析RX/TX两条Route，Peer Exchange提供外设两端刺激与最终Observer。
    # 通过条件：三长度Peer最终数据等于输入，Route正确且Channel Free。

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    dma = support.dma
    sysctrl = sysctrl_driver
    try:
        require_dma_transfer_capability(
            target_capabilities,
            instance_id=instance_id,
            transfer_type=DmaTransferType.PERIPHERAL_TO_PERIPHERAL,
        )
        if (
            dma.capabilities_get().features & DmaFeature.PERIPHERAL_TO_PERIPHERAL
            != DmaFeature.PERIPHERAL_TO_PERIPHERAL
        ):
            raise UnsupportedCapability(
                "running firmware does not support peripheral_to_peripheral"
            )
        source_route = resolve_uart_dma_route(
            target_capabilities, dma_peripheral_pair_config, DmaPeripheralDirection.RX
        )
        _require_route_controller(source_route, instance_id)
        destination_route = resolve_uart_dma_route(
            target_capabilities, dma_peripheral_pair_config, DmaPeripheralDirection.TX
        )
        _require_route_controller(destination_route, instance_id)
    except UnsupportedCapability as exc:
        pytest.skip(str(exc))
    payload = bytes((index * 37 + 17) & 0xFF for index in range(length))
    dut_initialized = peer_initialized = uart_dma_enabled = source_route_configured = (
        destination_route_configured
    ) = False
    controller_enabled = configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if source_route_configured:
            actions.append(
                (
                    "SYSCTRL UART RX route release",
                    lambda: sysctrl.release_dma_request(
                        source_route.controller, source_route.interface
                    ),
                )
            )
        if destination_route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(
                        destination_route.controller, destination_route.interface
                    ),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART DMA disable", lambda: uart_dut_handle.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer_handle.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(**_uart_init_kwargs(dma_peripheral_pair_config))
        dut_initialized = True
        uart_peer_handle.initialize(**_uart_init_kwargs(dma_peripheral_pair_config))
        peer_initialized = True
        uart_dut_handle.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(
                source_route.controller, source_route.interface, source_route.request_id
            )
        )
        source_route_configured = True
        sysctrl.configure_route(
            DmaRequestRoute(
                destination_route.controller,
                destination_route.interface,
                destination_route.request_id,
            )
        )
        destination_route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source_route.peripheral_address,
                destination_address=destination_route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.PERIPHERAL_TO_PERIPHERAL,
                source_address_mode=DmaAddressMode.FIXED,
                destination_address_mode=DmaAddressMode.FIXED,
                source_interface=source_route.interface,
                destination_interface=destination_route.interface,
            )
        )
        configured = True
        dma.start(0)
        actual = uart_peer_handle.exchange(payload, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        status = dma.channel_status(0)

        record_property("expected_payload", payload)
        record_property("length_bytes", length)
        record_property("source_request_id", source_route.request_id)
        record_property("destination_request_id", destination_route.request_id)
        record_property("peer_capture_digest", _digest(actual))
        record_observation(
            record_property,
            key="peer_capture",
            value=actual,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_010_p2p_dma{instance_id}_{length}_bytes.json",
            {
                "measurement_schema": "et.measurement.v1",
                "length_bytes": length,
                "source_request_id": source_route.request_id,
                "destination_request_id": destination_route.request_id,
                "peer_capture_digest": _digest(actual),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )
        assert actual == payload
        assert status.is_free


# 测试 Feature：
# 1. Destination Software Handshake逐Item Request推进。
#
# 测试方法：
# 1. Start后先观察Peer无接收，再逐Byte发送Request并读取Peer接收计数。
#
# 通过条件：
# 1. 无Request不前进，4/4请求各推进1 Byte，Peer数据正确且Free。
def test_dma_p2_011_software_handshake(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：Destination Software Handshake逐Item Request推进。
    # 测试方法：Start后先观察Peer无接收，再逐Byte发送Request并读取Peer接收计数。
    # 通过条件：无Request不前进，4/4请求各推进1 Byte，Peer数据正确且Free。

    support = dma_uart_support_for(
        instance_id, DmaPeripheralDirection.TX, UartFeature.TX_DMA, UartFeature.RX_POLLING
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource, dma, sysctrl = support.resource, support.dma, support.sysctrl
    uart_dut, uart_peer, pair, route = (
        support.uart_dut,
        support.uart_peer,
        support.pair,
        support.route,
    )
    required = DmaFeature.SOFTWARE_HANDSHAKE | DmaFeature.HANDSHAKE_MODE
    if support.dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: DMA software handshake unavailable")
    payload = bytes((0x31, 0x52, 0x73, 0x94))
    dut_initialized = peer_initialized = capture_started = uart_dma_enabled = route_configured = (
        False
    )
    controller_enabled = configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.interface,
                destination_handshake_mode=DmaHandshakeMode.SOFTWARE,
            )
        )
        configured = True
        uart_peer.capture_start(len(payload))
        capture_started = True
        dma.start(0)

        # CASE_CHANGE：短窗口仅用于负对照采样，不替代完成条件。
        before_no_request = uart_peer.capture_get().received
        time.sleep(0.005)
        after_no_request = uart_peer.capture_get().received
        no_request_delta = after_no_request - before_no_request
        progress_deltas: list[int] = []
        progress_before = after_no_request
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for _ in payload:
            dma.software_handshake_request_set(
                0, DmaHandshakeTarget.DESTINATION, DmaSoftwareRequestKind.TRANSFER, True
            )
            dma.software_handshake_request_set(
                0, DmaHandshakeTarget.DESTINATION, DmaSoftwareRequestKind.SINGLE, True
            )
            time.sleep(0.002)
            progress_after = uart_peer.capture_get().received
            progress_deltas.append(progress_after - progress_before)
            progress_before = progress_after

        actual = uart_peer.capture_wait(len(payload)).data
        dma.wait_channel_free(0, timeout_s=2.0)
        status = dma.channel_status(0)
        record_observation(
            record_property,
            key="progress_before_request",
            value=before_no_request,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE.RECEIVED",
        )
        record_observation(
            record_property,
            key="progress_after_request",
            value=progress_before,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE.RECEIVED",
        )
        record_property("no_request_progress_delta", no_request_delta)
        record_property("request_progress_deltas", progress_deltas)
        record_property("peer_capture_digest", _digest(actual))
        record_observation(
            record_property,
            key="peer_capture",
            value=actual,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_011_software_handshake_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "request_id": route.request_id,
                "no_request_progress_delta": no_request_delta,
                "request_progress_deltas": progress_deltas,
                "peer_capture_digest": _digest(actual),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )

        assert no_request_delta == 0
        assert progress_deltas == [1] * len(payload)
        assert actual == payload
        assert status.is_free


# 测试 Feature：
# 1. UART TX Endpoint的Hardware/Software Handshake Mode因果对照。
#
# 测试方法：
# 1. 两种Mode共用同一数据路径；Software Mode增加无Request停滞负对照后逐Item请求。
#
# 通过条件：
# 1. Software无Request不前进，两种Mode数据/TFR/Free均正确。本Case不覆盖Polarity。
@pytest.mark.parametrize(
    "handshake_mode",
    [DmaHandshakeMode.HARDWARE, DmaHandshakeMode.SOFTWARE],
    ids=["hardware", "software"],
)
def test_dma_p2_012_handshake_mode(
    dma_uart_support_for: DmaUartSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    handshake_mode: DmaHandshakeMode,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 测试 Feature：UART TX Endpoint的Hardware/Software Handshake Mode因果对照。
    # 测试方法：两种Mode共用同一数据路径；Software Mode增加无Request停滞负对照后逐Item请求。
    # 通过条件：Software无Request不前进，两种Mode数据/TFR/Free均正确。本Case不覆盖Polarity。

    support = dma_uart_support_for(
        instance_id, DmaPeripheralDirection.TX, UartFeature.TX_DMA, UartFeature.RX_POLLING
    )

    # 隔离：Route Gate 通过后复位 DMA、UART DUT/Peer 和 Resource Pool。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=support.uart_peer.instance_id)
    resource_driver.reset()
    resource, dma, sysctrl = support.resource, support.dma, support.sysctrl
    uart_dut, uart_peer, pair, route = (
        support.uart_dut,
        support.uart_peer,
        support.pair,
        support.route,
    )
    required = DmaFeature.HANDSHAKE_MODE | _software_handshake_features(handshake_mode)
    if support.dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: DMA handshake mode requirements unavailable")
    payload = bytes((0x29, 0x4A, 0x6B, 0x8C))
    events = DmaIrqEvent.TRANSFER_DONE
    dut_initialized = peer_initialized = capture_started = uart_dma_enabled = route_configured = (
        False
    )
    controller_enabled = configured = irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if uart_dma_enabled:
            actions.append(("UART DMA disable", lambda: uart_dut.dma_enable_set(False)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut.deinitialize))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        uart_dut.initialize(**_uart_init_kwargs(pair))
        dut_initialized = True
        uart_peer.initialize(**_uart_init_kwargs(pair))
        peer_initialized = True
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.interface,
                destination_handshake_mode=handshake_mode,
            )
        )
        configured = True
        dma.irq_enable(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        uart_peer.capture_start(len(payload))
        capture_started = True
        dma.start(0)

        software_no_request_progress: int | None = None
        software_progress_deltas: list[int] = []
        if handshake_mode is DmaHandshakeMode.SOFTWARE:
            before = uart_peer.capture_get().received
            time.sleep(0.005)
            after = uart_peer.capture_get().received
            software_no_request_progress = after - before
            previous = after
            # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
            for _ in payload:
                dma.software_handshake_request_set(
                    0, DmaHandshakeTarget.DESTINATION, DmaSoftwareRequestKind.TRANSFER, True
                )
                dma.software_handshake_request_set(
                    0, DmaHandshakeTarget.DESTINATION, DmaSoftwareRequestKind.SINGLE, True
                )
                time.sleep(0.002)
                current = uart_peer.capture_get().received
                software_progress_deltas.append(current - previous)
                previous = current
        actual = uart_peer.capture_wait(len(payload)).data
        irq = dma.wait_irq_count(minimum_count=1, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        status = dma.channel_status(0)

        record_property("handshake_mode", handshake_mode.name.lower())
        if handshake_mode is DmaHandshakeMode.SOFTWARE:
            record_property("software_no_request_progress", software_no_request_progress)
            record_property("software_progress_deltas", software_progress_deltas)
        record_property("peer_capture_digest", _digest(actual))
        record_observation(
            record_property,
            key="peer_capture",
            value=actual,
            source="peer",
            device_id="uart_peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(irq.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        write_json_result(
            et_artifact_dir / f"dma_p2_012_{handshake_mode.name.lower()}_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "handshake_mode": handshake_mode.name.lower(),
                "software_no_request_progress": software_no_request_progress,
                "software_progress_deltas": software_progress_deltas,
                "peer_capture_digest": _digest(actual),
                "irq_count": irq.irq_count,
                "latched_events": int(irq.latched_events),
                "data_match": actual == payload,
                "channel_free": status.is_free,
            },
        )

        if handshake_mode is DmaHandshakeMode.SOFTWARE:
            assert software_no_request_progress == 0
            assert software_progress_deltas == [1] * len(payload)
        assert actual == payload
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert status.is_free
