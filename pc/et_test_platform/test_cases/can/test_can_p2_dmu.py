# pyright: reportMissingImports=none
# CAN DMU通过片内DMA的收发与事件搬运。
# 职责：显式编排CAN、DMA、SYSCTRL和Resource，独立比较数据与硬件终态。
# 边界：Case不解释芯片元素位域，不由CPU读写DMU虚拟窗口。
# 依赖：CAN Driver、DMA Driver与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanDmuElement,
    CanDmuRequest,
    CanEventFormat,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxEventType,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaTransferType,
    DmaWidth,
)
from ._support import TIMEOUT_S, dmu_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# DMA通过DMU虚拟TX及RX0/RX1窗口搬运完整FD 64-byte帧，自动推进FIFO。
#
# 测试方法：
# 1. 显式执行 can_handle.reset()，停止并解除原有DMA通道配置。
# 2. 在SRAM开辟接收与发送缓冲区，设置DMU触发源。
# 3. 先启动RX DMA，再启动TX DMA，对比接收数据与DMA计数器。
#
# 通过条件：
# 1. 64-byte负载完全一致，DMA无错误。
# 2. TX与RX各完成两次搬运，DMU计数器推进正确。
@pytest.mark.parametrize("fifo", [0, 1], ids=["rx0", "rx1"])
def test_can_p2_001_dmu_tx_rx(can_support, can_dma_support, resource_driver, fifo) -> None:
    # 1）复位
    support, transport = can_support, can_dma_support
    controller = transport.controller
    can_handle, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can_handle.instance_id]
    layout = dmu_ram(support)
    rx_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1

    dma.stop(tx_channel)
    dma.stop(rx_channel)
    dma.deconfigure(tx_channel)
    dma.deconfigure(rx_channel)
    can_handle.reset()

    # 2）IP 配置与激励准备
    deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU TX/RX")
    can_handle.initializing_set(True, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(True, timeout_s=deadline.remaining_s())
    can_handle.timing_set(
        CanTiming(
            phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
            phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
        ),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.options_set(
        CanOptions(True, True, False, False, False, True, False, 0, 0, 0),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
    can_handle.ram_layout_set(layout, timeout_s=deadline.remaining_s())
    can_handle.filter_set(
        0,
        CanFilter(
            CanFilterType.DUAL,
            CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1,
            0x123,
            0x123,
        ),
        extended=False,
        timeout_s=deadline.remaining_s(),
    )
    can_handle.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
    can_handle.bus_config_set(
        CanBusConfig(
            True,
            False,
            1,
            CanTimestampSource.DISABLED,
            CanTimeoutSource.CONTINUOUS,
            0,
            False,
            True,
            True,
            CanUnmatchedPolicy.REJECT,
            CanUnmatchedPolicy.REJECT,
        ),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.dmu_request_set(
        CanDmuRequest.RX0 if fifo == 0 else CanDmuRequest.RX1, timeout_s=deadline.remaining_s()
    )
    tx_endpoint = can_handle.dmu_endpoint_get(CanDmuElement.TX, timeout_s=deadline.remaining_s())
    rx_endpoint = can_handle.dmu_endpoint_get(
        CanDmuElement.RX0 if fifo == 0 else CanDmuElement.RX1, timeout_s=deadline.remaining_s()
    )
    can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())

    # 3）获取并判断结果：双帧DMA收发
    sysctrl.configure_dma_request(controller, tx_interface, requests["tx"])
    sysctrl.configure_dma_request(controller, rx_interface, requests[f"rx{fifo}"])
    dma.controller_enable()

    for seq in (0, 1):
        payload = pattern(64, inverse=seq == 1)
        image = can_handle.dmu_tx_image_encode(
            CanTxFrame(0x123, CanFrameFlags.FD | CanFrameFlags.BRS, 15, seq, payload)
        )
        source_mem = resource_driver.create(len(image))
        destination = resource_driver.create(rx_bytes)
        resource_driver.write(source_mem, image)

        # 配置 RX 与 TX DMA
        dma.configure(
            DmaConfig(
                rx_channel,
                rx_endpoint,
                destination.address,
                rx_bytes // word_bytes,
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_width=DmaWidth.BITS_32,
                destination_width=DmaWidth.BITS_32,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_burst=DmaBurst.ITEMS_32,
                destination_burst=DmaBurst.ITEMS_32,
                source_interface=rx_interface,
            )
        )
        dma.start(rx_channel)

        dma.configure(
            DmaConfig(
                tx_channel,
                source_mem.address,
                tx_endpoint,
                len(image) // word_bytes,
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                source_width=DmaWidth.BITS_32,
                destination_width=DmaWidth.BITS_32,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_burst=DmaBurst.ITEMS_32,
                destination_burst=DmaBurst.ITEMS_32,
                destination_interface=tx_interface,
            )
        )
        dma.start(tx_channel)

        dma.wait_channels_free((tx_channel, rx_channel), timeout_s=deadline.remaining_s())
        can_handle.wait_tx_complete(1 << seq, timeout_s=deadline.remaining_s())

        # 解码接收数据并断言
        raw = resource_driver.read(destination)
        decoded = can_handle.dmu_rx_image_decode(seq, raw)
        assert decoded.frame.identifier == 0x123 and decoded.frame.data == payload

    counters = can_handle.dmu_counters_get()
    assert counters.tx_count == 2 and counters.rx0_count == (2 if fifo == 0 else 0)
    assert counters.rx1_count == (2 if fifo == 1 else 0)


# 测试 Feature：
# DMA从DMU Event虚拟窗口搬运两次真实发送事件并自动推进队列。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，停止并解除DMA通道。
# 2. 依次发送两条带Marker的FD64报文，产生TX Event。
# 3. 启动DMA搬运Event记录到SRAM，解码比对Marker与ID。
#
# 通过条件：
# 1. 两次事件搬运数据匹配，Event队列归零，DMU出队计数为2。
def test_can_p2_002_dmu_tx_event(can_support, can_dma_support, resource_driver) -> None:
    # 1）复位
    support, transport = can_support, can_dma_support
    controller = transport.controller
    can_handle, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    event_bytes = mapping.CAN_EVENT_BYTES
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    channel, interface = 0, 0
    expected_markers = (0x12, 0x34)

    dma.stop(channel)
    dma.deconfigure(channel)
    can_handle.reset()

    # 2）IP 配置与激励准备
    deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU TX Event")
    can_handle.initializing_set(True, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(True, timeout_s=deadline.remaining_s())
    can_handle.timing_set(
        CanTiming(
            phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
            phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
        ),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.options_set(
        CanOptions(True, True, False, False, False, True, False, 0, 0, 0),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
    can_handle.ram_layout_set(dmu_ram(support), timeout_s=deadline.remaining_s())
    can_handle.filter_set(
        0,
        CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
        extended=False,
        timeout_s=deadline.remaining_s(),
    )
    can_handle.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
    can_handle.bus_config_set(
        CanBusConfig(
            True,
            False,
            1,
            CanTimestampSource.DISABLED,
            CanTimeoutSource.CONTINUOUS,
            0,
            False,
            True,
            True,
            CanUnmatchedPolicy.REJECT,
            CanUnmatchedPolicy.REJECT,
        ),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.dmu_request_set(CanDmuRequest.TX_EVENT, timeout_s=deadline.remaining_s())
    endpoint = can_handle.dmu_endpoint_get(CanDmuElement.TX_EVENT, timeout_s=deadline.remaining_s())
    can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())

    sysctrl.configure_dma_request(
        controller, interface, mapping.CAN_DMU_REQUESTS[can_handle.instance_id]["rx"]
    )
    dma.controller_enable()
    destination = resource_driver.create(2 * event_bytes)
    resource_driver.write(destination, b"\xa5" * (2 * event_bytes))

    # 3）获取并判断结果：发送两帧并通过DMA读取事件
    for sequence, marker in enumerate(expected_markers):
        offset = sequence * event_bytes
        dma.configure(
            DmaConfig(
                channel,
                endpoint,
                destination.address + offset,
                event_bytes // word_bytes,
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_width=DmaWidth.BITS_32,
                destination_width=DmaWidth.BITS_32,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_burst=DmaBurst.ITEMS_32,
                destination_burst=DmaBurst.ITEMS_32,
                source_interface=interface,
            )
        )
        dma.start(channel)

        can_handle.tx_write(
            sequence,
            CanTxFrame(
                0x123,
                CanFrameFlags.FD | CanFrameFlags.BRS | CanFrameFlags.STORE_EVENT,
                15,
                marker,
                pattern(64, inverse=bool(sequence)),
            ),
        )
        can_handle.tx_request(1 << sequence)
        can_handle.wait_tx_complete(1 << sequence, timeout_s=deadline.remaining_s())
        dma.wait_done(channel, timeout_s=deadline.remaining_s())

        raw_event = resource_driver.read(destination.slice(offset, event_bytes))
        decoded = can_handle.dmu_event_image_decode(raw_event)
        assert decoded.details.event.identifier == 0x123 and decoded.details.event.marker == marker
        assert decoded.details.event.event_type is CanTxEventType.TRANSMITTED

    counters = can_handle.dmu_counters_get()
    assert counters.event_count == 2
    assert can_handle.tx_event_status_get().fill == 0
