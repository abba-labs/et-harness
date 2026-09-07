# CAN内部16-bit时间戳。
# 职责：关闭对照、帧锁存窗口、自然回绕和受限清零快照。
# 边界：PC时间仅作保守窗口上界，不作为硬件计数精度Oracle。
# 依赖：CAN/CRG/Resource Driver、纯数据布局和统一Deadline。

from dataclasses import asdict
from math import ceil
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
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# 内部时间戳关闭、分频、RX锁存、自然回卷及显式清零。
#
# 测试方法：
# 1. 125k内部回环，独立复位建立关闭和内部计数两组，分频1/2/16。
# 2. 关闭组发一帧，内部组发两帧；逐帧记录计数前后值及完整RX。
# 3. 内部采样窗口必须短于半周期；观察相邻计数下降及新Wrap Raw，再W1C。
# 4. 等待中段计数后单命令清零快照，预先固定100ms保守包围上界。
#
# 通过条件：
# 1. 关闭组全零；内部RX时间戳落在实读模区间，有真实回卷和有效清IRQ。
# 2. 清零前远离0及回卷，清零后不超过预算；无效窗口失败，不重试找样本。
@pytest.mark.parametrize("divisor", (1, 2, 16))
def test_can_p1_013_internal_timestamp(can_support, resource_driver, record_property, divisor):

    support = can_support
    can = support.can
    bitrate, modulus = 125_000, 65536
    period_s = modulus * divisor / bitrate
    reset_limit_s = 0.100
    reset_upper = ceil(reset_limit_s * bitrate / divisor) + 1
    timing = CanTiming(
        phase_timing(support.clock_hz, bitrate, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    timestamps, wraps = [], []
    reset_snapshot = {}
    record_property("timestamp", timestamps)
    record_property("wrap", wraps)
    record_property("reset_snapshot", reset_snapshot)
    record_property(
        "expected",
        {
            "bitrate": bitrate,
            "divisor": divisor,
            "half_period_s": period_s / 2,
            "reset_limit_s": reset_limit_s,
            "reset_upper": reset_upper,
        },
    )
    deadline = OperationDeadline.start(2 * period_s + 5, label="CAN internal timestamp")

    # 清理：不安装ISR或使用DMA；复位CAN后释放整池资源。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：两组独立复位CAN和资源，不继承关闭组的RAM及计数配置。
        for source in (CanTimestampSource.DISABLED, CanTimestampSource.INTERNAL):
            internal = source is CanTimestampSource.INTERNAL
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(timing, timeout_s=deadline.remaining_s())
            can.options_set(
                CanOptions(False, False, False, False, False, True, False, 0, 0, 0),
                timeout_s=deadline.remaining_s(),
            )
            can.ram_layout_set(loopback_ram(support), timeout_s=deadline.remaining_s())
            can.filter_set(
                0,
                CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
            can.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
            config = CanBusConfig(
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
            can.bus_config_set(config, timeout_s=deadline.remaining_s())
            actual = can.bus_config_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="config",
                value=asdict(actual),
                source="dut",
                endpoint=f"{source.name}.BUS.CONFIG",
            )
            assert actual == config
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            if internal:
                can.timestamp_reset(timeout_s=deadline.remaining_s())
                can.irq_clear(CanIrqSource.TIMESTAMP_WRAP, timeout_s=deadline.remaining_s())

            # 刺激：关闭组一帧，内部组A/B两帧；Ack放在采样窗口之后。
            for index in range(2 if internal else 1):
                payload = pattern(8, inverse=index == 1)
                started = monotonic()
                before = can.timestamp_get(timeout_s=deadline.remaining_s())
                can.tx_write(
                    0,
                    CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, payload),
                    timeout_s=deadline.remaining_s(),
                )
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                fifo = can.wait_rx_available(0, timeout_s=deadline.remaining_s())
                frame = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
                after = can.timestamp_get(timeout_s=deadline.remaining_s())
                elapsed = monotonic() - started
                timestamps.append(
                    {
                        "source": source.name,
                        "before": before,
                        "after": after,
                        "timestamp": frame.timestamp,
                        "window_s": elapsed,
                    }
                )
                # 原始计数分别进入Canonical Observation；时间预算属于Measurement。
                for label, value in (
                    ("before", before),
                    ("after", after),
                    ("captured", frame.timestamp),
                ):
                    record_observation(
                        record_property,
                        key=f"timestamp_{label}",
                        value=value,
                        source="dut",
                        endpoint=f"{source.name}.RX0.{index}.{label}",
                    )
                record_observation(
                    record_property,
                    key="rx_frame",
                    value=str(frame),
                    source="dut",
                    endpoint=f"{source.name}.RX0.{index}",
                )
                record_observation(
                    record_property,
                    key="tx_state",
                    value=asdict(tx),
                    source="dut",
                    endpoint=f"{source.name}.TX.{index}",
                )
                assert tx.completed & 1 and not tx.pending & 1
                assert fifo.fill == 1 and not fifo.lost
                assert frame.identifier == 0x123 and frame.flags == CanFrameFlags.NONE
                assert frame.dlc == 8 and frame.data == payload
                assert 0 <= before < modulus and 0 <= after < modulus
                assert 0 <= frame.timestamp < modulus
                if internal:
                    assert elapsed < period_s / 2, "invalid timestamp sampling window"
                    span = (after - before) % modulus
                    assert span < modulus / 2
                    assert (frame.timestamp - before) % modulus <= span
                else:
                    assert before == after == frame.timestamp == 0
                can.rx_fifo_ack(0, frame.index, timeout_s=deadline.remaining_s())

        # 自然回卷：清除旧Raw后同时观察相邻计数下降与新Raw，不强制IRQ。
        can.irq_clear(CanIrqSource.TIMESTAMP_WRAP, timeout_s=deadline.remaining_s())
        previous_start = monotonic()
        previous = can.timestamp_get(timeout_s=deadline.remaining_s())
        # 等待自然回卷；每一对读数都必须满足采样窗口，首次不合格即失败。
        while True:
            current_start = monotonic()
            current = can.timestamp_get(timeout_s=deadline.remaining_s())
            pending = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
            elapsed = monotonic() - previous_start
            wraps.append(
                {
                    "before": previous,
                    "after": current,
                    "raw": int(pending.raw_status),
                    "window_s": elapsed,
                }
            )
            record_observation(
                record_property,
                key="wrap_pair",
                value={"before": previous, "after": current},
                source="dut",
                endpoint="TIMESTAMP.WRAP.COUNTERS",
            )
            record_observation(
                record_property,
                key="wrap_raw",
                value=int(pending.raw_status),
                source="dut",
                endpoint="TIMESTAMP.WRAP.RAW",
            )
            assert 0 <= previous < modulus and 0 <= current < modulus
            assert elapsed < period_s / 2, "invalid wrap sampling window"
            if current < previous:
                assert pending.raw_status & CanIrqSource.TIMESTAMP_WRAP
                break
            previous, previous_start = current, current_start
            deadline.sleep(0.005)
        can.irq_clear(CanIrqSource.TIMESTAMP_WRAP, timeout_s=deadline.remaining_s())
        cleared = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="wrap_clear",
            value=int(cleared.raw_status),
            source="dut",
            endpoint="TIMESTAMP.WRAP.RAW_AFTER_W1C",
        )
        assert not cleared.raw_status & CanIrqSource.TIMESTAMP_WRAP

        # 清零：先等待中段，再以单个RPC包围MCU相邻读写读；快照无效不重采。
        while True:
            middle = can.timestamp_get(timeout_s=deadline.remaining_s())
            if modulus // 2 <= middle <= 3 * modulus // 4:
                break
            deadline.sleep(0.005)
        started = monotonic()
        before, after = can.timestamp_reset_snapshot(timeout_s=deadline.remaining_s())
        elapsed = monotonic() - started
        reset_snapshot.update({"before": before, "after": after, "window_s": elapsed})
        record_observation(
            record_property,
            key="reset_before",
            value=before,
            source="dut",
            endpoint="TIMESTAMP.RESET.BEFORE",
        )
        record_observation(
            record_property,
            key="reset_after",
            value=after,
            source="dut",
            endpoint="TIMESTAMP.RESET.AFTER",
        )
        assert elapsed <= reset_limit_s, "invalid reset sampling window"
        assert reset_upper < before and before + reset_upper < modulus
        assert after <= reset_upper
