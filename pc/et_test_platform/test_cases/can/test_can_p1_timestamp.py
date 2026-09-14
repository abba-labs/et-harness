# pyright: reportMissingImports=false
# CAN内部16-bit时间戳测试。
# 职责：验证关闭对照、帧时间戳锁存、自然回卷与显式清零。
# 边界：不作为高精度外部时钟源。
# 依赖：CAN Driver与选定实例句柄。

from math import ceil

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
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 内部时间戳关闭、分频、RX锁存、自然回卷及显式清零。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置分频与内部/关闭两组时间戳。
# 2. 发送报文，核对接收帧捕获的时间戳；观测自然回绕与WRAP中断。
# 3. 执行清零快照，验证计数值归位。
#
# 通过条件：
# 1. 关闭组时间戳为0，内部组时间戳在合理区间内递增。
# 2. 自然回卷触发WRAP中断且可W1C清除，清零快照有效。
@pytest.mark.parametrize("divisor", (1, 2, 16))
def test_can_p1_013_internal_timestamp(can0, divisor) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    bitrate, modulus = 125_000, 65536
    period_s = modulus * divisor / bitrate
    reset_upper = ceil(0.100 * bitrate / divisor) + 1
    timing = CanTiming(
        phase_timing(support.clock_hz, bitrate, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    deadline = OperationDeadline.start(2 * period_s + 5, label="CAN internal timestamp")

    # 对比测试：Disabled 与 Internal
    for source in (CanTimestampSource.DISABLED, CanTimestampSource.INTERNAL):
        internal = source is CanTimestampSource.INTERNAL
        can_handle.reset()

        can_handle.initializing_set(True)
        can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
        can_handle.timing_set(timing)
        can_handle.options_set(CanOptions(False, False, False, False, False, True, False, 0, 0, 0))
        can_handle.ram_layout_set(loopback_ram(support))
        can_handle.filter_set(
            0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123), extended=False
        )
        can_handle.loopback_set(CanLoopback.INTERNAL)
        can_handle.event_format_set(CanEventFormat(8, False))
        can_handle.bus_config_set(
            CanBusConfig(
                True,
                False,
                divisor,
                source,
                CanTimeoutSource.CONTINUOUS,
                1000,
                False,
                True,
                True,
                CanUnmatchedPolicy.REJECT,
                CanUnmatchedPolicy.REJECT,
            )
        )
        can_handle.initializing_set(False)
        can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

        if internal:
            can_handle.timestamp_reset()
            can_handle.irq_clear(CanIrqSource.TIMESTAMP_WRAP)

        for idx in range(2 if internal else 1):
            payload = pattern(8, inverse=idx == 1)
            before = can_handle.timestamp_get()
            can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, payload))
            can_handle.tx_request(1)
            tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            assert tx.completed & 1
            can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
            frame = can_handle.rx_read(CanRxSource.FIFO0)
            after = can_handle.timestamp_get()
            assert frame.identifier == 0x123 and frame.data == payload
            if internal:
                span = (after - before) % modulus
                assert (frame.timestamp - before) % modulus <= span
            else:
                assert before == after == frame.timestamp == 0
            can_handle.rx_fifo_ack(0, frame.index)

    # 自然回卷等待与中断检查
    can_handle.irq_clear(CanIrqSource.TIMESTAMP_WRAP)
    prev = can_handle.timestamp_get()
    while not deadline.expired:
        cur = can_handle.timestamp_get()
        pending = can_handle.irq_snapshot_get()
        if cur < prev:
            assert pending.raw_status & CanIrqSource.TIMESTAMP_WRAP
            break
        prev = cur
        deadline.sleep(0.005)

    can_handle.irq_clear(CanIrqSource.TIMESTAMP_WRAP)
    assert not (can_handle.irq_snapshot_get().raw_status & CanIrqSource.TIMESTAMP_WRAP)

    # 显式清零快照检查
    while True:
        mid = can_handle.timestamp_get()
        if modulus // 2 <= mid <= 3 * modulus // 4:
            break
        deadline.sleep(0.005)

    before, after = can_handle.timestamp_reset_snapshot()
    assert after <= reset_upper and before > reset_upper
