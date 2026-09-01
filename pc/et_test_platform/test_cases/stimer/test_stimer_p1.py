# STIMER P1 Formal Case。
#
# 职责：验证生命周期控制、Latch、Compare和IRQ控制矩阵。
# 边界：时钟比例、Shadow时序、外部脉宽、DMA和Debugger留在未实现高等级Case。
# 依赖：仅依赖 STIMER Driver、本 IP Fixture 和公共 Evidence API。

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from statistics import median

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.stimer import (
    StimerConfig,
    StimerFeature,
    StimerIrqEvent,
    StimerLoadMode,
    StimerMode,
    StimerRuntimeStatus,
)
from ...instruments.oscilloscopes import SignalEdge, SignalObserver
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import StimerSupportFactory, require_stimer_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("stimer")]

SHORT_PERIOD_TICKS = 2_000_000
LONG_PERIOD_TICKS = 50_000_000
COMPARE_BASE_TICKS = 20_000_000
LOAD_OLD_PERIOD_TICKS = 15_000_000
LOAD_NEW_PERIOD_TICKS = 45_000_000
LOAD_UPDATE_COUNT_TICKS = 3_000_000
LOAD_OLD_PERIOD_CROSS_TICKS = 18_000_000
SAMPLE_INTERVAL_S = 0.01
IRQ_TIMEOUT_S = 2.0
REPEAT_PERIOD_TICKS = 64
REPEAT_COMPARE_TICKS = 1
REPEAT_EVENT_PULSE_WIDTH_CYCLES = 256
NON_EXTENDED_EVENT_PULSE_WIDTH_CYCLES = 1
PRESCALER_REFERENCE_PERIOD_TICKS = 0xFFFFFFFF
PRESCALER_REFERENCE_WINDOW_S = 0.05
PRESCALER_RATIO_SAMPLE_COUNT = 3
PRESCALER_RATE_RELATIVE_TOLERANCE = 0.20
PULSE_WIDTH_PERIOD_TICKS = 1_000
PULSE_WIDTH_COMPARE_TICKS = 250
PULSE_WIDTH_CYCLES = (1, 8, 32)
PULSE_WIDTH_TIME_SCALE_S = 0.001
PULSE_WIDTH_RATIO_RELATIVE_TOLERANCE = 0.30


# 测试 Feature：
# STIMER 可编程预分频与计数速率比例。
#
# 测试方法：
# 1. 对最小、代表性和Capability最大分频分别配置同一长周期，读取固定窗口内的COUNT.LIVE增量。
# 2. 每个分频节点重复测量三轮并取中位速率，降低串口往返与PC调度抖动影响。
# 3. 以divider=1为基准，比较其他divider的实际速率比与硬件分频比。
#
# 通过条件：
# 1. 每个合法分频节点均能在有界窗口内产生非零计数增量。
# 2. 分频增大时中位计数速率单调下降，实际速率比在统一容差内符合divider比例。
def test_stimer_p1_001_prescaler_ratio(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只消费STIMER预分频、周期和Free-Run能力；分频边界来自Runtime Capability。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.PRESCALER | StimerFeature.PERIOD | StimerFeature.FREE_RUN,
    )
    maximum_divider = support.runtime.maximum_prescaler_divider
    if maximum_divider <= 1:
        raise AssertionError("STIMER prescaler capability must provide at least two divider values")

    divider_values = tuple(
        dict.fromkeys(
            (
                1,
                min(4, maximum_divider),
                maximum_divider,
            )
        )
    )
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.append(("STIMER stop", support.stimer.stop))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 测量：交错执行三轮divider矩阵，避免一次性的PC调度抖动决定最终结果。
        measurements: list[dict[str, float | int]] = []
        rates_by_divider: dict[int, list[float]] = {divider: [] for divider in divider_values}

        # 轮次循环：重复完整divider矩阵，避免连续测同一divider形成顺序偏差。
        for sample_index in range(PRESCALER_RATIO_SAMPLE_COUNT):
            # 节点循环：每个divider都从Stop、Configure和Clear后的确定状态开始。
            for divider in divider_values:
                support.stimer.stop()
                support.stimer.configure(
                    StimerConfig(
                        period_ticks=PRESCALER_REFERENCE_PERIOD_TICKS,
                        prescaler_divider=divider,
                        mode=StimerMode.FREE_RUN,
                    )
                )
                support.stimer.clear()
                configured = True
                support.stimer.start()

                count_before = support.stimer.live_count_get()
                started_s = time.monotonic()
                time.sleep(PRESCALER_REFERENCE_WINDOW_S)
                count_after = support.stimer.live_count_get()
                elapsed_s = time.monotonic() - started_s
                count_delta = count_after - count_before
                actual_rate = count_delta / elapsed_s
                support.stimer.stop()

                rates_by_divider[divider].append(actual_rate)
                measurements.append(
                    {
                        "sample_index": sample_index,
                        "divider": divider,
                        "count_before": count_before,
                        "count_after": count_after,
                        "count_delta": count_delta,
                        "elapsed_s": elapsed_s,
                        "actual_rate_hz": actual_rate,
                    }
                )
                record_observation(
                    record_property,
                    key=f"prescaler_count_samples_{divider}_{sample_index}",
                    value=[count_before, count_after],
                    source="dut",
                    endpoint="COUNT.LIVE",
                )

                if count_delta <= 0:
                    raise AssertionError(f"prescaler divider {divider} produced no count increment")

        # 计算：用各divider的中位速率建立内部比例Oracle。
        median_rates = {divider: median(rates_by_divider[divider]) for divider in divider_values}
        base_divider = divider_values[0]
        base_rate = median_rates[base_divider]
        rate_ratios: list[dict[str, float | int]] = []

        # 比例计算：先形成全部Measurement，随后统一记录Evidence再执行断言。
        for divider in divider_values[1:]:
            actual_ratio = base_rate / median_rates[divider]
            expected_ratio = divider / base_divider
            rate_ratios.append(
                {
                    "base_divider": base_divider,
                    "divider": divider,
                    "expected_ratio": expected_ratio,
                    "actual_ratio": actual_ratio,
                }
            )

        # 证据：保存全部COUNT.LIVE样本、中位速率和分频比，便于定位单轮抖动。
        # Canonical Result要求Mapping Key为字符串；计算过程仍保留整数divider索引。
        median_rates_by_divider = {str(divider): rate for divider, rate in median_rates.items()}
        record_property("actual_rate_hz", median_rates_by_divider)
        record_property("prescaler_rate_ratios", rate_ratios)
        record_property("prescaler_measurements", measurements)
        write_json_result(
            et_artifact_dir / "stimer_p1_001_prescaler_ratio.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_001",
                "measurements": measurements,
                "median_rates_hz": median_rates_by_divider,
                "rate_ratios": rate_ratios,
            },
        )

        # 断言：在Evidence落盘后验证速率单调性和divider比例。
        previous_rate = base_rate
        # 逐节点断言：每一项都与前一速率和基准divider比例独立比较。
        for ratio in rate_ratios:
            divider = int(ratio["divider"])
            if median_rates[divider] >= previous_rate:
                raise AssertionError("STIMER median count rate must decrease as divider increases")

            assert ratio["actual_ratio"] == pytest.approx(
                ratio["expected_ratio"],
                rel=PRESCALER_RATE_RELATIVE_TOLERANCE,
            )
            previous_rate = median_rates[divider]


# 测试 Feature：
# STIMER Compare事件脉宽配置与外部数字波形。
#
# 测试方法：
# 1. 通过逻辑名获取事件输出观测器，配置同一Compare0周期和连续Free-Run计数。
# 2. 依次设置最小、代表性和扩展脉宽，启动STIMER并由真实Compare IRQ确认事件已经产生。
# 3. 读取外部波形的周期和正脉宽，用事件周期与STIMER周期的比例计算Expected脉宽比例。
#
# 通过条件：
# 1. 每个脉宽节点都产生真实Compare事件，并取得正脉宽与周期观测值。
# 2. 实测正脉宽/周期比例与配置的脉宽周期/计数周期比例一致。
def test_stimer_p1_008_event_pulse_width(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    signal_observer_for: Callable[[str], SignalObserver],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求Compare、脉宽、Free-Run、周期和IRQ能力，外部路由由Bench逻辑名决定。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.COMPARE
        | StimerFeature.EVENT_PULSE_WIDTH
        | StimerFeature.FREE_RUN
        | StimerFeature.PERIOD
        | StimerFeature.INTERRUPTS,
    )
    event = StimerIrqEvent.COMPARE0
    observer = signal_observer_for("stimer_output")
    observer_open = False
    observer_running = False
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if observer_running:
            actions.append(("STIMER output observer stop", observer.stop))
        if observer_open:
            actions.append(("STIMER output observer close", observer.close))
        if configured:
            actions.extend(
                (
                    ("STIMER stop", support.stimer.stop),
                    ("STIMER IRQ disable", lambda: support.stimer.irq_disable(event)),
                    ("STIMER IRQ clear", lambda: support.stimer.irq_clear(event)),
                    (
                        "STIMER event pulse width restore",
                        lambda: support.stimer.event_pulse_width_set(
                            event,
                            NON_EXTENDED_EVENT_PULSE_WIDTH_CYCLES,
                        ),
                    ),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 外部观测器准备：只使用Bench绑定的逻辑信号，不出现型号、物理通道或引脚。
        observer.open()
        observer_open = True
        observer.configure_edge_capture(
            time_scale_s=PULSE_WIDTH_TIME_SCALE_S,
            edge=SignalEdge.RISING,
        )

        # 公共STIMER配置：固定周期和Compare门限，只改变待验证的脉宽参数。
        support.stimer.stop()
        support.stimer.configure(
            StimerConfig(
                period_ticks=PULSE_WIDTH_PERIOD_TICKS,
                mode=StimerMode.FREE_RUN,
            )
        )
        support.stimer.clear()
        support.stimer.compare_set(0, PULSE_WIDTH_COMPARE_TICKS)
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        configured = True

        measurements: list[dict[str, float | int]] = []
        # 执行脉宽矩阵：每个节点都重新Arm观测器并等待真实Compare事件。
        for width_cycles in PULSE_WIDTH_CYCLES:
            # 每个宽度节点重新清除事件并重新Arm，避免复用上一个节点的波形。
            support.stimer.stop()
            support.stimer.clear()
            support.stimer.irq_clear(event)
            support.stimer.event_pulse_width_set(event, width_cycles)
            baseline = support.stimer.irq_snapshot_get()
            observer.arm_single()
            observer.run()
            observer_running = True
            support.stimer.start()
            delivered = support.stimer.wait_irq_count(
                baseline.event_count + 2,
                timeout_s=IRQ_TIMEOUT_S,
            )
            observer.stop()
            observer_running = False
            measured = observer.measure()
            if measured.period_s <= 0.0 or measured.positive_width_s <= 0.0:
                raise AssertionError(
                    "STIMER event observer returned a non-positive width or period"
                )
            expected_ratio = width_cycles / PULSE_WIDTH_PERIOD_TICKS
            actual_ratio = measured.positive_width_s / measured.period_s
            measurement = {
                "width_cycles": width_cycles,
                "period_ticks": PULSE_WIDTH_PERIOD_TICKS,
                "expected_ratio": expected_ratio,
                "actual_ratio": actual_ratio,
                "frequency_hz": measured.frequency_hz,
                "period_s": measured.period_s,
                "positive_width_s": measured.positive_width_s,
                "event_count_delta": delivered.event_count - baseline.event_count,
                "last_event": int(delivered.last_event),
            }
            measurements.append(measurement)
        # 证据：保存所有配置值、波形物理量和真实IRQ投递事实。
        record_property("event_pulse_width_cycles", list(PULSE_WIDTH_CYCLES))
        record_property("expected_width_cycles", list(PULSE_WIDTH_CYCLES))
        record_observation(
            record_property,
            key="actual_width_s",
            value=[measurement["positive_width_s"] for measurement in measurements],
            source="observer",
            endpoint="EVENT_PULSE.COMPARE0.POSITIVE_WIDTH_S",
            device_id=observer.identity,
        )
        record_observation(
            record_property,
            key="actual_period_s",
            value=[measurement["period_s"] for measurement in measurements],
            source="observer",
            endpoint="EVENT_PULSE.COMPARE0.PERIOD_S",
            device_id=observer.identity,
        )
        record_property("event_pulse_widths", measurements)
        write_json_result(
            et_artifact_dir / "stimer_p1_008_event_pulse_width.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_008",
                "observer_identity": observer.identity,
                "measurements": measurements,
            },
        )

        # 断言：所有节点的真实Compare Source和外部脉宽比例均符合配置。
        for measurement in measurements:
            assert int(measurement["last_event"]) & int(event) == int(event)
            assert measurement["actual_ratio"] == pytest.approx(
                measurement["expected_ratio"],
                rel=PULSE_WIDTH_RATIO_RELATIVE_TOLERANCE,
            )


# 测试 Feature：
# STIMER One-Shot与Free-Run周期生命周期。
#
# 测试方法：
# 1. One-Shot模式运行到一次自然Overflow，清事件后继续观察一个周期。
# 2. Free-Run模式使用同一Period运行，等待连续两次自然Overflow。
# 3. 比较两种模式的ISR Event Count增量。
#
# 通过条件：
# 1. One-Shot只产生一次Overflow且不会自动进入第二周期。
# 2. Free-Run连续产生至少两次Overflow。
def test_stimer_p1_002_one_shot_and_free_run(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用相同短Period隔离Mode这一唯一变量。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.ONE_SHOT | StimerFeature.FREE_RUN | StimerFeature.INTERRUPTS,
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
        # 公共IRQ配置：清理历史事件并建立Overflow投递。
        support.stimer.stop()
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        configured = True

        # One-Shot阶段：等待一次自然Overflow后观察没有第二次投递。
        support.stimer.configure(
            StimerConfig(period_ticks=SHORT_PERIOD_TICKS, mode=StimerMode.ONE_SHOT)
        )
        support.stimer.clear()
        one_before = support.stimer.irq_snapshot_get()
        support.stimer.start()
        one_after = support.stimer.wait_irq_count(
            one_before.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        time.sleep(0.05)
        one_observed = support.stimer.irq_snapshot_get()

        # Free-Run阶段：清理并切换Mode，等待两个连续自然周期。
        support.stimer.stop()
        support.stimer.irq_clear(event)
        support.stimer.configure(
            StimerConfig(period_ticks=SHORT_PERIOD_TICKS, mode=StimerMode.FREE_RUN)
        )
        support.stimer.clear()
        free_before = support.stimer.irq_snapshot_get()
        support.stimer.start()
        free_after = support.stimer.wait_irq_count(
            free_before.event_count + 2,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # 证据：记录两种Mode的实际Event Count增量。
        one_delta = one_observed.event_count - one_before.event_count
        free_delta = free_after.event_count - free_before.event_count
        record_property("one_shot_event_count_delta", one_delta)
        record_property("free_run_event_count_delta", free_delta)
        record_observation(
            record_property,
            key="free_run_last_event",
            value=int(free_after.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )

        # 附件：断言前保存两种生命周期的完整计数证据。
        write_json_result(
            et_artifact_dir / "stimer_p1_002_one_shot_and_free_run.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_002",
                "one_shot": {
                    "before": one_before.event_count,
                    "first": one_after.event_count,
                    "observed": one_observed.event_count,
                },
                "free_run": {"before": free_before.event_count, "after": free_after.event_count},
            },
        )

        # 断言：One-Shot只终止一次，Free-Run进入后续周期。
        assert one_after.event_count == one_before.event_count + 1
        assert one_delta == 1
        assert free_delta >= 2


# 测试 Feature：
# STIMER软件清零、Pause冻结与Resume连续运行。
#
# 测试方法：
# 1. 以长周期启动计数并读取运行值。
# 2. Pause后间隔读取两次COUNT.LIVE，随后在暂停态执行Clear。
# 3. Resume后再次间隔读取COUNT.LIVE。
#
# 通过条件：
# 1. Pause期间计数保持一致，Clear后计数回到零附近。
# 2. Resume后计数从清零值继续推进。
def test_stimer_p1_003_clear_pause_resume(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用长周期避免本Case与Overflow边界耦合。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.CLEAR | StimerFeature.PAUSE_RESUME,
    )
    started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not started:
            return ()
        return (("STIMER stop", support.stimer.stop),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立正在运行的长周期基线。
        support.stimer.stop()
        support.stimer.configure(StimerConfig(period_ticks=LONG_PERIOD_TICKS))
        support.stimer.clear()
        support.stimer.start()
        started = True
        running = support.stimer.live_count_get()

        # Pause观测：暂停后两次计数必须稳定。
        support.stimer.pause()
        paused_first = support.stimer.live_count_get()
        time.sleep(SAMPLE_INTERVAL_S)
        paused_second = support.stimer.live_count_get()

        # Clear/Resume激励：暂停态清零，再恢复并确认重新推进。
        support.stimer.clear()
        cleared = support.stimer.live_count_get()
        support.stimer.resume()
        resumed_first = support.stimer.live_count_get()
        time.sleep(SAMPLE_INTERVAL_S)
        resumed_second = support.stimer.live_count_get()

        # 证据：记录运行、暂停、清零和恢复四阶段硬件计数。
        record_observation(
            record_property,
            key="count_sequence",
            value=[running, paused_first, paused_second, cleared, resumed_first, resumed_second],
            source="dut",
            endpoint="COUNT.LIVE",
        )

        # 附件：断言前保存生命周期的实际计数时间线。
        write_json_result(
            et_artifact_dir / "stimer_p1_003_clear_pause_resume.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_003",
                "running": running,
                "paused": [paused_first, paused_second],
                "cleared": cleared,
                "resumed": [resumed_first, resumed_second],
            },
        )

        # 断言：Pause冻结、Clear归零、Resume恢复推进。
        assert paused_second == paused_first
        assert cleared < paused_first
        assert resumed_second > resumed_first


# 测试 Feature：
# STIMER Immediate/Shadow 周期加载与生效边界。
#
# 测试方法：
# 1. 两阶段都先用相同旧周期启动 Free-Run，并在计数中段写入更长的新周期。
# 2. Immediate阶段等待计数越过旧周期，确认旧周期边界没有产生Overflow。
# 3. Shadow阶段先等待旧周期Overflow，再确认下一周期可越过旧周期并按新周期Overflow。
#
# 通过条件：
# 1. Immediate更新后COUNT.LIVE可越过旧周期，越过前Event Count不增加。
# 2. Shadow更新后当前旧周期仍产生第一次Overflow。
# 3. Shadow下一周期可越过旧周期，并在新周期终点产生第二次Overflow。
def test_stimer_p1_004_immediate_and_shadow_period_load(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求周期、加载模式、Free-Run和Overflow IRQ能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.PERIOD
        | StimerFeature.LOAD_MODE
        | StimerFeature.FREE_RUN
        | StimerFeature.INTERRUPTS,
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
        # 公共IRQ准备：只观察自然Overflow，不使用Force替代周期边界。
        support.stimer.stop()
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        configured = True

        # Immediate基线：旧周期运行到中段后，立即装载更长的新周期。
        support.stimer.configure(
            StimerConfig(
                period_ticks=LOAD_OLD_PERIOD_TICKS,
                mode=StimerMode.FREE_RUN,
                load_mode=StimerLoadMode.IMMEDIATE,
            )
        )
        support.stimer.clear()
        immediate_before = support.stimer.irq_snapshot_get()
        support.stimer.start()
        immediate_update_count = support.stimer.wait_count(
            lambda count: count >= LOAD_UPDATE_COUNT_TICKS,
            timeout_s=IRQ_TIMEOUT_S,
        )
        support.stimer.configure(
            StimerConfig(
                period_ticks=LOAD_NEW_PERIOD_TICKS,
                mode=StimerMode.FREE_RUN,
                load_mode=StimerLoadMode.IMMEDIATE,
            )
        )

        # Immediate观测：计数越过旧周期时不应已有Overflow。
        immediate_cross_count = support.stimer.wait_count(
            lambda count: count >= LOAD_OLD_PERIOD_CROSS_TICKS,
            timeout_s=IRQ_TIMEOUT_S,
        )
        immediate_cross = support.stimer.irq_snapshot_get()
        immediate_overflow = support.stimer.wait_irq_count(
            immediate_before.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # Shadow基线：重新装载旧周期，在中段只更新Shadow新周期。
        support.stimer.stop()
        support.stimer.irq_clear(event)
        support.stimer.configure(
            StimerConfig(
                period_ticks=LOAD_OLD_PERIOD_TICKS,
                mode=StimerMode.FREE_RUN,
                load_mode=StimerLoadMode.IMMEDIATE,
            )
        )
        support.stimer.clear()
        shadow_before = support.stimer.irq_snapshot_get()
        support.stimer.start()
        shadow_update_count = support.stimer.wait_count(
            lambda count: count >= LOAD_UPDATE_COUNT_TICKS,
            timeout_s=IRQ_TIMEOUT_S,
        )
        support.stimer.configure(
            StimerConfig(
                period_ticks=LOAD_NEW_PERIOD_TICKS,
                mode=StimerMode.FREE_RUN,
                load_mode=StimerLoadMode.SHADOW,
            )
        )

        # Shadow观测：旧周期先完成，新周期随后允许计数越过旧周期。
        shadow_first_overflow = support.stimer.wait_irq_count(
            shadow_before.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        shadow_cross_count = support.stimer.wait_count(
            lambda count: count >= LOAD_OLD_PERIOD_CROSS_TICKS,
            timeout_s=IRQ_TIMEOUT_S,
        )
        shadow_cross = support.stimer.irq_snapshot_get()
        shadow_second_overflow = support.stimer.wait_irq_count(
            shadow_before.event_count + 2,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # 证据：记录两种加载模式的更新位置、越界计数与事件增量。
        record_observation(
            record_property,
            key="immediate_update_count",
            value=immediate_update_count,
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_observation(
            record_property,
            key="immediate_cross_count",
            value=immediate_cross_count,
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_property(
            "immediate_cross_event_delta",
            immediate_cross.event_count - immediate_before.event_count,
        )
        record_observation(
            record_property,
            key="shadow_update_count",
            value=shadow_update_count,
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_property(
            "shadow_first_event_delta",
            shadow_first_overflow.event_count - shadow_before.event_count,
        )
        write_json_result(
            et_artifact_dir / "stimer_p1_004_immediate_and_shadow_period_load.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_004",
                "periods": {
                    "old": LOAD_OLD_PERIOD_TICKS,
                    "new": LOAD_NEW_PERIOD_TICKS,
                },
                "immediate": {
                    "update_count": immediate_update_count,
                    "cross_count": immediate_cross_count,
                    "cross_event_count": immediate_cross.event_count,
                    "overflow_event_count": immediate_overflow.event_count,
                },
                "shadow": {
                    "update_count": shadow_update_count,
                    "first_event_count": shadow_first_overflow.event_count,
                    "cross_count": shadow_cross_count,
                    "cross_event_count": shadow_cross.event_count,
                    "second_event_count": shadow_second_overflow.event_count,
                },
            },
        )

        # 断言：Immediate替换当前周期，Shadow只在下一周期采用新值。
        assert immediate_update_count >= LOAD_UPDATE_COUNT_TICKS
        assert immediate_cross_count >= LOAD_OLD_PERIOD_CROSS_TICKS
        assert immediate_cross.event_count == immediate_before.event_count
        assert immediate_overflow.event_count == immediate_before.event_count + 1
        assert shadow_update_count >= LOAD_UPDATE_COUNT_TICKS
        assert shadow_first_overflow.event_count == shadow_before.event_count + 1
        assert shadow_cross_count >= LOAD_OLD_PERIOD_CROSS_TICKS
        assert shadow_cross.event_count == shadow_first_overflow.event_count
        assert shadow_second_overflow.event_count == shadow_before.event_count + 2


# 测试 Feature：
# STIMER实时计数与重复Latch快照。
#
# 测试方法：
# 1. 启动长周期计数并读取第一组Live/Latch。
# 2. 间隔后再次执行Latch并读取第二组Live/Latch。
# 3. 比较两次Latch与Live推进关系。
#
# 通过条件：
# 1. 每次Latch值落在相邻Live观测区间内。
# 2. 第二次Latch大于第一次且Live计数持续推进。
def test_stimer_p1_005_live_and_repeated_latch(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用Runtime明确发布的Latch能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(support.runtime, StimerFeature.LATCH)
    started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not started:
            return ()
        return (("STIMER stop", support.stimer.stop),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启动不会在观测窗内溢出的长周期。
        support.stimer.stop()
        support.stimer.configure(StimerConfig(period_ticks=LONG_PERIOD_TICKS))
        support.stimer.clear()
        support.stimer.start()
        started = True

        # 第一组观测：实时值后立即触发一次Latch。
        live_before = support.stimer.live_count_get()
        latched_first = support.stimer.latched_count_get()
        live_middle = support.stimer.live_count_get()

        # 第二组观测：独立间隔后重复Latch，证明脉冲可重复使用。
        time.sleep(SAMPLE_INTERVAL_S)
        latched_second = support.stimer.latched_count_get()
        live_after = support.stimer.live_count_get()

        # 证据：分别保存Live序列和Latch序列。
        record_observation(
            record_property,
            key="live_counts",
            value=[live_before, live_middle, live_after],
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_observation(
            record_property,
            key="latched_counts",
            value=[latched_first, latched_second],
            source="dut",
            endpoint="COUNT.LATCHED",
        )

        # 附件：在断言前保存两类计数端点。
        write_json_result(
            et_artifact_dir / "stimer_p1_005_live_and_repeated_latch.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_005",
                "live_counts": [live_before, live_middle, live_after],
                "latched_counts": [latched_first, latched_second],
            },
        )

        # 断言：每次Latch保存当时值，重复Latch会更新快照。
        assert live_before <= latched_first <= live_middle
        assert live_middle <= latched_second <= live_after
        assert latched_second > latched_first


# 测试 Feature：
# STIMER四路Compare门限与事件来源隔离。
#
# 测试方法：
# 1. 参数化四个Compare通道并为每个通道配置不同合法门限。
# 2. 仅使能目标Source，启动计数并等待自然Compare ISR。
# 3. 读取Last Event和全部Source快照。
#
# 通过条件：
# 1. Event Count增加一次，Last Event只包含当前Compare Source。
# 2. 不产生其他Compare或Overflow Source。
@pytest.mark.parametrize(
    ("channel", "event"),
    (
        (0, StimerIrqEvent.COMPARE0),
        (1, StimerIrqEvent.COMPARE1),
        (2, StimerIrqEvent.COMPARE2),
        (3, StimerIrqEvent.COMPARE3),
    ),
)
def test_stimer_p1_006_compare_channels(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    channel: int,
    event: StimerIrqEvent,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：每个参数分支只改变Compare通道和对应门限。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.COMPARE | StimerFeature.INTERRUPTS,
    )
    threshold = COMPARE_BASE_TICKS + channel * 1_000_000
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("STIMER stop", support.stimer.stop),
            ("STIMER IRQ disable", lambda: support.stimer.irq_disable(event)),
            ("STIMER IRQ clear", lambda: support.stimer.irq_clear(StimerIrqEvent.ALL)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：长One-Shot周期确保Compare发生在Overflow之前。
        support.stimer.stop()
        support.stimer.configure(StimerConfig(period_ticks=LONG_PERIOD_TICKS))
        support.stimer.clear()
        support.stimer.compare_set(channel, threshold)
        configured = True
        support.stimer.irq_clear(StimerIrqEvent.ALL)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        baseline = support.stimer.irq_snapshot_get()

        # 激励：启动计数并等待目标Compare自然到达。
        support.stimer.start()
        delivered = support.stimer.wait_irq_count(
            baseline.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # 证据：记录通道门限与真实ISR Source。
        record_property("compare_channel", channel)
        record_property("compare_threshold", threshold)
        record_observation(
            record_property,
            key="irq_last_event",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )

        # 附件：按参数分支保存自然Compare事实。
        write_json_result(
            et_artifact_dir / f"stimer_p1_006_compare_channel_{channel}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_006",
                "channel": channel,
                "threshold": threshold,
                "event_count": {"before": baseline.event_count, "after": delivered.event_count},
                "last_event": int(delivered.last_event),
                "last_raw": int(delivered.last_raw),
            },
        )

        # 断言：自然事件只属于目标Compare Source。
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw & event == event


# 测试 Feature：
# STIMER IRQ Enable/Disable、Mask/Unmask、Force、Clear与真实Delivery。
#
# 测试方法：
# 1. 参数化五类Source，在Mask状态Force并读取Raw/Status/Event Count。
# 2. Unmask后再次Force并等待CPU Delivery。
# 3. Disable后再次Force，确认不再产生Delivery。
#
# 通过条件：
# 1. Mask阶段Raw置位而Status和Event Count不增加。
# 2. Unmask阶段投递一次；Disable阶段Event Count保持不变。
@pytest.mark.parametrize(
    "event",
    tuple(
        event for event in StimerIrqEvent if event not in (StimerIrqEvent.NONE, StimerIrqEvent.ALL)
    ),
)
def test_stimer_p1_007_irq_control_matrix(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    event: StimerIrqEvent,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只使用Runtime发布的IRQ能力和目标Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(support.runtime, StimerFeature.INTERRUPTS)
    irq_bound = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not irq_bound:
            return ()
        return (
            ("STIMER IRQ disable", lambda: support.stimer.irq_disable(event)),
            ("STIMER IRQ clear", lambda: support.stimer.irq_clear(event)),
            ("STIMER IRQ unmask", lambda: support.stimer.irq_unmask(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # Mask阶段：使能Source但保持Mask，随后Force并读取快照。
        support.stimer.irq_clear(event)
        support.stimer.irq_enable(event)
        irq_bound = True
        support.stimer.irq_mask(event)
        baseline = support.stimer.irq_snapshot_get()
        support.stimer.irq_force(event)
        masked = support.stimer.irq_snapshot_get()

        # Unmask阶段：清旧事件后重新Force并等待真实ISR交付。
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        before_delivery = support.stimer.irq_snapshot_get()
        support.stimer.irq_force(event)
        delivered = support.stimer.wait_irq_count(
            before_delivery.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # Disable阶段：关闭Source后Force，确认不产生新的CPU投递。
        support.stimer.irq_clear(event)
        support.stimer.irq_disable(event)
        disabled_before = support.stimer.irq_snapshot_get()
        support.stimer.irq_force(event)
        disabled_after = support.stimer.irq_snapshot_get()

        # 证据：记录三个阶段的Raw、Status和Event Count。
        record_property("irq_source", event.name)
        record_observation(
            record_property,
            key="masked_raw",
            value=int(masked.raw),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="masked_status",
            value=int(masked.status),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )
        record_property("delivery_delta", delivered.event_count - before_delivery.event_count)
        record_property(
            "disabled_delivery_delta",
            disabled_after.event_count - disabled_before.event_count,
        )

        # 附件：按Source保存控制矩阵硬件事实。
        write_json_result(
            et_artifact_dir / f"stimer_p1_007_irq_{event.name.lower()}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_007",
                "event": event.name,
                "masked": {
                    "raw": int(masked.raw),
                    "status": int(masked.status),
                    "event_count": masked.event_count,
                },
                "delivered": {
                    "last_event": int(delivered.last_event),
                    "event_count": delivered.event_count,
                },
                "disabled": {
                    "status": int(disabled_after.status),
                    "event_count": disabled_after.event_count,
                },
            },
        )

        # 断言：Mask、Unmask和Disable分别保持稳定IRQ语义。
        assert masked.raw & event == event
        assert masked.status & event == StimerIrqEvent.NONE
        assert masked.event_count == baseline.event_count
        assert delivered.event_count == before_delivery.event_count + 1
        assert delivered.last_event & event == event
        assert disabled_after.status & event == StimerIrqEvent.NONE
        assert disabled_after.event_count == disabled_before.event_count


# 测试 Feature：
# STIMER Overflow历史状态与read-to-clear生命周期。
#
# 测试方法：
# 1. 单次读取Runtime Status清理前序诊断现场。
# 2. 配置短周期One-Shot并等待一次自然Overflow ISR。
# 3. 连续读取两次Runtime Status，比较首次现场与清除后状态。
#
# 通过条件：
# 1. 自然Overflow后首次原子Snapshot包含OVERFLOW历史位。
# 2. 第二次Snapshot不再包含OVERFLOW，证明read-to-clear生效。
def test_stimer_p1_009_overflow_history_read_to_clear(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求Period、Runtime Status和自然Overflow IRQ三项稳定能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.PERIOD | StimerFeature.STATUS | StimerFeature.INTERRUPTS,
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
            ("STIMER runtime status consume", support.stimer.status_get),
        )

    with case_cleanup_scope(cleanup_actions):
        # 基线：单次原子读取并消费任何前序read-to-clear诊断状态。
        support.stimer.stop()
        baseline_status = support.stimer.status_get()
        support.stimer.configure(
            StimerConfig(period_ticks=SHORT_PERIOD_TICKS, mode=StimerMode.ONE_SHOT)
        )
        support.stimer.clear()
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        configured = True
        baseline_irq = support.stimer.irq_snapshot_get()

        # 激励：只使用自然周期终点，不用IRQ Force替代Overflow行为。
        support.stimer.start()
        delivered = support.stimer.wait_irq_count(
            baseline_irq.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # 观测：第一次读取保存完整现场，第二次读取验证read-to-clear。
        first_status = support.stimer.status_get()
        cleared_status = support.stimer.status_get()

        # 证据：分别记录激励前、Overflow后和清除后的原子状态值。
        record_observation(
            record_property,
            key="overflow_history_status",
            value=[int(baseline_status), int(first_status), int(cleared_status)],
            source="dut",
            endpoint="STATUS_HISTORY.OVERFLOW",
        )
        record_property("overflow_delivery_delta", delivered.event_count - baseline_irq.event_count)
        write_json_result(
            et_artifact_dir / "stimer_p1_009_overflow_history_read_to_clear.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_009",
                "status": {
                    "baseline": int(baseline_status),
                    "first": int(first_status),
                    "cleared": int(cleared_status),
                },
                "irq": {
                    "before": baseline_irq.event_count,
                    "after": delivered.event_count,
                    "last_event": int(delivered.last_event),
                },
            },
        )

        # 断言：自然Overflow真实发生，首次历史位有效，随后被读取动作清除。
        assert delivered.event_count == baseline_irq.event_count + 1
        assert delivered.last_event & event == event
        assert first_status & StimerRuntimeStatus.OVERFLOW == StimerRuntimeStatus.OVERFLOW
        assert cleared_status & StimerRuntimeStatus.OVERFLOW == StimerRuntimeStatus.NONE


# 测试 Feature：
# STIMER Compare重复事件诊断与read-to-clear生命周期。
#
# 测试方法：
# 1. 配置短周期Free-Run、Compare0门限和长于周期的Compare0事件脉宽。
# 2. Mask CPU投递但保留硬件Raw，连续捕获并清除两次自然Compare0事件。
# 3. 停止计数后连续读取两次Runtime Status，保存重复诊断首次现场和清除后状态。
#
# 通过条件：
# 1. 两次自然Compare0均进入Raw，Mask期间CPU Delivery计数不增加。
# 2. 首次状态只包含Compare0 Repeat目标位，第二次读取后目标位清零。
def test_stimer_p1_010_compare_repeat_diagnostic(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只要求本Case直接消费的Compare、脉宽、状态和IRQ控制能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.COMPARE
        | StimerFeature.EVENT_PULSE_WIDTH
        | StimerFeature.FREE_RUN
        | StimerFeature.STATUS
        | StimerFeature.INTERRUPTS,
    )
    event = StimerIrqEvent.COMPARE0
    repeat_status = StimerRuntimeStatus.COMPARE0_REPEAT
    all_repeat_status = (
        StimerRuntimeStatus.COMPARE0_REPEAT
        | StimerRuntimeStatus.COMPARE1_REPEAT
        | StimerRuntimeStatus.COMPARE2_REPEAT
        | StimerRuntimeStatus.COMPARE3_REPEAT
    )
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("STIMER stop", support.stimer.stop),
            ("STIMER IRQ disable", lambda: support.stimer.irq_disable(event)),
            ("STIMER IRQ clear", lambda: support.stimer.irq_clear(event)),
            ("STIMER IRQ unmask", lambda: support.stimer.irq_unmask(event)),
            (
                "STIMER event pulse width restore",
                lambda: support.stimer.event_pulse_width_set(
                    event,
                    NON_EXTENDED_EVENT_PULSE_WIDTH_CYCLES,
                ),
            ),
            ("STIMER runtime status consume", support.stimer.status_get),
        )

    with case_cleanup_scope(cleanup_actions):
        # 基线：消费前序read-to-clear状态，再建立短周期自然重复条件。
        support.stimer.stop()
        baseline_status = support.stimer.status_get()
        support.stimer.configure(
            StimerConfig(period_ticks=REPEAT_PERIOD_TICKS, mode=StimerMode.FREE_RUN)
        )
        support.stimer.clear()
        support.stimer.compare_set(0, REPEAT_COMPARE_TICKS)
        support.stimer.event_pulse_width_set(event, REPEAT_EVENT_PULSE_WIDTH_CYCLES)
        configured = True

        # IRQ控制：Mask只阻止CPU投递，Raw仍用于确认两次自然Compare已发生。
        support.stimer.irq_clear(event)
        support.stimer.irq_unmask(event)
        support.stimer.irq_enable(event)
        support.stimer.irq_mask(event)
        baseline_irq = support.stimer.irq_snapshot_get()

        # 激励：连续捕获两次独立Raw边界，避免用固定Sleep猜测硬件已经重复运行。
        support.stimer.start()
        first_raw = support.stimer.wait_irq_raw(event, timeout_s=IRQ_TIMEOUT_S)
        support.stimer.irq_clear(event)
        second_raw = support.stimer.wait_irq_raw(event, timeout_s=IRQ_TIMEOUT_S)
        support.stimer.stop()

        # 观测：第一次原子状态读取保留Repeat现场，第二次证明read-to-clear。
        first_status = support.stimer.status_get()
        cleared_status = support.stimer.status_get()

        # 证据：硬件Raw、CPU Delivery与Repeat诊断分别记录，不互相冒充。
        record_property("event_pulse_width_cycles", REPEAT_EVENT_PULSE_WIDTH_CYCLES)
        record_property("repeat_period_ticks", REPEAT_PERIOD_TICKS)
        record_observation(
            record_property,
            key="compare_raw_sequence",
            value=[int(first_raw.raw), int(second_raw.raw)],
            source="dut",
            endpoint="IRQ_RAW.COMPARE0",
        )
        record_property(
            "masked_delivery_delta",
            second_raw.event_count - baseline_irq.event_count,
        )
        record_observation(
            record_property,
            key="compare_repeat_status",
            value=[int(baseline_status), int(first_status), int(cleared_status)],
            source="dut",
            endpoint="STATUS_DIAG.COMPARE_REPEAT[0]",
        )

        # 附件：一次发布完整配置、两次Raw与两次诊断读取结果。
        write_json_result(
            et_artifact_dir / "stimer_p1_010_compare_repeat_diagnostic.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p1_010",
                "configuration": {
                    "period_ticks": REPEAT_PERIOD_TICKS,
                    "compare_ticks": REPEAT_COMPARE_TICKS,
                    "event_pulse_width_cycles": REPEAT_EVENT_PULSE_WIDTH_CYCLES,
                },
                "irq": {
                    "baseline_event_count": baseline_irq.event_count,
                    "first_raw": int(first_raw.raw),
                    "second_raw": int(second_raw.raw),
                    "final_event_count": second_raw.event_count,
                },
                "status": {
                    "baseline": int(baseline_status),
                    "first": int(first_status),
                    "cleared": int(cleared_status),
                },
            },
        )

        # 断言：两次自然Compare确实发生，Mask未投递CPU，Repeat目标位有效且可清除。
        assert first_raw.raw & event == event
        assert second_raw.raw & event == event
        assert second_raw.event_count == baseline_irq.event_count
        assert first_status & all_repeat_status == repeat_status
        assert cleared_status & repeat_status == StimerRuntimeStatus.NONE
