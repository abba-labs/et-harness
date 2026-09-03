# SYSCNT P0停止装载与启停测试。
# 职责：线性配置、激励、观测和强断言。
# 边界：不直接读写寄存器，不隐藏基线建立。
# 依赖：SYSCNT/CRG/SYSCTRL/Resource Driver和Canonical Evidence。

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.syscnt import SyscntHaltPolicy, SyscntView
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import cleanup_actions

pytestmark = [pytest.mark.hardware, pytest.mark.ip("syscnt")]


# 测试 Feature：
# 停止时装载完整计数值，CONTROL与READ窗口一致，装载不隐式启动。
#
# 测试方法：
# 1. 逐参数建立停止、RUN_FREE、零计数及空资源池基线。
# 2. 写入六种位型之一，分别读取两个窗口及使能位，间隔10ms后再次读取。
#
# 通过条件：
# 1. 三次读数等于装载值，ENABLE始终为0。
@pytest.mark.parametrize(
    "pattern", ("zero", "one", "low_ones", "high_one", "alternating", "all_ones")
)
def test_syscnt_p0_001_stopped_load_and_views(
    syscnt_support, resource_driver, record_property, pattern
) -> None:

    # 准备：位型由当前计数/字位宽生成，不固定芯片计数宽度。
    support = syscnt_support
    counter = support.counter
    bits, word = support.runtime.counter_bits, support.runtime.word_bits
    values = {
        "zero": 0,
        "one": 1,
        "low_ones": (1 << word) - 1,
        "high_one": 1 << word,
        "alternating": sum(1 << bit for bit in range(0, bits, 2)),
        "all_ones": (1 << bits) - 1,
    }
    expected = values[pattern]
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    deadline = OperationDeadline.start(2.0, label="SYSCNT_P0_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：无独立复位位，执行已批准的软件可控状态归一；不冒充CRG硬复位。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        baseline = counter.count_get(timeout_s=deadline.remaining_s())
        baseline_enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
        resource_driver.reset()
        assert baseline == 0
        assert baseline_enabled is False

        # 配置：停止装载，两个读窗口必须原样保留全部位型。
        counter.value_load(expected, timeout_s=deadline.remaining_s())
        control_count = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())
        read_count = counter.count_get(timeout_s=deadline.remaining_s())
        enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled

        # 观测：给计数器10ms保持窗口，检查装载后没有隐式启动。
        deadline.sleep(0.01)
        held_count = counter.count_get(timeout_s=deadline.remaining_s())
        held_control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())
        record_property("expected_count", expected)
        record_observation(
            record_property,
            key="control_count",
            value=control_count,
            source="dut",
            endpoint="COUNT.CONTROL",
        )
        record_observation(
            record_property, key="read_count", value=read_count, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="held_count", value=held_count, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="enabled", value=enabled, source="dut", endpoint="CONTROL.ENABLE"
        )
        record_observation(
            record_property,
            key="held_control",
            value=held_control,
            source="dut",
            endpoint="COUNT.CONTROL",
        )
        assert control_count == read_count == held_count == held_control == expected
        assert enabled is False


# 测试 Feature：
# 计数使能递增、停止保持、重新使能保留原值继续递增。
#
# 测试方法：
# 1. 建立独立基线后装载非零值，运行10ms读取计数。
# 2. 停止后间隔10ms读取两次，再启动10ms并读取计数及ENABLE。
#
# 通过条件：
# 1. 运行值大于初值，停止值完全不变，续计数大于停止值且ENABLE为1。
def test_syscnt_p0_002_start_stop_resume(syscnt_support, resource_driver, record_property) -> None:

    # 准备：非零初值能识别错误的“重新启动即清零”。
    support = syscnt_support
    counter = support.counter
    initial = 1 << (support.runtime.counter_bits - 2)
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    deadline = OperationDeadline.start(2.0, label="SYSCNT_P0_002")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：停止、归一策略、装载零及资源整池复位均显式执行。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
        resource_driver.reset()

        # 激励：装载后启动，给出短运行窗口再采样。
        counter.value_load(initial, timeout_s=deadline.remaining_s())
        counter.enable_set(True, timeout_s=deadline.remaining_s())
        started_enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
        deadline.sleep(0.01)
        running = counter.count_get(timeout_s=deadline.remaining_s())

        # 停止：两次读数必须保持一致，不以“差值很小”代替停止。
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        stopped_enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
        stopped = counter.count_get(timeout_s=deadline.remaining_s())
        deadline.sleep(0.01)
        held = counter.count_get(timeout_s=deadline.remaining_s())

        # 恢复：原计数基础上重新使能，不重新装载。
        counter.enable_set(True, timeout_s=deadline.remaining_s())
        deadline.sleep(0.01)
        resumed = counter.count_get(timeout_s=deadline.remaining_s())
        enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
        record_property("initial_count", initial)
        record_observation(
            record_property,
            key="enable_sequence",
            value=[started_enabled, stopped_enabled, enabled],
            source="dut",
            endpoint="CONTROL.ENABLE",
        )
        record_observation(
            record_property, key="running_count", value=running, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="stopped_count", value=stopped, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="held_count", value=held, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="resumed_count", value=resumed, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property, key="enabled", value=enabled, source="dut", endpoint="CONTROL.ENABLE"
        )
        assert initial < running <= stopped == held < resumed
        assert enabled is True
        assert started_enabled is True and stopped_enabled is False
