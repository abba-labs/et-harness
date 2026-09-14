# pyright: reportMissingImports=none
# CAN FD ISO/Non-ISO格式矩阵。
# 职责：实际格式读回、匹配双向通信、失配首次错误及ISO恢复取证。
# 边界：不访问寄存器，不以发送成功或接收超时替代协议差异证据。
# 依赖：CAN Driver、Peer与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
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
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...instruments.can_boxes.models import CanBusConfig as PeerBusConfig
from ...instruments.can_boxes.models import CanFrame as PeerFrame
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
NEGATIVE_WINDOW_S = 0.1


# 测试 Feature：
# ISO/Non-ISO两种FD编码匹配收发、交叉格式拒绝及恢复。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置对应波特率、FD/BRS及ISO/Non-ISO格式。
# 2. 匹配组合下执行双向收发核验；失配组合下校验协议错误中断及零接收。
# 3. 失配后重置为标准ISO模式，双向收发验证功能恢复。
#
# 通过条件：
# 1. 匹配与恢复帧数据完全一致；失配时产生协议错误中断且无有效RX帧。
# 2. 终态无挂起与残留。
@pytest.mark.parametrize("length", (16, 64))
@pytest.mark.parametrize(
    "dut_non_iso,peer_non_iso", ((False, False), (True, True), (False, True), (True, False))
)
def test_can_p1_020_fd_format_matrix(
    can_external_support, length, dut_non_iso, peer_non_iso
) -> None:
    # 1）复位
    support, gpio, pins, box = can_external_support
    can_handle = support.can
    can_handle.reset()

    # 2）IP 配置与激励准备
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    payload = pattern(length)
    dlc = 10 if length == 16 else 15
    flags = CanFrameFlags.FD | CanFrameFlags.BRS
    errors = CanIrqSource.PROTOCOL_ARBITRATION | CanIrqSource.PROTOCOL_DATA
    matching = dut_non_iso == peer_non_iso

    for number, function in pins:
        gpio.configure_signal(number, function, can_handle.instance_id)
    box.open()
    box.configure(
        PeerBusConfig(nominal_bitrate=500_000, data_bitrate=2_000_000, non_iso=peer_non_iso)
    )
    box.clear()

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(timing)
    can_handle.options_set(CanOptions(True, True, False, False, False, True, False, 0, 0, 0))
    can_handle.non_iso_set(dut_non_iso)
    can_handle.ram_layout_set(loopback_ram(support, payload_bytes=length))
    can_handle.filter_set(
        0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x321, 0x321), extended=False
    )
    can_handle.loopback_set(CanLoopback.DISABLED)
    can_handle.bus_config_set(
        CanBusConfig(
            False,
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
    assert can_handle.non_iso_get() == dut_non_iso
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果
    if matching:
        # 匹配收发：DUT -> Peer
        can_handle.tx_write(0, CanTxFrame(0x123, flags, dlc, 0, payload))
        can_handle.tx_request(1)
        tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        assert tx.completed & 1
        received = box.receive(timeout_s=TIMEOUT_S)
        assert received is not None and not received.is_echo
        assert received.frame == PeerFrame(0x123, payload, fd=True, brs=True)

        # Peer -> DUT
        box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
        ready = can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        frame = can_handle.rx_read(CanRxSource.FIFO0)
        assert ready.fill == 1 and not ready.lost
        assert frame.identifier == 0x321 and frame.data == payload
        can_handle.rx_fifo_ack(0, frame.index)
    else:
        # 失配验证：Peer 发送，DUT 应报错且不入队
        can_handle.irq_clear(errors)
        box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
        assert can_handle.wait_irq_pending(errors, timeout_s=TIMEOUT_S).raw_status & errors
        protocol = can_handle.protocol_status_consume()
        assert protocol.last_error.name != "NONE"

        deadline = OperationDeadline.start(NEGATIVE_WINDOW_S, label="silent window")
        while not deadline.expired:
            assert can_handle.rx_fifo_status_get(0).fill == 0
            deadline.sleep(0.01)

        # 恢复到标准 ISO 验证
        can_handle.reset()
        box.configure(PeerBusConfig(nominal_bitrate=500_000, data_bitrate=2_000_000, non_iso=False))
        can_handle.initializing_set(True)
        can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
        can_handle.timing_set(timing)
        can_handle.options_set(CanOptions(True, True, False, False, False, True, False, 0, 0, 0))
        can_handle.non_iso_set(False)
        can_handle.ram_layout_set(loopback_ram(support, payload_bytes=length))
        can_handle.filter_set(
            0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x321, 0x321), extended=False
        )
        can_handle.loopback_set(CanLoopback.DISABLED)
        can_handle.bus_config_set(
            CanBusConfig(
                False,
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
        can_handle.initializing_set(False)
        can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

        box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
        can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        recovered = can_handle.rx_read(CanRxSource.FIFO0)
        assert recovered.identifier == 0x321 and recovered.data == payload
        can_handle.rx_fifo_ack(0, recovered.index)

    assert can_handle.rx_fifo_status_get(0).fill == 0
    assert not can_handle.protocol_status_consume().bus_off
