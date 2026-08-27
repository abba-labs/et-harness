# WDG P1 Formal Case。
#
# 职责：验证 WDG 超时IRQ、模块复位、锁保护、记录和多实例隔离。
# 边界：系统复位、NMI和调试器Halt留给更高等级Case；本文件不包含芯片事实。
# 依赖：WDG Driver、公共清理/证据工具和pytest。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.wdg import (
    WdgConfig,
    WdgFeature,
    WdgIrqEvent,
    WdgMode,
    WdgRecord,
    WdgWorkMode,
)
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import WdgSupportFactory, require_wdg_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("wdg")]

SAFE_RELOAD_COUNT = 5_000_000
ALTERNATE_RELOAD_COUNT = 7_000_000
IRQ_TIMEOUT_S = 2.0
WINDOW_RELOAD_COUNT = 5_000_000
WINDOW_EARLY_LOW_COUNT = 1_000_000
WINDOW_EARLY_HIGH_COUNT = 4_000_000
WINDOW_INSIDE_LOW_COUNT = 2_000_000
WINDOW_INSIDE_HIGH_COUNT = 4_000_000
WINDOW_INSIDE_SAMPLE_LOW_COUNT = 3_000_000
WINDOW_INSIDE_SAMPLE_HIGH_COUNT = 3_500_000
WINDOW_LATE_LOW_COUNT = WINDOW_RELOAD_COUNT - 1_000
WINDOW_LATE_HIGH_COUNT = WINDOW_RELOAD_COUNT - 500
WINDOW_POSITION_TIMEOUT_S = 6.0
WORK_MODE_RESET_TIMEOUT_S = 30.0


# 测试 Feature：
# WDG自然超时、IRQ Source和CPU中断投递。
#
# 测试方法：
# 1. 关闭复位输出，清除历史Raw并使能TIMEOUT IRQ。
# 2. 启动WDG并等待一个自然超时周期，不使用软件Force代替自然事件。
# 3. 读取ISR事件计数、Last Raw与中断记录。
#
# 通过条件：
# 1. Event Count恰好增加一次，Last Raw包含TIMEOUT。
# 2. 持久中断记录置位，系统仍可继续响应协议命令。
def test_wdg_p1_001_natural_timeout_irq(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择安全Reload，明确关闭系统复位输出。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.INTERRUPTS)
    event = WdgIrqEvent.TIMEOUT
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("WDG disable", support.wdg.disable),
            ("WDG IRQ disable", lambda: support.wdg.irq_disable(event)),
            ("WDG IRQ clear", lambda: support.wdg.irq_clear(event)),
            ("WDG interrupt record clear", lambda: support.wdg.record_clear(WdgRecord.INTERRUPT)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立没有历史Pending和持久记录的IRQ会话。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.configure(WdgConfig(reload_count=SAFE_RELOAD_COUNT, reset_enable=False))
        configured = True
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        support.wdg.irq_unmask(event)
        support.wdg.irq_enable(event)
        baseline = support.wdg.irq_snapshot_get()

        # 激励：启动计数并等待一次真实自然超时投递。
        support.wdg.enable()
        delivered = support.wdg.wait_irq(
            minimum_event_count=baseline.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        records = support.wdg.record_get()

        # 证据：分别记录Service投递和持久硬件记录。
        record_property("event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="irq_last_raw",
            value=int(delivered.last_raw),
            source="dut",
            endpoint="IRQ_DELIVERY.LAST_RAW",
        )
        record_observation(
            record_property,
            key="interrupt_record",
            value=records.interrupt,
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )

        # 附件：断言前保存自然事件的完整可回放事实。
        write_json_result(
            et_artifact_dir / "wdg_p1_001_natural_timeout_irq.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_001",
                "event_count": {"before": baseline.event_count, "after": delivered.event_count},
                "irq": {"last_raw": int(delivered.last_raw), "latched": int(delivered.latched)},
                "interrupt_record": records.interrupt,
            },
        )

        # 断言：自然超时形成一次真实投递和持久记录。
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_raw & event == event
        assert records.interrupt is True


# 测试 Feature：
# WDG窗口模式、窗口门限以及窗口内外喂狗行为。
#
# 测试方法：
# 1. 主实例依次执行Inside和Early，第二实例独立执行Late，隔离违规状态。
# 2. 每个区域都重新装载Reload、配置门限并清理IRQ会话。
# 3. Inside执行合法Feed；Early Feed和Late越过Low分别观测真实IRQ。
#
# 通过条件：
# 1. Early Feed和Late越过Low均至少形成一次真实IRQ投递。
# 2. 窗口内部合法喂狗使Counter回到Reload尺度，且Event Count保持不变。
# 3. Late越过Low后形成真实IRQ；Feed后Counter只作为硬件观测，不虚构跨芯片语义。
def test_wdg_p1_002_window_feed_regions(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：至少两个实例才能把Late违规状态与Inside/Early刺激完全隔离。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    for reset_instance_id in wdg_instance_ids[:2]:
        crg_driver.reset(CrgPeripheral.WDG, instance=reset_instance_id)
    resource_driver.reset()

    if len(wdg_instance_ids) < 2:
        pytest.skip("skip_by_execution_mapping: WDG window matrix requires two instances")

    primary_support = wdg_support_for(wdg_instance_ids[0])
    late_support = wdg_support_for(wdg_instance_ids[1])
    required_features = WdgFeature.FEED | WdgFeature.WINDOW | WdgFeature.INTERRUPTS
    require_wdg_runtime_feature(
        primary_support.runtime,
        required_features,
    )
    require_wdg_runtime_feature(late_support.runtime, required_features)
    event = WdgIrqEvent.TIMEOUT
    prime_config = WdgConfig(reload_count=WINDOW_RELOAD_COUNT, reset_enable=False)
    inside_config = WdgConfig(
        reload_count=WINDOW_RELOAD_COUNT,
        window_low_count=WINDOW_INSIDE_LOW_COUNT,
        window_high_count=WINDOW_INSIDE_HIGH_COUNT,
        mode=WdgMode.WINDOW,
        work_mode=WdgWorkMode.SAME_ROUND_IRQ_RESET,
        reset_enable=False,
    )
    early_config = WdgConfig(
        reload_count=WINDOW_RELOAD_COUNT,
        window_low_count=WINDOW_EARLY_LOW_COUNT,
        window_high_count=WINDOW_EARLY_HIGH_COUNT,
        mode=WdgMode.WINDOW,
        work_mode=WdgWorkMode.SAME_ROUND_IRQ_RESET,
        reset_enable=False,
    )
    late_config = WdgConfig(
        reload_count=WINDOW_RELOAD_COUNT,
        window_low_count=WINDOW_LATE_LOW_COUNT,
        window_high_count=WINDOW_LATE_HIGH_COUNT,
        mode=WdgMode.WINDOW,
        work_mode=WdgWorkMode.SAME_ROUND_IRQ_RESET,
        reset_enable=False,
    )

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("WDG primary disable", primary_support.wdg.disable),
            ("WDG primary IRQ disable", lambda: primary_support.wdg.irq_disable(event)),
            ("WDG primary IRQ clear", lambda: primary_support.wdg.irq_clear(event)),
            (
                "WDG primary interrupt record clear",
                lambda: primary_support.wdg.record_clear(WdgRecord.INTERRUPT),
            ),
            ("WDG late disable", late_support.wdg.disable),
            ("WDG late IRQ disable", lambda: late_support.wdg.irq_disable(event)),
            ("WDG late IRQ clear", lambda: late_support.wdg.irq_clear(event)),
            (
                "WDG late interrupt record clear",
                lambda: late_support.wdg.record_clear(WdgRecord.INTERRUPT),
            ),
        )

    with case_cleanup_scope(cleanup_actions):
        # Inside准备：主实例在独立模式装载Reload，再切换到可稳定定位的中段窗口。
        primary_support.wdg.disable()
        primary_support.wdg.unlock()
        primary_support.wdg.configure(prime_config)
        primary_support.wdg.enable()
        primary_support.wdg.feed()
        primary_support.wdg.disable()
        primary_support.wdg.unlock()
        primary_support.wdg.configure(inside_config)
        primary_support.wdg.irq_clear(event)
        primary_support.wdg.record_clear(WdgRecord.INTERRUPT)
        primary_support.wdg.irq_unmask(event)
        primary_support.wdg.irq_enable(event)

        # Inside激励：先定位到门限中段，再Feed以区分真实重载与自然递减。
        primary_support.wdg.enable()
        inside_before = primary_support.wdg.wait_counter_between(
            WINDOW_INSIDE_SAMPLE_LOW_COUNT,
            WINDOW_INSIDE_SAMPLE_HIGH_COUNT,
            timeout_s=WINDOW_POSITION_TIMEOUT_S,
        )
        inside_baseline = primary_support.wdg.irq_snapshot_get()
        assert inside_baseline.raw & event == WdgIrqEvent.NONE
        primary_support.wdg.feed()
        inside_after = primary_support.wdg.status_get()
        inside_irq = primary_support.wdg.irq_snapshot_get()

        # Early准备：主实例仍处于干净状态，重新装载后使Counter初始高于High。
        primary_support.wdg.disable()
        primary_support.wdg.irq_disable(event)
        primary_support.wdg.irq_clear(event)
        primary_support.wdg.unlock()
        primary_support.wdg.configure(prime_config)
        primary_support.wdg.enable()
        primary_support.wdg.feed()
        primary_support.wdg.disable()
        primary_support.wdg.unlock()
        primary_support.wdg.configure(early_config)
        primary_support.wdg.record_clear(WdgRecord.INTERRUPT)
        primary_support.wdg.irq_unmask(event)
        primary_support.wdg.irq_enable(event)

        # Early激励：刚装载的Counter高于High，立即Feed应产生真实违规IRQ。
        primary_support.wdg.enable()
        early_before = primary_support.wdg.status_get()
        early_baseline = primary_support.wdg.irq_snapshot_get()
        assert early_baseline.raw & event == WdgIrqEvent.NONE
        primary_support.wdg.feed()
        early_after = primary_support.wdg.status_get()
        early_irq = primary_support.wdg.wait_irq(
            minimum_event_count=early_baseline.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # Late准备：使用第二实例，避免继承主实例已经形成的Early违规状态。
        late_support.wdg.disable()
        late_support.wdg.unlock()
        late_support.wdg.configure(prime_config)
        late_support.wdg.enable()
        late_support.wdg.feed()
        late_support.wdg.disable()
        late_support.wdg.unlock()
        late_support.wdg.configure(late_config)
        late_support.wdg.irq_clear(event)
        late_support.wdg.record_clear(WdgRecord.INTERRUPT)
        late_support.wdg.irq_unmask(event)
        late_support.wdg.irq_enable(event)

        # Late基线：在计数启动前确认本阶段没有历史IRQ投递。
        late_baseline = late_support.wdg.irq_snapshot_get()
        assert late_baseline.raw & event == WdgIrqEvent.NONE

        # Late区域：Counter越过Low就形成窗口超时IRQ，不把该事件错归因于后续Feed。
        late_support.wdg.enable()
        late_before = late_support.wdg.wait_counter_between(
            1,
            WINDOW_LATE_LOW_COUNT - 1,
            timeout_s=WINDOW_POSITION_TIMEOUT_S,
        )
        late_irq = late_support.wdg.wait_irq(
            minimum_event_count=late_baseline.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # Late Feed：保存越过Low后的真实Feed行为，不预设芯片未声明的重载语义。
        late_support.wdg.feed()
        late_after = late_support.wdg.status_get()

        # 阶段收口：违规源可能保持为Level，保存快照后立即停止计数与IRQ风暴。
        primary_support.wdg.disable()
        primary_support.wdg.irq_disable(event)
        primary_support.wdg.irq_clear(event)
        late_support.wdg.disable()
        late_support.wdg.irq_disable(event)
        late_support.wdg.irq_clear(event)

        # 证据：每个Counter样本单独绑定真实硬件端点，不把多个读数伪装成一个Observation。
        record_observation(
            record_property,
            key="early_counter_before",
            value=early_before.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="early_counter_after",
            value=early_after.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="inside_counter_before",
            value=inside_before.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="inside_counter_after",
            value=inside_after.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="late_counter_before",
            value=late_before.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="late_counter_after",
            value=late_after.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_property(
            "irq_event_deltas",
            [
                early_irq.event_count - early_baseline.event_count,
                inside_irq.event_count - inside_baseline.event_count,
                late_irq.event_count - late_baseline.event_count,
            ],
        )

        # 附件：断言前保存三组窗口门限、Feed位置、重载结果和IRQ事实。
        write_json_result(
            et_artifact_dir / "wdg_p1_002_window_feed_regions.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_002",
                "windows": {
                    "early": {
                        "low": WINDOW_EARLY_LOW_COUNT,
                        "high": WINDOW_EARLY_HIGH_COUNT,
                    },
                    "inside": {
                        "low": WINDOW_INSIDE_LOW_COUNT,
                        "high": WINDOW_INSIDE_HIGH_COUNT,
                    },
                    "late": {
                        "low": WINDOW_LATE_LOW_COUNT,
                        "high": WINDOW_LATE_HIGH_COUNT,
                    },
                },
                "counter_before_feed": {
                    "early": early_before.counter,
                    "inside": inside_before.counter,
                    "late": late_before.counter,
                },
                "counter_after_feed": {
                    "early": early_after.counter,
                    "inside": inside_after.counter,
                    "late": late_after.counter,
                },
                "event_count_delta": {
                    "early": early_irq.event_count - early_baseline.event_count,
                    "inside": inside_irq.event_count - inside_baseline.event_count,
                    "late": late_irq.event_count - late_baseline.event_count,
                },
            },
        )

        # 断言：三次激励的实际Counter确实位于各自窗口区域。
        assert early_before.counter > early_config.window_high_count
        assert (
            inside_config.window_low_count
            <= inside_before.counter
            <= inside_config.window_high_count
        )
        assert late_before.counter < late_config.window_low_count

        # 断言：Inside合法Feed必须重载；Late Feed后的Counter保留为硬件观测。
        assert inside_after.counter > inside_before.counter

        # 断言：Early Feed和Late越过Low均产生真实事件；Level源允许重复投递。
        assert early_irq.event_count > early_baseline.event_count
        assert early_irq.last_raw & event == event
        assert inside_irq.event_count == inside_baseline.event_count
        assert inside_irq.raw & event == WdgIrqEvent.NONE
        assert late_irq.event_count > late_baseline.event_count
        assert late_irq.last_raw & event == event


# 测试 Feature：
# WDG模块复位与复位后的可重新配置能力。
#
# 测试方法：
# 1. 写入非默认Reload并启动WDG，读取复位前状态。
# 2. 关闭复位输出后执行模块级复位，不触发系统复位。
# 3. 重新解锁、配置另一组Reload并启动，读取恢复后的状态。
#
# 通过条件：
# 1. 模块复位后WDG为禁用状态。
# 2. 复位后可以接受新配置并恢复计数。
def test_wdg_p1_004_module_reset_and_recovery(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只使用Runtime明确发布的模块复位能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.MODULE_RESET)
    active = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not active:
            return ()
        return (("WDG disable", support.wdg.disable),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：先建立一份明确的非默认工作状态。
        support.wdg.unlock()
        support.wdg.configure(WdgConfig(reload_count=SAFE_RELOAD_COUNT, reset_enable=False))
        support.wdg.enable()
        active = True
        before_reset = support.wdg.status_get()

        # 激励：执行当前实例的模块复位并读取复位后状态。
        support.wdg.module_reset()
        after_reset = support.wdg.status_get()

        # 恢复：重新解锁、写入第二组配置并启动计数。
        support.wdg.unlock()
        support.wdg.configure(WdgConfig(reload_count=ALTERNATE_RELOAD_COUNT, reset_enable=False))
        support.wdg.enable()
        recovered = support.wdg.status_get()

        # 证据：记录复位前、复位后和重新运行三个硬件阶段。
        record_observation(
            record_property,
            key="enabled_states",
            value=[before_reset.enabled, after_reset.enabled, recovered.enabled],
            source="dut",
            endpoint="STATE.ENABLED",
        )
        record_observation(
            record_property,
            key="recovered_counter",
            value=recovered.counter,
            source="dut",
            endpoint="COUNTER.CURRENT",
        )

        # 附件：保存模块复位与恢复全过程。
        write_json_result(
            et_artifact_dir / "wdg_p1_004_module_reset_and_recovery.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_004",
                "enabled": {
                    "before_reset": before_reset.enabled,
                    "after_reset": after_reset.enabled,
                    "recovered": recovered.enabled,
                },
                "counter": {"before_reset": before_reset.counter, "recovered": recovered.counter},
            },
        )

        # 断言：模块复位只清当前模块，并允许后续重新工作。
        assert before_reset.enabled is True
        assert after_reset.enabled is False
        assert recovered.enabled is True
        assert recovered.counter > 0


# 测试 Feature：
# WDG配置锁保护、解锁恢复与硬件配置读回。
#
# 测试方法：
# 1. 解锁后写入第一组配置并读回。
# 2. 锁定配置寄存器后尝试写入第二组配置，再次读取硬件配置。
# 3. 重新解锁并写入第二组配置，读取最终配置。
#
# 通过条件：
# 1. 锁定期间硬件配置保持第一组值。
# 2. 解锁后第二组配置能够完整生效。
def test_wdg_p1_005_lock_unlock_and_readback(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用两份可区分且不触发系统复位的配置。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.LOCK | WdgFeature.CONFIG_READBACK)
    first = WdgConfig(reload_count=SAFE_RELOAD_COUNT, reset_enable=False)
    second = WdgConfig(reload_count=ALTERNATE_RELOAD_COUNT, reset_enable=False)

    try:
        # 第一阶段：解锁并写入第一组配置，确认基线读回。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.configure(first)
        first_readback = support.wdg.config_get()

        # 第二阶段：锁定后尝试更新，读取实际硬件而不是信任命令返回。
        support.wdg.lock()
        support.wdg.configure(second)
        locked_readback = support.wdg.config_get()

        # 第三阶段：重新解锁并更新，确认保护可恢复。
        support.wdg.unlock()
        support.wdg.configure(second)
        unlocked_readback = support.wdg.config_get()

        # 证据：公开三次硬件读回中的Reload字段。
        record_observation(
            record_property,
            key="reload_readbacks",
            value=[
                first_readback.reload_count,
                locked_readback.reload_count,
                unlocked_readback.reload_count,
            ],
            source="dut",
            endpoint="CONFIG.RELOAD",
        )

        # 附件：保存锁前、锁定期间和解锁后的实际配置。
        write_json_result(
            et_artifact_dir / "wdg_p1_005_lock_unlock_and_readback.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_005",
                "reload_readback": {
                    "initial": first_readback.reload_count,
                    "locked": locked_readback.reload_count,
                    "unlocked": unlocked_readback.reload_count,
                },
            },
        )

        # 断言：锁定阻止更新，重新解锁后允许更新。
        assert first_readback.reload_count == first.reload_count
        assert locked_readback.reload_count == first.reload_count
        assert unlocked_readback.reload_count == second.reload_count
    finally:
        # 清理：保持WDG处于解锁且禁用状态，避免锁状态泄漏到下一Case。
        support.wdg.unlock()
        support.wdg.disable()


# 测试 Feature：
# WDG IRQ Enable、Mask、Force、Unmask、Disable与精确Clear。
#
# 测试方法：
# 1. Enable后保持Mask并Force TIMEOUT，读取Raw、Status和ISR计数。
# 2. Clear后解除Mask并再次Force，读取有效Status与ISR投递。
# 3. Disable Source后再次Force，确认Raw可见但不再产生ISR投递。
#
# 通过条件：
# 1. Mask阶段Raw置位而Status和Event Count不增加。
# 2. Unmask阶段Event Count增加一次；Disable阶段不再增加。
def test_wdg_p1_006_irq_control_matrix(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用唯一发布的TIMEOUT Source并建立可清理IRQ会话。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.INTERRUPTS)
    event = WdgIrqEvent.TIMEOUT
    irq_bound = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not irq_bound:
            return ()
        return (
            ("WDG IRQ disable", lambda: support.wdg.irq_disable(event)),
            ("WDG IRQ clear", lambda: support.wdg.irq_clear(event)),
            ("WDG IRQ unmask", lambda: support.wdg.irq_unmask(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：清理Pending并使能Source，随后保持Mask。
        support.wdg.irq_clear(event)
        support.wdg.irq_enable(event)
        irq_bound = True
        support.wdg.irq_mask(event)
        baseline = support.wdg.irq_snapshot_get()

        # Mask刺激：Force后Raw应可见，但有效Status和ISR计数不变。
        support.wdg.irq_force(event)
        masked = support.wdg.irq_snapshot_get()

        # Unmask刺激：清除旧事件后解除Mask，再次Force并等待真实投递。
        support.wdg.irq_clear(event)
        support.wdg.irq_unmask(event)
        before_delivery = support.wdg.irq_snapshot_get()
        support.wdg.irq_force(event)
        delivered = support.wdg.wait_irq(
            minimum_event_count=before_delivery.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )

        # Disable刺激：关闭Source后Force，确认不再产生新投递。
        support.wdg.irq_clear(event)
        support.wdg.irq_disable(event)
        disabled_before = support.wdg.irq_snapshot_get()
        support.wdg.irq_force(event)
        disabled_after = support.wdg.irq_snapshot_get()

        # 证据：记录三个控制阶段的Raw、Status与Event Count。
        record_observation(
            record_property,
            key="masked_raw",
            value=int(masked.raw),
            source="dut",
            endpoint="IRQ_RAW.TIMEOUT",
        )
        record_observation(
            record_property,
            key="masked_status",
            value=int(masked.status),
            source="dut",
            endpoint="IRQ_STATUS.TIMEOUT",
        )
        record_property("delivery_count_delta", delivered.event_count - before_delivery.event_count)
        record_property(
            "disabled_count_delta",
            disabled_after.event_count - disabled_before.event_count,
        )

        # 附件：断言前保存Mask、Unmask和Disable全部硬件阶段。
        write_json_result(
            et_artifact_dir / "wdg_p1_006_irq_control_matrix.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_006",
                "masked": {
                    "raw": int(masked.raw),
                    "status": int(masked.status),
                    "event_count": masked.event_count,
                },
                "delivered": {
                    "last_raw": int(delivered.last_raw),
                    "event_count": delivered.event_count,
                },
                "disabled": {
                    "raw": int(disabled_after.raw),
                    "status": int(disabled_after.status),
                    "event_count": disabled_after.event_count,
                },
            },
        )

        # 断言：三个阶段分别满足Raw、有效Status和CPU投递语义。
        assert masked.raw & event == event
        assert masked.status & event == WdgIrqEvent.NONE
        assert masked.event_count == baseline.event_count
        assert delivered.event_count == before_delivery.event_count + 1
        assert delivered.last_raw & event == event
        assert disabled_after.status & event == WdgIrqEvent.NONE
        assert disabled_after.event_count == disabled_before.event_count


# 测试 Feature：
# WDG自然中断记录的置位、保持与精确清除。
#
# 测试方法：
# 1. 清除中断记录并验证基线为False。
# 2. 关闭复位输出后运行到一次自然TIMEOUT并读取记录。
# 3. 清除中断记录并再次读取，不清除Reset记录。
#
# 通过条件：
# 1. 自然TIMEOUT后中断记录置位。
# 2. 精确清除后中断记录恢复False。
def test_wdg_p1_007_interrupt_record_set_and_clear(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求中断和持久记录两项能力同时存在。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(
        support.runtime,
        WdgFeature.INTERRUPTS | WdgFeature.PERSISTENT_RECORDS,
    )
    event = WdgIrqEvent.TIMEOUT
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("WDG disable", support.wdg.disable),
            ("WDG IRQ disable", lambda: support.wdg.irq_disable(event)),
            ("WDG IRQ clear", lambda: support.wdg.irq_clear(event)),
            ("WDG interrupt record clear", lambda: support.wdg.record_clear(WdgRecord.INTERRUPT)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立清洁记录和自然IRQ会话。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.configure(WdgConfig(reload_count=SAFE_RELOAD_COUNT, reset_enable=False))
        configured = True
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        support.wdg.irq_clear(event)
        support.wdg.irq_unmask(event)
        support.wdg.irq_enable(event)
        baseline_irq = support.wdg.irq_snapshot_get()
        before = support.wdg.record_get()

        # 激励：等待一次自然超时，随后读取持久记录。
        support.wdg.enable()
        support.wdg.wait_irq(
            minimum_event_count=baseline_irq.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        after_event = support.wdg.record_get()

        # 恢复：精确清除Interrupt记录并读取最终状态。
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        after_clear = support.wdg.record_get()

        # 证据：记录真实持久位的完整变化序列。
        record_observation(
            record_property,
            key="interrupt_record_sequence",
            value=[before.interrupt, after_event.interrupt, after_clear.interrupt],
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )

        # 附件：保存事件前、事件后和清除后三个硬件快照。
        write_json_result(
            et_artifact_dir / "wdg_p1_007_interrupt_record_set_and_clear.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_007",
                "interrupt_record": {
                    "before": before.interrupt,
                    "after_event": after_event.interrupt,
                    "after_clear": after_clear.interrupt,
                },
            },
        )

        # 断言：记录只由真实自然事件置位，并可被精确清除。
        assert before.interrupt is False
        assert after_event.interrupt is True
        assert after_clear.interrupt is False


# 测试 Feature：
# 多WDG实例的配置、计数与IRQ状态隔离。
#
# 测试方法：
# 1. 要求至少两个Runtime实例，并分别写入不同Reload。
# 2. 仅使能第一个实例并采样两个实例的计数和使能状态。
# 3. 对第一个实例Force IRQ，读取两个实例各自的快照。
#
# 通过条件：
# 1. 两个实例配置读回互不覆盖，只有第一个实例处于运行状态。
# 2. 第一个实例的IRQ投递不改变第二个实例的Event Count与Raw。
def test_wdg_p1_008_multi_instance_isolation(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：多实例Feature必须使用两个不同的Runtime实例，不能重复同一实例。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    for reset_instance_id in wdg_instance_ids[:2]:
        crg_driver.reset(CrgPeripheral.WDG, instance=reset_instance_id)
    resource_driver.reset()

    if len(wdg_instance_ids) < 2:
        pytest.skip("skip_by_runtime_service: multi-instance WDG case requires two instances")
    primary = wdg_support_for(wdg_instance_ids[0])
    secondary = wdg_support_for(wdg_instance_ids[1])
    event = WdgIrqEvent.TIMEOUT
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("primary WDG disable", primary.wdg.disable),
            ("secondary WDG disable", secondary.wdg.disable),
            ("primary WDG IRQ disable", lambda: primary.wdg.irq_disable(event)),
            ("primary WDG IRQ clear", lambda: primary.wdg.irq_clear(event)),
            ("secondary WDG IRQ clear", lambda: secondary.wdg.irq_clear(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：两个实例使用不同Reload且都关闭系统复位输出。
        primary.wdg.unlock()
        secondary.wdg.unlock()
        primary.wdg.disable()
        secondary.wdg.disable()
        primary.wdg.configure(WdgConfig(reload_count=SAFE_RELOAD_COUNT, reset_enable=False))
        secondary.wdg.configure(WdgConfig(reload_count=ALTERNATE_RELOAD_COUNT, reset_enable=False))
        configured = True
        primary.wdg.irq_clear(event)
        secondary.wdg.irq_clear(event)
        primary.wdg.irq_unmask(event)
        primary.wdg.irq_enable(event)

        # 激励：仅启动Primary并只对Primary Force一个IRQ事件。
        primary_config = primary.wdg.config_get()
        secondary_config = secondary.wdg.config_get()
        secondary_before = secondary.wdg.irq_snapshot_get()
        primary.wdg.enable()
        primary_status = primary.wdg.status_get()
        secondary_status = secondary.wdg.status_get()
        primary_before = primary.wdg.irq_snapshot_get()
        primary.wdg.irq_force(event)
        primary_after = primary.wdg.wait_irq(
            minimum_event_count=primary_before.event_count + 1,
            timeout_s=IRQ_TIMEOUT_S,
        )
        secondary_after = secondary.wdg.irq_snapshot_get()

        # 证据：分别记录两个实例的配置、使能和IRQ端点。
        record_observation(
            record_property,
            key="primary_reload_count",
            value=primary_config.reload_count,
            source="dut",
            endpoint="CONFIG.RELOAD",
        )
        record_observation(
            record_property,
            key="secondary_reload_count",
            value=secondary_config.reload_count,
            source="dut",
            endpoint="CONFIG.RELOAD",
        )
        record_observation(
            record_property,
            key="primary_enabled_state",
            value=primary_status.enabled,
            source="dut",
            endpoint="STATE.ENABLED",
        )
        record_observation(
            record_property,
            key="secondary_enabled_state",
            value=secondary_status.enabled,
            source="dut",
            endpoint="STATE.ENABLED",
        )
        record_property(
            "secondary_event_count_delta",
            secondary_after.event_count - secondary_before.event_count,
        )

        # 附件：断言前保存两个实例的隔离证据。
        write_json_result(
            et_artifact_dir / "wdg_p1_008_multi_instance_isolation.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_008",
                "reload_counts": [primary_config.reload_count, secondary_config.reload_count],
                "enabled": [primary_status.enabled, secondary_status.enabled],
                "event_counts": {
                    "primary_before": primary_before.event_count,
                    "primary_after": primary_after.event_count,
                    "secondary_before": secondary_before.event_count,
                    "secondary_after": secondary_after.event_count,
                },
                "secondary_raw": int(secondary_after.raw),
            },
        )

        # 断言：配置、计数和IRQ投递均保持实例隔离。
        assert primary_config.reload_count != secondary_config.reload_count
        assert primary_status.enabled is True
        assert secondary_status.enabled is False
        assert primary_after.event_count == primary_before.event_count + 1
        assert secondary_after.event_count == secondary_before.event_count
        assert secondary_after.raw & event == WdgIrqEvent.NONE


# 测试 Feature：
# WDG两种IRQ/Reset轮次模式、真实IRQ投递和复位记录。
#
# 测试方法：
# 1. 配置ROUND1_IRQ_ROUND2_RESET，等待第一轮自然IRQ并确认系统仍在线。
# 2. 停止发送WDG命令，使用公共生命周期Fixture等待第二轮真实系统复位并重建Session。
# 3. 在新Session配置SAME_ROUND_IRQ_RESET，等待第一次自然事件复位，再读取两类持久记录。
#
# 通过条件：
# 1. ROUND1_IRQ_ROUND2_RESET的第一轮只有真实IRQ和中断记录，第二轮才形成系统复位。
# 2. SAME_ROUND_IRQ_RESET的同一轮复位后，IRQ与Reset记录均能读回并精确清除。
def test_wdg_p1_003_work_mode_irq_and_reset_rounds(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    target_lifecycle,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：要求工作模式、真实IRQ、复位输出和持久记录都由当前Runtime发布。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(
        support.runtime,
        WdgFeature.WORK_MODE
        | WdgFeature.INTERRUPTS
        | WdgFeature.RESET_OUTPUT
        | WdgFeature.PERSISTENT_RECORDS,
    )
    event = WdgIrqEvent.TIMEOUT
    reconnected_support = None
    cleanup_support = support

    try:
        # 第一轮基线：清除实时IRQ和持久记录，建立ROUND1_IRQ_ROUND2_RESET配置。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.ALL)
        first_config = WdgConfig(
            reload_count=SAFE_RELOAD_COUNT,
            work_mode=WdgWorkMode.ROUND1_IRQ_ROUND2_RESET,
            reset_enable=True,
        )
        support.wdg.configure(first_config)
        support.wdg.irq_unmask(event)
        support.wdg.irq_enable(event)
        first_baseline = support.wdg.irq_snapshot_get()
        support.wdg.enable()

        # 第一轮激励与观测：自然超时应只投递IRQ，系统保持在线并留下中断记录。
        first_irq = support.wdg.wait_irq(
            minimum_event_count=first_baseline.event_count + 1,
            timeout_s=WORK_MODE_RESET_TIMEOUT_S,
        )
        first_records = support.wdg.record_get()

        # 第二轮激励：第一轮响应后不再发送WDG命令，等待第二轮真实系统复位。
        transition_first = target_lifecycle.wait_for_reset_and_reconnect(
            timeout_s=WORK_MODE_RESET_TIMEOUT_S,
        )
        reconnected_support = wdg_support_for(wdg_instance_id)
        cleanup_support = reconnected_support
        second_round_records = reconnected_support.wdg.record_get()

        # 第二模式基线：在新Session清理全部记录，避免两种模式的证据互相污染。
        reconnected_support.wdg.unlock()
        reconnected_support.wdg.disable()
        reconnected_support.wdg.irq_disable(event)
        reconnected_support.wdg.irq_clear(event)
        reconnected_support.wdg.record_clear(WdgRecord.ALL)
        second_config = WdgConfig(
            reload_count=SAFE_RELOAD_COUNT,
            work_mode=WdgWorkMode.SAME_ROUND_IRQ_RESET,
            reset_enable=True,
        )
        reconnected_support.wdg.configure(second_config)
        reconnected_support.wdg.irq_unmask(event)
        reconnected_support.wdg.irq_enable(event)
        reconnected_support.wdg.enable()

        # 同轮模式激励：第一次自然事件即触发系统复位，不要求普通ISR先于复位完成。
        transition_second = target_lifecycle.wait_for_reset_and_reconnect(
            timeout_s=WORK_MODE_RESET_TIMEOUT_S,
        )
        final_support = wdg_support_for(wdg_instance_id)
        cleanup_support = final_support
        final_records = final_support.wdg.record_get()
        final_support.wdg.record_clear(WdgRecord.ALL)
        cleared_records = final_support.wdg.record_get()

        # 证据：在决定性断言前保存两种模式的实际事件、Session和记录时间线。
        record_property(
            "first_round_event_count_delta", first_irq.event_count - first_baseline.event_count
        )
        record_property("first_reset_session", transition_first.new_session_id)
        record_property("second_reset_session", transition_second.new_session_id)
        record_observation(
            record_property,
            key="round1_irq_last_raw",
            value=int(first_irq.last_raw),
            source="dut",
            endpoint="IRQ_DELIVERY.LAST_RAW",
        )
        record_observation(
            record_property,
            key="round1_interrupt_record",
            value=first_records.interrupt,
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )
        record_observation(
            record_property,
            key="round1_reset_record",
            value=first_records.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="round2_reset_record",
            value=second_round_records.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="same_round_interrupt_record",
            value=final_records.interrupt,
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )
        record_observation(
            record_property,
            key="same_round_reset_record",
            value=final_records.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_observation(
            record_property,
            key="cleared_interrupt_record",
            value=cleared_records.interrupt,
            source="dut",
            endpoint="RECORD.INTERRUPT",
        )
        record_observation(
            record_property,
            key="cleared_reset_record",
            value=cleared_records.reset,
            source="dut",
            endpoint="RECORD.RESET",
        )
        record_property(
            "expected_sequence",
            {
                "round1_irq_round2_reset": ["IRQ", "RESET"],
                "same_round_irq_reset": ["IRQ", "RESET"],
            },
        )
        record_property(
            "actual_sequence",
            {
                "round1_irq_round2_reset": {
                    "first_irq": first_irq.event_count - first_baseline.event_count,
                    "first_records": {
                        "interrupt": first_records.interrupt,
                        "reset": first_records.reset,
                    },
                    "second_records": {
                        "interrupt": second_round_records.interrupt,
                        "reset": second_round_records.reset,
                    },
                },
                "same_round_irq_reset": {
                    "interrupt": final_records.interrupt,
                    "reset": final_records.reset,
                },
            },
        )
        write_json_result(
            et_artifact_dir / "wdg_p1_003_work_mode_irq_and_reset_rounds.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p1_003",
                "round1_irq_round2_reset": {
                    "irq_event_count_delta": first_irq.event_count - first_baseline.event_count,
                    "first_records": {
                        "interrupt": first_records.interrupt,
                        "reset": first_records.reset,
                    },
                    "second_records": {
                        "interrupt": second_round_records.interrupt,
                        "reset": second_round_records.reset,
                    },
                    "session": {
                        "old": transition_first.old_session_id,
                        "new": transition_first.new_session_id,
                    },
                },
                "same_round_irq_reset": {
                    "records": {
                        "interrupt": final_records.interrupt,
                        "reset": final_records.reset,
                    },
                    "after_clear": {
                        "interrupt": cleared_records.interrupt,
                        "reset": cleared_records.reset,
                    },
                    "session": {
                        "old": transition_second.old_session_id,
                        "new": transition_second.new_session_id,
                    },
                },
            },
        )

        # 断言：第一模式按两轮产生IRQ后Reset，第二模式同轮产生两类持久记录。
        assert first_irq.event_count == first_baseline.event_count + 1
        assert first_irq.last_raw & event == event
        assert first_records.interrupt is True
        assert first_records.reset is False
        assert second_round_records.reset is True
        assert final_records.interrupt is True
        assert final_records.reset is True
        assert cleared_records.interrupt is False
        assert cleared_records.reset is False
        assert transition_first.old_session_id != transition_first.new_session_id
        assert transition_second.old_session_id != transition_second.new_session_id
    finally:
        # 清理：第二次复位后优先使用最新Session，失败时退回当前可用Session。
        cleanup_support.wdg.disable()
        cleanup_support.wdg.irq_disable(event)
        cleanup_support.wdg.irq_clear(event)
        cleanup_support.wdg.record_clear(WdgRecord.ALL)
