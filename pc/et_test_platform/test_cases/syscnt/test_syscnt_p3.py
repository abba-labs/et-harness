# SYSCNT P3短轮次重复验证。
# 职责：每轮显式重建基线、装载、运行、停止、读回并判定。
# 边界：固定20轮，不升级为无界老化或隐藏测试流程。
# 依赖：公开Driver、统一Deadline与Canonical Evidence。

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.syscnt import SyscntHaltPolicy, SyscntView
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import cleanup_actions

pytestmark = [pytest.mark.hardware, pytest.mark.ip("syscnt")]


# 测试 Feature：
# 重复装载、启停及双窗口读取，确认轮次间无状态残留。
#
# 测试方法：
# 1. 固定20轮，每轮先停止、归一计数和策略、复位资源池，再装载不同非零初值。
# 2. 运行1ms读取，停止后间隔1ms再次读取，并比较CONTROL窗口。
#
# 通过条件：
# 1. 每轮装载准确、运行递增、停止保持、双窗口相等，20轮全部完成。
def test_syscnt_p3_001_repeat_load_start_stop(
    syscnt_support, resource_driver, record_property
) -> None:

    # 准备：不同高位初值可发现错误清零，257步长覆盖低字多种位型。
    support = syscnt_support
    counter = support.counter
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    rows = []
    deadline = OperationDeadline.start(15.0, label="SYSCNT_P3_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 轮次：每个iteration均建立独立基线，前一轮失败不被后续PASS掩盖。
        for index in range(20):
            # 隔离：停止、RUN_FREE、零值读回、整池资源复位；不假称硬件全复位。
            support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
            counter.enable_set(False, timeout_s=deadline.remaining_s())
            counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
            counter.value_load(0, timeout_s=deadline.remaining_s())
            assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
            resource_driver.reset()

            # 配置：写入本轮初值并精确读取两个窗口。
            initial = (1 << (support.runtime.counter_bits - 1)) + 257 * index
            counter.value_load(initial, timeout_s=deadline.remaining_s())
            loaded = counter.count_get(timeout_s=deadline.remaining_s())
            loaded_control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())

            # 激励：运行短窗口，停止后再等待短窗口检查计数保持。
            counter.enable_set(True, timeout_s=deadline.remaining_s())
            running_enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
            deadline.sleep(0.001)
            running = counter.count_get(timeout_s=deadline.remaining_s())
            counter.enable_set(False, timeout_s=deadline.remaining_s())
            stopped_enabled = counter.control_get(timeout_s=deadline.remaining_s()).enabled
            stopped = counter.count_get(timeout_s=deadline.remaining_s())
            deadline.sleep(0.001)
            held = counter.count_get(timeout_s=deadline.remaining_s())
            control = counter.count_get(SyscntView.CONTROL, timeout_s=deadline.remaining_s())

            # 证据：记录至当前轮的完整值；不是覆写Artifact，同一execution保留关键硬件观测。
            rows.append([initial, loaded, loaded_control, running, stopped, held, control])
            record_property(f"round_{index}_expected", initial)
            record_observation(
                record_property,
                key=f"round_{index}_enable",
                value=[running_enabled, stopped_enabled],
                source="dut",
                endpoint="CONTROL.ENABLE",
            )
            record_observation(
                record_property,
                key=f"round_{index}_read_counts",
                value=[loaded, running, stopped, held],
                source="dut",
                endpoint="COUNT.READ",
            )
            record_observation(
                record_property,
                key=f"round_{index}_control_counts",
                value=[loaded_control, control],
                source="dut",
                endpoint="COUNT.CONTROL",
            )
            record_observation(
                record_property,
                key="final_count",
                value=control,
                source="dut",
                endpoint="COUNT.CONTROL",
            )
            record_property("rounds_completed", index + 1)
            assert loaded == loaded_control == initial
            assert initial < running <= stopped == held == control
            assert running_enabled and not stopped_enabled

        record_property("round_count", len(rows))
        assert len(rows) == 20
