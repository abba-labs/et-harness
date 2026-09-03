# STIMER P2 Formal Case。
#
# 职责：验证 STIMER 事件到 DMA Request、DMAMUX、Channel 和内存终点的真实链路。
# 边界：跨 IP 顺序只在 Case 中编排，各 Driver 保持单 IP。
# 依赖：STIMER、DMA、SYSCTRL、Resource Driver 和已审核执行映射。

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaFeature,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.stimer import (
    StimerConfig,
    StimerDebugHaltPolicy,
    StimerFeature,
    StimerIrqEvent,
    StimerMode,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...instruments.signal_generators import PulseStimulus
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    StimerDmaCaseSupport,
    StimerSupportFactory,
    require_stimer_runtime_feature,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("stimer")]

DMA_PERIOD_TICKS = 128
DMA_COMPARE_TICKS = 64
DMA_TRANSFER_BYTES = 4
DMA_DESTINATION_FILL = 0xA5
DMA_TIMEOUT_S = 2.0
DEBUG_HALT_PERIOD_TICKS = 0xFFFFFFFF
DEBUG_HALT_WINDOW_S = 0.2
DEBUG_HALT_SAMPLE_INTERVAL_S = 0.01
EMERGENCY_CAPTURE_SOURCE_ID = 0
EMERGENCY_CAPTURE_TRIGGER_GROUP = 0
EMERGENCY_CAPTURE_MIN_PERIOD_TICKS = 0x10000
EMERGENCY_CAPTURE_PERIOD_TICKS = 0x100000
EMERGENCY_CAPTURE_SETTLE_S = 0.005
UINT32_MODULUS = 1 << 32
DMA_EVENTS = (
    StimerIrqEvent.COMPARE0,
    StimerIrqEvent.COMPARE1,
    StimerIrqEvent.COMPARE2,
    StimerIrqEvent.COMPARE3,
    StimerIrqEvent.OVERFLOW,
)


# 测试 Feature：
# STIMER Compare事件触发DMA P2M搬运。
#
# 测试方法：
# 1. 由执行映射选择STIMER计数周期寄存器、DMAMUX Request和DMA Controller/Interface。
# 2. 对Overflow和Compare0..3逐项配置32-bit固定源到内存的DMA Channel。
# 3. 使能当前自然事件，先启动DMA Channel，再启动STIMER产生目标事件。
# 4. 通过ISR保存的last_raw、last_event和event_count证明目标事件真实发生。
# 5. 等待DMA Channel完成，读取目标内存并与Period硬件编码值比较。
#
# 通过条件：
# 1. ISR投递计数增加，last_raw和last_event均包含当前目标Source。
# 2. DMA Channel在deadline内回到Free且没有ERROR。
# 3. 目标内存32-bit值等于Period减一，证明真实STIMER Request完成一次P2M搬运。
@pytest.mark.parametrize("event", DMA_EVENTS, ids=lambda event: event.name.lower())
def test_stimer_p2_001_dma_event_transfer(
    stimer_dma_support: StimerDmaCaseSupport,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    event: StimerIrqEvent,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只使用Runtime Capability、已审核Route和当前空闲Channel。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=stimer_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.STIMER,
        instance=stimer_dma_support.stimer_support.instance_id,
    )
    resource_driver.reset()

    support = stimer_dma_support
    require_stimer_runtime_feature(
        support.stimer_support.runtime,
        StimerFeature.COMPARE | StimerFeature.DMA_REQUEST,
    )
    dma_capabilities = support.dma.capabilities_get()
    if not dma_capabilities.features & DmaFeature.PERIPHERAL_TO_MEMORY:
        pytest.skip("skip_by_runtime_feature: peripheral-to-memory DMA is unavailable")
    channel = support.dma.find_free_channel()
    expected_value = DMA_PERIOD_TICKS - 1
    resource_ready = False
    controller_enabled = False
    route_configured = False
    channel_configured = False
    stimer_configured = False
    stimer_irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if stimer_irq_enabled:
            actions.append(
                ("STIMER IRQ disable", lambda: support.stimer_support.stimer.irq_disable(event))
            )
        if stimer_configured:
            actions.append(("STIMER stop", support.stimer_support.stimer.stop))
            actions.append(
                ("STIMER IRQ clear", lambda: support.stimer_support.stimer.irq_clear(event))
            )
        if channel_configured:
            actions.append(("DMA channel stop", lambda: support.dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: support.dma.deconfigure(channel)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL STIMER route release",
                    lambda: support.sysctrl.release_dma_request(
                        support.route.controller,
                        support.route.interface,
                    ),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", support.dma.controller_disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # Resource：创建4字节目标内存，并填入可区分的非零背景值。
        support.resource.reset()
        resource_ready = True
        destination = support.resource.create(DMA_TRANSFER_BYTES, alignment=4)
        support.resource.fill(destination, DMA_DESTINATION_FILL)

        # DMA：配置固定外设源到递增内存目标的单Word搬运。
        dma_config = DmaConfig(
            channel=channel,
            source_address=support.route.peripheral_address,
            destination_address=destination.address,
            transfer_count=1,
            transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
            source_width=DmaWidth.BITS_32,
            destination_width=DmaWidth.BITS_32,
            source_address_mode=DmaAddressMode.FIXED,
            destination_address_mode=DmaAddressMode.INCREMENT,
            source_burst=DmaBurst.ITEMS_1,
            destination_burst=DmaBurst.ITEMS_1,
            source_interface=support.route.interface,
        )
        support.dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.interface,
                support.route.request_id,
            )
        )
        route_configured = True
        support.dma.configure(dma_config)
        channel_configured = True

        # STIMER：配置已知Period，并把当前自然事件选为DMA Request源。
        support.stimer_support.stimer.stop()
        support.stimer_support.stimer.irq_disable(event)
        support.stimer_support.stimer.irq_unmask(event)
        support.stimer_support.stimer.irq_clear(event)
        support.stimer_support.stimer.configure(
            StimerConfig(period_ticks=DMA_PERIOD_TICKS, mode=StimerMode.ONE_SHOT)
        )
        if event != StimerIrqEvent.OVERFLOW:
            compare_channel = int(event).bit_length() - 1
            support.stimer_support.stimer.compare_set(compare_channel, DMA_COMPARE_TICKS)
        support.stimer_support.stimer.dma_request_select(event)
        baseline_irq = support.stimer_support.stimer.irq_snapshot_get()
        support.stimer_support.stimer.irq_enable(event)
        stimer_irq_enabled = True
        stimer_configured = True

        # 激励：先武装DMA，再启动STIMER，避免丢失首个Compare0 Request。
        support.dma.start(channel)
        support.stimer_support.stimer.start()
        final_status = support.dma.wait_channel_free(channel, timeout_s=DMA_TIMEOUT_S)

        # 观测：等待ISR保存清除前的自然事件，再读真实DMA目标内存和Channel终态。
        trigger_snapshot = support.stimer_support.stimer.wait_irq_count(
            baseline_irq.event_count + 1,
            timeout_s=DMA_TIMEOUT_S,
        )
        actual_bytes = support.resource.read(destination, DMA_TRANSFER_BYTES)
        actual_value = int.from_bytes(actual_bytes, "little")
        no_error = not bool(final_status.interrupt_events & DmaIrqEvent.ERROR)
        record_observation(
            record_property,
            key="trigger_latched_source",
            value=int(trigger_snapshot.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )
        record_observation(
            record_property,
            key="trigger_latched_raw",
            value=int(trigger_snapshot.last_raw),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_RAW",
        )
        record_property(
            "trigger_event_count_delta",
            trigger_snapshot.event_count - baseline_irq.event_count,
        )
        record_observation(
            record_property,
            key="dma_interrupt_status",
            value=int(final_status.interrupt_events),
            source="dut",
            endpoint="DMA_CHANNEL.INTERRUPT_STATUS",
        )
        record_property("dma_channel_is_free", final_status.is_free)
        record_observation(
            record_property,
            key="dma_actual_word",
            value=actual_value,
            source="dut",
            endpoint="DMA_DESTINATION<-STIMER_COUNT_PERIOD",
        )
        record_property("dma_expected_word", expected_value)

        # Evidence：在决定性断言前保存Expected、Actual与硬件终态。
        write_json_result(
            et_artifact_dir / f"stimer_p2_001_dma_event_transfer_{event.name.lower()}.json",
            {
                "case_id": "stimer_p2_001",
                "event": event.name,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "trigger_delivery": {
                    "event_count_delta": trigger_snapshot.event_count - baseline_irq.event_count,
                    "last_raw": int(trigger_snapshot.last_raw),
                    "last_event": int(trigger_snapshot.last_event),
                },
                "channel_status": {
                    "is_free": final_status.is_free,
                    "interrupt_events": int(final_status.interrupt_events),
                },
            },
        )

        # 断言：必须同时满足真实事件投递、DMA终态和数据终点。
        assert trigger_snapshot.event_count > baseline_irq.event_count
        assert trigger_snapshot.last_raw & event
        assert trigger_snapshot.last_event & event
        assert final_status.is_free
        assert no_error
        assert actual_value == expected_value


# 测试 Feature：
# STIMER 紧急触发源锁存当前计数到系统级捕获端点。
#
# 测试方法：
# 1. 读取Runtime Capability，选择第一个已审核的逻辑紧急源和触发组；外部激励只通过Bench逻辑名获取。
# 2. 配置长周期Free-Run STIMER，先停止旧路由并清理历史状态，再打开脉冲激励器。
# 3. 使能逻辑紧急捕获路由并启动STIMER，读取触发前COUNT.LIVE形成硬件基线。
# 4. 通过pulse_stimulus_for("stimer_emergency_input")发出一个有界脉冲，并保存真实主机激励时间窗。
# 5. 读取EMERGENCY_CAPTURE.COUNT与触发后的COUNT.LIVE，确认捕获值位于本次计数推进窗口。
# 6. 在断言前记录DUT捕获值、DUT实时计数和外部脉冲证据，保证失败时仍可回溯原始硬件现象。
# 7. 停止STIMER、禁用紧急路由并关闭激励器；目标只读捕获值由下一次有效触发覆盖，不猜写清零值。
#
# 通过条件：
# 1. 运行时确实声明EMERGENCY_CAPTURE，配置与读取命令均成功。
# 2. 外部脉冲激励器返回真实执行时间窗，且DUT COUNT.LIVE在触发前后推进。
# 3. EMERGENCY_CAPTURE.COUNT落在触发前后COUNT.LIVE的无符号32-bit计数窗口内。
# 4. Case结束时STIMER停止、紧急路由禁用、外部激励输出关闭。
def test_stimer_p2_002_emergency_capture(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    pytestconfig,
    pulse_stimulus_for: Callable[[str], PulseStimulus],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只消费紧急捕获、周期、Free-Run和Start/Stop能力；缺少能力时由Runtime门禁真实跳过。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.EMERGENCY_CAPTURE
        | StimerFeature.PERIOD
        | StimerFeature.FREE_RUN
        | StimerFeature.START_STOP,
    )
    if support.runtime.maximum_period_ticks < EMERGENCY_CAPTURE_MIN_PERIOD_TICKS:
        pytest.skip(
            "skip_by_runtime_feature: STIMER period range is too small for emergency capture"
        )
    if not pytestconfig.getoption("et_bench"):
        pytest.skip("skip_by_bench_profile: STIMER emergency input pulse is not configured")

    # 逻辑源参数来自当前Capability映射的第一个公开槽位，不暴露芯片XBAR mask或寄存器编号。
    source_id = EMERGENCY_CAPTURE_SOURCE_ID
    trigger_group = EMERGENCY_CAPTURE_TRIGGER_GROUP
    period_ticks = min(
        EMERGENCY_CAPTURE_PERIOD_TICKS,
        support.runtime.maximum_period_ticks,
    )
    stimulus = pulse_stimulus_for("stimer_emergency_input")
    route_configured = False
    timer_started = False
    stimulus_open = False

    try:
        # 配置：停止并清零计数，禁用旧路由后建立本次长周期Free-Run会话。
        support.stimer.stop()
        support.stimer.emergency_capture_clear(source_id, trigger_group)
        support.stimer.configure(StimerConfig(period_ticks=period_ticks, mode=StimerMode.FREE_RUN))
        support.stimer.clear()
        support.stimer.emergency_capture_configure(source_id, trigger_group)
        route_configured = True

        # 激励准备：打开Bench绑定的逻辑脉冲源；打开动作本身不产生DUT触发。
        stimulus.open()
        stimulus_open = True

        # 激励：启动STIMER后读取触发前硬件计数，再发出一次有界外部脉冲。
        support.stimer.start()
        timer_started = True
        count_before = support.stimer.live_count_get()
        pulse_event = stimulus.emit_pulse(width_s=EMERGENCY_CAPTURE_SETTLE_S)
        time.sleep(EMERGENCY_CAPTURE_SETTLE_S)

        # 观测：读取系统级捕获值和触发后COUNT.LIVE，均来自DUT真实端点。
        captured_count = support.stimer.emergency_capture_get()
        count_after = support.stimer.live_count_get()
        count_span = (count_after - count_before) % UINT32_MODULUS
        capture_offset = (captured_count - count_before) % UINT32_MODULUS
        capture_in_window = capture_offset <= count_span

        # 证据：在决定性断言前保存DUT寄存器语义和外部脉冲执行时间窗。
        record_observation(
            record_property,
            key="emergency_capture_count",
            value=captured_count,
            source="dut",
            endpoint="EMERGENCY_CAPTURE.COUNT",
        )
        record_observation(
            record_property,
            key="live_count_samples",
            value=[count_before, count_after],
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_property("live_count_span", count_span)
        record_observation(
            record_property,
            key="pulse_event",
            value={
                "started_s": pulse_event.started_s,
                "completed_s": pulse_event.completed_s,
            },
            source="instrument",
            endpoint="PULSE_STIMULUS",
            device_id=stimulus.identity,
        )
        write_json_result(
            et_artifact_dir / "stimer_p2_002_emergency_capture.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p2_002",
                "source_id": source_id,
                "trigger_group": trigger_group,
                "period_ticks": period_ticks,
                "count_before": count_before,
                "count_after": count_after,
                "captured_count": captured_count,
                "count_span": count_span,
                "capture_offset": capture_offset,
                "capture_in_window": capture_in_window,
                "pulse_event": {
                    "identity": stimulus.identity,
                    "started_s": pulse_event.started_s,
                    "completed_s": pulse_event.completed_s,
                },
            },
        )

        # 断言：计数真实推进，且捕获值来自本次外部激励对应的计数窗口。
        assert count_span > 0
        assert capture_in_window
    finally:
        # 清理：先停止计数，再禁用只读捕获路由，最后关闭外部激励输出。
        if timer_started:
            support.stimer.stop()
        if route_configured:
            support.stimer.emergency_capture_clear(source_id, trigger_group)
        if stimulus_open:
            stimulus.close()


# 测试 Feature：
# STIMER在真实Debugger CPU Halt期间的PAUSE与RUN_FREE策略。
#
# 测试方法：
# 1. 读取Runtime Capability，使用最大合法周期和Free-Run模式避免测试窗口内自然Overflow。
# 2. 配置PAUSE策略，启动STIMER，在CPU保持Halt期间由Debugger间隔读取两次COUNT.LIVE。
# 3. 重新建立独立生命周期，配置RUN_FREE策略并重复相同Debugger Halt窗口。
# 4. 记录计数、策略寄存器和每组采样前后的CPU停核状态；全部采样后才Resume。
#
# 通过条件：
# 1. PAUSE策略的两次停核内读数完全相同，配置回读符合PAUSE。
# 2. RUN_FREE策略的Halt窗口计数增量为正，证明CPU Halt期间STIMER仍在运行。
# 3. 每个策略均由真实Debugger Halt/Resume完成，不能用STIMER软件Pause替代。
def test_stimer_p2_003_debugger_halt_behavior(
    stimer_support_for: StimerSupportFactory,
    stimer_instance_id: int,
    debug_controller,
    stimer_halt_mapping,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求STIMER公开的Debug Halt、周期、Start/Stop和Free-Run能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.STIMER, instance=stimer_instance_id)
    resource_driver.reset()

    support = stimer_support_for(stimer_instance_id)
    require_stimer_runtime_feature(
        support.runtime,
        StimerFeature.DEBUG_HALT
        | StimerFeature.PERIOD
        | StimerFeature.START_STOP
        | StimerFeature.FREE_RUN,
    )
    configured = False
    sample_spec, run_free_mask = stimer_halt_mapping

    try:
        # 配置：建立PAUSE策略的独立长周期计数会话。
        support.stimer.stop()
        support.stimer.configure(
            StimerConfig(
                period_ticks=min(DEBUG_HALT_PERIOD_TICKS, support.runtime.maximum_period_ticks),
                mode=StimerMode.FREE_RUN,
            )
        )
        support.stimer.clear()
        support.stimer.debug_halt_policy_set(StimerDebugHaltPolicy.PAUSE)
        configured = True
        support.stimer.start()
        time.sleep(DEBUG_HALT_SAMPLE_INTERVAL_S)

        # 观测：两组读数均在确认CPU停核后取得；请求等待时长不冒充实际停核时长。
        pause_samples = debug_controller.sample_while_halted(sample_spec, DEBUG_HALT_WINDOW_S)
        pause_before, pause_after = pause_samples.before[0], pause_samples.after[0]
        pause_delta = (pause_after - pause_before) % UINT32_MODULUS
        pause_hold = pause_samples.action
        pause_window_s = pause_samples.interval_s

        # 重建：停止并清零后切换RUN_FREE策略，避免前一策略残留计数影响结果。
        support.stimer.stop()
        support.stimer.clear()
        support.stimer.debug_halt_policy_set(StimerDebugHaltPolicy.RUN_FREE)
        support.stimer.start()
        time.sleep(DEBUG_HALT_SAMPLE_INTERVAL_S)

        # 观测：重复相同停核采样，RUN_FREE应推进；全部读取结束后才恢复CPU。
        run_samples = debug_controller.sample_while_halted(sample_spec, DEBUG_HALT_WINDOW_S)
        run_before, run_after = run_samples.before[0], run_samples.after[0]
        run_delta = (run_after - run_before) % UINT32_MODULUS
        run_hold = run_samples.action
        run_window_s = run_samples.interval_s

        # 证据：在决定性断言前记录COUNT.LIVE、策略和Debugger动作时间线。
        record_property("debugger_identity", debug_controller.identity)
        record_property("pause_window_s", pause_window_s)
        record_property("run_free_window_s", run_window_s)
        record_property("pause_delta", pause_delta)
        record_property("run_free_delta", run_delta)
        record_property("requested_sample_interval_s", [pause_window_s, run_window_s])
        record_observation(
            record_property,
            key="pause_count_samples",
            value=[pause_before, pause_after],
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_observation(
            record_property,
            key="run_free_count_samples",
            value=[run_before, run_after],
            source="dut",
            endpoint="COUNT.LIVE",
        )
        record_observation(
            record_property,
            key="cpu_halt_status",
            value=[*pause_samples.halt_status, *run_samples.halt_status],
            source="dut",
            endpoint="CPU.DEBUG.HALT_STATUS",
            device_id=debug_controller.identity,
        )
        record_observation(
            record_property,
            key="debug_policy_readback",
            value=[
                pause_samples.before[1],
                pause_samples.after[1],
                run_samples.before[1],
                run_samples.after[1],
            ],
            source="dut",
            endpoint="DEBUG_HALT.CONFIG",
            device_id=debug_controller.identity,
        )
        write_json_result(
            et_artifact_dir / "stimer_p2_003_debugger_halt_behavior.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "stimer_p2_003",
                "debugger": {
                    "identity": debug_controller.identity,
                    "pause_hold": {
                        "action": pause_hold.action,
                        "requested_hold_s": pause_hold.requested_hold_s,
                        "started_s": pause_hold.started_s,
                        "completed_s": pause_hold.completed_s,
                        "stdout": str(pause_hold.stdout_path),
                        "stderr": str(pause_hold.stderr_path),
                    },
                    "run_hold": {
                        "action": run_hold.action,
                        "requested_hold_s": run_hold.requested_hold_s,
                        "started_s": run_hold.started_s,
                        "completed_s": run_hold.completed_s,
                        "stdout": str(run_hold.stdout_path),
                        "stderr": str(run_hold.stderr_path),
                    },
                },
                "pause": {
                    "requested_interval_s": pause_window_s,
                    "halt_status": pause_samples.halt_status,
                    "resumed_status": pause_samples.resumed_status,
                    "policy_readback": [pause_samples.before[1], pause_samples.after[1]],
                    "before": pause_before,
                    "after": pause_after,
                    "delta": pause_delta,
                },
                "run_free": {
                    "requested_interval_s": run_window_s,
                    "halt_status": run_samples.halt_status,
                    "resumed_status": run_samples.resumed_status,
                    "policy_readback": [run_samples.before[1], run_samples.after[1]],
                    "before": run_before,
                    "after": run_after,
                    "delta": run_delta,
                },
            },
        )

        # 断言：PAUSE冻结、RUN_FREE推进且两种策略由真实Debugger动作区分。
        assert pause_samples.before[1] & run_free_mask == 0
        assert pause_samples.after[1] & run_free_mask == 0
        assert run_samples.before[1] & run_free_mask == run_free_mask
        assert run_samples.after[1] & run_free_mask == run_free_mask
        assert run_delta > 0
        assert pause_delta == 0
    finally:
        # 清理：原子Halt动作已在单一会话内恢复CPU；这里只恢复STIMER默认策略。
        if configured:
            support.stimer.stop()
            support.stimer.debug_halt_policy_set(StimerDebugHaltPolicy.RUN_FREE)
