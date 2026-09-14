# pyright: reportMissingImports=none
# CAN TDC开启后的外部FD通信。
# 职责：配置读回、双向独立帧比较、实际采样点和错误状态取证。
# 边界：不测物理延迟极限；芯片时序仅来自只读Mapping，不直写寄存器。
# 依赖：CAN Driver、Peer与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...drivers.can import (
    CanBusConfig,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanPhaseTiming,
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


# 测试 Feature：
# TDC Enable/Offset/Filter读回及开启补偿后的FD BRS外部收发。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置外部引脚、Peer盒子与对应TDC参数。
# 2. DUT向Peer发送正向高速FD帧，校验Peer实际捕获并读取TDC采样点。
# 3. Peer向DUT发送反向高速FD帧，校验DUT接收与终态无Bus Off。
#
# 通过条件：
# 1. TDC配置和时序等于输入，双向各两帧完全匹配，无回显、Lost或Bus Off。
@pytest.mark.parametrize("data_bitrate", (2_000_000, 5_000_000))
def test_can_p1_021_tdc_external_fd(can_external_support, data_bitrate) -> None:
    # 1）复位
    support, gpio, pins, box = can_external_support
    can_handle = support.can
    can_handle.reset()

    # 2）IP 配置与激励准备
    phase, offset = support.mapping.CAN_TDC_TIMING_PROFILES[support.clock_hz][data_bitrate]
    timing = CanTiming(
        phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
        CanPhaseTiming(*phase),
    )
    options = CanOptions(True, True, True, False, False, True, True, offset, 0, 0)
    flags = CanFrameFlags.FD | CanFrameFlags.BRS
    forward = tuple(i.to_bytes(4, "little") + pattern(64)[4:] for i in (1, 2))
    reverse = tuple(i.to_bytes(4, "little") + pattern(64, inverse=True)[4:] for i in (3, 4))

    for number, function in pins:
        gpio.configure_signal(number, function, can_handle.instance_id)
    box.open()
    box.configure(PeerBusConfig(nominal_bitrate=1_000_000, data_bitrate=data_bitrate))
    box.clear()

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(timing)
    can_handle.options_set(options)
    can_handle.ram_layout_set(loopback_ram(support, payload_bytes=64))
    can_handle.filter_set(
        0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x321, 0x321), extended=False
    )
    can_handle.loopback_set(CanLoopback.DISABLED)
    can_handle.bus_config_set(
        CanBusConfig(
            monitor=False,
            restricted=False,
            timestamp_divisor=1,
            timestamp_source=CanTimestampSource.DISABLED,
            timeout_source=CanTimeoutSource.CONTINUOUS,
            timeout_period=0,
            timeout_enabled=False,
            reject_remote_ext=True,
            reject_remote_std=True,
            unmatched_ext=CanUnmatchedPolicy.REJECT,
            unmatched_std=CanUnmatchedPolicy.REJECT,
        )
    )
    actual_options = can_handle.options_get()
    assert actual_options.tdc_enabled is True and actual_options.tdc_offset_cycles == offset
    assert can_handle.timing_get() == timing
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：双向收发
    # 正向：DUT -> Peer
    for payload in forward:
        can_handle.tx_write(0, CanTxFrame(0x123, flags, 15, 0, payload))
        can_handle.tx_request(1)
        tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        assert tx.completed & 1
        received = box.receive(timeout_s=TIMEOUT_S)
        assert received is not None and not received.is_echo
        assert received.frame == PeerFrame(0x123, payload, fd=True, brs=True)

    # 反向：Peer -> DUT
    for payload in reverse:
        box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
        ready = can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        dut_frame = can_handle.rx_read(CanRxSource.FIFO0)
        assert ready.fill == 1 and not ready.lost
        assert dut_frame.identifier == 0x321 and dut_frame.flags == flags
        assert dut_frame.dlc == 15 and dut_frame.data == payload
        can_handle.rx_fifo_ack(0, dut_frame.index)

    tx = can_handle.tx_status_get()
    rx = can_handle.rx_fifo_status_get(0)
    protocol = can_handle.protocol_status_consume()
    assert tx.pending == 0 and rx.fill == 0 and not rx.lost and not protocol.bus_off
