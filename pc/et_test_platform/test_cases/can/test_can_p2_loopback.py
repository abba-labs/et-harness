# pyright: reportMissingImports=none
# CAN内部/外部回环的引脚输出对照。
# 职责：先证明正常捕获，再用只听Observer比较内部静默与外部真实帧。
# 边界：只调用公共Driver和盒子API；错误捕获窗口不能解释成无外发。
# 依赖：CAN Driver、Peer与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...core.deadline import OperationDeadline
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
from ._support import PATTERN_A, TIMEOUT_S, loopback_ram, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
SILENT_WINDOW_S = 0.1


# 测试 Feature：
# 内部回环无引脚输出、外部回环有引脚输出，且两者本机都完成收发。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置引脚并打开Peer盒子。
# 2. 依次测试 Normal、Internal、External 三种模式。
# 3. 校验本机收发及Peer捕获结果（Internal模式下Peer静默100ms）。
#
# 通过条件：
# 1. Normal/External模式Peer均捕获到帧；Internal模式Peer收不到帧且DUT自收成功。
# 2. 各模式下终态无Bus Off且无Lost。
def test_can_p2_005_loopback_pin_comparison(can_external_support) -> None:
    # 1）复位
    support, gpio, pins, box = can_external_support
    can_handle = support.can
    can_handle.reset()

    # 2）IP 配置与激励准备
    timing = CanTiming(
        phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    for number, function in pins:
        gpio.configure_signal(number, function, can_handle.instance_id)
    box.open()

    # 3）获取并判断结果：三阶段对比 (Normal -> Internal -> External)
    for stage, mode, sequences in (
        ("normal", CanLoopback.DISABLED, (0,)),
        ("internal", CanLoopback.INTERNAL, (1, 2)),
        ("external", CanLoopback.EXTERNAL, (3, 4)),
    ):
        can_handle.reset()
        box.configure(PeerBusConfig(nominal_bitrate=1_000_000, listen_only=False))
        box.clear()

        can_handle.initializing_set(True)
        can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
        can_handle.timing_set(timing)
        can_handle.options_set(CanOptions(False, False, True, False, False, True, False, 0, 0, 0))
        can_handle.ram_layout_set(loopback_ram(support))
        can_handle.filter_set(
            0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123), extended=False
        )
        can_handle.loopback_set(mode)
        can_handle.bus_config_set(
            CanBusConfig(
                monitor=stage == "internal",
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
        can_handle.initializing_set(False)
        can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)
        assert can_handle.loopback_get() == mode

        for sequence in sequences:
            payload = sequence.to_bytes(4, "little") + PATTERN_A[4:]
            can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, payload))
            can_handle.tx_request(1)
            tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            assert tx.completed & 1

            if stage != "normal":
                can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
                local = can_handle.rx_read(CanRxSource.FIFO0)
                assert local.identifier == 0x123 and local.data == payload
                can_handle.rx_fifo_ack(0, local.index)

            if stage != "internal":
                captured = box.receive(timeout_s=TIMEOUT_S)
                assert not captured.is_echo and captured.frame == PeerFrame(0x123, payload)

        if stage == "internal":
            deadline = OperationDeadline.start(SILENT_WINDOW_S, label="silent window")
            while not deadline.expired:
                assert box.receive(timeout_s=0.01) is None
                deadline.sleep(0.01)

        assert can_handle.rx_fifo_status_get(0).fill == 0
        assert not can_handle.protocol_status_consume().bus_off
