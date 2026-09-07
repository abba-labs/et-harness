# CAN RAM Watchdog基础触发、关闭对照和清除恢复。
# 职责：显式编排CAN/DMU与DMA搬运，使用STIMER证明非零观察窗口。
# 边界：不声称控制或测得单次RAM应答延迟；未触发WDI必须失败。
# 依赖：公共CAN/DMA/STIMER/SYSCTRL/Resource Driver和Canonical Evidence。

from dataclasses import asdict
from time import monotonic

import pytest

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
    CanIrqSource,
    CanLoopback,
    CanOptions,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.stimer import StimerConfig
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, dmu_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# RAM Watchdog低门限触发、关闭负向对照、真实W1C及复位后通信恢复。
#
# 测试方法：
# 1. 独立复位DMA/STIMER/CAN及资源，依次执行门限1、关闭、关闭恢复三个阶段。
# 2. 前两阶段各DMA搬运8帧FD 64-byte回环，最后阶段搬运一帧；逐帧比较实际数据。
# 3. 前两阶段均观察至少100 ms，保存STIMER计数、RWD、硬件WDI及Service ISR。
# 4. 开启必须触发WDI及ISR，关闭必须均为零；停止刺激后显式清WDI并读回零。
#
# 通过条件：
# 1. 开启、关闭和清除矩阵严格成立，无IRQ Fault、DMA错误或DMU错误。
# 2. 所有实际接收帧匹配，DMA全部完成且FIFO排空，恢复后无残留WDI。
def test_can_p2_010_ram_watchdog(
    can_support,
    can_dma_support,
    can_stimer_reference,
    resource_driver,
    record_property,
) -> None:

    support, transport = can_support, can_dma_support
    controller = transport.controller
    can, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    timer_id, timer, timer_limits = can_stimer_reference
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can.instance_id]
    layout = dmu_ram(support)
    frame_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1
    wdi = CanIrqSource.RAM_WATCHDOG
    record_property("expected", "WDC=1: WDI+ISR; WDC=0: no WDI/ISR; W1C=0; RX exact")
    record_property("coverage_limit", "No exact 8/32-cycle RAM handshake injection or measurement")
    # 提前声明报告摘要，任何失败均明确区分尚未观测的阶段。
    for key in ("wd", "irq", "window", "recovery"):
        record_property(key, "NOT_OBSERVED")

    with case_cleanup_scope(
        lambda: (
            ("CAN IRQ stop", can.irq_capture_stop),
            ("TX DMA stop", lambda: dma.stop(tx_channel)),
            ("RX DMA stop", lambda: dma.stop(rx_channel)),
            ("TX DMA deconfigure", lambda: dma.deconfigure(tx_channel)),
            ("RX DMA deconfigure", lambda: dma.deconfigure(rx_channel)),
            ("TX request release", lambda: sysctrl.release_dma_request(controller, tx_interface)),
            ("RX request release", lambda: sysctrl.release_dma_request(controller, rx_interface)),
            ("DMA disable", dma.controller_disable),
            ("STIMER stop", timer.stop),
            ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=controller)),
            ("STIMER reset", lambda: support.crg.reset(CrgPeripheral.STIMER, instance=timer_id)),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource reset", resource_driver.reset),
        )
    ):
        # 三阶段使用同一数据路径；恢复阶段不是对失败节点的隐式重试。
        for stage, limit, rounds in (("enabled", 1, 8), ("disabled", 0, 8), ("recovery", 0, 1)):
            can.irq_capture_stop()
            # 隔离：先复位辅助总线主设备与计数器，再复位CAN，最后清资源池。
            support.crg.reset(CrgPeripheral.DMA, instance=controller)
            support.crg.reset(CrgPeripheral.STIMER, instance=timer_id)
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            dma.deconfigure(tx_channel)
            dma.deconfigure(rx_channel)
            deadline = OperationDeadline.start(TIMEOUT_S, label=f"CAN Watchdog {stage}")
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(
                CanTiming(
                    phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
                    phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
                ),
                timeout_s=deadline.remaining_s(),
            )
            can.options_set(
                CanOptions(True, True, False, False, False, True, False, 0, 0, limit),
                timeout_s=deadline.remaining_s(),
            )
            can.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
            can.ram_layout_set(layout, timeout_s=deadline.remaining_s())
            can.filter_set(
                0,
                CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
            can.bus_config_set(
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
            can.dmu_request_set(CanDmuRequest.RX0, timeout_s=deadline.remaining_s())
            tx_endpoint = can.dmu_endpoint_get(CanDmuElement.TX)
            rx_endpoint = can.dmu_endpoint_get(CanDmuElement.RX0)
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            configured, initial_count = can.ram_watchdog_get()
            record_observation(
                record_property,
                key=f"{stage}_wd_config",
                value=configured,
                source="dut",
                endpoint="WATCHDOG.CONFIG",
            )
            record_observation(
                record_property,
                key=f"{stage}_wd_initial",
                value=initial_count,
                source="dut",
                endpoint="WATCHDOG.VALUE",
            )
            record_property("wd", {"stage": stage, "limit": configured, "value": initial_count})
            assert configured == limit

            # 仅捕获WDI，其他完成源保持屏蔽；ISR锁存后屏蔽该源但保留Raw供显式W1C。
            can.irq_capture_start(wdi, timeout_s=deadline.remaining_s())
            baseline = can.irq_event_get(timeout_s=deadline.remaining_s())
            initial = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
            record_property(f"{stage}_irq_initial", asdict(baseline))
            record_observation(
                record_property,
                key=f"{stage}_wdi_initial",
                value=bool(initial.raw_status & wdi),
                source="dut",
                endpoint="IRQ.RAW.WDI",
            )
            record_observation(
                record_property,
                key=f"{stage}_irq_enable_initial",
                value=int(initial.enabled_sources),
                source="dut",
                endpoint="IRQ.ENABLED",
            )
            record_observation(
                record_property,
                key=f"{stage}_irq_lines_initial",
                value=initial.enabled_lines,
                source="dut",
                endpoint="IRQ.LINES",
            )
            assert baseline.event_count == 0 and not initial.raw_status & wdi
            assert initial.enabled_sources == wdi and initial.enabled_lines == 1
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
            first_tick = timer.live_count_get()
            started_at = monotonic()

            # 成对DMA使CAN/DMU都实际访问Message RAM；不把有搬运解释为已知延迟周期。
            for sequence in range(rounds):
                expected = CanTxFrame(
                    0x123,
                    CanFrameFlags.FD | CanFrameFlags.BRS,
                    15,
                    0,
                    pattern(64, inverse=bool(sequence % 2)),
                )
                image = can.dmu_tx_image_encode(expected, timeout_s=deadline.remaining_s())
                resource_driver.write(source, image)
                resource_driver.write(destination, b"\xa5" * frame_bytes)
                tx_before = can.tx_status_get(timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key=f"{stage}_tx_put_{sequence}",
                    value=tx_before.put_index,
                    source="dut",
                    endpoint="TX.FIFO.PUT_INDEX",
                )
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
                statuses = dma.wait_channels_free(
                    (tx_channel, rx_channel), timeout_s=deadline.remaining_s()
                )
                tx = can.wait_tx_complete(
                    1 << tx_before.put_index, timeout_s=deadline.remaining_s()
                )
                raw = resource_driver.read(destination)
                actual = can.dmu_rx_image_decode(0, raw, timeout_s=deadline.remaining_s())
                record_property(
                    f"{stage}_frame_{sequence}", {"actual": str(actual), "expected": str(expected)}
                )
                record_observation(
                    record_property,
                    key=f"{stage}_rx_{sequence}",
                    value=raw,
                    source="dut",
                    endpoint="DMA.DESTINATION",
                )
                record_observation(
                    record_property,
                    key=f"{stage}_tx_{sequence}",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                # 两个DMA通道的完成与错误分别留证。
                for channel, status in statuses.items():
                    # 不把FREE、FIFO和IRQ拼成单一寄存器观察值。
                    for field, value in (
                        ("FREE", status.is_free),
                        ("FIFO_EMPTY", status.fifo_empty),
                        ("IRQ.ERROR", bool(status.interrupt_events & DmaIrqEvent.ERROR)),
                    ):
                        record_observation(
                            record_property,
                            key=f"{stage}_dma_{sequence}_{channel}_{field}",
                            value=value,
                            source="dut",
                            endpoint=f"DMA.CHANNEL[{channel}].{field}",
                        )
                assert all(
                    state.is_free
                    and state.fifo_empty
                    and not state.interrupt_events & DmaIrqEvent.ERROR
                    for state in statuses.values()
                )
                assert tx.completed & (1 << tx_before.put_index)
                assert (
                    actual.frame.identifier,
                    actual.frame.flags,
                    actual.frame.dlc,
                    actual.frame.data,
                ) == (
                    expected.identifier,
                    expected.flags,
                    expected.dlc,
                    expected.data,
                )

            # 有界观察：至少100 ms且STIMER未回绕；没有WDI不解释为“不支持”或SKIP。
            while True:
                pending = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
                event = can.irq_event_get(timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="wdi",
                    value=bool(pending.raw_status & wdi),
                    source="dut",
                    endpoint="IRQ.RAW.WDI",
                )
                record_property("irq", {"stage": stage, **asdict(event)})
                record_observation(
                    record_property,
                    key=f"{stage}_isr_wdi",
                    value=bool(event.raw_status & wdi),
                    source="dut",
                    endpoint="IRQ.RAW.WDI",
                )
                assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                if limit == 0:
                    assert not pending.raw_status & wdi and event.event_count == 0
                    assert event.latched_events == CanIrqSource.NONE
                if monotonic() - started_at >= 0.1 and (limit == 0 or event.event_count > 0):
                    break
                deadline.sleep(0.001)
            timer.stop()
            last_tick = timer.live_count_get()
            configured, value = can.ram_watchdog_get()
            record_property(
                "wd",
                {
                    "stage": stage,
                    "limit": configured,
                    "value": value,
                    "wdi": bool(pending.raw_status & wdi),
                },
            )
            record_property(
                "window",
                {
                    "stage": stage,
                    "first_tick": first_tick,
                    "last_tick": last_tick,
                    "seconds": monotonic() - started_at,
                },
            )
            record_observation(
                record_property,
                key=f"{stage}_timer",
                value=[first_tick, last_tick],
                source="dut",
                endpoint=f"STIMER[{timer_id}].COUNT.LIVE",
            )
            record_observation(
                record_property,
                key=f"{stage}_wd_value",
                value=value,
                source="dut",
                endpoint="WATCHDOG.VALUE",
            )
            assert first_tick < last_tick < timer_limits.maximum_period_ticks
            assert configured == limit and event.generation == baseline.generation
            if limit:
                assert pending.raw_status & wdi and event.raw_status & wdi
                assert event.masked_status == event.latched_events == wdi and event.event_count == 1

            # 清除前已无DMA活动；先留WDI/ISR证据，再停止捕获并显式W1C，随后核对排空。
            can.irq_capture_stop(timeout_s=deadline.remaining_s())
            can.irq_clear(wdi, timeout_s=deadline.remaining_s())
            cleared = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
            fifo = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            errors = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
            # 停止刺激后分别核对中断、队列和DMU，证明不会污染下一阶段。
            for key, observed, endpoint in (
                ("cleared_wdi", bool(cleared.raw_status & wdi), "IRQ.RAW.WDI"),
                ("irq_enabled", int(cleared.enabled_sources), "IRQ.ENABLED"),
                ("irq_lines", cleared.enabled_lines, "IRQ.LINES"),
                ("rx_fifo", asdict(fifo), "RX.FIFO_STATUS"),
                ("dmu_errors", int(errors.errors), "DMU.ERROR"),
                (
                    "dmu_counters",
                    [
                        counters.tx_enqueued,
                        counters.rx0_dequeued,
                        counters.rx1_dequeued,
                        counters.tx_event_dequeued,
                    ],
                    "DMU.COUNTERS",
                ),
            ):
                record_observation(
                    record_property,
                    key=f"{stage}_{key}",
                    value=observed,
                    source="dut",
                    endpoint=endpoint,
                )
            record_property(
                "recovery",
                {
                    "stage": stage,
                    "frames": rounds,
                    "fifo_fill": fifo.fill,
                    "wdi": bool(cleared.raw_status & wdi),
                    "errors": int(errors.errors),
                },
            )
            assert not cleared.raw_status & wdi and cleared.enabled_sources == CanIrqSource.NONE
            assert cleared.enabled_lines == 0 and fifo.fill == 0 and not fifo.lost
            assert errors.errors == CanDmuError.NONE
            assert (
                counters.tx_enqueued,
                counters.rx0_dequeued,
                counters.rx1_dequeued,
                counters.tx_event_dequeued,
            ) == (rounds % counters.modulus, rounds % counters.modulus, 0, 0)
