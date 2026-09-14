# pyright: reportMissingImports=false
# CAN Timeout四种计数源测试。
# 职责：独立源刺激、自然到期ISR、重装以及禁止计数对照。
# 边界：不用Force IRQ，不让非目标FIFO同时非空干扰源选择结论。
# 依赖：CAN Driver与选定实例句柄。

from time import monotonic

import pytest  # type: ignore

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanEventFormat,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanIrqSource,
    CanLoopback,
    CanOptions,
    CanRxSource,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxEventType,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ._support import TIMEOUT_S, pattern, phase_timing, timeout_fifo_ram

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 连续、TX Event、RX0、RX1四源Timeout、自然IRQ及禁用后的静默。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置对应超时源及周期。
# 2. 在使能状态下注入报文触发计数递减与超时中断；消费数据并验证重装。
# 3. 在禁用状态下维持非空，观察至少两倍周期确认无超时且计数不变。
#
# 通过条件：
# 1. 使能时自然超时触发IRQ且事件正确；消费数据后计数重装到TOP。
# 2. 禁用时无超时中断产生，计数器暂停。
@pytest.mark.parametrize("source", tuple(CanTimeoutSource))
def test_can_p1_014_timeout_sources(can0, source) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    top, bitrate, divisor = 1000, 500_000, 1
    period_s = top * divisor / bitrate
    event_source = source is CanTimeoutSource.TX_EVENT
    fifo_source = source is not CanTimeoutSource.CONTINUOUS
    expired_max = 0 if fifo_source else top
    fifo = 1 if source is CanTimeoutSource.RX1 else 0
    action = (
        CanFilterAction.REJECT
        if event_source
        else (CanFilterAction.FIFO1 if fifo else CanFilterAction.FIFO0)
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, bitrate, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    deadline = OperationDeadline.start(TIMEOUT_S + 2 * period_s, label="CAN Timeout source")

    can_handle.initializing_set(True, timeout_s=deadline.remaining_s())
    can_handle.wait_initializing(True, timeout_s=deadline.remaining_s())
    can_handle.timing_set(timing, timeout_s=deadline.remaining_s())
    can_handle.options_set(
        CanOptions(False, False, False, False, False, True, False, 0, 0, 0),
        timeout_s=deadline.remaining_s(),
    )
    can_handle.ram_layout_set(timeout_fifo_ram(support), timeout_s=deadline.remaining_s())
    can_handle.filter_set(
        0,
        CanFilter(CanFilterType.DUAL, action, 0x123, 0x123),
        extended=False,
        timeout_s=deadline.remaining_s(),
    )
    can_handle.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
    can_handle.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())

    # 3）获取并判断结果：三阶段连续验证 (baseline -> enabled -> disabled)
    for stage in ("baseline", "enabled", "disabled"):
        enabled = stage == "enabled"
        can_handle.irq_capture_stop(timeout_s=deadline.remaining_s())
        can_handle.irq_event_reset(timeout_s=deadline.remaining_s())
        can_handle.initializing_set(True, timeout_s=deadline.remaining_s())
        can_handle.wait_initializing(True, timeout_s=deadline.remaining_s())
        can_handle.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=divisor,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=source,
                timeout_period=top,
                timeout_enabled=enabled,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            ),
            timeout_s=deadline.remaining_s(),
        )
        can_handle.initializing_set(False, timeout_s=deadline.remaining_s())
        can_handle.wait_initializing(False, timeout_s=deadline.remaining_s())
        can_handle.irq_clear(CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s())

        if enabled and not fifo_source:
            _, after = can_handle.timeout_reload(timeout_s=deadline.remaining_s())
            assert 0 < after <= top
        elif enabled:
            assert can_handle.timeout_counter_get(timeout_s=deadline.remaining_s()) == top

        can_handle.irq_capture_pending(CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s())

        stimulated = fifo_source and stage != "baseline"
        payload = pattern(8, inverse=stage == "disabled")
        if stimulated:
            flags = CanFrameFlags.STORE_EVENT if event_source else CanFrameFlags.NONE
            can_handle.tx_write(
                0, CanTxFrame(0x123, flags, 8, 0x5A, payload), timeout_s=deadline.remaining_s()
            )
            can_handle.tx_request(1, timeout_s=deadline.remaining_s())
            tx = can_handle.wait_tx_complete(1, timeout_s=deadline.remaining_s())
            assert tx.completed & 1

        rx0 = can_handle.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
        rx1 = can_handle.rx_fifo_status_get(1, timeout_s=deadline.remaining_s())
        events = can_handle.tx_event_status_get(timeout_s=deadline.remaining_s())
        assert rx0.fill == int(stimulated and not event_source and fifo == 0) and not rx0.lost
        assert rx1.fill == int(stimulated and not event_source and fifo == 1) and not rx1.lost
        assert events.fill == int(stimulated and event_source) and not events.lost

        if enabled:
            pending = can_handle.wait_irq_pending(
                CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s()
            )
            while True:
                event = can_handle.irq_event_get(timeout_s=deadline.remaining_s())
                if event.event_count:
                    break
                deadline.sleep(0.001)
            counter = can_handle.timeout_counter_get(timeout_s=deadline.remaining_s())
            assert pending.raw_status & CanIrqSource.TIMEOUT
            assert 0 <= counter <= expired_max
            assert event.event_count == 1 and event.latched_events == CanIrqSource.TIMEOUT
            assert event.unexpected_count == event.overflow_count == event.fault_flags == 0
        else:
            baseline = can_handle.timeout_counter_get(timeout_s=deadline.remaining_s())
            end = monotonic() + 2 * period_s
            while monotonic() < end:
                pending = can_handle.irq_snapshot_get(timeout_s=deadline.remaining_s())
                event = can_handle.irq_event_get(timeout_s=deadline.remaining_s())
                counter = can_handle.timeout_counter_get(timeout_s=deadline.remaining_s())
                assert not (pending.raw_status & CanIrqSource.TIMEOUT) and event.event_count == 0
                assert counter == baseline
                deadline.sleep(0.001)

        can_handle.irq_capture_stop(timeout_s=deadline.remaining_s())

        if stimulated and event_source:
            frame_event = can_handle.tx_event_read(timeout_s=deadline.remaining_s())
            assert frame_event.identifier == 0x123 and frame_event.marker == 0x5A
            assert frame_event.event_type is CanTxEventType.TRANSMITTED_AFTER_CANCEL
            can_handle.tx_event_ack(frame_event.index, timeout_s=deadline.remaining_s())
        elif stimulated:
            frame = can_handle.rx_read(
                CanRxSource.FIFO1 if fifo else CanRxSource.FIFO0, timeout_s=deadline.remaining_s()
            )
            assert frame.identifier == 0x123 and frame.data == payload
            can_handle.rx_fifo_ack(fifo, frame.index, timeout_s=deadline.remaining_s())

        if enabled and fifo_source:
            assert can_handle.timeout_counter_get(timeout_s=deadline.remaining_s()) == top
        elif enabled:
            before, after = can_handle.timeout_reload(timeout_s=deadline.remaining_s())
            assert 0 <= before <= top and 0 < after <= top
