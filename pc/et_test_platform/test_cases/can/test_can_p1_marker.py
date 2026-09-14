# pyright: reportMissingImports=none
# CAN发送事件Marker位宽。
# 职责：完整Marker、独立RX数据及事件排空的端到端验证。
# 边界：只用内部回环，不把宽Marker占用位解释为时间戳。
# 依赖：CAN Driver与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

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
from ._support import TIMEOUT_S, pattern, phase_timing, tx_event_loopback_ram

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 8/16-bit Message Marker完整传递及宽格式时间戳无效性。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置对应位宽的Event Format及内部回环。
# 2. 连续发送两条带极值Marker的报文，校验RX接收与TX Event内容。
# 3. Ack后保持100ms静默观察，确认无多余事件产生。
#
# 通过条件：
# 1. 8-bit与16-bit Marker读回值完全准确，16-bit模式下高字节不丢失。
# 2. 100ms窗口内事件FIFO与RX FIFO保持为空。
@pytest.mark.parametrize("marker_bits", (8, 16))
def test_can_p1_010_message_marker_width(can0, marker_bits) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    markers = (0x12, 0xAB) if marker_bits == 8 else (0x1234, 0xABCD)
    payloads = (pattern(8), pattern(8, inverse=True))

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(
        CanTiming(
            phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
            phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
        )
    )
    can_handle.options_set(CanOptions(False, False, False, False, False, True, False, 0, 0, 0))
    can_handle.ram_layout_set(tx_event_loopback_ram(support, watermark=0))
    can_handle.filter_set(
        0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123), extended=False
    )
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(
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
        )
    )
    can_handle.event_format_set(CanEventFormat(marker_bits, False))
    actual_format = can_handle.event_format_get()
    assert actual_format == CanEventFormat(marker_bits, False)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：发送两帧并逐帧核验
    for marker, payload in zip(markers, payloads, strict=True):
        can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.STORE_EVENT, 8, marker, payload))
        can_handle.tx_request(1)
        tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        assert tx.completed & 1
        can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        rx = can_handle.rx_read(CanRxSource.FIFO0, 0)
        assert rx.identifier == 0x123 and rx.dlc == 8 and rx.data == payload
        can_handle.rx_fifo_ack(0, rx.index)

    # 读取两条 TX Event 并比对 Marker
    for idx, expected_marker in enumerate(markers):
        event = can_handle.tx_event_details_read()
        assert event.index == idx and event.marker == expected_marker
        assert event.identifier == 0x123 and event.dlc == 8
        assert event.event_type is CanTxEventType.TRANSMITTED_AFTER_CANCEL
        if marker_bits == 16:
            assert event.timestamp is None
        else:
            assert event.timestamp is not None and 0 <= event.timestamp <= 0xFFFF
        can_handle.tx_event_ack(event.index)

    # 100ms 负向静默窗口观察
    deadline = OperationDeadline.start(0.1, label="negative window")
    while not deadline.expired:
        assert can_handle.tx_event_status_get().fill == 0
        assert can_handle.rx_fifo_status_get(0).fill == 0
        deadline.sleep(0.01)
