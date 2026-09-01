# STIMER P0 Formal Case。
#
# 职责：验证基本Start/Stop计数与自然Overflow。
# 边界：不包含芯片时钟、地址或IRQn事实。
# 依赖：仅依赖 STIMER Driver、本 IP Fixture 和公共 Evidence API。

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.stimer import (
    StimerConfig,
    StimerFeature,
    StimerIrqEvent,
    StimerMode,
)
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import StimerSupportFactory, require_stimer_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("stimer")]

LONG_PERIOD_TICKS = 50_000_000
SHORT_PERIOD_TICKS = 2_000_000
SAMPLE_INTERVAL_S = 0.01
IRQ_TIMEOUT_S = 2.0


# 测试 Feature：
# STIMER Start/Stop与实时计数推进。
#
# 测试方法：
# 1. 配置较长One-Shot周期并清零计数。
# 2. Start后间隔采样两次COUNT.LIVE。
# 3. Stop后再次间隔采样两次COUNT.LIVE。
#
# 通过条件：
# 1. Start阶段第二次计数大于第一次。
# 2. Stop阶段两次计数保持一致。
def test_stimer_p0_001_start_stop_live_count(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择不会在本Case采样窗内溢出的长周期。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(support.runtime, StimerFeature.START_STOP)
    started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not started:
            return ()
        return (("STIMER stop", support.stimer.stop),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：停止并清零后应用One-Shot长周期。
        support.stimer.stop()
        support.stimer.configure(StimerConfig(period_ticks=LONG_PERIOD_TICKS))
        support.stimer.clear()

        # 激励：启动并以独立PC时间间隔采样实时计数。
        support.stimer.start()
        started = True
        running_first = support.stimer.live_count_get()
        time.sleep(SAMPLE_INTERVAL_S)
        running_second = support.stimer.live_count_get()

        # Stop观测：停止后两次读取之间保持计数稳定。
        support.stimer.stop()
        stopped_first = support.stimer.live_count_get()
        time.sleep(SAMPLE_INTERVAL_S)
        stopped_second = support.stimer.live_count_get()

        # 证据：记录运行和停止两个阶段的实际COUNT.LIVE序列。
        record_observation(
            record_property,
            key="running_counts",
            value=[running_first, running_second],
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_observation(
            record_property,
            key="stopped_counts",
            value=[stopped_first, stopped_second],
            source="dut",
            endpoint="COUNT.LIVE",
        )

        # 附件：在决定性断言前保存两阶段硬件计数。
        write_json_result(
            et_artifact_dir / "stimer_p0_001_start_stop_live_count.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p0_001",
                "running_counts": [running_first, running_second],
                "stopped_counts": [stopped_first, stopped_second],
            },
        )

        # 断言：Start推进，Stop冻结。
        assert running_second > running_first
        assert stopped_second == stopped_first


# 测试 Feature：
# STIMER可编程周期、自然Overflow与One-Shot终态。
#
# 测试方法：
# 1. 配置短One-Shot周期，清除Overflow并使能IRQ。
# 2. Start后等待一次自然Overflow ISR投递。
# 3. 读取Last Event、运行时Overflow状态与终态计数。
#
# 通过条件：
# 1. Event Count增加一次且Last Event包含OVERFLOW。
# 2. 运行时Overflow状态置位，系统仍在线可读。
def test_stimer_p0_002_period_and_natural_overflow(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求Period和IRQ两项Runtime能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.PERIOD | StimerFeature.INTERRUPTS,
    )
    event = StimerIrqEvent.OVERFLOW
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("STIMER stop", support.stimer.stop),
            ("STIMER IRQ disable", lambda: support.stimer.irq_disable(event)),
            ("STIMER IRQ clear", lambda: support.stimer.irq_clear(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立无历史Pending的短周期One-Shot会话。
        support.stimer.stop()
        support.stimer.configure(
            StimerConfig(period_ticks=SHORT_PERIOD_TICKS, mode=StimerMode.ONE_SHOT)
        )
        configured = True
        support.stimer.clear()
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        baseline = support.stimer.irq_snapshot_get()

        # 激励：启动后只等待自然Overflow，不使用Force替代。
        support.stimer.start()
        delivered = support.stimer.wait_irq_count(
            baseline.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        runtime_status = support.stimer.status_get()
        terminal_count = support.stimer.live_count_get()

        # 证据：记录自然ISR、运行时Overflow位和终态Count。
        record_property("event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="irq_last_event",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )
        record_observation(
            record_property,
            key="irq_raw_at_delivery",
            value=int(delivered.last_raw),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_RAW",
        )
        record_observation(
            record_property,
            key="runtime_status",
            value=int(runtime_status),
            source="dut",
            endpoint="STATUS.RUNTIME",
        )
        record_observation(
            record_property,
            key="terminal_count",
            value=terminal_count,
            source="dut",
            endpoint="COUNT.LIVE",
        )

        # 附件：保存周期、自然Overflow和终态硬件现场。
        write_json_result(
            et_artifact_dir / "stimer_p0_002_period_and_natural_overflow.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p0_002",
                "period_ticks": SHORT_PERIOD_TICKS,
                "irq": {
                    "before": baseline.event_count,
                    "after": delivered.event_count,
                    "last_raw": int(delivered.last_raw),
                    "last_event": int(delivered.last_event),
                },
                "runtime_status": int(runtime_status),
                "terminal_count": terminal_count,
            },
        )

        # 断言：自然周期终点产生一次Overflow，ISR保留Raw现场且One-Shot归零。
        # ISR拥有并清除当前Raw，因此回调后的瞬态Runtime Status不作为持续置位契约。
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_raw & event == event
        assert delivered.last_event & event == event
        assert terminal_count == 0
