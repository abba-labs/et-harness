# CAN TSU时间基、捕获覆盖和读清测试。
# 职责：比较真实TS0、独立输入及活动时间基，显式复用STIMER计数样本。
# 边界：不假设STIMER与CAN硬连线，不以外部向量读回代替ATB或捕获值。
# 依赖：公共CAN/STIMER/CRG Driver、CAN纯布局和Canonical Evidence。

from dataclasses import asdict

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
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTsuConfig,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...drivers.stimer import StimerConfig
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# TSU内外32-bit时间基、TX捕获New/Lost和单槽读清。
#
# 测试方法：
# 1. 内部源分频4；外部源使用两组固定值及片内STIMER运行中的真实计数样本。
# 2. 外部向量和ATB分别实读，必须均等于输入；逐一执行硬件支持的EOF/SOF。
# 3. 最多N次TX定位TS0新值，读取TS0并证明New/Lost只清目标槽。
# 4. 再执行2N次TX且不读槽，证明覆盖Lost，读取TS0后重新核对读清。
# 5. 内部节点用STIMER前后包围读取，对比分频4/16的相对计数速率。
#
# 通过条件：
# 1. 外部捕获逐bit等于独立输入；内部捕获位于小于半量程的ATB包围区间。
# 2. 捕获TX全部完成，New/Lost按刺激置位，读取只清TS0对应状态。
# 3. 分频归一后的TSU/STIMER速率区间相交，采样不确定度不超过25%。
@pytest.mark.parametrize("timebase", ["internal", 0x12345678, 0x89ABCDEF, "stimer"])
def test_can_p1_018_tsu_capture(
    can_support,
    can_stimer_reference,
    resource_driver,
    record_property,
    timebase,
) -> None:

    support = can_support
    can = support.can
    timer_id, timer, timer_limits = can_stimer_reference
    external = timebase != "internal"
    record_property(
        "expected", "New then Lost; TS0 read clears only slot 0; external exact/internal bounded"
    )
    record_property("capture_source", str(timebase))
    record_property("ts0", "NOT_OBSERVED")
    record_property("flags", "NOT_OBSERVED")
    record_property("timebase", "NOT_OBSERVED")
    original_vector = can.external_vector_get()
    with case_cleanup_scope(
        lambda: (
            ("STIMER stop", timer.stop),
            ("STIMER reset", lambda: support.crg.reset(CrgPeripheral.STIMER, instance=timer_id)),
            ("CAN enter INIT", lambda: can.initializing_set(True)),
            ("CAN await INIT", lambda: can.wait_initializing(True, timeout_s=TIMEOUT_S)),
            ("CAN external vector restore", lambda: can.external_vector_set(original_vector)),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource reset", resource_driver.reset),
        )
    ):
        # 隔离：支撑计数器先复位，随后CAN和资源池；不操作任何调试Halt路径。
        support.crg.reset(CrgPeripheral.STIMER, instance=timer_id)
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        limits = can.tsu_limits_get()
        record_property("tsu_limits", asdict(limits))
        assert limits.slots in (4, 8, 16)
        assert external or limits.internal
        vector = timebase if isinstance(timebase, int) else 0

        # 片内参考：停止前保存真实STIMER计数作为稳定输入，不依赖停止后的计数保持行为。
        if timebase == "stimer":
            timer.stop()
            timer.configure(StimerConfig(period_ticks=timer_limits.maximum_period_ticks))
            timer.clear()
            timer.start()
            first = timer.live_count_get()
            vector = timer.live_count_get()
            timer.stop()
            record_observation(
                record_property,
                key="stimer_sample",
                value=[first, vector],
                source="dut",
                endpoint=f"STIMER[{timer_id}].COUNT.LIVE",
            )
            assert first < vector < timer_limits.maximum_period_ticks

        # 捕获位置：EOF始终执行，SOF仅按真实综合能力增加，不能推断不存在的槽。
        for sof in (False, True) if limits.sof else (False,):
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            deadline = OperationDeadline.start(TIMEOUT_S, label="CAN TSU capture")
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(
                CanTiming(
                    phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
                    phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
                ),
                timeout_s=deadline.remaining_s(),
            )
            can.options_set(
                CanOptions(False, False, False, False, False, True, False, 0, 0, 0),
                timeout_s=deadline.remaining_s(),
            )
            can.ram_layout_set(loopback_ram(support), timeout_s=deadline.remaining_s())
            # 明确关闭RX过滤捕获，不能依赖Message RAM在复位后恰好为零。
            can.filter_set(
                0,
                CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.event_format_set(CanEventFormat(16, True), timeout_s=deadline.remaining_s())
            config = CanTsuConfig(True, external, sof, 4)
            can.tsu_config_set(config, timeout_s=deadline.remaining_s())
            actual = can.tsu_config_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="tsu_config",
                value=asdict(actual),
                source="dut",
                endpoint="TSU.CONFIG",
            )
            assert actual == config
            if external:
                can.external_vector_set(vector, timeout_s=deadline.remaining_s())
                readback = can.external_vector_get(timeout_s=deadline.remaining_s())
                atb = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
                record_property("external_expected", vector)
                record_observation(
                    record_property,
                    key="external_vector",
                    value=readback,
                    source="dut",
                    endpoint="EXTERNAL_VECTOR",
                )
                record_observation(
                    record_property,
                    key="external_atb",
                    value=atb,
                    source="dut",
                    endpoint="TSU.ACTIVE_TIMEBASE",
                )
                assert readback == vector
                assert atb == vector, "external vector has not reached TSU active timebase"
            can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
            can.bus_config_set(
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
                ),
                timeout_s=deadline.remaining_s(),
            )
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            initial = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="initial_new",
                value=initial[0],
                source="dut",
                endpoint="TSU.NEW",
            )
            record_observation(
                record_property,
                key="initial_lost",
                value=initial[1],
                source="dut",
                endpoint="TSU.LOST",
            )
            assert initial == (0, 0)
            frame = CanTxFrame(0x123, CanFrameFlags.CAPTURE_TIME, 8, 0, pattern(8))

            # 首次新值：只读标志，最多N次捕获必须轮到TS0，禁止提前消费时间戳。
            before = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            flags = initial
            # 首轮最多遍历实际槽数，等待分配器轮转到可读的TS0。
            for _ in range(limits.slots):
                can.tx_write(0, frame, timeout_s=deadline.remaining_s())
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="tx_completed",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1
                flags = can.tsu_flags_get(timeout_s=deadline.remaining_s())
                if flags[0] & 1:
                    break
            after = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property, key="first_new", value=flags[0], source="dut", endpoint="TSU.NEW"
            )
            record_observation(
                record_property, key="first_lost", value=flags[1], source="dut", endpoint="TSU.LOST"
            )
            record_observation(
                record_property,
                key="first_atb",
                value=[before, after],
                source="dut",
                endpoint="TSU.ACTIVE_TIMEBASE",
            )
            assert flags[0] & 1
            assert flags[1] == 0, "Lost occurred before any slot could have been overwritten"
            value = can.tsu_slot0_consume(timeout_s=deadline.remaining_s())
            cleared = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property, key="first_ts0", value=value, source="dut", endpoint="TSU.TS0"
            )
            record_observation(
                record_property,
                key="first_clear_new",
                value=cleared[0],
                source="dut",
                endpoint="TSU.NEW",
            )
            record_observation(
                record_property,
                key="first_clear_lost",
                value=cleared[1],
                source="dut",
                endpoint="TSU.LOST",
            )
            record_property("ts0", {"sof": sof, "first": value})
            record_property("flags", {"before": flags, "after": cleared})
            record_property("timebase", {"external": external, "before": before, "after": after})
            assert cleared == (flags[0] & ~1, flags[1] & ~1)
            span = (after - before) & 0xFFFFFFFF
            assert (
                value == vector
                if external
                else (0 < span < 0x80000000 and ((value - before) & 0xFFFFFFFF) <= span)
            )

            # 覆盖：完整2N次TX，中途不读任何槽，末次捕获仍由独立ATB区间包围。
            before = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            # 不消费捕获槽，连续两圈制造真实覆盖条件。
            for _ in range(2 * limits.slots):
                can.tx_write(0, frame, timeout_s=deadline.remaining_s())
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="overwrite_tx_completed",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1
            after = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            flags = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="overwrite_new",
                value=flags[0],
                source="dut",
                endpoint="TSU.NEW",
            )
            record_observation(
                record_property,
                key="overwrite_lost",
                value=flags[1],
                source="dut",
                endpoint="TSU.LOST",
            )
            record_observation(
                record_property,
                key="overwrite_atb",
                value=[before, after],
                source="dut",
                endpoint="TSU.ACTIVE_TIMEBASE",
            )
            assert flags[0] & flags[1] & 1
            value = can.tsu_slot0_consume(timeout_s=deadline.remaining_s())
            cleared = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property, key="overwrite_ts0", value=value, source="dut", endpoint="TSU.TS0"
            )
            record_observation(
                record_property,
                key="overwrite_clear_new",
                value=cleared[0],
                source="dut",
                endpoint="TSU.NEW",
            )
            record_observation(
                record_property,
                key="overwrite_clear_lost",
                value=cleared[1],
                source="dut",
                endpoint="TSU.LOST",
            )
            record_property("ts0", {"sof": sof, "overwrite": value})
            record_property("flags", {"before": flags, "after": cleared})
            record_property("timebase", {"external": external, "before": before, "after": after})
            assert cleared == (flags[0] & ~1, flags[1] & ~1)
            span = (after - before) & 0xFFFFFFFF
            assert (
                value == vector
                if external
                else (0 < span < 0x80000000 and ((value - before) & 0xFFFFFFFF) <= span)
            )

        # 片内计数对照：两种分频的归一速率应相交，不假定两IP时钟相等或绝对精度。
        rate_windows = []
        # 两组分频仅适用于内部时间基；外部节点没有内部速率断言。
        for divisor in (4, 16) if not external else ():
            deadline = OperationDeadline.start(TIMEOUT_S, label="CAN TSU STIMER relative rate")
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.tsu_config_set(
                CanTsuConfig(True, False, False, divisor), timeout_s=deadline.remaining_s()
            )
            rate_config = can.tsu_config_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="rate_config",
                value=asdict(rate_config),
                source="dut",
                endpoint="TSU.CONFIG",
            )
            assert rate_config == CanTsuConfig(True, False, False, divisor)
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            timer.stop()
            timer.configure(StimerConfig(period_ticks=timer_limits.maximum_period_ticks))
            timer.clear()
            timer.start()
            timer_before = timer.live_count_get()
            atb_before = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            timer_inner_before = timer.live_count_get()

            # 窗口由8次真实TX组成，不用PC Sleep推测硬件时间，也不轮询STIMER寄存器。
            for _ in range(8):
                can.tx_write(0, frame, timeout_s=deadline.remaining_s())
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="rate_tx_completed",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1
            timer_inner_after = timer.live_count_get()
            atb_after = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
            timer_after = timer.live_count_get()
            timer.stop()
            record_observation(
                record_property,
                key="rate_stimer_counts",
                value=[timer_before, timer_inner_before, timer_inner_after, timer_after],
                source="dut",
                endpoint=f"STIMER[{timer_id}].COUNT.LIVE",
            )
            record_observation(
                record_property,
                key="rate_atb_counts",
                value=[atb_before, atb_after],
                source="dut",
                endpoint="TSU.ACTIVE_TIMEBASE",
            )
            assert (
                0
                <= timer_before
                <= timer_inner_before
                < timer_inner_after
                <= timer_after
                < timer_limits.maximum_period_ticks
            )
            inner_span = timer_inner_after - timer_inner_before
            outer_span = timer_after - timer_before
            atb_span = (atb_after - atb_before) & 0xFFFFFFFF
            rate_windows.append(
                {
                    "divisor": divisor,
                    "tsu_delta": atb_span,
                    "reference_min": inner_span,
                    "reference_max": outer_span,
                }
            )
            record_property("relative_rate_windows", list(rate_windows))
            assert 0 < atb_span < 0x80000000
            assert outer_span * 4 <= inner_span * 5, "STIMER bracketing uncertainty exceeds 25%"

        # 用交叉乘法比较有理数区间，避免浮点容差或事后扩大误差带。
        if not external:
            fast, slow = rate_windows
            fast_numerator = fast["divisor"] * fast["tsu_delta"]
            slow_numerator = slow["divisor"] * slow["tsu_delta"]
            assert fast_numerator * slow["reference_min"] <= slow_numerator * fast["reference_max"]
            assert slow_numerator * fast["reference_min"] <= fast_numerator * slow["reference_max"]
