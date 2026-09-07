# CAN ECC Case独立软件响应回归。
# 职责：验证源/实例归属、Mask/Clear/重复投递强断言及报告闭合。
# 边界：固定响应不从SET/Force回显生成，不代表真实ECC或硬件IRQ。
# 依赖：真实Case、受限Driver Mock及既有Canonical报告入口。

from dataclasses import replace
from unittest.mock import Mock

import pytest
from et_test_platform.drivers.can import CanDriver, CanEccEvent, CanEccSnapshot, CanEccSource
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can import test_can_p2_ecc as case


# 两源、单/三实例均使用预先给定的观测；反例分别破坏每条核心判据。
@pytest.mark.parametrize("source", (CanEccSource.CORRECTED, CanEccSource.UNCORRECTED))
@pytest.mark.parametrize("count", (1, 3))
@pytest.mark.parametrize(
    "fault",
    (None, "masked", "raw", "clear", "instance", "source", "count", "fault", "leak", "stop"),
)
def test_ecc_case_independent_vectors(source, count, fault, monkeypatch, tmp_path) -> None:
    base, resource, _, resets = dependencies()
    supports = []
    # 每次负向窗口只一组固定观测，模拟时间至少100ms；不缩短正式窗口。
    ticks = iter(float(i) * 0.2 for i in range(2 * count))
    monkeypatch.setattr(case, "monotonic", lambda: next(ticks))
    empty = CanEccEvent(0, 0, 0, 0, 0, 0, 1, 0, None)
    for index in range(count):
        driver = Mock(spec=CanDriver)
        driver.instance_id = index
        support = replace(base, can=driver, handle=f"can{index}")
        supports.append(support)
        snapshots, events = [], []
        for target in range(count):
            selected = index == target
            first = CanEccEvent(3, int(source), int(source), 1, 0, 0, 1, 0, index)
            repeated = replace(first, event_count=2)
            events.append(
                replace(empty, event_count=1)
                if fault == "masked" and index == 0 and target == 0
                else empty
            )
            for stage in ("masked", "first", "cleared", "repeat", "stopped"):
                raw = (3 ^ int(source) if stage == "cleared" else 3) if selected else 0
                if stage == "stopped":
                    raw = 0
                if selected and target == 0:
                    if fault == "raw" and stage == "masked":
                        raw = 0
                    if fault == "clear" and stage == "cleared":
                        raw = 0
                    if fault == "stop" and stage == "stopped":
                        raw = 1
                snapshots.append(
                    CanEccSnapshot(raw, 0, 0 if stage == "stopped" else int(source), 3)
                )
                event = (
                    (repeated if stage == "repeat" else first)
                    if selected and stage not in ("masked", "stopped")
                    else empty
                )
                if fault == "leak" and target == 0 and index == count - 1 and stage == "first":
                    event = replace(first, instance_id=(index + 1) % count, event_count=4)
                events.append(event)
        driver.ecc_snapshot_get.side_effect = snapshots
        driver.ecc_event_get.side_effect = events
        first = CanEccEvent(3, int(source), int(source), 1, 0, 0, 1, 0, index)
        if index == 0:
            first = replace(
                first,
                **{
                    "instance": {"instance_id": 99},
                    "source": {"latched_events": 3 ^ int(source)},
                    "fault": {"fault_flags": 1},
                }.get(fault, {}),
            )
        repeated = replace(first, event_count=3 if fault == "count" and index == 0 else 2)
        driver.wait_ecc_event.side_effect = [first, repeated]
    properties = []
    if fault:
        with pytest.raises(AssertionError):
            case.test_can_p2_003_ecc_interrupt_chain(
                supports, resource, lambda k, v: properties.append((k, v)), source
            )
    else:
        case.test_can_p2_003_ecc_interrupt_chain(
            supports, resource, lambda k, v: properties.append((k, v)), source
        )
        assert_case_report(properties, "CAN_P2_003", "PASS", tmp_path)
        for support in supports:
            can = support.can
            assert can.ecc_force.call_args_list[0].args == (CanEccSource(3),)
            assert can.ecc_force.call_args_list[1].args == (source,)
            assert [call.args[0] for call in can.wait_ecc_event.call_args_list] == [0, 1]
            assert can.ecc_snapshot_get.call_count == 5 * count
            assert can.ecc_event_get.call_count == 6 * count
        assert len(dict(properties)["negative_windows"]) == count
    # 最外层清理无论断言阶段都尝试每个实例和整池资源。
    for support in supports:
        assert support.can.ecc_capture_stop.called
        assert support.can.ecc_clear.call_args.args == (CanEccSource(3),)
        assert support.can.ecc_enable_set.call_args.args == (CanEccSource(3), False)
    assert resets[-1] == ("resource",)
