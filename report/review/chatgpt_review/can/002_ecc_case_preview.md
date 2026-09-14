# CAN_P2_003 线性写法预览

状态：PROPOSED。关联方案：`001_ecc_interrupt_chain_plan.md`。
本文件中的代码只是供人工审阅的目标版本，没有替换实际 Case。

只有 `CanDriver.state_reset()` 是拟新增的设备接口，目前尚未实现。其余 ECC、CRG、Resource 动作沿用已审查版本的 API。先完成状态复位命令和隔离验证，再考虑替换运行文件。

下面保留完整辅助定义，便于看清主流程没有把测试搬进 Driver：

- `_ecc_cleanup_actions` 只构造退出动作，交给现有清理执行器；无主流程 I/O。
- `_record_ecc` 只接收已读数据，立即记录并原样返回；不接收 Driver，不比较 PASS/FAIL。
- `_assert_quiet`、`_assert_delivery`、`_check_ecc_state` 只检查传入值，留在 Case 模块。主流程仍明确写出 Expected 和每条设备命令。
- `stage` 仅是诊断标签，不再决定要执行哪个硬件动作。
- snapshot 成功后立即记录，才读取 event。一个后续请求失败不会令此前成功读到的数据因整批列表尚未生成而丢失。
- 末尾停止、解绑、Clear、记录复位和终态读回仍在 Case 中，是测试内容；外层兜底清理不替代它。

```python
from dataclasses import asdict
from functools import partial
from time import monotonic

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.can import CanEccSource, CanEccSnapshot, CanEccEvent
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope

ALL = CanEccSource.CORRECTED | CanEccSource.UNCORRECTED
NONE = CanEccSource.NONE
NEGATIVE_WINDOW_S = 0.1
pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 只构造退出动作，不在这里执行设备操作或测试。
def _ecc_cleanup_actions(supports, resource_driver):
    actions = []
    for support in supports:
        can = support.can
        actions.extend((
            ("ECC mask", partial(can.ecc_mask_set, ALL, True)),
            ("ECC disable", partial(can.ecc_enable_set, ALL, False)),
            ("ECC stop", can.ecc_capture_stop),
            ("ECC clear", partial(can.ecc_clear, ALL)),
            ("CAN reset", partial(support.crg.reset, CrgPeripheral.CAN,
                                  instance=can.instance_id)),
        ))
    actions.append(("Resource reset", resource_driver.reset))
    return tuple(actions)


# 纯比较：不接收 Driver，不执行 I/O。
def _assert_quiet(event):
    assert event.event_count == 0, event
    assert event.latched_events == NONE, event
    assert event.raw_status == event.masked_status == NONE, event
    assert event.instance_id is None, event
    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0, event


# 只检查 Case 已经读到的回调事实。
def _assert_delivery(event, *, instance_id, source, count):
    assert event.instance_id == instance_id, event
    assert event.latched_events == source, event
    assert event.raw_status == ALL and event.masked_status == source, event
    assert event.event_count == count, event
    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0, event


# 逐次保存成功读回，再原样返回数据；不操作设备，也不决定 PASS/FAIL。
def _record_ecc(stage, instance_id, value, *, target_id, evidence, record_property):
    row = {"stage": stage, "target": f"can{target_id}",
           "handle": f"can{instance_id}", **asdict(value)}
    if isinstance(value, CanEccSnapshot):
        evidence["ecc_summary"].append(row)
        for field in ("raw", "status", "enabled", "masked"):
            record_observation(record_property, key=f"ecc_{field}",
                               value=int(getattr(value, field)), source="dut",
                               endpoint=f"ECC_IRQ.{field.upper()}",
                               device_id=f"can{instance_id}")
    elif isinstance(value, CanEccEvent):
        evidence["isr"].append(row)
    else:
        raise TypeError("ECC recorder requires a snapshot or event")
    return value


# 纯 Case 层比较：stage 仅用于失败定位，不控制测试步骤。
def _check_ecc_state(instance_id, snapshot, event, *, stage, target_id, source,
                     target_raw, target_count, enabled):
    selected = instance_id == target_id
    count = target_count if selected else 0
    context = (stage, target_id, instance_id, snapshot, event)
    assert snapshot.raw == (target_raw if selected else NONE), context
    assert snapshot.status == NONE, context
    assert snapshot.masked == ALL, context
    assert snapshot.enabled == enabled, context
    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0, context
    assert event.event_count == count, context
    assert event.latched_events == (source if count else NONE), context
    assert event.instance_id == (target_id if count else None), context


# 测试 Feature：ECC Force/Mask/Clear、重复投递、共享 IRQ 的实例隔离。
# 测试方法：完整屏蔽窗口 -> 首次投递 -> 只清目标源 -> 再次投递 -> 退出读回。
# 通过条件：全部实例和两类源保持原覆盖；不代表真实 RAM ECC 纠错验证。
@pytest.mark.parametrize("source", (CanEccSource.CORRECTED, CanEccSource.UNCORRECTED))
def test_can_p2_003_ecc_interrupt_chain(
    can_all_supports, resource_driver, record_property, source
):
    supports = can_all_supports
    cans = tuple(support.can for support in supports)
    evidence = {"isr": [], "negative_windows": [], "ecc_summary": []}
    for key, values in evidence.items():
        record_property(key, values)
    record_property("expected", {"source": int(source), "masked_seconds": NEGATIVE_WINDOW_S})

    # 复用现有错误聚合：主错误保留，退出动作全部尝试。
    cleanup = partial(_ecc_cleanup_actions, supports, resource_driver)
    with case_cleanup_scope(cleanup):
        for target in cans:
            deadline = OperationDeadline.start(5.0, label="CAN ECC target/source")
            remaining = deadline.remaining_s
            check = partial(_check_ecc_state, target_id=target.instance_id, source=source)
            record = partial(_record_ecc, target_id=target.instance_id,
                             evidence=evidence, record_property=record_property)

            # 1. 独立基线：先清各实例软件会话，再 CRG 复位，最后复位公共资源池。
            for can in cans:
                can.state_reset(timeout_s=remaining())  # 拟新增，尚未实现
            for support in supports:
                support.crg.reset(CrgPeripheral.CAN, instance=support.can.instance_id)
            resource_driver.reset()
            for can in cans:
                can.ecc_mask_set(ALL, True, timeout_s=remaining())
                can.ecc_enable_set(ALL, False, timeout_s=remaining())
                can.ecc_clear(ALL, timeout_s=remaining())
                can.ecc_capture_start(source, timeout_s=remaining())

            # 2. 屏蔽两源并 Force；完整 100 ms 内轮询全部实例，而非只读一次。
            target.ecc_force(ALL, timeout_s=remaining())
            started = monotonic()
            while True:
                for can in cans:
                    event = record("masked", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                    _assert_quiet(event)
                elapsed = monotonic() - started
                if elapsed >= NEGATIVE_WINDOW_S:
                    evidence["negative_windows"].append({"target": f"can{target.instance_id}",
                                                          "seconds": elapsed})
                    break
                deadline.sleep(0.001)
            for can in cans:
                snapshot = record("masked", can.instance_id, can.ecc_snapshot_get(timeout_s=remaining()))
                event = record("masked", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                check(can.instance_id, snapshot, event, stage="masked",
                      target_raw=ALL, target_count=0, enabled=source)

            # 3. 只放行目标源：第一次真实回调，其他实例必须仍为零。
            target.ecc_mask_set(source, False, timeout_s=remaining())
            first = record("first", target.instance_id,
                           target.wait_ecc_event(0, timeout_s=remaining()))
            _assert_delivery(first, instance_id=target.instance_id, source=source, count=1)
            for can in cans:
                snapshot = record("first", can.instance_id, can.ecc_snapshot_get(timeout_s=remaining()))
                event = record("first", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                check(can.instance_id, snapshot, event, stage="first",
                      target_raw=ALL, target_count=1, enabled=source)

            # 4. 只清目标 Raw；另一源保留，既有回调证据不能被清掉。
            target.ecc_clear(source, timeout_s=remaining())
            for can in cans:
                snapshot = record("cleared", can.instance_id, can.ecc_snapshot_get(timeout_s=remaining()))
                event = record("cleared", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                check(can.instance_id, snapshot, event, stage="cleared",
                      target_raw=ALL ^ source, target_count=1, enabled=source)

            # 5. 不重建 Capture，再次 Force/放行：计数从 1 到 2，generation 不变。
            target.ecc_force(source, timeout_s=remaining())
            target.ecc_mask_set(source, False, timeout_s=remaining())
            second = record("repeat", target.instance_id,
                            target.wait_ecc_event(first.event_count, timeout_s=remaining()))
            _assert_delivery(second, instance_id=target.instance_id, source=source,
                             count=first.event_count + 1)
            assert second.generation == first.generation, (first, second)
            for can in cans:
                snapshot = record("repeat", can.instance_id, can.ecc_snapshot_get(timeout_s=remaining()))
                event = record("repeat", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                check(can.instance_id, snapshot, event, stage="repeat",
                      target_raw=ALL, target_count=2, enabled=source)

            # 6. 原测试要求的退出验证：不使用 CRG/state_reset 代替这些动作。
            for can in cans:
                can.ecc_mask_set(ALL, True, timeout_s=remaining())
                can.ecc_enable_set(ALL, False, timeout_s=remaining())
                can.ecc_capture_stop(timeout_s=remaining())
                can.ecc_clear(ALL, timeout_s=remaining())
                can.ecc_event_reset(timeout_s=remaining())
            for can in cans:
                snapshot = record("stopped", can.instance_id, can.ecc_snapshot_get(timeout_s=remaining()))
                event = record("stopped", can.instance_id, can.ecc_event_get(timeout_s=remaining()))
                check(can.instance_id, snapshot, event, stage="stopped",
                      target_raw=NONE, target_count=0, enabled=NONE)
```

## 与既有版本的边界

设备端调用仍然只经过 CAN/CRG/Resource Driver。数据比较函数不会反向进入 Driver；Driver 不 import test_cases，也不决定通过标准。

这份预览没有把 100 ms 的跨实例窗口包装成单实例 wait 函数，因为那会丢掉共享 IRQ 的旁路观察。也没有把末尾的停止链换成一次 reset，因为那会绕开原来的退出恢复验证。

主流程消除了 stage 分派循环和嵌套清理推导，仍保留必要的 for/while。辅助函数全文在本文件中，不是省略掉的黑箱。类型注解、项目样式门禁与契约扫描仍需在实际落地时按当前规则检查。

验证状态：仅做预览的语法解析和隔离的纯数据检查；仓库单元测试、Keil、真实 CAN 与 HIL 均未执行。新增 state_reset 未实现，因此不能据此声明改动后通过。
