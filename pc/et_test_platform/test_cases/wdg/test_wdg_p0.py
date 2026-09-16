# WDG P0 Formal Case。
# 职责：验证安全配置下的计数、使能/禁用和独立模式喂狗重载。
# 边界：不触发系统复位，不使用芯片物理事实，不把命令成功当作硬件结论。
# 依赖：WDG Driver、公共证据工具和 pytest。

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.wdg import WdgConfig, WdgFeature, WdgIrqEvent, WdgRecord, WdgWorkMode
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ._support import WdgSupportFactory, require_wdg_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("wdg")]

SAFE_RELOAD_COUNT = 5_000_000
SAFE_RELOAD_COUNT_SECOND = 7_000_000
COUNTER_SAMPLE_INTERVAL_S = 0.01
RESET_RECONNECT_TIMEOUT_S = 20.0


# 测试 Feature：
# WDG使能/禁用、重载尺度与当前计数推进。
#
# 测试方法：
# 1. 在复位输出关闭的独立模式下配置第一组安全Reload并读取使能前状态。
# 2. 使能后用独立单调时间间隔采样两次COUNTER.CURRENT，确认计数真实推进。
# 3. 禁用后再次采样，确认状态为禁用且计数不再产生新的自然事件。
# 4. 配置第二组Reload并使能，确认实际计数尺度与第一组可区分。
#
# 通过条件：
# 1. 使能阶段COUNTER.CURRENT真实递减，禁用状态读回为False。
# 2. 两组Reload形成可区分的实际计数尺度，全程没有新增Raw超时事件。
def test_wdg_p0_002_enable_disable_and_counter(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造不触发系统复位的两组独立模式配置。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.ENABLE)
    config_first = WdgConfig(reload_count=SAFE_RELOAD_COUNT)
    config_second = WdgConfig(reload_count=SAFE_RELOAD_COUNT_SECOND)

    try:
        # 清理：关闭计数并删除历史IRQ/中断记录，建立本Case干净基线。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.irq_clear()
        support.wdg.record_clear(WdgRecord.INTERRUPT)

        # 第一组配置：使能前读回状态，随后用独立时间窗口采样真实计数。
        support.wdg.configure(config_first)
        before_enable = support.wdg.status_get()
        support.wdg.enable()
        first_sample = support.wdg.status_get()
        first_time = time.monotonic()
        time.sleep(COUNTER_SAMPLE_INTERVAL_S)
        second_sample = support.wdg.status_get()
        second_time = time.monotonic()
        first_irq = support.wdg.irq_snapshot_get()

        # 禁用：确认硬件使能状态清零，并保存禁用后的计数现场。
        support.wdg.disable()
        disabled = support.wdg.status_get()

        # 第二组配置：重新使能后立即读取实际计数，证明Reload尺度已改变。
        support.wdg.configure(config_second)
        support.wdg.enable()
        second_reload_sample = support.wdg.status_get()
        support.wdg.disable()
        final_irq = support.wdg.irq_snapshot_get()

        # 证据：分别记录使能状态、实际Counter序列和Raw事件硬件端点。
        record_property("expected_counter_direction", "decreasing")
        record_property("sample_interval_s", second_time - first_time)
        record_observation(
            record_property,
            key="enabled_counter_samples",
            value=[first_sample.counter, second_sample.counter],
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="disabled_state",
            value=disabled.enabled,
            source="dut",
            endpoint="STATE.ENABLED",
        )
        record_observation(
            record_property,
            key="irq_raw",
            value=int(final_irq.raw),
            source="dut",
            endpoint="IRQ_RAW.WDG",
        )

        # 附件：在决定性断言前保存两组配置和实际硬件快照。
        write_json_result(
            et_artifact_dir / "wdg_p0_002_enable_disable_and_counter.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p0_002",
                "reload_counts": [config_first.reload_count, config_second.reload_count],
                "counter_samples": {
                    "before_enable": before_enable.counter,
                    "first": first_sample.counter,
                    "second": second_sample.counter,
                    "second_reload": second_reload_sample.counter,
                },
                "enabled_states": {
                    "before": before_enable.enabled,
                    "running": first_sample.enabled,
                    "disabled": disabled.enabled,
                },
                "irq_raw": {"first": int(first_irq.raw), "final": int(final_irq.raw)},
            },
        )

        # 断言：使用实际硬件状态证明计数、禁用和两组Reload均生效。
        assert before_enable.enabled is False
        assert first_sample.enabled is True
        assert second_sample.counter < first_sample.counter
        assert disabled.enabled is False
        assert second_reload_sample.counter > first_sample.counter
        assert first_irq.raw & WdgIrqEvent.TIMEOUT == WdgIrqEvent.NONE
        assert final_irq.raw & WdgIrqEvent.TIMEOUT == WdgIrqEvent.NONE
    finally:
        # 清理：无论Case结果如何，均关闭复位输出路径并禁用当前WDG。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.irq_clear()


# 测试 Feature：
# WDG独立模式喂狗、Counter重载与原超时边界延后。
#
# 测试方法：
# 1. 配置复位输出关闭、IRQ使能的独立模式并启动计数。
# 2. 等待Counter进入中段区间，保存feed前实际值并执行一次不可重试FEED。
# 3. 立即读取feed后Counter，确认重新靠近Reload尺度且高于feed前剩余值。
# 4. 继续等待新Reload边界产生自然IRQ，证明喂狗没有停止WDG。
#
# 通过条件：
# 1. FEED后COUNTER.CURRENT显著回升且自然IRQ未在原剩余边界前错误出现。
# 2. 新边界最终产生真实ISR交付和Raw/Last Raw证据。
def test_wdg_p0_003_independent_feed_reload(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用足以完成协议往返的安全Reload，并关闭系统复位输出。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.FEED | WdgFeature.INTERRUPTS)
    config = WdgConfig(reload_count=SAFE_RELOAD_COUNT)
    event = WdgIrqEvent.TIMEOUT

    try:
        # 配置：清理旧事件后建立自然timeout IRQ会话。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.configure(config)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)

        support.wdg.irq_unmask(event)
        support.wdg.irq_enable(event)
        baseline = support.wdg.irq_snapshot_get()
        support.wdg.enable()

        # 激励：等待Counter进入中段，执行一次FEED并立即读取重载后值。
        before_feed = support.wdg.wait_counter_between(
            config.reload_count // 4,
            config.reload_count // 2,
        )
        support.wdg.feed()
        after_feed = support.wdg.status_get()
        after_feed_irq = support.wdg.irq_snapshot_get()

        # 观测：等待新完整周期产生真实ISR，并读取持久中断记录。
        delivered = support.wdg.wait_irq(
            minimum_event_count=baseline.event_count + 1,
            timeout_s=2.0,
        )
        records = support.wdg.record_get()

        # 证据：分开记录Counter、IRQ硬件端点和Service投递计数。
        record_property("expected_reload_count", config.reload_count)
        record_property("event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="counter_before_feed",
            value=before_feed.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="counter_after_feed",
            value=after_feed.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="interrupt_record",
            value=records.interrupt,
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )

        # 附件：保存喂狗前后Counter和自然IRQ完整时间线。
        write_json_result(
            et_artifact_dir / "wdg_p0_003_independent_feed_reload.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p0_003",
                "counter": {"before_feed": before_feed.counter, "after_feed": after_feed.counter},
                "irq": {
                    "before": baseline.event_count,
                    "after_feed": after_feed_irq.event_count,
                    "delivered": delivered.event_count,
                    "last_raw": int(delivered.last_raw),
                },
                "record_interrupt": records.interrupt,
            },
        )

        # 断言：feed产生真实重载，原边界前无事件，新边界产生一次自然投递。
        assert after_feed.counter > before_feed.counter
        assert after_feed.counter > config.reload_count // 2
        assert after_feed_irq.event_count == baseline.event_count
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_raw & event == event
        assert records.interrupt is True
    finally:
        # 清理：先关闭Source和计数，再清Raw及持久记录，避免影响下一Case。
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)


# 测试 Feature：
# WDG真实系统复位输出、复位记录和跨Session恢复。
#
# 测试方法：
# 1. 在目标和对照实例上清除历史记录，目标实例配置reset_enable并启动安全短Reload。
# 2. Arm响应返回后停止全部WDG业务命令，由公共生命周期Fixture观察真实断线并重建HELLO/Discover。
# 3. 在新Session读取目标和对照实例的RECORD.RESET，清除目标记录后再次读取。
#
# 通过条件：
# 1. 旧Session确实断线，且新Session身份变化并完成HELLO/Discover。
# 2. 只有触发目标实例的RECORD.RESET置位，目标记录可精确清除且对照记录保持不变。
def test_wdg_p0_004_reset_reconnect_and_record(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_ids: tuple[int, ...],
    target_lifecycle,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：需要目标/对照两个实例，避免把复位归属证明退化为单实例自证。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    for reset_instance_id in wdg_instance_ids[:2]:
        crg_driver.reset(CrgPeripheral.WDG, instance=reset_instance_id)
    resource_driver.reset()

    if len(wdg_instance_ids) < 2:
        pytest.skip("skip_by_runtime_service: reset record isolation requires two WDG instances")

    target = wdg_support_for(wdg_instance_ids[0])
    control = wdg_support_for(wdg_instance_ids[1])
    require_wdg_runtime_feature(
        target.runtime,
        WdgFeature.RESET_OUTPUT | WdgFeature.PERSISTENT_RECORDS,
    )
    require_wdg_runtime_feature(
        control.runtime,
        WdgFeature.PERSISTENT_RECORDS,
    )
    # 实测本FPGA：ROUND1_IRQ_ROUND2_RESET不产生复位（与厂商WDG_15一致，其复位输出关闭），
    # 因此系统复位判据使用同轮模式，使能后第一次自然到期即输出复位。
    config = WdgConfig(
        reload_count=SAFE_RELOAD_COUNT,
        work_mode=WdgWorkMode.SAME_ROUND_IRQ_RESET,
        reset_enable=True,
    )
    reset_observed = False
    reconnected_target = None
    reconnected_control = None

    try:
        # 基线：关闭两个实例并清除两类记录，防止历史复位污染本轮证据。
        target.wdg.unlock()
        control.wdg.unlock()
        target.wdg.disable()
        control.wdg.disable()
        target.wdg.record_clear(WdgRecord.ALL)
        control.wdg.record_clear(WdgRecord.ALL)
        target_before = target.wdg.record_get()
        control_before = control.wdg.record_get()

        # 激励：配置并启动目标WDG，Arm响应成功后不再发送任何WDG业务命令。
        # 轮次模式的第一轮依赖中断事件推进；中断未使能时到不了复位输出，因此必须先放行IRQ源。
        target.wdg.irq_clear(WdgIrqEvent.TIMEOUT)
        target.wdg.irq_unmask(WdgIrqEvent.TIMEOUT)
        target.wdg.irq_enable(WdgIrqEvent.TIMEOUT)
        target.wdg.configure(config)
        target.wdg.enable()
        transition = target_lifecycle.wait_for_reset_and_reconnect(
            timeout_s=RESET_RECONNECT_TIMEOUT_S,
        )
        reset_observed = True

        # 观测：用新Session构造新的Driver，读取目标/对照复位记录。
        reconnected_target = wdg_support_for(wdg_instance_ids[0])
        reconnected_control = wdg_support_for(wdg_instance_ids[1])
        target_after = reconnected_target.wdg.record_get()
        control_after = reconnected_control.wdg.record_get()
        reconnected_target.wdg.record_clear(WdgRecord.RESET)
        target_cleared = reconnected_target.wdg.record_get()
        control_after_clear = reconnected_control.wdg.record_get()

        # 证据：在决定性断言前保存Session时间线与两实例记录的真实读回。
        record_property("old_session_id", transition.old_session_id)
        record_property("new_session_id", transition.new_session_id)
        record_property("disconnect_elapsed_s", transition.disconnect_elapsed_s)
        record_property("reconnect_elapsed_s", transition.reconnect_elapsed_s)
        record_observation(
            record_property,
            key="target_reset_record_before",
            value=target_before.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="control_reset_record_before",
            value=control_before.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="target_reset_record_after",
            value=target_after.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="control_reset_record_after",
            value=control_after.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="target_reset_record_after_clear",
            value=target_cleared.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="control_reset_record_after_clear",
            value=control_after_clear.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_property(
            "expected_reset_chain",
            {
                "disconnect_observed": True,
                "new_session": transition.new_session_id != transition.old_session_id,
                "target_reset": True,
                "control_reset": False,
            },
        )
        record_property(
            "actual_reset_record",
            {
                "before": {"target": target_before.reset, "control": control_before.reset},
                "after": {"target": target_after.reset, "control": control_after.reset},
                "after_clear": {
                    "target": target_cleared.reset,
                    "control": control_after_clear.reset,
                },
            },
        )
        write_json_result(
            et_artifact_dir / "wdg_p0_004_reset_reconnect_and_record.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p0_004",
                "session": {
                    "old": transition.old_session_id,
                    "new": transition.new_session_id,
                    "disconnect_elapsed_s": transition.disconnect_elapsed_s,
                    "reconnect_elapsed_s": transition.reconnect_elapsed_s,
                },
                "reset_record": {
                    "before": {"target": target_before.reset, "control": control_before.reset},
                    "after": {"target": target_after.reset, "control": control_after.reset},
                    "after_clear": {
                        "target": target_cleared.reset,
                        "control": control_after_clear.reset,
                    },
                },
            },
        )

        # 断言：真实断线和新Session完成后，复位记录归属于触发实例且可精确清除。
        assert transition.old_session_id != transition.new_session_id
        assert target_before.reset is False
        assert control_before.reset is False
        assert target_after.reset is True
        assert control_after.reset is False
        assert target_cleared.reset is False
        assert control_after_clear.reset is False
    finally:
        # 清理：复位成功后只使用新Session清理；未复位时使用原Session收尾。
        cleanup_target = reconnected_target if reset_observed else target
        cleanup_control = reconnected_control if reset_observed else control
        if cleanup_target is not None:
            cleanup_target.wdg.disable()
            cleanup_target.wdg.record_clear(WdgRecord.ALL)
        if cleanup_control is not None:
            cleanup_control.wdg.disable()
            cleanup_control.wdg.record_clear(WdgRecord.ALL)
