# STIMER P3 Formal Case。
#
# 职责：验证长时间Free-Run周期、外部周期观测和Service IRQ累计的一致性。
# 边界：不选择仪器型号、物理通道或芯片引脚；长期窗口保持有界并由逻辑信号Fixture提供。
# 依赖：STIMER Driver、逻辑SignalObserver、Runtime Capability和公共Evidence API。

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
    StimerRuntimeStatus,
)
from ...instruments.oscilloscopes import SignalEdge, SignalObserver
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import StimerSupportFactory, require_stimer_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("stimer")]

LONG_RUN_WINDOW_S = 2.0
LONG_RUN_TIME_SCALE_S = 0.1
LONG_RUN_TARGET_EVENTS = 16
LONG_RUN_MIN_PERIOD_TICKS = 1_023
LONG_RUN_EVENT_PULSE_WIDTH_CYCLES = 1
LONG_RUN_COUNT_RELATIVE_TOLERANCE = 0.25
LONG_RUN_FREQUENCY_RELATIVE_TOLERANCE = 0.25
LONG_RUN_DIVIDER_LIMIT = 4

_UNEXPECTED_STATUS = (
    StimerRuntimeStatus.COMPARE0_VALUE_ERROR
    | StimerRuntimeStatus.COMPARE1_VALUE_ERROR
    | StimerRuntimeStatus.COMPARE2_VALUE_ERROR
    | StimerRuntimeStatus.COMPARE3_VALUE_ERROR
    | StimerRuntimeStatus.COMPARE0_REPEAT
    | StimerRuntimeStatus.COMPARE1_REPEAT
    | StimerRuntimeStatus.COMPARE2_REPEAT
    | StimerRuntimeStatus.COMPARE3_REPEAT
)


# 测试 Feature：
# STIMER 长时间Free-Run周期、外部Overflow波形和Service IRQ累计稳定性。
#
# 测试方法：
# 1. 通过逻辑信号获取独立参考频率和STIMER事件输出观测器，不固定仪器或物理通道。
# 2. 依据参考频率和Runtime边界生成两个有界divider/period组合，清除IRQ和诊断基线。
# 3. 对每个组合配置Free-Run及Overflow脉宽，记录START前COUNT.LIVE和IRQ event_count。
# 4. 启动外部Observer与STIMER，运行固定长时窗口；窗口中按预定点读取一次诊断状态。
# 5. 停止STIMER和Observer，读取结束COUNT.LIVE、外部周期、IRQ累计和最终诊断快照。
# 6. 使用参考频率、divider和period计算Expected Overflow总数及Expected输出频率。
# 7. 比较外部周期、IRQ累计和Expected值，区分外部Observer与DUT Service证据。
# 8. 保存所有参数、原始计数、状态和观测器身份，供长时失败复现和报告回溯。
#
# 通过条件：
# 1. 两个合法参数节点均在有界窗口内产生Overflow输出和非零IRQ累计。
# 2. 外部输出频率与独立参考计算值一致，DUT IRQ event_count与Expected Overflow数一致。
# 3. 最终COUNT.LIVE持续推进，诊断状态不包含Compare错误或重复事件。
# 4. 每个节点均有完整的外部观测、DUT快照和结构化Evidence，不以ACK代替硬件事实。
def test_stimer_p3_001_long_run_stability(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    pytestconfig,
    signal_observer_for: Callable[[str], SignalObserver],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只要求本Case直接消费的周期、分频、Free-Run、脉宽、IRQ和状态能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.START_STOP
        | StimerFeature.PERIOD
        | StimerFeature.PRESCALER
        | StimerFeature.FREE_RUN
        | StimerFeature.INTERRUPTS
        | StimerFeature.STATUS
        | StimerFeature.EVENT_PULSE_WIDTH,
    )
    if support.runtime.maximum_period_ticks < LONG_RUN_MIN_PERIOD_TICKS:
        pytest.skip("skip_by_runtime_capability: STIMER period range is too small for P3")
    if not pytestconfig.getoption("et_bench"):
        pytest.skip("skip_by_bench_profile: STIMER long-run logical observers are not configured")

    reference_observer = signal_observer_for("stimer_reference")
    output_observer = signal_observer_for("stimer_output")
    event = StimerIrqEvent.OVERFLOW
    reference_open = False
    reference_running = False
    output_open = False
    output_running = False
    configured = False
    records: list[dict[str, object]] = []

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if output_running:
            actions.append(("STIMER output observer stop", output_observer.stop))
        if output_open:
            actions.append(("STIMER output observer close", output_observer.close))
        if reference_running:
            actions.append(("STIMER reference observer stop", reference_observer.stop))
        if reference_open:
            actions.append(("STIMER reference observer close", reference_observer.close))
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
                            LONG_RUN_EVENT_PULSE_WIDTH_CYCLES,
                        ),
                    ),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 独立参考：先测量时钟频率，后续Expected值不使用PC串口往返时间替代。
        reference_observer.open()
        reference_open = True
        reference_observer.configure_edge_capture(
            time_scale_s=LONG_RUN_TIME_SCALE_S,
            edge=SignalEdge.RISING,
        )
        reference_observer.arm_single()
        reference_observer.run()
        reference_running = True
        reference_observer.stop()
        reference_running = False
        reference = reference_observer.measure()
        if reference.frequency_hz <= 0.0:
            raise AssertionError("independent STIMER reference frequency must be positive")

        # 参数矩阵：用参考频率和Runtime最大周期生成两个可观测的长时Overflow节点。
        maximum_period = support.runtime.maximum_period_ticks
        maximum_divider = support.runtime.maximum_prescaler_divider
        divider_values = tuple(
            dict.fromkeys(
                (
                    1,
                    min(LONG_RUN_DIVIDER_LIMIT, maximum_divider),
                )
            )
        )
        period_values = tuple(
            dict.fromkeys(
                max(
                    LONG_RUN_MIN_PERIOD_TICKS,
                    min(
                        maximum_period,
                        int(
                            reference.frequency_hz
                            * LONG_RUN_WINDOW_S
                            / (divider * LONG_RUN_TARGET_EVENTS)
                        )
                        - 1,
                    ),
                )
                for divider in divider_values
            )
        )

        # 外部观测：一次打开逻辑输出连接，逐节点重新Arm以保持证据边界清晰。
        output_observer.open()
        output_open = True
        output_observer.configure_edge_capture(
            time_scale_s=LONG_RUN_TIME_SCALE_S,
            edge=SignalEdge.RISING,
        )

        # 执行矩阵：每个节点都有独立生命周期、基线、窗口和最终Snapshot。
        for divider, period_ticks in zip(divider_values, period_values, strict=True):
            # 配置：只改变本节点的divider/period，Overflow输出使用最小合法脉宽。
            support.stimer.stop()
            support.stimer.configure(
                StimerConfig(
                    period_ticks=period_ticks,
                    prescaler_divider=divider,
                    mode=StimerMode.FREE_RUN,
                )
            )
            support.stimer.clear()
            support.stimer.event_pulse_width_set(event, LONG_RUN_EVENT_PULSE_WIDTH_CYCLES)
            support.stimer.irq_clear(event)
            support.stimer.irq_unmask(event)
            support.stimer.irq_enable(event)
            configured = True
            baseline_count = support.stimer.live_count_get()
            baseline_irq = support.stimer.irq_snapshot_get()

            # 激励：先Arm外部观测，再启动STIMER，避免丢失本节点的首个输出边沿。
            output_observer.arm_single()
            output_observer.run()
            output_running = True
            started_s = time.monotonic()
            support.stimer.start()
            time.sleep(LONG_RUN_WINDOW_S / 2.0)

            # 中途健康检查：按计划读取一次状态并单独保存，不把它当作最终诊断结论。
            mid_status = support.stimer.status_get()
            time.sleep(LONG_RUN_WINDOW_S / 2.0)
            support.stimer.stop()
            elapsed_s = time.monotonic() - started_s
            output_observer.stop()
            output_running = False
            output = output_observer.measure()

            # 结束采样：读取DUT计数、IRQ累计和最终状态，保留所有原始硬件端点。
            final_count = support.stimer.live_count_get()
            final_irq = support.stimer.irq_snapshot_get()
            final_status = support.stimer.status_get()
            count_delta = final_count - baseline_count
            irq_delta = final_irq.event_count - baseline_irq.event_count
            expected_frequency_hz = reference.frequency_hz / divider / (period_ticks + 1)
            expected_overflow_count = max(1, round(expected_frequency_hz * elapsed_s))
            actual_frequency_hz = output.frequency_hz

            # 证据：在决定性断言前记录独立参考、外部波形和Service累计事实。
            measurement = {
                "divider": divider,
                "period_ticks": period_ticks,
                "elapsed_s": elapsed_s,
                "baseline_count": baseline_count,
                "final_count": final_count,
                "count_delta": count_delta,
                "baseline_event_count": baseline_irq.event_count,
                "final_event_count": final_irq.event_count,
                "irq_delta": irq_delta,
                "expected_frequency_hz": expected_frequency_hz,
                "actual_frequency_hz": actual_frequency_hz,
                "expected_overflow_count": expected_overflow_count,
                "mid_status": int(mid_status),
                "final_status": int(final_status),
                "output_period_s": output.period_s,
                "output_positive_width_s": output.positive_width_s,
            }
            records.append(measurement)
            record_property("expected_overflow_count", expected_overflow_count)
            record_property("stimer_divider", divider)
            record_property("stimer_period_ticks", period_ticks)
            record_observation(
                record_property,
                key="output_frequency",
                value=actual_frequency_hz,
                source="observer",
                endpoint="STIMER_OUTPUT.OVERFLOW.FREQUENCY_HZ",
                device_id=output_observer.identity,
            )
            record_observation(
                record_property,
                key="irq_latched_source",
                value=int(final_irq.last_event),
                source="dut",
                endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
            )
            record_property("irq_event_count_before", baseline_irq.event_count)
            record_property("irq_event_count_after", final_irq.event_count)
            record_property("irq_event_count_delta", irq_delta)
            record_observation(
                record_property,
                key="count_samples",
                value=[baseline_count, final_count],
                source="dut",
                endpoint="COUNT.LIVE",
            )
            record_property("count_delta", count_delta)

            # 数学核对：外部频率、IRQ累计与最终诊断状态必须分别满足自己的判定条件。
            assert actual_frequency_hz == pytest.approx(
                expected_frequency_hz,
                rel=LONG_RUN_FREQUENCY_RELATIVE_TOLERANCE,
            )
            assert irq_delta == pytest.approx(
                expected_overflow_count,
                abs=max(2, round(expected_overflow_count * LONG_RUN_COUNT_RELATIVE_TOLERANCE)),
            )
            assert count_delta > 0
            assert final_irq.last_event & event == event
            assert mid_status & _UNEXPECTED_STATUS == StimerRuntimeStatus.NONE
            assert final_status & _UNEXPECTED_STATUS == StimerRuntimeStatus.NONE

        # 汇总：保留参考身份、参数矩阵和所有节点原始值，供报告与失败复现使用。
        record_observation(
            record_property,
            key="reference_frequency_hz",
            value=reference.frequency_hz,
            source="observer",
            endpoint="REFERENCE.FREQUENCY_HZ",
            device_id=reference_observer.identity,
        )
        record_property("stimer_long_run_measurements", records)
        write_json_result(
            et_artifact_dir / "stimer_p3_001_long_run_stability.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p3_001",
                "reference_identity": reference_observer.identity,
                "output_identity": output_observer.identity,
                "reference_frequency_hz": reference.frequency_hz,
                "measurements": records,
            },
        )
