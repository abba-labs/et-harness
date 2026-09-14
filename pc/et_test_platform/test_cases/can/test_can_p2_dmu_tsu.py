# pyright: reportMissingImports=none
# CAN DMU接收时间戳搬运与满payload覆盖检测。
# 职责：显式配置TSU/过滤器、定位TS0关联帧、DMA搬运后独立比较TS0及ATB区间。
# 边界：不提前读取TS0、不解释芯片Header位域、不由CPU补写DMA目标或补Ack。
# 依赖：CAN Driver、DMA Driver与选定实例句柄。

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
    CanTsuConfig,
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
# RX0/RX1在真实DMA搬运中携带TSU时间戳，满payload时准确报告覆盖并验证复位恢复。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，停止并解除DMA通道。
# 2. 开启TSU与接收过滤SYNC，配置对应FIFO与TTS开关。
# 3. 定位TS0关联帧，由DMA搬运完整元素至SRAM缓冲区。
# 4. 校验DMA完成状态、数据内容、时间戳字段及覆盖错误标志。
#
# 通过条件：
# 1. 正常帧数据完整，TTS开启时目标末word等于TS0且位于ATB区间。
# 2. 64-byte负向帧时正确置位覆盖错误，复位恢复8-byte帧无错误。
@pytest.mark.parametrize(
    "fifo,transfer_timestamp,overwrite",
    (
        (0, False, False),
        (0, True, False),
        (1, False, False),
        (1, True, False),
        (1, True, True),
    ),
    ids=["rx0_plain", "rx0_tsu", "rx1_plain", "rx1_tsu", "rx1_overwrite_recover"],
)
def test_can_p2_008_dmu_rx_timestamp(
    can_support,
    can_dma_support,
    resource_driver,
    fifo,
    transfer_timestamp,
    overwrite,
) -> None:
    # 1）复位
    support, transport = can_support, can_dma_support
    controller = transport.controller
    can_handle, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    layout = dmu_ram(support)
    channel, interface = 0, 0
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    element_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    guard = b"\xa5" * word_bytes

    dma.stop(channel)
    dma.deconfigure(channel)
    can_handle.reset()

    # 2）IP 配置与激励准备
    deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU RX TSU")
    limits = can_handle.tsu_limits_get(timeout_s=deadline.remaining_s())
    assert limits.internal and 4 <= limits.slots <= 16

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
    can_handle.event_format_set(CanEventFormat(16, True), timeout_s=deadline.remaining_s())
    can_handle.tsu_config_set(CanTsuConfig(True, False, False, 1), timeout_s=deadline.remaining_s())
    can_handle.dmu_timestamp_set(transfer_timestamp, timeout_s=deadline.remaining_s())
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
    can_handle.filter_sync_set(0, True, timeout_s=deadline.remaining_s())
    can_handle.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
    can_handle.bus_config_set(
        CanBusConfig(
            True,
            False,
            1,
            CanTimestampSource.EXTERNAL,
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
    can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())

    # 3）获取并判断结果：定位TS0并执行DMA搬运
    payload_bytes = 64 if overwrite else 8
    expected = CanTxFrame(
        0x123,
        CanFrameFlags.FD | CanFrameFlags.BRS,
        15 if payload_bytes == 64 else 8,
        0,
        pattern(payload_bytes),
    )

    head = None
    atb_before = 0
    atb_after = 0
    for _ in range(limits.slots):
        tx = can_handle.tx_status_get(timeout_s=deadline.remaining_s())
        can_handle.tx_write(tx.put_index, expected, timeout_s=deadline.remaining_s())
        atb_before = can_handle.tsu_timebase_get(timeout_s=deadline.remaining_s())
        can_handle.tx_request(1 << tx.put_index, timeout_s=deadline.remaining_s())
        can_handle.wait_tx_complete(1 << tx.put_index, timeout_s=deadline.remaining_s())
        can_handle.wait_rx_available(fifo, timeout_s=deadline.remaining_s())
        atb_after = can_handle.tsu_timebase_get(timeout_s=deadline.remaining_s())
        head = can_handle.rx_timestamp_get(fifo, timeout_s=deadline.remaining_s())
        if head.tsu_pointer == 0:
            break
        can_handle.rx_fifo_ack(fifo, head.index, timeout_s=deadline.remaining_s())

    assert head is not None and head.tsu_pointer == 0
    new, lost = can_handle.tsu_flags_get(timeout_s=deadline.remaining_s())
    assert new & 1 and not lost & 1

    # 执行DMA搬运
    destination = resource_driver.create(element_bytes + 2 * word_bytes)
    resource_driver.write(destination, b"\xa5" * destination.size)
    endpoint = can_handle.dmu_endpoint_get(CanDmuElement.RX0 if fifo == 0 else CanDmuElement.RX1)
    sysctrl.configure_dma_request_v2(
        controller, interface, mapping.CAN_DMU_REQUESTS[can_handle.instance_id]["rx"]
    )
    dma.controller_enable()
    dma.configure(
        DmaConfig(
            channel,
            endpoint,
            destination.address + word_bytes,
            element_bytes // word_bytes,
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
    dma.wait_channel_free(channel, timeout_s=deadline.remaining_s())

    # 校验DMA结果
    copied = resource_driver.read(destination)
    raw = copied[word_bytes:-word_bytes]
    assert copied[:word_bytes] == guard and copied[-word_bytes:] == guard

    ts0 = can_handle.tsu_slot0_consume(timeout_s=deadline.remaining_s())
    errors = can_handle.dmu_status_consume(timeout_s=deadline.remaining_s())
    expected_error = (
        CanDmuError.RX1_TIMESTAMP_OVERWRITE if payload_bytes == 64 else CanDmuError.NONE
    )
    assert errors.errors == expected_error

    decoded = can_handle.dmu_rx_image_decode(head.index, raw)
    assert decoded.frame.identifier == 0x123
    if transfer_timestamp:
        assert decoded.transferred_timestamp_valid
        assert decoded.transferred_timestamp == ts0
        span = (atb_after - atb_before) & 0xFFFFFFFF
        assert ((ts0 - atb_before) & 0xFFFFFFFF) <= span
