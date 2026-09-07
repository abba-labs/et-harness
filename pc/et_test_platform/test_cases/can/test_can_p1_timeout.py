# CAN Timeout四种计数源。
# 职责：独立源刺激、自然到期ISR、重装以及禁止计数对照。
# 边界：不用Force IRQ，不让非目标FIFO同时非空干扰源选择结论。
# 依赖：CAN/CRG/Resource Driver、纯RAM布局与统一Deadline。

from dataclasses import asdict
from time import monotonic

import pytest

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
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, pattern, phase_timing, timeout_fifo_ram

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 连续、TX Event、RX0、RX1四源Timeout、自然IRQ及禁用后的静默。
#
# 测试方法：
# 1. 独立复位，TOP1000/分频1/500k，三个FIFO各深度四，先禁用作空基线。
# 2. 启用后连续源单写重装；FIFO源先验证空时TOP，再仅产生所选FIFO条目。
# 3. 等待Raw及实际ISR，保留FIFO条目直到到期并读到计数0。
# 4. 连续源再次重装立即读回；FIFO源读数据并Ack到空，读回TOP。
# 5. 再禁用，FIFO模式重新保持目标非空，至少两倍周期内无Timeout且计数不下降。
#
# 通过条件：
# 1. 启用阶段真实到期、ISR一次且无错误，所选源之外FIFO保持空。
# 2. 重装为真实读回；禁用窗口不只检查空FIFO，且退出时停止IRQ并复位资源。
@pytest.mark.parametrize("source", tuple(CanTimeoutSource))
def test_can_p1_014_timeout_sources(can_support, resource_driver, record_property, source) -> None:

    support = can_support
    can = support.can
    top, bitrate, divisor = 1000, 500_000, 1
    period_s = top * divisor / bitrate
    event_source = source is CanTimeoutSource.TX_EVENT
    fifo_source = source is not CanTimeoutSource.CONTINUOUS
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
    counter_trace, irq_trace, negative_windows = [], [], []
    record_property("counter", counter_trace)
    record_property("irq", irq_trace)
    record_property("negative_windows", negative_windows)
    record_property(
        "expected",
        {
            "source": source.name,
            "top": top,
            "divisor": divisor,
            "bitrate": bitrate,
            "negative_min_seconds": 2 * period_s,
        },
    )
    deadline = OperationDeadline.start(TIMEOUT_S + 2 * period_s, label="CAN Timeout source")

    # 清理：先释放ISR路由，再复位CAN和资源；异常时也执行全部步骤。
    with case_cleanup_scope(
        lambda: (
            ("CAN IRQ stop", can.irq_capture_stop),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        can.initializing_set(True, timeout_s=deadline.remaining_s())
        can.wait_initializing(True, timeout_s=deadline.remaining_s())
        can.timing_set(timing, timeout_s=deadline.remaining_s())
        can.options_set(
            CanOptions(False, False, False, False, False, True, False, 0, 0, 0),
            timeout_s=deadline.remaining_s(),
        )
        can.ram_layout_set(timeout_fifo_ram(support), timeout_s=deadline.remaining_s())
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, action, 0x123, 0x123),
            extended=False,
            timeout_s=deadline.remaining_s(),
        )
        can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
        can.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())

        # 三阶段只改Timeout使能，不清RAM或复位；启用后的真实条目必须显式消费。
        for stage in ("baseline", "enabled", "disabled"):
            enabled = stage == "enabled"
            config = CanBusConfig(
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
            )
            can.irq_capture_stop(timeout_s=deadline.remaining_s())
            can.irq_event_reset(timeout_s=deadline.remaining_s())
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.bus_config_set(config, timeout_s=deadline.remaining_s())
            actual_config = can.bus_config_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="config",
                value=asdict(actual_config),
                source="dut",
                endpoint=f"{stage}.TIMEOUT.CONFIG",
            )
            assert actual_config == config
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            can.irq_clear(CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s())
            if enabled and not fifo_source:
                before, after = can.timeout_reload(timeout_s=deadline.remaining_s())
                counter_trace.append({"stage": "start", "before": before, "after": after})
                assert 0 < after <= top
            elif enabled:
                empty_count = can.timeout_counter_get(timeout_s=deadline.remaining_s())
                counter_trace.append({"stage": "empty", "count": empty_count})
                assert empty_count == top
            can.irq_capture_pending(CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s())

            # FIFO刺激仅在启用/再次禁用阶段产生；Event模式过滤掉自收帧，三个源互斥。
            stimulated = fifo_source and stage != "baseline"
            payload = pattern(8, inverse=stage == "disabled")
            if stimulated:
                flags = CanFrameFlags.STORE_EVENT if event_source else CanFrameFlags.NONE
                can.tx_write(
                    0, CanTxFrame(0x123, flags, 8, 0x5A, payload), timeout_s=deadline.remaining_s()
                )
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="tx_complete",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1 and not tx.pending & 1
            rx0 = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            rx1 = can.rx_fifo_status_get(1, timeout_s=deadline.remaining_s())
            events = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            # 目标非空且其他两源必须空；任何非目标源同时启动都使方法不成立。
            for name, status, expected in (
                ("RX0", rx0, int(stimulated and not event_source and fifo == 0)),
                ("RX1", rx1, int(stimulated and not event_source and fifo == 1)),
                ("EVENT", events, int(stimulated and event_source)),
            ):
                record_observation(
                    record_property,
                    key="source_fill",
                    value=status.fill,
                    source="dut",
                    endpoint=f"{stage}.{name}.FILL",
                )
                record_observation(
                    record_property,
                    key="source_lost",
                    value=status.lost,
                    source="dut",
                    endpoint=f"{stage}.{name}.LOST",
                )
                assert status.fill == expected and not status.lost

            if enabled:
                pending = can.wait_irq_pending(
                    CanIrqSource.TIMEOUT, timeout_s=deadline.remaining_s()
                )
                # Raw不是ISR证据；等待实际回调计数，最后保留全部锁存字段。
                while True:
                    event = can.irq_event_get(timeout_s=deadline.remaining_s())
                    if event.event_count:
                        break
                    deadline.sleep(0.001)
                counter = can.timeout_counter_get(timeout_s=deadline.remaining_s())
                counter_trace.append({"stage": "expired", "count": counter})
                irq_trace.append({"stage": stage, "raw": int(pending.raw_status), **asdict(event)})
                assert counter == 0 and pending.raw_status & CanIrqSource.TIMEOUT
                assert event.event_count == 1 and event.latched_events == CanIrqSource.TIMEOUT
                assert event.unexpected_count == event.overflow_count == event.fault_flags == 0
            else:
                baseline = can.timeout_counter_get(timeout_s=deadline.remaining_s())
                window_start = monotonic()
                end = window_start + 2 * period_s
                # 禁用窗口实际保留目标条目，不靠空FIFO自然停止掩盖ETOC失效。
                while True:
                    pending = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
                    event = can.irq_event_get(timeout_s=deadline.remaining_s())
                    counter = can.timeout_counter_get(timeout_s=deadline.remaining_s())
                    irq_trace.append(
                        {"stage": stage, "raw": int(pending.raw_status), **asdict(event)}
                    )
                    counter_trace.append({"stage": stage, "count": counter})
                    assert not pending.raw_status & CanIrqSource.TIMEOUT and event.event_count == 0
                    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                    assert counter == baseline
                    assert event.latched_events == CanIrqSource.NONE
                    observed_at = monotonic()
                    if observed_at >= end:
                        negative_windows.append(
                            {"stage": stage, "seconds": observed_at - window_start}
                        )
                        break
                    deadline.sleep(0.001)
            can.irq_capture_stop(timeout_s=deadline.remaining_s())

            # 由Case消费目标数据再Ack，IRQ回调不碰FIFO；消费错误仍保留实际数据。
            if stimulated and event_source:
                frame_event = can.tx_event_read(timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="event_frame",
                    value=asdict(frame_event),
                    source="dut",
                    endpoint="TX_EVENT.HEAD",
                )
                assert frame_event.identifier == 0x123 and frame_event.marker == 0x5A
                assert frame_event.flags == CanFrameFlags.NONE
                assert frame_event.dlc == 8 and frame_event.event_type is CanTxEventType.TRANSMITTED
                can.tx_event_ack(frame_event.index, timeout_s=deadline.remaining_s())
            elif stimulated:
                receive_source = CanRxSource.FIFO1 if fifo else CanRxSource.FIFO0
                frame = can.rx_read(receive_source, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="rx_frame",
                    value=str(frame),
                    source="dut",
                    endpoint=f"RX{fifo}.HEAD",
                )
                assert frame.identifier == 0x123 and frame.flags == CanFrameFlags.NONE
                assert frame.dlc == 8 and frame.data == payload
                can.rx_fifo_ack(fifo, frame.index, timeout_s=deadline.remaining_s())
            if enabled and fifo_source:
                reloaded = can.timeout_counter_get(timeout_s=deadline.remaining_s())
                counter_trace.append({"stage": "empty_reload", "count": reloaded})
                assert reloaded == top
            elif enabled:
                before, after = can.timeout_reload(timeout_s=deadline.remaining_s())
                counter_trace.append({"stage": "reload", "before": before, "after": after})
                assert before == 0 and 0 < after <= top
