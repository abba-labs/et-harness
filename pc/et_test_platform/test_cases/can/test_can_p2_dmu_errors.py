# pyright: reportMissingImports=none
# CAN DMU最短非法窗口刺激及独立IRQ、复位后真实DMA恢复。
# 职责：Case显式编排九个独立故障节点，保存首个ISR值并比较合法恢复帧。
# 边界：只调用命名窗口Driver，不访问任意地址；不推测DMUIR W1C。
# 依赖：CAN Driver、DMA Driver与选定实例句柄。

from dataclasses import replace

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanDmuElement,
    CanDmuError,
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

FAULTS = (
    ("tx_read", CanDmuError.TX_READ),
    ("rx1_write", CanDmuError.RX1_WRITE),
    ("event_write", CanDmuError.EVENT_WRITE),
    ("rx1_empty", CanDmuError.RX1_DEQUEUE),
    ("event_empty", CanDmuError.EVENT_DEQUEUE),
    ("tx_dlc", CanDmuError.TX_DLC),
    ("configuration", CanDmuError.CONFIGURATION_ACCESS),
    ("tx_start", CanDmuError.TX_START),
    ("tx_sequence", CanDmuError.TX_SEQUENCE),
)


# 测试 Feature：
# DMU非法读写、空出队、超容量DLC、CCE访问及起址/步进错误产生真实专用IRQ。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置DMU测试环境。
# 2. 捕获目标错误源并执行最短非法窗口刺激，校验专用IRQ事件产生。
# 3. 复位后通过合法DMA收发一帧，证明错误状态解除且硬件功能恢复。
#
# 通过条件：
# 1. 错误中断准确命中且事件计数为1。
# 2. 复位后合法收发无任何错误残留。
@pytest.mark.parametrize("fault,expected_error", FAULTS, ids=[item[0] for item in FAULTS])
def test_can_p2_007_dmu_illegal_irq(
    can_support,
    can_dma_support,
    resource_driver,
    fault,
    expected_error,
) -> None:
    # 1）复位
    support, transport = can_support, can_dma_support
    controller = transport.controller
    can_handle, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can_handle.instance_id]
    layout = replace(
        dmu_ram(support),
        tx_payload_bytes=8,
        rx0_payload_bytes=8,
        rx1_payload_bytes=8,
        rx0_count=2,
        rx1_count=2,
        event_count=2,
    )
    expected = CanTxFrame(0x123, CanFrameFlags(0), 8, 0, pattern(8))
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    rx_bytes = mapping.CAN_RAM_HEADER_BYTES + 8

    # 阶段一：制造非法访问刺激并检验错误中断
    dma.stop(tx_channel)
    dma.stop(rx_channel)
    dma.deconfigure(tx_channel)
    dma.deconfigure(rx_channel)
    can_handle.reset()

    deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU illegal")
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
        CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
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
    can_handle.dmu_request_set(CanDmuRequest.RX1, timeout_s=deadline.remaining_s())

    if fault == "configuration":
        can_handle.configuration_write_set(True, timeout_s=deadline.remaining_s())
    else:
        can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
        can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())

    image = can_handle.dmu_tx_image_encode(expected, timeout_s=deadline.remaining_s())
    words = tuple(
        int.from_bytes(image[offset : offset + word_bytes], "little")
        for offset in range(0, len(image), word_bytes)
    )
    if fault == "tx_dlc":
        oversized = can_handle.dmu_tx_image_encode(
            CanTxFrame(0x123, CanFrameFlags.FD, 15, 0, pattern(64)),
            timeout_s=deadline.remaining_s(),
        )
        words = tuple(
            int.from_bytes(oversized[offset : offset + word_bytes], "little")
            for offset in range(0, len(oversized), word_bytes)
        )

    accesses = {
        "tx_read": ((CanDmuElement.TX, 0, False, 0),),
        "rx1_write": ((CanDmuElement.RX1, 0, True, 0),),
        "event_write": ((CanDmuElement.TX_EVENT, 0, True, 0),),
        "rx1_empty": ((CanDmuElement.RX1, 0, False, 0),),
        "event_empty": ((CanDmuElement.TX_EVENT, 0, False, 0),),
        "tx_dlc": ((CanDmuElement.TX, 0, True, words[0]), (CanDmuElement.TX, 1, True, words[1])),
        "tx_sequence": (
            (CanDmuElement.TX, 0, True, words[0]),
            (CanDmuElement.TX, 2, True, words[2]),
        ),
        "tx_start": ((CanDmuElement.TX, 1, True, words[1]),),
        "configuration": ((CanDmuElement.TX, 0, True, words[0]),),
    }[fault]

    can_handle.dmu_capture_start(expected_error, timeout_s=deadline.remaining_s())
    for element, index, write, value in accesses:
        can_handle.dmu_word_access(
            element, index, write=write, value=value, timeout_s=deadline.remaining_s()
        )

    event = can_handle.dmu_event_get(timeout_s=deadline.remaining_s())
    assert event.raw_status & expected_error and event.event_count == 1
    assert event.instance_id == can_handle.instance_id and event.fault_flags == 0
    can_handle.dmu_capture_stop()

    # 阶段二：恢复验证（重置后通过合法DMA收发一帧）
    can_handle.reset()
    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(
        CanTiming(
            phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
            phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
        )
    )
    can_handle.options_set(CanOptions(True, True, False, False, False, True, False, 0, 0, 0))
    can_handle.event_format_set(CanEventFormat(8, False))
    can_handle.ram_layout_set(layout)
    can_handle.filter_set(
        0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123), extended=False
    )
    can_handle.loopback_set(CanLoopback.INTERNAL)
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
        )
    )
    can_handle.dmu_request_set(CanDmuRequest.RX1)
    tx_endpoint = can_handle.dmu_endpoint_get(CanDmuElement.TX)
    rx_endpoint = can_handle.dmu_endpoint_get(CanDmuElement.RX1)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    sysctrl.configure_dma_request(controller, tx_interface, requests["tx"])
    sysctrl.configure_dma_request(controller, rx_interface, requests["rx1"])
    dma.controller_enable()

    source_mem = resource_driver.create(len(image))
    destination = resource_driver.create(rx_bytes)
    resource_driver.write(source_mem, image)

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

    dma.wait_channels_free((tx_channel, rx_channel), timeout_s=TIMEOUT_S)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    raw = resource_driver.read(destination)
    decoded = can_handle.dmu_rx_image_decode(0, raw)
    assert decoded.frame.identifier == 0x123 and decoded.frame.data == expected.data
    assert can_handle.dmu_counters_get().rx1_count == 1
