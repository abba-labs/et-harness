# pyright: reportMissingImports=false
# CAN固定位时钟下的速率矩阵。
# 职责：按公开Profile计算时序、实读配置并进行外部双向完整帧检查。
# 边界：不修改CRG输入时钟；Profile频率不是寄存器读数或示波器实测。
# 依赖：CAN Driver、Peer与选定实例句柄。

import pytest  # type: ignore

from ...drivers.can import (
    CanBusConfig,
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
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...instruments.can_boxes.models import CanBusConfig as PeerBusConfig
from ...instruments.can_boxes.models import CanFrame as PeerFrame
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
RATE_NODES = (
    (125_000, None),
    (250_000, None),
    (500_000, None),
    (800_000, None),
    (1_000_000, None),
    (500_000, 2_000_000),
    (500_000, 5_000_000),
    (1_000_000, 2_000_000),
    (1_000_000, 5_000_000),
)


# 测试 Feature：
# 固定输入时钟下五种Classic速率、四种FD仲裁/数据组合的双向真实外部通信。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置外部引脚、Peer盒子与对应波特率时序。
# 2. DUT向Peer发送正向报文，校验Peer无回显接收。
# 3. Peer向DUT发送反向报文，校验DUT接收与终态无Bus Off。
#
# 通过条件：
# 1. 双向四帧收发均无错误，格式及负载字节完全相符。
# 2. Pending/Fill归零，无Lost和Bus Off。
@pytest.mark.parametrize("nominal_bitrate,data_bitrate", RATE_NODES)
def test_can_p1_012_bitrate_matrix(can_external_support, nominal_bitrate, data_bitrate):
    support, gpio, pins, box = can_external_support
    can_handle = support.can
    can_handle.reset()

    fd = data_bitrate is not None
    size, dlc = (64, 15) if fd else (8, 8)
    flags = CanFrameFlags.FD | CanFrameFlags.BRS if fd else CanFrameFlags.NONE
    timing = CanTiming(
        phase_timing(
            support.clock_hz,
            nominal_bitrate,
            support.timing_limits.nominal,
            quanta=25 if nominal_bitrate == 800_000 else 20,
        ),
        phase_timing(
            support.clock_hz,
            data_bitrate or 2_000_000,
            support.timing_limits.data,
            quanta=8 if data_bitrate == 5_000_000 else 20,
        ),
    )
    offset = (1 + timing.data.segment1) * timing.data.prescaler if fd else 0
    options = CanOptions(fd, fd, True, False, False, True, fd, offset, 0, 0)
    forward = tuple(i.to_bytes(4, "little") + pattern(size)[4:] for i in (1, 2))
    reverse = tuple(i.to_bytes(4, "little") + pattern(size, inverse=True)[4:] for i in (3, 4))

    for number, function in pins:
        gpio.configure_signal(number, function, can_handle.instance_id)
    box.open()
    box.configure(
        PeerBusConfig(nominal_bitrate=nominal_bitrate, data_bitrate=data_bitrate or 2_000_000)
    )
    box.clear()

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(timing)
    can_handle.options_set(options)
    can_handle.ram_layout_set(loopback_ram(support, payload_bytes=size))
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
    assert can_handle.timing_get() == timing and can_handle.options_get() == options
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 正向：DUT -> Peer
    for payload in forward:
        can_handle.tx_write(0, CanTxFrame(0x123, flags, dlc, 0, payload))
        can_handle.tx_request(1)
        tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        assert tx.completed & 1 and not tx.pending & 1
        received = box.receive(timeout_s=TIMEOUT_S)
        assert received is not None and not received.is_echo
        assert received.frame == PeerFrame(0x123, payload, fd=fd, brs=fd)

    # 反向：Peer -> DUT
    for payload in reverse:
        box.send(PeerFrame(0x321, payload, fd=fd, brs=fd), single_shot=True)
        ready = can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        frame = can_handle.rx_read(CanRxSource.FIFO0)
        assert ready.fill == 1 and not ready.lost
        assert frame.identifier == 0x321 and frame.flags == flags
        assert frame.dlc == dlc and frame.data == payload
        can_handle.rx_fifo_ack(0, frame.index)

    tx = can_handle.tx_status_get()
    rx = can_handle.rx_fifo_status_get(0)
    protocol = can_handle.protocol_status_consume()
    assert tx.pending == 0 and rx.fill == 0 and not rx.lost and not protocol.bus_off
