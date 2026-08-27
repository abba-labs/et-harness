# Formal Case测试模块。
#
# 职责：按测试等级承载可执行Feature流程、证据和最终断言。
# 边界：不直接调用Codec、Transport或芯片专有接口。
# 依赖：仅依赖Fixture、公共Driver及Case本地Support。

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaConfig,
    DmaIrqEvent,
    DmaTransferType,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...drivers.uart import UartFeature, UartIrqSource
from ...scheduling.run_context import record_evidence, record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import UartDmaFullDuplexSupport, UartDmaSupport
from .uart_helpers import DEFAULT_BAUDRATE, DEFAULT_MAX_POLLS, make_pattern, record_result

pytestmark = [pytest.mark.hardware, pytest.mark.ip("uart")]

GUARD_SIZE = 8
GUARD_VALUE = 0xD3
DMA_FULL_DUPLEX_LENGTH = 128
DMA_GUARD_SIZE = 16
FLOW_CONTROL_BAUDRATE = 9_600
FLOW_CONTROL_LENGTH = 128
FLOW_CONTROL_TIMEOUT_S = 3.0
MODEM_INPUT_CTS_MASK = 1 << 0
MODEM_INPUT_DSR_MASK = 1 << 1
MODEM_OUTPUT_RTS_MASK = 1 << 0
MODEM_OUTPUT_DTR_MASK = 1 << 1


# =============================================================================
# DMA 数据通路
# =============================================================================


# 测试 Feature：
# UART TX DMA 从内存到 UART TX 端点的单次传输。
#
# 测试方法：
# 1. 申请源 Buffer，选择空闲 DMA Channel，并按 Bench 帧格式初始化 UART DUT/Peer。
# 2. 依次使能 UART DMA、配置 SYSCTRL TX Route、DMA Controller/Channel/IRQ 和 Peer Capture。
# 3. 启动 DMA，等待 TRANSFER_DONE 与 Peer Capture，再读取 Channel 终态。
#
# 通过条件：
# 1. Peer Capture 数据逐字节等于源 Payload，TRANSFER_DONE 被锁存且 IRQ Count 至少为 1。
# 2. Unexpected/Overflow 均为 0，DMA Channel 最终为 Free；跨 IP Cleanup 保持既有顺序。
def test_uart_p2_001_dma_tx(
    uart_dma_tx_support: UartDmaSupport,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：从Support取得UART主测试体及DMA/SYSCTRL/Resource支撑事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=uart_dma_tx_support.route.controller)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dma_tx_support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dma_tx_support.uart_peer.instance_id)
    resource_driver.reset()

    support = uart_dma_tx_support
    resource = support.resource
    dma = support.dma
    sysctrl = support.sysctrl
    uart_dut = support.uart_dut
    uart_peer = support.uart_peer
    pair = support.pair
    route = support.route

    # 准备：构造 DMA TX Payload 与中断事件要求。
    payload = make_pattern(32, seed=0x41)
    events = DmaIrqEvent.TRANSFER_DONE
    channel: int | None = None
    resource_pool_owned = False
    dut_initialized = False
    peer_initialized = False
    uart_dma_enabled = False
    route_configured = False
    controller_enabled = False
    channel_configured = False
    irq_enabled = False
    peer_capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if peer_capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if channel_configured and channel is not None:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
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
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置固定池后申请并写入 DMA 源 Buffer。
        resource.reset()
        resource_pool_owned = True
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)

        # 资源：选择一个当前空闲的 DMA Channel。
        channel = dma.find_free_channel()

        # 配置：DUT 与 Peer 使用 Bench 声明的相同帧格式。
        uart_dut.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        dut_initialized = True
        uart_peer.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        peer_initialized = True

        # 配置：使能 UART DMA 请求。
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True

        # 配置：将 UART TX 请求路由到选定 DMA 接口。
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True

        # 配置：使能 DMA Controller 并建立 Memory-to-Peripheral Channel。
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=source.address,
                destination_address=route.peripheral_address,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.interface,
            )
        )
        channel_configured = True

        # 配置：使能传输完成中断并清除历史 IRQ 结果。
        dma.irq_enable(channel, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()

        # 接收：Peer Capture 必须先于 DMA 启动。
        uart_peer.capture_start(len(payload))
        peer_capture_started = True

        # 激励：启动 DMA TX Channel。
        dma.start(channel)

        # 观测：等待 DMA IRQ、Peer 数据和 Channel 终态。
        irq = dma.wait_irq()
        capture = uart_peer.capture_wait(len(payload))
        channel_status = dma.channel_status(channel)

        # 断言：数据、中断计数和 Channel 终态必须全部有效。
        data_match = capture.data == payload
        record_observation(
            record_property,
            key="peer_rx_data",
            value=capture.data,
            source="peer",
            device_id="peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="dma_irq_events",
            value=int(irq.latched_events),
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.IRQ_EVENTS",
        )
        record_observation(
            record_property,
            key="dma_channel_free",
            value=channel_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_property("data_match", data_match)
        assert data_match
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert channel_status.is_free

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_001_dma_tx",
        controller=route.controller,
        channel=channel,
        interface=route.interface,
        request_id=route.request_id,
        peripheral_address=route.peripheral_address,
        address_evidence=route.address_evidence,
        request_evidence=route.request_evidence,
        bench_evidence=route.bench_evidence,
        bytes=len(payload),
        irq_count=irq.irq_count,
        data_match=data_match,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输。
#
# 测试方法：
# 1. 申请带 Guard 的目标 Buffer，选择空闲 DMA Channel，并初始化 UART DUT/Peer。
# 2. 依次使能 UART DMA、配置 SYSCTRL RX Route、DMA Controller/Channel/IRQ，然后启动 DMA。
# 3. Peer 发送 Payload，等待 TRANSFER_DONE 后读取 Channel 状态和目标 Buffer。
#
# 通过条件：
# 1. Peer 完整发送，目标有效区逐字节等于 Payload，前后 Guard 均保持不变。
# 2. TRANSFER_DONE 被锁存、Unexpected/Overflow 为 0，DMA Channel 最终为 Free。
def test_uart_p2_002_dma_rx(
    uart_dma_rx_support: UartDmaSupport,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：从Support取得UART主测试体及DMA/SYSCTRL/Resource支撑事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=uart_dma_rx_support.route.controller)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dma_rx_support.uart_dut.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dma_rx_support.uart_peer.instance_id)
    resource_driver.reset()

    support = uart_dma_rx_support
    resource = support.resource
    dma = support.dma
    sysctrl = support.sysctrl
    uart_dut = support.uart_dut
    uart_peer = support.uart_peer
    pair = support.pair
    route = support.route

    # 准备：构造 DMA RX Payload 与中断事件要求。
    payload = make_pattern(32, seed=0x51)
    events = DmaIrqEvent.TRANSFER_DONE
    channel: int | None = None
    resource_pool_owned = False
    dut_initialized = False
    peer_initialized = False
    uart_dma_enabled = False
    route_configured = False
    controller_enabled = False
    channel_configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if channel_configured and channel is not None:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
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
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置固定池并申请带前后 Guard 的目标 Buffer。
        resource.reset()
        resource_pool_owned = True
        destination = resource.create(len(payload) + 2 * GUARD_SIZE, alignment=4)
        resource.fill(destination, GUARD_VALUE)

        # 资源：选择一个当前空闲的 DMA Channel。
        channel = dma.find_free_channel()

        # 配置：DUT 与 Peer 使用 Bench 声明的相同帧格式。
        uart_dut.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        dut_initialized = True
        uart_peer.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        peer_initialized = True

        # 配置：使能 UART DMA 请求。
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True

        # 配置：将 UART RX 请求路由到选定 DMA 接口。
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True

        # 配置：使能 DMA Controller 并建立 Peripheral-to-Memory Channel。
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=route.peripheral_address,
                destination_address=destination.address + GUARD_SIZE,
                transfer_count=len(payload),
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_address_mode=DmaAddressMode.FIXED,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_interface=route.interface,
            )
        )
        channel_configured = True

        # 配置：使能传输完成中断并清除历史 IRQ 结果。
        dma.irq_enable(channel, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()

        # 激励：先启动 DMA RX，再由 Peer 发送 Payload。
        dma.start(channel)
        transferred = uart_peer.write(payload)

        # 观测：等待 DMA IRQ，读取 Channel 终态和完整目标 Buffer。
        irq = dma.wait_irq()
        channel_status = dma.channel_status(channel)
        raw = resource.read(destination)
        guard = bytes([GUARD_VALUE]) * GUARD_SIZE

        # 分析：分别计算有效数据区和前后 Guard 的匹配结果。
        data_match = raw[GUARD_SIZE:-GUARD_SIZE] == payload
        guards_intact = raw[:GUARD_SIZE] == guard and raw[-GUARD_SIZE:] == guard

        record_observation(
            record_property,
            key="dma_destination_data",
            value=raw[GUARD_SIZE:-GUARD_SIZE],
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="dma_irq_events",
            value=int(irq.latched_events),
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.IRQ_EVENTS",
        )
        record_observation(
            record_property,
            key="dma_channel_free",
            value=channel_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_property("guards_intact", guards_intact)

        # 断言：发送、数据、Guard、中断和 Channel 终态必须全部有效。
        assert transferred == len(payload)
        assert data_match
        assert guards_intact
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert channel_status.is_free

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_002_dma_rx",
        controller=route.controller,
        channel=channel,
        interface=route.interface,
        request_id=route.request_id,
        peripheral_address=route.peripheral_address,
        address_evidence=route.address_evidence,
        request_evidence=route.request_evidence,
        bench_evidence=route.bench_evidence,
        bytes=len(payload),
        irq_count=irq.irq_count,
        data_match=data_match,
        guards_intact=guards_intact,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输。
#
# 测试方法：
# 1. 选择两个不同空闲 Channel，准备带 Guard 的 TX/RX Buffer，并初始化 UART DUT/Peer。
# 2. 配置 TX/RX 两条 SYSCTRL Route、两个 DMA Channel、TRANSFER_DONE IRQ 和 Peer Capture。
# 3. 一次 CHANNELS_START 原子启动双向 DMA，Peer 同时发送反向 Payload，再等待两个 Channel、IRQ 与 Capture。
#
# 通过条件：
# 1. TX Capture 与 RX Buffer 分别匹配各自 Payload，TX/RX 全部 Guard 保持不变。
# 2. 两个 Channel 均为 Free 且无 ERROR，IRQ 无 Unexpected/Overflow；不伪称测得精确重叠时长。
def test_uart_p2_003_dma_full_duplex(
    uart_dma_full_duplex_support: UartDmaFullDuplexSupport,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：解析双向 DMA Route 和两个独立 Channel，保留跨 IP 顺序在 Case 中可见。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=uart_dma_full_duplex_support.tx_route.controller)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dma_full_duplex_support.uart_dut.instance_id)
    crg_driver.reset(
        CrgPeripheral.UART, instance=uart_dma_full_duplex_support.uart_peer.instance_id
    )
    resource_driver.reset()

    support = uart_dma_full_duplex_support
    resource = support.resource
    dma = support.dma
    sysctrl = support.sysctrl
    uart_dut = support.uart_dut
    uart_peer = support.uart_peer
    pair = support.pair
    tx_route = support.tx_route
    rx_route = support.rx_route
    capabilities = support.dma_capabilities

    # 资源：选择两个不同的空闲 DMA Channel。
    tx_channel = dma.find_free_channel()
    rx_channel = next(
        (
            candidate
            for candidate in range(min(capabilities.channel_count, 8))
            if candidate != tx_channel and dma.channel_status(candidate).is_free
        ),
        None,
    )
    if rx_channel is None:
        pytest.skip("skip_by_runtime_state: no second free DMA channel")

    # 准备：构造两个方向各自可区分的 Payload。
    tx_payload = make_pattern(DMA_FULL_DUPLEX_LENGTH, seed=0xA1)
    peer_payload = make_pattern(DMA_FULL_DUPLEX_LENGTH, seed=0xB2)
    events = DmaIrqEvent.TRANSFER_DONE
    uart_dma_enabled = False
    controller_enabled = False
    irq_enabled = False
    tx_route_configured = False
    rx_route_configured = False
    configured_channels: list[int] = []
    peer_capture_started = False
    resource_pool_owned = False
    dut_initialized = False
    peer_initialized = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if peer_capture_started:
            actions.append(("UART peer capture cancel", uart_peer.capture_cancel))
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))

        # 清理：按配置逆序停止并释放本Case实际占用的两个DMA Channel。
        for channel in reversed(configured_channels):
            actions.append(
                (f"DMA channel {channel} stop", lambda channel=channel: dma.stop(channel))
            )
            actions.append(
                (
                    f"DMA channel {channel} deconfigure",
                    lambda channel=channel: dma.deconfigure(channel),
                )
            )
        if rx_route_configured:
            actions.append(
                (
                    "SYSCTRL UART RX route release",
                    lambda: sysctrl.release_dma_request(
                        rx_route.controller,
                        rx_route.interface,
                    ),
                )
            )
        if tx_route_configured:
            actions.append(
                (
                    "SYSCTRL UART TX route release",
                    lambda: sysctrl.release_dma_request(
                        tx_route.controller,
                        tx_route.interface,
                    ),
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
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置固定池并申请带 Guard 的 TX/RX Buffer。
        resource.reset()
        resource_pool_owned = True
        tx_storage = resource.create(
            len(tx_payload) + DMA_GUARD_SIZE * 2,
            alignment=4,
        )
        rx_storage = resource.create(
            len(peer_payload) + DMA_GUARD_SIZE * 2,
            alignment=4,
        )
        resource.fill(tx_storage, 0xC3)
        resource.fill(rx_storage, 0x5A)
        resource.write(tx_storage, tx_payload, DMA_GUARD_SIZE)

        # 配置：DUT 与 Peer 使用 Bench 声明的相同帧格式。
        uart_dut.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        dut_initialized = True
        uart_peer.initialize(
            baudrate=pair.baudrate,
            data_bits=pair.data_bits,
            parity=pair.parity,
            stop_bits=pair.stop_bits,
        )
        peer_initialized = True

        # 配置：使能 UART DMA 请求。
        uart_dut.dma_enable_set(True)
        uart_dma_enabled = True

        # 配置：分别建立 UART TX 与 RX 的 DMA 请求路由。
        sysctrl.configure_route(
            DmaRequestRoute(
                tx_route.controller,
                tx_route.interface,
                tx_route.request_id,
            )
        )
        tx_route_configured = True
        sysctrl.configure_route(
            DmaRequestRoute(
                rx_route.controller,
                rx_route.interface,
                rx_route.request_id,
            )
        )
        rx_route_configured = True

        # 配置：使能 DMA Controller 并建立 TX Channel。
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=tx_channel,
                source_address=tx_storage.address + DMA_GUARD_SIZE,
                destination_address=tx_route.peripheral_address,
                transfer_count=len(tx_payload),
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=tx_route.interface,
            )
        )
        configured_channels.append(tx_channel)

        # 配置：建立 RX Channel。
        dma.configure(
            DmaConfig(
                channel=rx_channel,
                source_address=rx_route.peripheral_address,
                destination_address=rx_storage.address + DMA_GUARD_SIZE,
                transfer_count=len(peer_payload),
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_address_mode=DmaAddressMode.FIXED,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_interface=rx_route.interface,
            )
        )
        configured_channels.append(rx_channel)

        # 配置：使能传输完成中断并清除历史 IRQ 结果。
        dma.irq_enable(tx_channel, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()

        # 接收：Peer Capture 必须先于双 Channel 启动。
        uart_peer.capture_start(len(tx_payload))
        peer_capture_started = True

        # 激励：通过一次 Channel Mask 原子启动 TX/RX，再由 Peer 发送反向 Payload。
        channel_mask = (1 << tx_channel) | (1 << rx_channel)
        dma.start_channels(channel_mask)
        transferred = uart_peer.write(peer_payload)

        # 观测：等待两个 Channel、IRQ、Peer Capture 和两个 Buffer 终态。
        completed = dma.wait_channels_free((tx_channel, rx_channel))
        irq = dma.wait_irq()
        capture = uart_peer.capture_wait(len(tx_payload))
        rx_raw = resource.read(rx_storage)
        tx_raw = resource.read(tx_storage)

        # 分析：分别计算双向数据和四个 Guard 区的匹配结果。
        data_match = (
            capture.data == tx_payload and rx_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == peer_payload
        )
        guards_intact = (
            tx_raw[:DMA_GUARD_SIZE] == bytes([0xC3]) * DMA_GUARD_SIZE
            and tx_raw[-DMA_GUARD_SIZE:] == bytes([0xC3]) * DMA_GUARD_SIZE
            and rx_raw[:DMA_GUARD_SIZE] == bytes([0x5A]) * DMA_GUARD_SIZE
            and rx_raw[-DMA_GUARD_SIZE:] == bytes([0x5A]) * DMA_GUARD_SIZE
        )

        record_observation(
            record_property,
            key="peer_rx_data",
            value=capture.data,
            source="peer",
            device_id="peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="dma_destination_data",
            value=rx_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE],
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_property("all_channels_free", all(status.is_free for status in completed.values()))
        record_property("all_data_match", data_match)

        # 断言：双向数据、Guard、Channel 和 IRQ 终态必须全部有效。
        assert transferred == len(peer_payload)
        assert data_match
        assert guards_intact
        assert all(status.is_free for status in completed.values())
        assert all(not status.interrupt_events & DmaIrqEvent.ERROR for status in completed.values())
        assert irq.latched_events & events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_003_dma_full_duplex",
        controller=tx_route.controller,
        channels=[tx_channel, rx_channel],
        interfaces=[tx_route.interface, rx_route.interface],
        request_ids=[tx_route.request_id, rx_route.request_id],
        channel_mask=channel_mask,
        atomic_start=True,
        tx_bytes=len(tx_payload),
        rx_bytes=len(peer_payload),
        irq_count=irq.irq_count,
        data_match=data_match,
        guards_intact=guards_intact,
        tx_address_evidence=tx_route.address_evidence,
        rx_address_evidence=rx_route.address_evidence,
        tx_request_evidence=tx_route.request_evidence,
        rx_request_evidence=rx_route.request_evidence,
        bench_evidence=[tx_route.bench_evidence, rx_route.bench_evidence],
    )
    record_property("uart_result", str(output))


# =============================================================================
# 9-bit 与地址匹配
# =============================================================================


# 测试 Feature：
# UART 9-bit 软件数据双向收发及普通模式恢复。
#
# 测试方法：
# 1. Gate DUT/Peer 的 NINE_BIT 能力，初始化后同时开启 9-bit，双向发送包含第 9 位 0/1 的序列。
# 2. 显式关闭两端 9-bit，再重新初始化 DUT 并执行最小内部回环恢复传输。
#
# 通过条件：
# 1. 两方向 9-bit 元素逐项保持不变。
# 2. 恢复后的普通 8-bit 回环完整一致。
def test_uart_p2_004_nine_bit_software_transfer(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造两组 9-bit 输入，并在任何状态修改前检查 DUT/Peer 能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    first = (0x012, 0x155, 0x0A5, 0x1FE)
    second = (0x100, 0x007, 0x1AA, 0x05A)
    dut_caps = uart_dut_handle.capabilities_get()
    if dut_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.NINE_BIT.name} unavailable"
        )
    peer_caps = uart_peer_handle.capabilities_get()
    if peer_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART Peer feature {UartFeature.NINE_BIT.name} unavailable"
        )

    capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = [
            ("UART peer 9-bit disable", lambda: uart_peer_handle.nine_bit_config(False)),
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
        ]
        if capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        actions.extend(
            (
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                ("UART DUT 9-bit disable", lambda: uart_dut_handle.nine_bit_config(False)),
                ("UART DUT deinitialize", uart_dut_handle.deinitialize),
            )
        )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化两端普通帧格式。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)

        # 配置：同时开启两端 9-bit 模式。
        uart_dut_handle.nine_bit_config(True)
        uart_peer_handle.nine_bit_config(True)

        # DUT→Peer：发送并读回第一组 9-bit 元素。
        assert uart_dut_handle.write_9bit(first) == len(first)
        received_first = uart_peer_handle.read_9bit(len(first))
        record_observation(
            record_property,
            key="peer_9bit_data",
            value=received_first,
            source="peer",
            device_id="peer",
            endpoint="UART_9BIT.DATA",
        )
        assert received_first == first

        # Peer→DUT：发送并读回第二组 9-bit 元素。
        assert uart_peer_handle.write_9bit(second) == len(second)
        received_second = uart_dut_handle.read_9bit(len(second))
        record_observation(
            record_property,
            key="dut_9bit_data",
            value=received_second,
            source="dut",
            endpoint="UART_9BIT.DATA",
        )
        assert received_second == second

        # 恢复：关闭两端 9-bit 模式，并恢复 DUT 默认配置。
        uart_dut_handle.nine_bit_config(False)
        uart_peer_handle.nine_bit_config(False)
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造普通 8-bit 恢复路径 Payload。
        recovery_payload = bytes(make_pattern(2, seed=0x81))

        # 配置：开启 DUT 内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))
        capture_started = True

        # 发送：写入恢复路径 Payload。
        recovery_tx = uart_dut_handle.write(recovery_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待普通模式接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：关闭 9-bit 后的普通 UART 路径必须完整恢复。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_004_nine_bit_software_transfer",
        first=list(received_first),
        second=list(received_second),
        recovery={
            "tx_requested": len(recovery_payload),
            "tx_completed": recovery_tx,
            "rx_expected": len(recovery_payload),
            "rx_completed": recovery_capture.received,
            "data_match": recovery_capture.data == recovery_payload,
        },
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 9-bit 硬件地址匹配和不匹配地址过滤。
#
# 测试方法：
# 1. Gate 两端 NINE_BIT，DUT 开启地址匹配 0x12，Peer 发送匹配地址加两个数据帧。
# 2. 再发送不匹配地址加数据，等待硬件处理后读取 RX FIFO 状态，最后恢复普通回环。
#
# 通过条件：
# 1. 匹配地址后的三个低 8-bit 值进入普通 RX 路径，不匹配地址后的数据被过滤。
# 2. 恢复后的普通 8-bit 回环完整一致。
def test_uart_p2_005_nine_bit_hardware_address_match(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 执行：按Formal Case契约完成受控硬件动作，并在决定性断言前保存证据。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    address = 0x12
    values = (0x100 | address, 0x022, 0x0A5)
    expected_data = bytes((address, 0x22, 0xA5))
    mismatch_values = (0x133, 0x044, 0x055)
    dut_caps = uart_dut_handle.capabilities_get()
    if dut_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.NINE_BIT.name} unavailable"
        )
    peer_caps = uart_peer_handle.capabilities_get()
    if peer_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART Peer feature {UartFeature.NINE_BIT.name} unavailable"
        )
    capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = [
            ("UART peer 9-bit disable", lambda: uart_peer_handle.nine_bit_config(False)),
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
        ]
        if capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        actions.extend(
            (
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                ("UART DUT 9-bit disable", lambda: uart_dut_handle.nine_bit_config(False)),
                ("UART DUT deinitialize", uart_dut_handle.deinitialize),
            )
        )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)
        uart_dut_handle.nine_bit_config(True, address_match=True, address=address)
        uart_peer_handle.nine_bit_config(True)

        matched_written = uart_peer_handle.write_9bit(values)
        record_property("matched_words_written", matched_written)
        assert matched_written == len(values)
        received = uart_dut_handle.read_exact(len(expected_data))
        record_observation(
            record_property,
            key="matched_actual_data",
            value=received,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        assert received == expected_data

        mismatch_written = uart_peer_handle.write_9bit(mismatch_values)
        record_property("mismatch_words_written", mismatch_written)
        assert mismatch_written == len(mismatch_values)

        # 观测：连续读取三个目标侧FIFO快照，避免把单次串口事务耗时误当成采样窗口。
        levels: list[int] = []

        # 连续采样：保存完整观察窗口，用于证明不匹配数据始终未进入RX FIFO。
        for _ in range(3):
            levels.append(uart_dut_handle.status_get().rx_fifo_level)

        mismatch_window_stable = all(level == 0 for level in levels)
        mismatch_peak_rx_fifo_level = max(levels, default=-1)
        record_property("mismatch_peak_rx_fifo_level", mismatch_peak_rx_fifo_level)
        record_property("mismatch_sample_count", len(levels))
        record_property("mismatch_window_stable", mismatch_window_stable)
        assert mismatch_window_stable

        uart_dut_handle.nine_bit_config(False)
        uart_peer_handle.nine_bit_config(False)
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        recovery_payload = bytes(make_pattern(2, seed=0x92))
        uart_dut_handle.loopback_set(True)
        uart_dut_handle.capture_start(len(recovery_payload))
        capture_started = True
        recovery_tx = uart_dut_handle.write(recovery_payload, max_polls=DEFAULT_MAX_POLLS)
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))
        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_005_nine_bit_hardware_address_match",
        address=address,
        matched=list(received),
        mismatch_levels=levels,
        mismatch_peak_rx_fifo_level=mismatch_peak_rx_fifo_level,
        mismatch_sample_count=len(levels),
        mismatch_window_stable=mismatch_window_stable,
        recovery_data_match=recovery_capture.data == recovery_payload,
    )
    record_property("uart_result", str(output))


# =============================================================================
# 流控与 Modem
# =============================================================================


# 测试 Feature：
# UART RTS/CTS 自动流控的暂停和恢复。
#
# 测试方法：
# 1. Gate FLOW_CONTROL，开启 FIFO、内部回环和 AFCE，撤销 RTS 后循环 write_partial 直到出现暂停。
# 2. 恢复 RTS，在同一有界 Deadline 内继续发送剩余数据，最后等待完整 Capture。
#
# 通过条件：
# 1. 暂停阶段最后一次 write_partial 返回 0，恢复后全部剩余字节被接受。
# 2. Capture 数据逐字节等于原始 128 字节 Payload。
def test_uart_p2_006_automatic_flow_control(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：先确认 DUT 支持自动流控，再创建载荷和可变状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    capabilities = uart_dut_handle.capabilities_get()
    if not capabilities.features & UartFeature.FLOW_CONTROL:
        pytest.skip("skip_by_capability: UART automatic flow control unavailable")
    payload = make_pattern(FLOW_CONTROL_LENGTH, seed=0xC6)
    capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        actions.extend(
            (
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                ("UART DUT flow control disable", lambda: uart_dut_handle.flow_control_set(False)),
                (
                    "UART DUT modem outputs release",
                    lambda: uart_dut_handle.modem_control_set(rts=False, dtr=False),
                ),
                ("UART DUT deinitialize", uart_dut_handle.deinitialize),
            )
        )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化低波特率 UART 并开启普通 FIFO。
        uart_dut_handle.initialize(baudrate=FLOW_CONTROL_BAUDRATE)
        uart_dut_handle.fifo_config(enabled=True, dma_mode=0)

        # 配置：开启内部回环和自动流控。
        uart_dut_handle.loopback_set(True)
        uart_dut_handle.flow_control_set(enabled=True)

        # 接收：Capture 必须先于流控激励启动。
        uart_dut_handle.capture_start(len(payload))
        capture_started = True

        # 激励：撤销 RTS，使内部 CTS 进入未就绪状态。
        uart_dut_handle.modem_control_set(rts=False, dtr=False)

        # 准备：保存尚未接受的数据和暂停阶段观测。
        pending = payload
        paused_attempts: list[int] = []
        paused_received = 0
        pause_deadline = time.monotonic() + FLOW_CONTROL_TIMEOUT_S

        # 等待：CTS未就绪期间有界尝试写入，记录每轮接受长度和接收进度。
        while pending and time.monotonic() < pause_deadline:
            drained = uart_dut_handle.capture_get()
            paused_received = max(paused_received, drained.received)
            accepted = uart_dut_handle.write_partial(pending)
            if not 0 <= accepted <= len(pending):
                raise AssertionError(f"write_partial returned {accepted} for {len(pending)} bytes")
            paused_attempts.append(accepted)
            pending = pending[accepted:]
            if accepted == 0:
                break
            time.sleep(0.001)

        pause_zero_seen = bool(paused_attempts and paused_attempts[-1] == 0)
        record_property("pause_zero_seen", pause_zero_seen)
        record_property("paused_received", paused_received)

        # 断言：暂停窗口内必须出现一次零字节接受。
        assert pause_zero_seen

        # 激励：恢复 RTS，使内部 CTS 重新就绪。
        uart_dut_handle.modem_control_set(rts=True, dtr=False)

        # 准备：建立恢复阶段累计值和有界 Deadline。
        resumed_bytes = 0
        resume_deadline = time.monotonic() + FLOW_CONTROL_TIMEOUT_S

        # 等待：恢复CTS后在同一有界窗口内送完剩余数据，并持续更新接收进度。
        while pending and time.monotonic() < resume_deadline:
            drained = uart_dut_handle.capture_get()
            paused_received = max(paused_received, drained.received)
            accepted = uart_dut_handle.write_partial(pending)
            if not 0 <= accepted <= len(pending):
                raise AssertionError(f"write_partial returned {accepted} for {len(pending)} bytes")
            resumed_bytes += accepted
            pending = pending[accepted:]
            if accepted == 0:
                time.sleep(0.001)

        record_property("resumed_bytes", resumed_bytes)

        # 断言：恢复阶段必须接受全部剩余数据。
        assert not pending

        # 观测：等待完整 Capture 并比较原始 Payload。
        captured = uart_dut_handle.capture_wait(len(payload))
        data_match = captured.data == payload

        record_observation(
            record_property,
            key="resumed_actual_data",
            value=captured.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("flow_data_match", data_match)

        # 断言：流控暂停与恢复不得改变数据内容。
        assert data_match

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p2_006_automatic_flow_control",
        baudrate=FLOW_CONTROL_BAUDRATE,
        payload_bytes=len(payload),
        paused_attempts=paused_attempts,
        paused_received=paused_received,
        resumed_bytes=resumed_bytes,
        data_match=data_match,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态。
#
# 测试方法：
# 1. Gate MODEM，初始化并开启内部回环，先清空 Delta，再依次翻转 RTS 和 DTR。
# 2. 每次翻转后读取一次状态和一次清零后的状态，最后同时拉低 RTS/DTR。
#
# 通过条件：
# 1. RTS→CTS、DTR→DSR 的 input/output/delta 均匹配，第二次读取对应 Delta 清零。
# 2. RI/DCD 明确保留为未覆盖输入，不把无刺激冒充通过。
def test_uart_p2_007_modem_internal_loopback(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：先确认 Modem 状态能力，再进入内部回环与输出切换。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    capabilities = uart_dut_handle.capabilities_get()
    if not capabilities.features & UartFeature.MODEM:
        pytest.skip("skip_by_capability: UART modem status unavailable")

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
            (
                "UART DUT modem outputs release",
                lambda: uart_dut_handle.modem_control_set(rts=False, dtr=False),
            ),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 UART 并开启内部 Modem 回环。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        uart_dut_handle.loopback_set(True)

        # 配置：先将 RTS/DTR 均置低，建立明确初态。
        uart_dut_handle.modem_control_set(rts=False, dtr=False)

        # 观测：连续读取两次初态，第二次用于确认 Delta 已清零。
        initial = uart_dut_handle.modem_status_get()
        initial_clear = uart_dut_handle.modem_status_get()

        # 断言：初态二次读取不得残留 CTS/DSR Delta。
        assert not (initial_clear.delta_flags & (MODEM_INPUT_CTS_MASK | MODEM_INPUT_DSR_MASK))

        # 激励：只拉高 RTS，验证内部 RTS→CTS 映射。
        uart_dut_handle.modem_control_set(rts=True, dtr=False)

        # 观测与断言：CTS 当前状态、RTS 输出和 CTS Delta 必须同时有效。
        rts_status = uart_dut_handle.modem_status_get()
        record_observation(
            record_property,
            key="rts_raw_status",
            value=rts_status.raw_status,
            source="dut",
            endpoint="UART_MODEM.RAW_STATUS",
        )
        assert rts_status.input_flags & MODEM_INPUT_CTS_MASK
        assert rts_status.output_flags & MODEM_OUTPUT_RTS_MASK
        assert rts_status.delta_flags & MODEM_INPUT_CTS_MASK

        # 观测与断言：再次读取后 CTS Delta 必须清零。
        rts_clear = uart_dut_handle.modem_status_get()
        assert not (rts_clear.delta_flags & MODEM_INPUT_CTS_MASK)

        # 激励：保持 RTS 高并拉高 DTR，验证内部 DTR→DSR 映射。
        uart_dut_handle.modem_control_set(rts=True, dtr=True)

        # 观测与断言：DSR 当前状态、DTR 输出和 DSR Delta 必须同时有效。
        dtr_status = uart_dut_handle.modem_status_get()
        record_observation(
            record_property,
            key="dtr_raw_status",
            value=dtr_status.raw_status,
            source="dut",
            endpoint="UART_MODEM.RAW_STATUS",
        )
        assert dtr_status.input_flags & MODEM_INPUT_DSR_MASK
        assert dtr_status.output_flags & MODEM_OUTPUT_DTR_MASK
        assert dtr_status.delta_flags & MODEM_INPUT_DSR_MASK

        # 观测与断言：再次读取后 DSR Delta 必须清零。
        dtr_clear = uart_dut_handle.modem_status_get()
        assert not (dtr_clear.delta_flags & MODEM_INPUT_DSR_MASK)

        # 激励：同时拉低 RTS/DTR，验证两个输入的下降沿 Delta。
        uart_dut_handle.modem_control_set(rts=False, dtr=False)

        # 观测与断言：CTS/DSR 当前状态均应为低，两个 Delta 均应出现。
        falling_status = uart_dut_handle.modem_status_get()
        record_observation(
            record_property,
            key="falling_raw_status",
            value=falling_status.raw_status,
            source="dut",
            endpoint="UART_MODEM.RAW_STATUS",
        )
        record_property("covered_inputs", ["CTS", "DSR"])
        assert not (falling_status.input_flags & MODEM_INPUT_CTS_MASK)
        assert not (falling_status.input_flags & MODEM_INPUT_DSR_MASK)
        assert falling_status.delta_flags & (MODEM_INPUT_CTS_MASK | MODEM_INPUT_DSR_MASK)

        # 观测与断言：第二次读取必须清除全部已覆盖 Delta。
        falling_clear = uart_dut_handle.modem_status_get()
        assert not (falling_clear.delta_flags & (MODEM_INPUT_CTS_MASK | MODEM_INPUT_DSR_MASK))

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p2_007_modem_internal_loopback",
        initial=asdict(initial),
        initial_clear=asdict(initial_clear),
        rts_status=asdict(rts_status),
        rts_clear=asdict(rts_clear),
        dtr_status=asdict(dtr_status),
        dtr_clear=asdict(dtr_clear),
        falling_status=asdict(falling_status),
        falling_clear=asdict(falling_clear),
        covered_inputs=["CTS", "DSR"],
        unsupported_inputs=["RI", "DCD"],
    )
    record_property("uart_result", str(output))


# =============================================================================
# 复位与长稳
# =============================================================================


# 测试 Feature：
# UART 软件复位后的实例身份和数据路径恢复。
#
# 测试方法：
# 1. Gate SOFTWARE_RESET，初始化 DUT/Peer，读取 DUT 快照后软件复位并重新初始化 DUT。
# 2. 比较身份字段，再执行 8 字节内部回环恢复传输。
#
# 通过条件：
# 1. 软件复位前后组件身份字段保持稳定。
# 2. 恢复回环完整收发且数据逐字节一致。
def test_uart_p2_008_reset_recovery(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：确认软件复位能力后，再初始化 DUT/Peer 并执行恢复传输。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    runtime_caps = uart_dut_handle.capabilities_get()
    if runtime_caps.features & UartFeature.SOFTWARE_RESET != UartFeature.SOFTWARE_RESET:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.SOFTWARE_RESET.name} unavailable"
        )

    capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = [("UART peer deinitialize", uart_peer_handle.deinitialize)]
        if capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        actions.extend(
            (
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                ("UART DUT deinitialize", uart_dut_handle.deinitialize),
            )
        )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：DUT 与 Peer 使用相同默认帧格式。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 观测：读取软件复位前的 DUT 身份快照。
        before = uart_dut_handle.snapshot_get()

        # 激励：执行 DUT 软件复位并重新初始化。
        uart_dut_handle.software_reset()
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 观测：读取软件复位后的 DUT 身份快照。
        after = uart_dut_handle.snapshot_get()

        identity_stable = (
            after.component_parameter == before.component_parameter
            and after.component_version == before.component_version
            and after.peripheral_id == before.peripheral_id
        )
        record_observation(
            record_property,
            key="component_parameter_before",
            value=before.component_parameter,
            source="dut",
            endpoint="UART_COMPONENT.COMPONENT_PARAMETER",
        )
        record_observation(
            record_property,
            key="component_parameter_after",
            value=after.component_parameter,
            source="dut",
            endpoint="UART_COMPONENT.COMPONENT_PARAMETER",
        )
        record_property("identity_stable", identity_stable)

        # 断言：软件复位前后组件身份必须保持稳定。
        assert after.component_parameter == before.component_parameter
        assert after.component_version == before.component_version
        assert after.peripheral_id == before.peripheral_id

        # 准备：构造复位后的恢复路径 Payload。
        recovery_payload = bytes(make_pattern(8, seed=0xA2))

        # 配置：开启 DUT 内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))
        capture_started = True

        # 发送：写入恢复路径 Payload。
        recovery_tx = uart_dut_handle.write(recovery_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待恢复路径数据接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：软件复位后的数据路径必须完整恢复。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_008_reset_recovery",
        before_uart_status=before.uart_status,
        after_uart_status=after.uart_status,
        identity_stable=True,
        recovery={
            "tx_requested": len(recovery_payload),
            "tx_completed": recovery_tx,
            "rx_expected": len(recovery_payload),
            "rx_completed": recovery_capture.received,
            "data_match": recovery_capture.data == recovery_payload,
        },
    )
    record_property("uart_result", str(output))


# =============================================================================
# 9-bit 地址中断
# =============================================================================


# 测试 Feature：
# UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径。
#
# 测试方法：
# 1. Gate 两端 NINE_BIT，DUT 配地址 0x12 并使能 NINE_BIT_ADDRESS，读取 IRQ 基线。
# 2. Peer 发送匹配地址与一个数据帧，直接读取 IRQ 状态和 RX 数据，再关闭中断并恢复普通回环。
#
# 通过条件：
# 1. IRQ event_count 增加、fault_count 不增加，并明确观测到 NINE_BIT_ADDRESS 来源。
# 2. 关闭后 pending/active 均无该来源，RX 数据正确且普通回环恢复成功。
def test_uart_p2_010_nine_bit_address_irq(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造地址事件输入，并在状态修改前检查 DUT/Peer 9-bit 能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    address = 0x12
    values = (0x100 | address, 0x022)
    expected_data = bytes((address, 0x22))
    irq_source = UartIrqSource.NINE_BIT_ADDRESS
    dut_caps = uart_dut_handle.capabilities_get()
    if dut_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.NINE_BIT.name} unavailable"
        )
    peer_caps = uart_peer_handle.capabilities_get()
    if peer_caps.features & UartFeature.NINE_BIT != UartFeature.NINE_BIT:
        pytest.skip(
            f"skip_by_runtime_feature: UART Peer feature {UartFeature.NINE_BIT.name} unavailable"
        )

    capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = [
            ("UART peer 9-bit disable", lambda: uart_peer_handle.nine_bit_config(False)),
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
        ]
        if capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        actions.extend(
            (
                (
                    "UART DUT IRQ disable irq_source",
                    lambda: uart_dut_handle.irq_config(irq_source, False, priority=4),
                ),
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                ("UART DUT 9-bit disable", lambda: uart_dut_handle.nine_bit_config(False)),
                ("UART DUT deinitialize", uart_dut_handle.deinitialize),
            )
        )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化两端普通帧格式。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8)

        # 配置：DUT 开启地址匹配，Peer 开启普通 9-bit 发送。
        uart_dut_handle.nine_bit_config(True, address_match=True, address=address)
        uart_peer_handle.nine_bit_config(True)

        # 配置：使能 NINE_BIT_ADDRESS 中断。
        uart_dut_handle.irq_config(irq_source, True, priority=4)

        # 观测：读取地址激励前的 IRQ 基线。
        baseline = uart_dut_handle.irq_state_get()

        # 激励：Peer 发送匹配地址与一个数据元素。
        assert uart_peer_handle.write_9bit(values) == len(values)

        # 观测：读取地址匹配后的 IRQ 状态。
        state = uart_dut_handle.irq_state_get()

        # 分析：计算本轮中断事件、故障与来源事实。
        event_delta = state.event_count - baseline.event_count
        fault_delta = state.fault_count - baseline.fault_count
        source_observed = bool(
            state.pending_mask & int(irq_source) or state.active_mask & int(irq_source)
        )

        record_property("irq_pending_mask", state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：地址匹配必须产生 NINE_BIT_ADDRESS 事件且无 IRQ fault。
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

        # 观测与断言：DUT 普通 RX 路径必须收到地址和数据低八位。
        received = uart_dut_handle.read_exact(len(expected_data))
        record_observation(
            record_property,
            key="received_data",
            value=received,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        assert received == expected_data

        # 配置：关闭地址中断并读取清除后的 IRQ 状态。
        uart_dut_handle.irq_config(irq_source, False, priority=4)
        cleared = uart_dut_handle.irq_state_get()

        record_property("cleared_pending_mask", cleared.pending_mask)

        # 断言：关闭后 Pending 与 Active 均不得保留该来源。
        assert not (cleared.pending_mask & int(irq_source) or cleared.active_mask & int(irq_source))

        # 恢复：关闭两端 9-bit 模式，并恢复 DUT 默认配置。
        uart_dut_handle.nine_bit_config(False)
        uart_peer_handle.nine_bit_config(False)
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造普通 8-bit 恢复路径 Payload。
        recovery_payload = bytes(make_pattern(2, seed=0x93))

        # 配置：开启 DUT 内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))
        capture_started = True

        # 发送：写入恢复路径 Payload。
        recovery_tx = uart_dut_handle.write(recovery_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待恢复路径数据接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：地址中断测试后普通 UART 路径必须完整恢复。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p2_010_nine_bit_address_irq",
        address=address,
        transmitted=list(values),
        received=list(received),
        irq_state=asdict(state),
        event_count_delta=event_delta,
        cleared_irq_state=asdict(cleared),
        recovery={
            "tx_requested": len(recovery_payload),
            "tx_completed": recovery_tx,
            "rx_expected": len(recovery_payload),
            "rx_completed": recovery_capture.received,
            "data_match": recovery_capture.data == recovery_payload,
        },
    )
    record_property("uart_result", str(output))
