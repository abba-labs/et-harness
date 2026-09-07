# CAN发送事件Marker位宽。
# 职责：完整Marker、独立RX数据及事件排空的端到端验证。
# 边界：只用内部回环，不把宽Marker占用位解释为时间戳。
# 依赖：CAN/CRG/Resource公共Driver和只读RAM布局。

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
from ._support import TIMEOUT_S, pattern, phase_timing, tx_event_loopback_ram

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 8/16-bit Message Marker完整传递及宽格式时间戳无效性。
#
# 测试方法：
# 1. 两种位宽独立复位，关闭TSU，开启内部回环与TX Event。
# 2. 读回格式，预先确定两条不同Marker和8-byte A/B载荷。
# 3. 逐帧等待TX完成、核对并Ack完整RX，保留两条TX Event。
# 4. 按格式读两条事件并Ack，核对完整Marker、事件类型及时间戳有效性。
# 5. 排空后连续100ms核对RX和Event无额外条目。
#
# 通过条件：
# 1. 实际格式、两帧RX和两条事件全部匹配，16-bit高字节不能丢失。
# 2. 宽格式时间戳为None，TSU指针始终无效，无丢失或额外事件。
@pytest.mark.parametrize("marker_bits", (8, 16))
def test_can_p1_010_message_marker_width(
    can_support, resource_driver, record_property, marker_bits
) -> None:

    # Expected：两组Marker和载荷均在任何硬件读回前确定。
    support = can_support
    can = support.can
    markers = (0x12, 0xAB) if marker_bits == 8 else (0x1234, 0xABCD)
    payloads = (pattern(8), pattern(8, inverse=True))
    layout = tx_event_loopback_ram(support, watermark=0)
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    event_summary = []
    record_property("event_summary", event_summary)
    record_property("empty_window", "NOT_OBSERVED")
    record_property("expected", {"marker_bits": marker_bits, "markers": markers})
    deadline = OperationDeadline.start(TIMEOUT_S, label="CAN Marker width")

    # 清理：无论在哪条断言停止，复位参与CAN和整池资源。
    with case_cleanup_scope(
        lambda: (
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
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            ),
            timeout_s=deadline.remaining_s(),
        )
        can.event_format_set(CanEventFormat(marker_bits, False), timeout_s=deadline.remaining_s())

        # 实际格式：硬件读回不是请求回显，两项各自保留。
        actual_format = can.event_format_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="marker_bits",
            value=actual_format.marker_bits,
            source="dut",
            endpoint="CONFIG.MARKER_BITS",
        )
        record_observation(
            record_property,
            key="tsu_enabled",
            value=actual_format.tsu_enabled,
            source="dut",
            endpoint="CONFIG.TSU_ENABLED",
        )
        assert actual_format == CanEventFormat(marker_bits, False)
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())

        # 逐帧接收：避免RX FIFO容量影响发送事件数量；事件此时不Ack。
        for sequence, (marker, payload) in enumerate(zip(markers, payloads, strict=True)):
            can.tx_write(
                0,
                CanTxFrame(0x123, CanFrameFlags.STORE_EVENT, 8, marker, payload),
                timeout_s=deadline.remaining_s(),
            )
            can.tx_request(1, timeout_s=deadline.remaining_s())
            tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="completed",
                value=tx.completed,
                source="dut",
                endpoint="TX.COMPLETED",
            )
            assert tx.completed & 1 and not tx.pending & 1 and not tx.cancelled & 1
            can.wait_rx_available(0, timeout_s=deadline.remaining_s())
            rx = can.rx_read(CanRxSource.FIFO0, 0, timeout_s=deadline.remaining_s())
            # RX各字段分别留证，完整数据错误也必须能定位到当前帧。
            for key, value in (
                ("rx_id", rx.identifier),
                ("rx_flags", int(rx.flags)),
                ("rx_dlc", rx.dlc),
                ("rx_data", rx.data.hex()),
            ):
                record_observation(
                    record_property,
                    key=key,
                    value=value,
                    source="dut",
                    endpoint=f"RX0[{rx.index}].{key}",
                )
            assert rx.identifier == 0x123 and rx.flags == CanFrameFlags.NONE
            assert rx.dlc == 8 and rx.data == payload
            can.rx_fifo_ack(0, rx.index, timeout_s=deadline.remaining_s())
            event_status = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="event_fill",
                value=event_status.fill,
                source="dut",
                endpoint="TX_EVENT.FILL",
            )
            record_observation(
                record_property,
                key="event_lost",
                value=event_status.lost,
                source="dut",
                endpoint="TX_EVENT.LOST",
            )
            assert event_status.fill == sequence + 1 and not event_status.lost

        # 事件端点：完整Marker与预先输入比较，不借用RX时间戳或发送缓存。
        for index, expected_marker in enumerate(markers):
            event = can.tx_event_details_read(timeout_s=deadline.remaining_s())
            event_summary.append(
                {
                    "index": event.index,
                    "marker": event.marker,
                    "timestamp": event.timestamp,
                    "tsu_pointer": event.tsu_pointer,
                }
            )
            # 事件字段独立保留，格式无效值不得由摘要掩盖。
            record_observation(
                record_property,
                key="event_marker",
                value=event.marker,
                source="dut",
                endpoint=f"TX_EVENT[{event.index}].MARKER",
            )
            # 其余事件字段逐项保留，不合并为布尔结果。
            for key, value in (
                ("event_index", event.index),
                ("event_id", event.identifier),
                ("event_flags", int(event.flags)),
                ("event_dlc", event.dlc),
                ("event_type", int(event.event_type)),
                ("event_timestamp", event.timestamp),
                ("tsu_pointer", event.tsu_pointer),
            ):
                record_observation(
                    record_property,
                    key=key,
                    value=value,
                    source="dut",
                    endpoint=f"TX_EVENT[{event.index}].{key}",
                )
            assert event.index == index and event.marker == expected_marker
            assert (
                event.identifier == 0x123 and event.flags == CanFrameFlags.NONE and event.dlc == 8
            )
            # DAR模式自动取消发送请求；成功帧的事件类型仍为“取消后成功发送”。
            assert event.event_type is CanTxEventType.TRANSMITTED_AFTER_CANCEL
            assert event.tsu_pointer is None
            if marker_bits == 16:
                assert event.timestamp is None
            else:
                assert event.timestamp is not None and 0 <= event.timestamp <= 0xFFFF
            can.tx_event_ack(event.index, timeout_s=deadline.remaining_s())

        # 负向窗口：Ack后仍监视100ms，任一多余条目或Lost均失败。
        end = monotonic() + 0.1
        # 在固定静默窗口内连续读真实FIFO状态，不用一次空读代表整个窗口。
        while True:
            event_status = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            rx_status = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            # 阶段摘要：只记录已经取得的读数；提前失败时保留未到达状态而非伪造零值。
            record_property(
                "empty_window",
                {
                    "event_fill": event_status.fill,
                    "event_lost": event_status.lost,
                    "rx_fill": rx_status.fill,
                    "rx_lost": rx_status.lost,
                },
            )
            record_observation(
                record_property,
                key="empty_event_fill",
                value=event_status.fill,
                source="dut",
                endpoint="TX_EVENT.FILL",
            )
            # 两个FIFO的丢失和RX数量分开保存后再判定。
            for key, value in (
                ("empty_event_lost", event_status.lost),
                ("empty_rx_fill", rx_status.fill),
                ("empty_rx_lost", rx_status.lost),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=key
                )
            assert event_status.fill == 0 and not event_status.lost
            assert rx_status.fill == 0 and not rx_status.lost
            if monotonic() >= end:
                break
            deadline.sleep(0.005)
