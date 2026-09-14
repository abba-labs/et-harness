# pyright: reportMissingImports=none
# CAN TSU时间基、捕获覆盖和读清测试。
# 职责：比较真实TS0、独立输入及活动时间基，显式复用STIMER计数样本。
# 边界：不假设STIMER与CAN硬连线，不以外部向量读回代替ATB或捕获值。
# 依赖：CAN Driver、STIMER Driver与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...drivers.can import (
    CanBusConfig,
    CanEventFormat,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTsuConfig,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.stimer import StimerConfig
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# TSU内外32-bit时间基、TX捕获New/Lost和单槽读清。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置 TSU 时基及 EOF/SOF 捕获模式。
# 2. 发送帧直至 TS0 捕获新时间戳，消费 TS0 验证仅清目标槽。
# 3. 连续发送 2N 帧制造覆盖，验证 Lost 标志及单槽清零。
#
# 通过条件：
# 1. 外部时间基捕获与预设向量相等，内部时间基在合理区间递增。
# 2. 覆盖后正确报 Lost，读取 TS0 后清除对应槽位的 New 与 Lost。
@pytest.mark.parametrize("timebase", ["internal", 0x12345678, 0x89ABCDEF, "stimer"])
def test_can_p1_018_tsu_capture(
    can0,
    can_stimer_reference,
    timebase,
) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    timer_id, timer, timer_limits = can_stimer_reference
    external = timebase != "internal"
    limits = can_handle.tsu_limits_get()
    assert limits.slots in (4, 8, 16)
    assert external or limits.internal
    vector = timebase if isinstance(timebase, int) else 0

    if timebase == "stimer":
        timer.stop()
        timer.configure(StimerConfig(period_ticks=timer_limits.maximum_period_ticks))
        timer.clear()
        timer.start()
        first = timer.live_count_get()
        vector = timer.live_count_get()
        timer.stop()
        assert first < vector < timer_limits.maximum_period_ticks

    for sof in (False, True) if limits.sof else (False,):
        can_handle.reset()
        can_handle.initializing_set(True)
        can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
        can_handle.timing_set(
            CanTiming(
                phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
                phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
            )
        )
        can_handle.options_set(CanOptions(False, False, False, False, False, True, False, 0, 0, 0))
        can_handle.ram_layout_set(loopback_ram(support))
        can_handle.filter_set(
            0, CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0), extended=False
        )
        can_handle.event_format_set(CanEventFormat(16, True))
        config = CanTsuConfig(True, external, sof, 4)
        can_handle.tsu_config_set(config)
        assert can_handle.tsu_config_get() == config

        if external:
            can_handle.external_vector_set(vector)
            assert can_handle.external_vector_get() == vector
            assert can_handle.tsu_timebase_get() == vector

        can_handle.loopback_set(CanLoopback.INTERNAL)
        can_handle.bus_config_set(
            CanBusConfig(
                True,
                False,
                1,
                CanTimestampSource.EXTERNAL,
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

        initial = can_handle.tsu_flags_get()
        assert initial == (0, 0)
        frame = CanTxFrame(0x123, CanFrameFlags.CAPTURE_TIME, 8, 0, pattern(8))

        # 3）获取并判断结果：首次捕获
        before = can_handle.tsu_timebase_get()
        flags = initial
        for _ in range(limits.slots):
            can_handle.tx_write(0, frame)
            can_handle.tx_request(1)
            tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            assert tx.completed & 1
            flags = can_handle.tsu_flags_get()
            if flags[0] & 1:
                break
        after = can_handle.tsu_timebase_get()
        assert flags[0] & 1 and flags[1] == 0

        # 消费 TS0 并验证单槽读清
        value = can_handle.tsu_slot0_consume()
        cleared = can_handle.tsu_flags_get()
        assert cleared == (flags[0] & ~1, flags[1] & ~1)
        span = (after - before) & 0xFFFFFFFF
        if external:
            assert value == vector
        else:
            assert 0 < span < 0x80000000 and ((value - before) & 0xFFFFFFFF) <= span

        # 连续发送 2N 帧制造覆盖
        before = can_handle.tsu_timebase_get()
        for _ in range(2 * limits.slots):
            can_handle.tx_write(0, frame)
            can_handle.tx_request(1)
            tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            assert tx.completed & 1
        flags = can_handle.tsu_flags_get()
        assert flags[1] & 1, "Lost flag must be set after overwriting slot 0"

        # 再次消费 TS0 验证 Lost 恢复
        can_handle.tsu_slot0_consume()
        after_clear = can_handle.tsu_flags_get()
        assert not (after_clear[1] & 1)
