# SYSCNT P2独立参考计时与Debug Halt。
# 职责：公开跨IP编排、两种独立观测和最终强断言。
# 边界：不以请求等待时长代替测量，不把HDBG配置位当CPU停核事实。
# 依赖：SYSCNT/SYSCTRL/CRG/Resource、已有Debugger和Canonical Evidence。

from time import monotonic

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.syscnt import SyscntHaltPolicy
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import cleanup_actions
from .syscnt_helpers import halted_counter, timing_bounds

pytestmark = [pytest.mark.hardware, pytest.mark.ip("syscnt")]


# 测试 Feature：
# 两种输入时钟源的选择读回及10/50/100/1000/10000ms计时间隔。
#
# 测试方法：
# 1. 选择当前源、登记已确认频率，显式借用独立参考计数器后启动。
# 2. 在等待窗口前后各读取参考前值→SYSCNT→参考后值，并计算双端夹取误差区间。
#
# 通过条件：
# 1. 源选择准确，计数推进，最坏误差≤1ms且采样不确定区间≤0.1ms。
@pytest.mark.parametrize("window_ms", (10, 50, 100, 1000, 10000), ids=lambda value: f"{value}ms")
def test_syscnt_p2_001_clock_and_reference(
    syscnt_support, resource_driver, record_property, syscnt_clock_source, window_ms
) -> None:

    # 准备：频率必须来自独立证据，不使用CNTFID0读回自校准。
    support = syscnt_support
    counter = support.counter
    source = syscnt_clock_source
    hz = dict(support.source_hz)[int(source)]
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    deadline = OperationDeadline.start(window_ms / 1000 + 2.0, label="SYSCNT_P2_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：停止计数并归一可控状态；参考先释放，避免继承上轮所有权。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.reference_enable_set(False, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
        resource_driver.reset()

        # 配置：系统源由SYSCTRL负责，SYSCNT只登记频率、借用参考并启动。
        support.sysctrl.syscnt_source_set(counter.instance_id, source)
        actual_source, _ = support.sysctrl.syscnt_routing_get(counter.instance_id)
        counter.frequency_id_set(hz, timeout_s=deadline.remaining_s())
        counter.reference_enable_set(True, timeout_s=deadline.remaining_s())
        counter.enable_set(True, timeout_s=deadline.remaining_s())

        # 采样：PC时间只包围两个请求，不作为精度Golden。
        host_start = monotonic()
        first = counter.reference_sample_get(timeout_s=deadline.remaining_s())
        deadline.sleep(window_ms / 1000)
        last = counter.reference_sample_get(timeout_s=deadline.remaining_s())
        host_elapsed = monotonic() - host_start

        # 证据：换算前先保存四个参考值与两个被测计数，失败也能复算。
        record_property("clock_evidence", support.clock_evidence)
        record_property("counter_hz", hz)
        record_property("reference_hz", support.reference_hz)
        record_property("host_envelope_s", host_elapsed)
        record_observation(
            record_property,
            key="clock_source",
            value=int(actual_source),
            source="dut",
            endpoint="CLOCK.SOURCE",
        )
        record_observation(
            record_property,
            key="count_before",
            value=first.count,
            source="dut",
            endpoint="COUNT.READ",
        )
        record_observation(
            record_property,
            key="count_after",
            value=last.count,
            source="dut",
            endpoint="COUNT.READ",
        )
        record_observation(
            record_property,
            key="reference_count",
            value=[
                first.reference_before,
                first.reference_after,
                last.reference_before,
                last.reference_after,
            ],
            source="dut",
            endpoint="REFERENCE.COUNT",
        )

        # Oracle：完整模数检查、时间区间和最坏误差都由纯数学实现，阈值不按实测放宽。
        measured_s, error_s, uncertainty_s = timing_bounds(
            first,
            last,
            support.runtime.reference_bits,
            support.runtime.counter_bits,
            support.reference_hz,
            hz,
            host_elapsed,
        )
        record_property("measured_s", measured_s)
        record_property("worst_error_s", error_s)
        record_property("uncertainty_s", uncertainty_s)
        assert actual_source == source
        assert last.count > first.count
        assert error_s <= 0.001
        assert uncertainty_s <= 0.0001


# 测试 Feature：
# CPU真实停核时PAUSE冻结计数，RUN_FREE继续计数，恢复后可继续运行。
#
# 测试方法：
# 1. 逐策略建立独立基线，配置系统Halt路由、本IP策略并启动。
# 2. 由已有Debugger停核，在DHCSR确认停核期间两次读取计数、DBGH、HDBG，最后恢复CPU。
#
# 通过条件：
# 1. 两次CPU停核事实有效；PAUSE计数不变且DBGH=1，RUN_FREE计数增加且DBGH=0。
# 2. CPU恢复后DBGH回到0，计数继续增加，控制通信恢复。
@pytest.mark.parametrize(
    "policy", (SyscntHaltPolicy.PAUSE, SyscntHaltPolicy.RUN_FREE), ids=("pause", "run_free")
)
def test_syscnt_p2_002_debug_halt(
    syscnt_support, resource_driver, record_property, debug_controller, policy
) -> None:

    # 准备：观测地址/位含义只从芯片Execution Mapping取得。
    support = syscnt_support
    counter = support.counter
    old_route = support.sysctrl.syscnt_routing_get(counter.instance_id)
    deadline = OperationDeadline.start(5.0, label="SYSCNT_P2_002")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver, old_route)):
        # 隔离：先恢复计数控制基线，再复位资源池；不影响其他IP。
        support.crg.syscnt_clock_set(counter.instance_id, enabled=True)
        counter.enable_set(False, timeout_s=deadline.remaining_s())
        counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE, timeout_s=deadline.remaining_s())
        counter.value_load(0, timeout_s=deadline.remaining_s())
        assert counter.count_get(timeout_s=deadline.remaining_s()) == 0
        resource_driver.reset()

        # 配置：两个策略均启用同一系统Halt路由，只有本IP策略不同。
        support.sysctrl.syscnt_halt_set(counter.instance_id, enabled=True)
        counter.halt_policy_set(policy, timeout_s=deadline.remaining_s())
        counter.value_load(1 << support.runtime.word_bits, timeout_s=deadline.remaining_s())
        counter.enable_set(True, timeout_s=deadline.remaining_s())
        configured = counter.control_get(timeout_s=deadline.remaining_s())

        # 停核观测：Debugger在同一个会话内Halt、读两组、Resume；异常路径也负责恢复CPU。
        samples = debug_controller.sample_while_halted(support.halt_spec, 0.1)
        before, status_before, control_before = halted_counter(
            samples.before, support.runtime.word_bits
        )
        after, status_after, control_after = halted_counter(
            samples.after, support.runtime.word_bits
        )
        resumed = counter.count_get(timeout_s=deadline.remaining_s())
        resumed_state = counter.control_get(timeout_s=deadline.remaining_s())
        paused = policy is SyscntHaltPolicy.PAUSE

        # 证据：实际CPU状态、计数器暂停状态和策略配置分别记录，不能互相替代。
        record_property("policy", policy.name)
        record_property("debugger_identity", debug_controller.identity)
        record_property("debugger_log", str(samples.action.stdout_path))
        record_observation(
            record_property,
            key="cpu_halted",
            value=all(value & support.halt_spec.halted_mask for value in samples.halt_status),
            source="observer",
            endpoint="CPU.DEBUG_HALTED",
            device_id=debug_controller.identity,
        )
        record_observation(
            record_property,
            key="debug_halted",
            value=[bool(status_before & support.halt_mask), bool(status_after & support.halt_mask)],
            source="dut",
            endpoint="STATUS.DEBUG_HALTED",
        )
        record_observation(
            record_property,
            key="halted_count_before",
            value=before,
            source="dut",
            endpoint="COUNT.READ",
        )
        record_observation(
            record_property,
            key="halted_count_after",
            value=after,
            source="dut",
            endpoint="COUNT.READ",
        )
        record_observation(
            record_property, key="resumed_count", value=resumed, source="dut", endpoint="COUNT.READ"
        )
        record_observation(
            record_property,
            key="halt_policy",
            value=[
                bool(control_before & support.halt_mask),
                bool(control_after & support.halt_mask),
            ],
            source="dut",
            endpoint="CONTROL.HALT_ON_DEBUG",
        )
        assert configured.halt_policy == policy
        assert (
            bool(control_before & support.halt_mask)
            == bool(control_after & support.halt_mask)
            == paused
        )
        assert (
            bool(status_before & support.halt_mask)
            == bool(status_after & support.halt_mask)
            == paused
        )
        assert (after == before) if paused else (after > before)
        assert resumed > after and not resumed_state.debug_halted
