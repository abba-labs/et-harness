# SYSCNT P1计数边界及频率标识。
# 职责：构造自然进位/回绕和停止状态登记，直接比较真实读回。
# 边界：不根据频率标识推导真实频率，不访问裸寄存器。
# 依赖：公开Driver、独立时钟映射及Canonical Evidence。

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.syscnt import SyscntHaltPolicy, SyscntView
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import cleanup_actions

pytestmark = [pytest.mark.hardware, pytest.mark.ip("syscnt")]


# 测试 Feature：
# 低字向高字进位、完整计数器自然回绕，以及运行态双窗口连贯读取。
#
# 测试方法：
# 1. 装载边界前约50ms的初值，读取确认后启动。
# 2. 运行100ms跨过边界，依次读取READ/CONTROL，再停止比较两窗口。
#
# 通过条件：
# 1. 实际计数跨过目标边界，模数增量正向且有界，停止后两窗口完全一致。
@pytest.mark.parametrize("boundary", ("word_carry", "counter_wrap"))
def test_syscnt_p1_001_carry_and_rollover(
    syscnt_support, resource_driver, record_property, boundary
) -> None:

    # 准备：边界和余量由实际位宽/已确认频率生成，不靠串口恰好撞上某一总线周期。
    support = syscnt_support
    counter = support.counter
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    hz = dict(support.source_hz)[int(old_route[0])]
    modulus = 1 << support.runtime.counter_bits
    edge = 1 << (
        support.runtime.word_bits if boundary == "word_carry" else support.runtime.counter_bits
    )
    margin = max(1, hz // 20)
    initial = edge - margin
    deadline = OperationDeadline.start(1.0, label="SYSCNT_P1_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：批准的软件可控状态归一，不写不存在的硬复位位。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
        resource_driver.reset()

        # 配置：停止装载边界前值，两个窗口在启动前精确读回。
        counter.value_load(initial, timeout_s=deadline.remaining_s())
        loaded = counter.count_get(timeout_s=deadline.remaining_s())
        loaded_control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())
        counter.enable_set(True, timeout_s=deadline.remaining_s())

        # 激励：连续计数100ms跨过50ms余量；等待只形成观测窗口，不伪造计数。
        deadline.sleep(0.1)
        running = counter.count_get(timeout_s=deadline.remaining_s())
        running_control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        stopped = counter.count_get(timeout_s=deadline.remaining_s())
        stopped_control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())

        # 观测：先保留全部边界证据，失败时不能只剩一个比较布尔值。
        record_property("expected_count", initial)
        record_property("boundary", boundary)
        record_observation(
            record_property, key="loaded_count", value=loaded, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="running_count", value=running, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property,
            key="running_control",
            value=running_control,
            source="dut",
            endpoint="COUNT.CONTROL",
        )
        record_observation(
            record_property, key="stopped_count", value=stopped, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property,
            key="stopped_control",
            value=stopped_control,
            source="dut",
            endpoint="COUNT.CONTROL",
        )
        assert loaded == loaded_control == initial
        assert margin < (running - initial) % modulus < hz
        assert 0 <= (running_control - running) % modulus < hz
        assert stopped == stopped_control
        if boundary == "word_carry":
            assert running // edge == 1
        else:
            assert running < initial


# 测试 Feature：
# 频率标识可读写，修改标识不改变停止计数和ENABLE。
#
# 测试方法：
# 1. 建立停止基线，依次登记实际频率及其一半两个非零标识。
# 2. 每次分别读回标识、计数及ENABLE，最后恢复实际频率标识。
#
# 通过条件：
# 1. 两个标识和恢复值均精确读回，计数保持零且ENABLE为0。
def test_syscnt_p1_002_frequency_id(syscnt_support, resource_driver, record_property) -> None:

    # 准备：频率值在本Case只作为登记数据，不能证明实际时钟发生切换。
    support = syscnt_support
    counter = support.counter
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    nominal = dict(support.source_hz)[int(old_route[0])]
    expected = (nominal, max(1, nominal // 2), nominal)
    readings, counts, enables = [], [], []
    deadline = OperationDeadline.start(2.0, label="SYSCNT_P1_002")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：停止并装载零，资源池不继承其他Case的Handle。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
        resource_driver.reset()

        # 配置与观测：两次不同登记和一次恢复均走同一条原子命令路径。
        for frequency in expected:
            counter.frequency_id_set(frequency, timeout_s=deadline.remaining_s())
            state = counter.control_get(timeout_s=deadline.remaining_s())
            readings.append(state.frequency_id_hz)
            enables.append(state.enabled)
            counts.append(counter.count_get(timeout_s=deadline.remaining_s()))

        record_property("expected_frequency_id", expected)
        record_observation(
            record_property,
            key="frequency_id",
            value=readings,
            source="dut",
            endpoint="FREQUENCY.ID",
        )
        record_observation(
            record_property, key="count", value=counts, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="enabled", value=enables, source="dut", endpoint="CONTROL.ENABLE"
        )
        assert tuple(readings) == expected
        assert counts == [0] * len(expected)
        assert not any(enables)
