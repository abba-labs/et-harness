# CAN ECC中断链测试。
# 职责：Force、屏蔽、清除、重复投递和共享线路的实例隔离。
# 边界：不注入RAM错误，不配置全局ECC，不把Service计数当硬件状态。
# 依赖：CAN/CRG/Resource直接动作、统一Deadline和Canonical Observation。

from dataclasses import asdict
from time import monotonic

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.can import CanEccSource
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
ALL_SOURCES = CanEccSource.CORRECTED | CanEccSource.UNCORRECTED
NEGATIVE_WINDOW_S = 0.1


# 测试 Feature：
# ECC两类源的Force/Mask/Clear和共享中断回调归属，不验证真实RAM纠错。
#
# 测试方法：
# 1. 逐目标实例、逐源复位全部参与CAN和资源，清历史Raw及会话并同时捕获。
# 2. 屏蔽下Force两源，100ms内全部实例无ISR；只放行目标源等待实际回调。
# 3. 清目标Raw，证明另一源仍保留；再次Force/放行后Count增加且归属不变。
# 4. 屏蔽、关闭、解绑、清Raw并读回终态，异常也尝试全部清理。
#
# 通过条件：
# 1. 屏蔽不投递，放行只命中目标实例和源，事件无Fault/Unexpected/Overflow。
# 2. Clear不影响对照源，重复投递有效，非目标实例无串扰且退出无残留。
@pytest.mark.parametrize("source", (CanEccSource.CORRECTED, CanEccSource.UNCORRECTED))
def test_can_p2_003_ecc_interrupt_chain(
    can_all_supports, resource_driver, record_property, source
) -> None:

    supports = can_all_supports
    events, windows, results = [], [], []
    record_property("isr", events)
    record_property("negative_windows", windows)
    record_property("ecc_summary", results)
    record_property("expected", {"source": int(source), "masked_seconds": NEGATIVE_WINDOW_S})

    # 清理动作彼此独立；即使关闭/解绑失败，也继续清Raw、复位全部CAN与资源。
    with case_cleanup_scope(
        lambda: (
            tuple(
                action
                for support in supports
                for action in (
                    ("ECC mask", lambda s=support: s.can.ecc_mask_set(ALL_SOURCES, True)),
                    ("ECC disable", lambda s=support: s.can.ecc_enable_set(ALL_SOURCES, False)),
                    ("ECC stop", support.can.ecc_capture_stop),
                    ("ECC clear", lambda s=support: s.can.ecc_clear(ALL_SOURCES)),
                    (
                        "CAN reset",
                        lambda s=support: s.crg.reset(
                            CrgPeripheral.CAN, instance=s.can.instance_id
                        ),
                    ),
                )
            )
            + (("Resource pool reset", resource_driver.reset),)
        )
    ):
        # 实例归属本身是Feature；逐目标轮转，旁路实例同时捕获以检测共享IRQ串扰。
        for target in supports:
            deadline = OperationDeadline.start(5.0, label="CAN ECC target/source")
            can = target.can

            # 隔离：全部参与CAN先复位，再清资源；不复位控制UART或不参与的IP。
            for support in supports:
                support.crg.reset(CrgPeripheral.CAN, instance=support.can.instance_id)
            resource_driver.reset()
            # 捕获准备：先关闭所有源，清旧Raw与记录，再只启用当前语义源。
            for support in supports:
                support.can.ecc_mask_set(ALL_SOURCES, True, timeout_s=deadline.remaining_s())
                support.can.ecc_enable_set(ALL_SOURCES, False, timeout_s=deadline.remaining_s())
                support.can.ecc_capture_stop(timeout_s=deadline.remaining_s())
                support.can.ecc_clear(ALL_SOURCES, timeout_s=deadline.remaining_s())
                support.can.ecc_event_reset(timeout_s=deadline.remaining_s())
                support.can.ecc_capture_start(source, timeout_s=deadline.remaining_s())

            # 激励：两源均有Raw，只有当前源使能；负向窗口持续观察全部捕获者。
            can.ecc_force(ALL_SOURCES, timeout_s=deadline.remaining_s())
            start = monotonic()
            # 负向等待跨全部实例；完整时间窗口结束前不接受仅一次静默快照。
            while True:
                # 共享线路上的每个捕获者都必须静默，而非仅检查目标对象。
                for support in supports:
                    event = support.can.ecc_event_get(timeout_s=deadline.remaining_s())
                    events.append(
                        {
                            "stage": "masked",
                            "target": target.handle,
                            "handle": support.handle,
                            **asdict(event),
                        }
                    )
                    assert event.event_count == 0 and event.latched_events == CanEccSource.NONE
                    assert event.raw_status == event.masked_status == CanEccSource.NONE
                    assert event.instance_id is None
                    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                elapsed = monotonic() - start
                if elapsed >= NEGATIVE_WINDOW_S:
                    windows.append({"target": target.handle, "seconds": elapsed})
                    break
                deadline.sleep(0.001)

            # 状态阶段显式可读：屏蔽、首次ISR、目标Clear、再次ISR及退出终态。
            first = None
            # 逐阶段保留证据，Clear与再次Force不被重置会话隔开。
            for stage in ("masked", "first", "cleared", "repeat", "stopped"):
                if stage in ("first", "repeat"):
                    if stage == "repeat":
                        can.ecc_force(source, timeout_s=deadline.remaining_s())
                    can.ecc_mask_set(source, False, timeout_s=deadline.remaining_s())
                    event = can.wait_ecc_event(
                        0 if first is None else first.event_count, timeout_s=deadline.remaining_s()
                    )
                    events.append({"stage": stage, "target": target.handle, **asdict(event)})
                    assert event.instance_id == can.instance_id and event.latched_events == source
                    assert event.raw_status == ALL_SOURCES and event.masked_status == source
                    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                    assert event.event_count == (1 if first is None else first.event_count + 1)
                    first = event if first is None else first
                    assert event.generation == first.generation
                elif stage == "cleared":
                    can.ecc_clear(source, timeout_s=deadline.remaining_s())
                elif stage == "stopped":
                    # 退出观测前先解除每个会话所有权，再清空硬件和软件残留。
                    for support in supports:
                        support.can.ecc_mask_set(
                            ALL_SOURCES, True, timeout_s=deadline.remaining_s()
                        )
                        support.can.ecc_enable_set(
                            ALL_SOURCES, False, timeout_s=deadline.remaining_s()
                        )
                        support.can.ecc_capture_stop(timeout_s=deadline.remaining_s())
                        support.can.ecc_clear(ALL_SOURCES, timeout_s=deadline.remaining_s())
                        support.can.ecc_event_reset(timeout_s=deadline.remaining_s())

                # 每一独立寄存器端点单独记录，证据在断言及后续Cleanup前保留。
                for support in supports:
                    actual = support.can.ecc_snapshot_get(timeout_s=deadline.remaining_s())
                    record_observation(
                        record_property,
                        key="ecc_raw",
                        value=int(actual.raw),
                        source="dut",
                        endpoint="ECC_IRQ.RAW",
                        device_id=support.handle,
                    )
                    record_observation(
                        record_property,
                        key="ecc_status",
                        value=int(actual.status),
                        source="dut",
                        endpoint="ECC_IRQ.STATUS",
                        device_id=support.handle,
                    )
                    record_observation(
                        record_property,
                        key="ecc_enabled",
                        value=int(actual.enabled),
                        source="dut",
                        endpoint="ECC_IRQ.ENABLED",
                        device_id=support.handle,
                    )
                    record_observation(
                        record_property,
                        key="ecc_masked",
                        value=int(actual.masked),
                        source="dut",
                        endpoint="ECC_IRQ.MASKED",
                        device_id=support.handle,
                    )
                    event = support.can.ecc_event_get(timeout_s=deadline.remaining_s())
                    events.append(
                        {
                            "stage": stage,
                            "target": target.handle,
                            "handle": support.handle,
                            **asdict(event),
                        }
                    )
                    results.append(
                        {
                            "stage": stage,
                            "target": target.handle,
                            "handle": support.handle,
                            **asdict(actual),
                        }
                    )
                    expected_raw = (
                        (ALL_SOURCES ^ source if stage == "cleared" else ALL_SOURCES)
                        if support is target and stage != "stopped"
                        else CanEccSource.NONE
                    )
                    assert actual.raw == expected_raw and actual.status == CanEccSource.NONE
                    assert actual.masked == ALL_SOURCES
                    assert actual.enabled == (CanEccSource.NONE if stage == "stopped" else source)
                    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                    if stage == "stopped" or support is not target or stage == "masked":
                        assert event.event_count == 0 and event.instance_id is None
                        assert event.latched_events == CanEccSource.NONE
                    else:
                        assert (
                            event.instance_id == can.instance_id and event.latched_events == source
                        )
                        assert event.event_count == (2 if stage == "repeat" else 1)
