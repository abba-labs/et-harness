# pyright: reportMissingImports=none
# CAN RAM Watchdog基础触发、关闭对照和清除恢复。
# 职责：显式编排CAN/DMU与DMA搬运，使用STIMER证明非零观察窗口。
# 边界：不声称控制或测得单次RAM应答延迟；未触发WDI必须失败。
# 依赖：CAN Driver、DMA Driver、STIMER Driver与选定实例句柄。


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
    CanIrqSource,
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
from ...drivers.stimer import StimerConfig
from ._support import TIMEOUT_S, dmu_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# RAM Watchdog低门限触发、关闭负向对照、真实W1C及复位后通信恢复。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置DMA与STIMER。
# 2. 依次执行门限1开启、门限0关闭、恢复重开三个阶段。
# 3. 各阶段通过DMA搬运FD 64-byte报文，观察WDI中断与看门狗状态。
#
# 通过条件：
# 1. 门限1时触发WDI中断，门限0关闭时无WDI中断产生。
# 2. 恢复阶段通信正常，WDI清除后无残留。
def test_can_p2_010_ram_watchdog(
    can_support,
    can_dma_support,
    can_stimer_reference,
    resource_driver,
) -> None:
    # 1）复位
    support, transport = can_support, can_dma_support
    controller = transport.controller
    can_handle, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    timer_id, timer, timer_limits = can_stimer_reference
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can_handle.instance_id]
    layout = dmu_ram(support)
    frame_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1
    wdi = CanIrqSource.RAM_WATCHDOG

    # 2）三阶段连续执行 (enabled -> disabled -> recovery)
    for stage, limit, rounds in (("enabled", 1, 8), ("disabled", 0, 8), ("recovery", 0, 1)):
        dma.stop(tx_channel)
        dma.stop(rx_channel)
        dma.deconfigure(tx_channel)
        dma.deconfigure(rx_channel)
        can_handle.reset()

        deadline = OperationDeadline.start(TIMEOUT_S, label=f"CAN Watchdog {stage}")
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
            CanOptions(True, True, False, False, False, True, False, 0, 0, limit),
            timeout_s=deadline.remaining_s(),
        )
        can_handle.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
        can_handle.ram_layout_set(layout, timeout_s=deadline.remaining_s())
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
        can_handle.dmu_request_set(CanDmuRequest.RX0, timeout_s=deadline.remaining_s())
        tx_endpoint = can_handle.dmu_endpoint_get(CanDmuElement.TX)
        rx_endpoint = can_handle.dmu_endpoint_get(CanDmuElement.RX0)
        can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
        can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())

        configured, _ = can_handle.ram_watchdog_get()
        assert configured == limit

        can_handle.irq_capture_start(wdi, timeout_s=deadline.remaining_s())
        assert can_handle.irq_event_get(timeout_s=deadline.remaining_s()).event_count == 0

        sysctrl.configure_dma_request_v2(controller, tx_interface, requests["tx"])
        sysctrl.configure_dma_request_v2(controller, rx_interface, requests["rx"])
        dma.controller_enable()

        source = resource_driver.create(frame_bytes)
        destination = resource_driver.create(frame_bytes)
        timer.configure(
            StimerConfig(
                period_ticks=timer_limits.maximum_period_ticks,
                prescaler_divider=timer_limits.maximum_prescaler_divider,
            )
        )
        timer.clear()
        timer.start()

        # 3）获取并判断结果：DMA连续收发与看门狗事件监测
        for seq in range(rounds):
            expected = CanTxFrame(
                0x123,
                CanFrameFlags.FD | CanFrameFlags.BRS,
                15,
                0,
                pattern(64, inverse=bool(seq % 2)),
            )
            image = can_handle.dmu_tx_image_encode(expected, timeout_s=deadline.remaining_s())
            resource_driver.write(source, image)
            resource_driver.write(destination, b"\xa5" * frame_bytes)
            tx_before = can_handle.tx_status_get(timeout_s=deadline.remaining_s())

            dma.configure(
                DmaConfig(
                    rx_channel,
                    rx_endpoint,
                    destination.address,
                    frame_bytes // word_bytes,
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
                    source.address,
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
            can_handle.wait_tx_complete(1 << tx_before.put_index, timeout_s=deadline.remaining_s())

            raw = resource_driver.read(destination)
            decoded = can_handle.dmu_rx_image_decode(0, raw)
            assert decoded.frame.identifier == 0x123 and decoded.frame.data == expected.data

        # 检查 WDI 中断状态
        pending = can_handle.irq_snapshot_get(timeout_s=deadline.remaining_s())
        event = can_handle.irq_event_get(timeout_s=deadline.remaining_s())
        if stage == "enabled":
            assert pending.raw_status & wdi
            assert event.event_count >= 1 and event.latched_events & wdi
            can_handle.irq_clear(wdi, timeout_s=deadline.remaining_s())
            assert not (
                can_handle.irq_snapshot_get(timeout_s=deadline.remaining_s()).raw_status & wdi
            )
        else:
            assert not (pending.raw_status & wdi)
            assert event.event_count == 0

        timer.stop()
        can_handle.irq_capture_stop(timeout_s=deadline.remaining_s())
