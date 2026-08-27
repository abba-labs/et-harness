# CORDIC P3 Formal Case。
#
# 职责：在已闭合的 Float32 代表合法节点上验证重复执行的结果确定性和状态稳定性。
# 边界：只使用当前 CORDIC Driver 已发布的 Float32/Polling/32-bit 语义；不猜定点 Codec、边界容差或性能阈值。
# 依赖：CORDIC Support、Capability、公共证据工具和 pytest。

from __future__ import annotations

import struct
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.cordic import (
    CordicConfig,
    CordicFeature,
    CordicFunction,
    CordicIrqEvent,
    CordicNumericMode,
    CordicResultCount,
    CordicStatus,
    CordicWidth,
    CordicWorkMode,
)
from ...drivers.crg import CrgPeripheral
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import CordicSupportFactory

pytestmark = [pytest.mark.hardware, pytest.mark.ip("cordic")]

_CORDIC_P3_VECTOR_SEED = 0xC0D1C001
_CORDIC_P3_REPEAT_COUNT = 3
_CORDIC_P3_TIMED_TIMEOUT_POLLS = 128
_CORDIC_ABSOLUTE_TOLERANCE = 1.0e-4

# 只选择结果可由Float32特殊节点精确表示的三种输入形态，分别覆盖单输入单结果、
# 单输入双结果和双输入双结果；周期只作为目标侧事实记录，不设置未经审核的阈值。
_CORDIC_P3_TIMED_VECTORS = (
    (CordicFunction.SQRT, (1.0,), (1.0, None), CordicResultCount.ONE),
    (CordicFunction.SINCOS, (0.0,), (1.0, 0.0), CordicResultCount.TWO),
    (CordicFunction.PHASE_MODULUS, (1.0, 0.0), (0.0, 1.0), CordicResultCount.TWO),
)

# 当前只使用结果可由已闭合 Float32 语义精确表示的代表合法节点。
_CORDIC_P3_VECTORS = (
    (CordicFunction.SINCOS, (0.0,), (1.0, 0.0)),
    (CordicFunction.PHASE_MODULUS, (1.0, 0.0), (0.0, 1.0)),
    (CordicFunction.ARCTAN, (0.0,), (0.0, None)),
    (CordicFunction.HSINCOS, (0.0,), (1.0, 0.0)),
    (CordicFunction.ATANH, (0.0,), (0.0, None)),
    (CordicFunction.EXP, (0.0,), (1.0, None)),
    (CordicFunction.LN, (1.0,), (0.0, None)),
    (CordicFunction.SQRT, (0.25,), (0.5, None)),
    (CordicFunction.TAN, (0.0,), (0.0, None)),
)


# 把公共 IEEE-754 Float32 数值转换为 CORDIC Driver 接受的原始字。
def _float32_raw(value: float) -> int:

    return struct.unpack("<I", struct.pack("<f", value))[0]


# 把硬件 Float32 Raw 解码为数学值；CORDIC 近似结果不得按 Raw 逐位相等判定。
def _float32_value(raw: int) -> float:

    return struct.unpack("<f", struct.pack("<I", raw))[0]


# 使用历史验证共同采用的绝对误差预算判断CORDIC数学结果。
def _within_cordic_budget(actual: float, expected: float) -> bool:

    return abs(actual - expected) <= _CORDIC_ABSOLUTE_TOLERANCE


# 测试 Feature：
# CORDIC Float32 代表合法节点的重复执行确定性、完成状态和清理后状态稳定性。
#
# 测试方法：
# 1. 使用固定向量 seed 标识九类数学函数的代表合法节点，当前节点只采用已闭合的 Float32 精确值。
# 2. 对每个节点配置 Float32、32-bit、Polling，清除历史状态后连续执行固定轮数。
# 3. 每轮按函数参数顺序提交输入，在有界轮询内读取 RESULT 和 STATUS.COMPLETE。
# 4. 读取完成状态后显式清除 COMPLETE/错误状态，并记录清除后的硬件状态。
# 5. 将每轮 Raw 结果与节点 Golden 比较，同时比较同一节点的重复 Raw 结果是否一致。
# 6. 汇总函数节点、重复轮数、结果序列和状态序列，保留完整结构化 Artifact。
#
# 通过条件：
# 1. 九类函数的全部节点和固定重复轮数均完成，无超时。
# 2. 每轮 RESULT.PRIMARY/SECONDARY（适用时）均满足独立数学Golden和CORDIC误差预算。
# 3. 同一节点的重复 Raw 结果完全一致，不出现随机漂移。
# 4. 每轮完成前只出现 COMPLETE，Clear 后 COMPLETE/错误状态均为零。
def test_cordic_p3_001_deterministic_representative_stability(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：本Case只消费已发布的 Float32、32-bit、归一化输入和Polling语义。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    runtime = support.runtime
    required_features = (
        CordicFeature.FLOAT32
        | CordicFeature.WIDTH_32
        | CordicFeature.NORMALIZED_RANGE
        | CordicFeature.POLLING
        | CordicFeature.STATUS
    )
    if runtime.features & required_features != required_features:
        pytest.skip(
            "skip_by_runtime_capability: CORDIC P3 Float32 stability prerequisites unavailable"
        )
    missing_functions = tuple(
        function.name for function, _, _ in _CORDIC_P3_VECTORS if function not in runtime.functions
    )
    if missing_functions:
        pytest.skip(
            "skip_by_runtime_capability: CORDIC P3 functions unavailable: "
            + ", ".join(missing_functions)
        )

    records: list[dict[str, object]] = []
    configured = False
    planned_rounds = len(_CORDIC_P3_VECTORS) * _CORDIC_P3_REPEAT_COUNT

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (("CORDIC P3 status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 固定配置：只使用当前已闭合的 Float32 32-bit Polling路径；精度取Runtime上限，避免写死芯片数值。
            support.cordic.configure(
                CordicConfig(
                    numeric_mode=CordicNumericMode.FLOAT32,
                    argument_width=CordicWidth.BITS_32,
                    result_width=CordicWidth.BITS_32,
                    precision_cycles=runtime.maximum_precision_cycles,
                    work_mode=CordicWorkMode.POLLING,
                )
            )
            configured = True

            # 记录：seed用于固定本Case向量集合身份，重复轮数是本次执行的稳定参数。
            record_property("vector_seed", _CORDIC_P3_VECTOR_SEED)
            record_property("planned_rounds", planned_rounds)
            record_property("numeric_mode", CordicNumericMode.FLOAT32.name)

            # 节点遍历：每个函数只使用当前文档已审核的代表合法节点。
            for vector_index, (function, arguments, expected) in enumerate(_CORDIC_P3_VECTORS):
                expected_primary = _float32_raw(expected[0])
                expected_secondary = None if expected[1] is None else _float32_raw(expected[1])
                vector_records: list[dict[str, object]] = []

                # 重复执行：每轮从清洁状态开始，避免上一轮完成位污染当前结果。
                for repeat_index in range(_CORDIC_P3_REPEAT_COUNT):
                    support.cordic.status_clear(CordicStatus.ALL)

                    # 激励：按当前函数稳定参数顺序提交一个或两个Float32 Raw参数。
                    for argument in arguments:
                        support.cordic.argument_submit(function, _float32_raw(argument))

                    # 观测：有界等待完成，随后读取属于当前节点的Raw结果和状态。
                    status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
                    result = support.cordic.result_get()

                    # 清理观测：显式清除当前状态并读取清除后的状态，形成前后闭环。
                    support.cordic.status_clear(CordicStatus.ALL)
                    cleared = support.cordic.status_get()
                    round_record = {
                        "vector_index": vector_index,
                        "repeat_index": repeat_index,
                        "function": function.name,
                        "arguments_raw": [_float32_raw(argument) for argument in arguments],
                        "expected_primary_raw": expected_primary,
                        "expected_secondary_raw": expected_secondary,
                        "actual_primary_raw": result.primary_raw,
                        "actual_secondary_raw": result.secondary_raw,
                        "status_before_clear": int(status),
                        "status_after_clear": int(cleared),
                        "poll_count": poll_count,
                    }
                    vector_records.append(round_record)
                    records.append(round_record)

                # 证据：同一硬件端点的多轮结果以序列记录，不把软件Golden冒充DUT观察。
                record_observation(
                    record_property,
                    key=f"vector_{vector_index}_primary_raw_sequence",
                    value=[item["actual_primary_raw"] for item in vector_records],
                    source="dut",
                    endpoint="RESULT.PRIMARY",
                )
                if expected_secondary is not None:
                    record_observation(
                        record_property,
                        key=f"vector_{vector_index}_secondary_raw_sequence",
                        value=[item["actual_secondary_raw"] for item in vector_records],
                        source="dut",
                        endpoint="RESULT.SECONDARY",
                    )
                record_observation(
                    record_property,
                    key=f"vector_{vector_index}_status_after_clear",
                    value=[item["status_after_clear"] for item in vector_records],
                    source="dut",
                    endpoint="STATUS.COMPLETE",
                )
                record_observation(
                    record_property,
                    key="actual_primary_raw",
                    value=vector_records[-1]["actual_primary_raw"],
                    source="dut",
                    endpoint="RESULT.PRIMARY",
                )
                record_observation(
                    record_property,
                    key="actual_status_after_clear",
                    value=vector_records[-1]["status_after_clear"],
                    source="dut",
                    endpoint="STATUS.COMPLETE",
                )

                # 断言：数学正确性使用误差预算；重复确定性仍要求硬件Raw逐位一致。
                assert all(
                    _within_cordic_budget(
                        _float32_value(int(item["actual_primary_raw"])),
                        expected[0],
                    )
                    for item in vector_records
                )
                if expected_secondary is not None:
                    assert all(
                        _within_cordic_budget(
                            _float32_value(int(item["actual_secondary_raw"])),
                            expected[1],
                        )
                        for item in vector_records
                    )
                assert all(
                    int(item["status_before_clear"]) == int(CordicStatus.COMPLETE)
                    for item in vector_records
                )
                assert all(int(item["status_after_clear"]) == 0 for item in vector_records)
                assert len({item["actual_primary_raw"] for item in vector_records}) == 1
                if expected_secondary is not None:
                    assert len({item["actual_secondary_raw"] for item in vector_records}) == 1

            # 汇总：所有节点均形成完整轮次，防止部分执行被误报为完整覆盖。
            record_property("vectors", records)
            record_property("completed_rounds", len(records))
            assert len(records) == planned_rounds
    finally:
        # Evidence Closure：即使中途超时或断言失败，也只发布一次当前完整/部分Snapshot。
        write_json_result(
            et_artifact_dir / "cordic_p3_001_deterministic_representative_stability.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p3_001",
                "vector_seed": _CORDIC_P3_VECTOR_SEED,
                "repeat_count": _CORDIC_P3_REPEAT_COUNT,
                "planned_rounds": planned_rounds,
                "completed_rounds": len(records),
                "vectors": records,
            },
        )


# 测试 Feature：
# CORDIC 目标侧单次运算周期事实，覆盖单输入单结果、单输入双结果和双输入双结果路径。
#
# 测试方法：
# 1. 读取Runtime Capability，配置Float32、32-bit、Polling和当前Runtime允许的最高精度。
# 2. 按固定向量分别执行SQRT、SINCOS和PHASE_MODULUS，每次调用一次目标侧计时命令。
# 3. 由Firmware Driver Extension在目标DWT中采集从首个参数写入到结果可读的cycle delta。
# 4. 读取Raw结果和周期事实，使用PC独立Float32 Golden确认功能结果正确。
# 5. 保存每个节点的Raw、Decoded、Golden和cycles；没有冻结绝对性能阈值时只做周期表征。
#
# 通过条件：
# 1. 三种输入/结果形态均能完成，返回的目标周期数大于零且可追溯。
# 2. 每个节点的结果满足独立数学Golden和CORDIC误差预算。
# 3. 性能报告只包含目标侧cycle事实，不使用PC wall-clock或未经审核的速度阈值。
@pytest.mark.parametrize(
    ("function", "arguments", "expected", "result_count"),
    _CORDIC_P3_TIMED_VECTORS,
    ids=("sqrt_one_result", "sincos_two_result", "phase_modulus_two_argument"),
)
def test_cordic_p3_002_target_cycle_measurement(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    function: CordicFunction,
    arguments: tuple[float, ...],
    expected: tuple[float, float | None],
    result_count: CordicResultCount,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：性能Case只要求稳定的Float32、32-bit和Polling执行路径。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    required_features = CordicFeature.FLOAT32 | CordicFeature.WIDTH_32 | CordicFeature.POLLING
    if support.runtime.features & required_features != required_features:
        pytest.skip("skip_by_runtime_capability: CORDIC timed Float32/Polling path is unavailable")
    if function not in support.runtime.functions:
        pytest.skip(f"skip_by_runtime_capability: CORDIC function {function.name} is unavailable")

    # 配置：建立一次独立的Float32、32-bit、Polling会话，计时命令复用该配置。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            argument_width=CordicWidth.BITS_32,
            result_width=CordicWidth.BITS_32,
            precision_cycles=support.runtime.maximum_precision_cycles,
            sincos_result_count=(
                result_count if function is CordicFunction.SINCOS else CordicResultCount.TWO
            ),
            phase_modulus_result_count=(
                result_count if function is CordicFunction.PHASE_MODULUS else CordicResultCount.TWO
            ),
            work_mode=CordicWorkMode.POLLING,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励与观测：Firmware在目标侧关闭中断、写入参数、等待完成并返回DWT周期差。
    raw_arguments = tuple(_float32_raw(argument) for argument in arguments)
    timed = support.cordic.execute_timed(
        function,
        raw_arguments,
        timeout_polls=_CORDIC_P3_TIMED_TIMEOUT_POLLS,
    )
    status = support.cordic.status_get()
    support.cordic.status_clear(CordicStatus.ALL)
    cleared = support.cordic.status_get()

    # 证据：周期来源标记为DUT，结果端点保留Raw值，Golden仅作为期望来源。
    expected_primary = _float32_raw(expected[0])
    expected_secondary = None if expected[1] is None else _float32_raw(expected[1])
    record_property("function", function.name)
    record_property("arguments_raw", raw_arguments)
    record_property("expected_primary_raw", expected_primary)
    record_property("expected_secondary_raw", expected_secondary)
    record_observation(
        record_property,
        key="target_cycles",
        value=timed.elapsed_cycles,
        source="dut",
        endpoint="TIMING.CYCLE_COUNT",
    )
    record_observation(
        record_property,
        key="timed_primary_raw",
        value=timed.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    if expected_secondary is not None:
        record_observation(
            record_property,
            key="timed_secondary_raw",
            value=timed.secondary_raw,
            source="dut",
            endpoint="RESULT.SECONDARY",
        )
    write_json_result(
        et_artifact_dir / f"cordic_p3_002_target_cycle_measurement_{function.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p3_002",
            "function": function.name,
            "arguments_raw": raw_arguments,
            "expected": {
                "primary_raw": expected_primary,
                "secondary_raw": expected_secondary,
            },
            "actual": {
                "primary_raw": timed.primary_raw,
                "secondary_raw": timed.secondary_raw,
                "elapsed_cycles": timed.elapsed_cycles,
            },
            "status": {"before_clear": int(status), "after_clear": int(cleared)},
        },
    )

    # 断言：先闭合功能结果，再确认周期事实是非零目标侧采样；不判未经审核的绝对阈值。
    assert _within_cordic_budget(_float32_value(timed.primary_raw), expected[0])
    if expected_secondary is not None:
        assert _within_cordic_budget(_float32_value(timed.secondary_raw), expected[1])
    assert timed.elapsed_cycles > 0
    assert status == CordicStatus.COMPLETE
    assert cleared == CordicStatus(0)


# 测试 Feature：
# CORDIC Zero-Overhead 原子窗口在已有可控IRQ Pending条件下的结果隔离。
#
# 测试方法：
# 1. 配置Float32、32-bit和Zero-Overhead，清除已有状态与IRQ Pending。
# 2. 通过公开CORDIC IRQ接口Force一个CALCULATION_COMPLETE Pending事件，记录基线快照。
# 3. 在Pending条件保持期间调用Zero-Overhead PHASE_MODULUS(1.0, 0.0)原子事务。
# 4. 读取结果、状态和IRQ快照，清除并禁用本Case产生的IRQ源。
# 5. 以独立Float32 Golden核对当前事务，Pending事件只作为干扰证据，不作为结果Golden。
#
# 通过条件：
# 1. Forced Pending不会改变PHASE_MODULUS的primary=0.0、secondary=1.0结果。
# 2. 当前合法事务不产生ARG_OVERFLOW或PM_ARG2_ERROR。
# 3. IRQ Pending可被精确清除，Case退出后不遗留CORDIC IRQ状态。
def test_cordic_p3_003_zero_overhead_pending_irq_isolation(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：当前Case只消费Zero-Overhead、Float32和IRQ Source公共语义。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    required_features = (
        CordicFeature.FLOAT32
        | CordicFeature.WIDTH_32
        | CordicFeature.ZERO_OVERHEAD
        | CordicFeature.INTERRUPTS
    )
    if support.runtime.features & required_features != required_features:
        pytest.skip("skip_by_runtime_capability: CORDIC atomic IRQ prerequisites unavailable")
    event = CordicIrqEvent.CALCULATION_COMPLETE
    if not support.runtime.irq_events & event:
        pytest.skip("skip_by_runtime_capability: CORDIC completion IRQ source is unavailable")

    # 配置：建立零开销会话并清理硬件状态/IRQ Pending。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            argument_width=CordicWidth.BITS_32,
            result_width=CordicWidth.BITS_32,
            phase_modulus_result_count=CordicResultCount.TWO,
            work_mode=CordicWorkMode.ZERO_OVERHEAD,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)
    support.cordic.irq_clear(event)
    support.cordic.irq_unmask(event)
    support.cordic.irq_enable(event)
    support.cordic.irq_mask(event)

    # 干扰：Force一个可控Pending事件，随后立即进入公开Zero-Overhead原子接口。
    baseline = support.cordic.irq_snapshot_get()
    support.cordic.irq_force(event)
    pending = support.cordic.irq_snapshot_get()
    result = support.cordic.zero_overhead_execute(
        CordicFunction.PHASE_MODULUS,
        (_float32_raw(1.0), _float32_raw(0.0)),
    )
    status = support.cordic.status_get()
    after = support.cordic.irq_snapshot_get()

    # 清理：只释放本Case拥有的CORDIC IRQ源和状态，不操作其他IP。
    support.cordic.status_clear(CordicStatus.ALL)
    support.cordic.irq_clear(event)
    support.cordic.irq_disable(event)
    support.cordic.irq_unmask(event)
    final = support.cordic.irq_snapshot_get()

    # 证据：保存Pending前后和最终清理快照，以及零开销事务Raw结果。
    record_property("baseline_event_count", baseline.event_count)
    record_property("pending_event_count", pending.event_count)
    record_observation(
        record_property,
        key="atomic_primary_raw",
        value=result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="atomic_secondary_raw",
        value=result.secondary_raw,
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    record_observation(
        record_property,
        key="forced_irq_pending",
        value=int(pending.raw),
        source="dut",
        endpoint="IRQ_RAW.CALCULATION_COMPLETE",
    )
    write_json_result(
        et_artifact_dir / "cordic_p3_003_zero_overhead_pending_irq_isolation.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p3_003",
            "pending_event": event.name,
            "baseline": {
                "raw": int(baseline.raw),
                "status": int(baseline.status),
                "event_count": baseline.event_count,
            },
            "pending": {
                "raw": int(pending.raw),
                "status": int(pending.status),
                "event_count": pending.event_count,
            },
            "actual": {
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
                "status": int(status),
                "after_raw": int(after.raw),
            },
            "final": {"raw": int(final.raw), "status": int(final.status)},
        },
    )

    # 断言：结果隔离、错误状态隔离和IRQ清理必须同时成立。
    assert pending.raw & event == event
    assert _within_cordic_budget(_float32_value(result.primary_raw), 0.0)
    assert _within_cordic_budget(_float32_value(result.secondary_raw), 1.0)
    assert status & (CordicStatus.ARG_OVERFLOW | CordicStatus.PM_ARG2_ERROR) == CordicStatus(0)
    assert final.raw & event == CordicIrqEvent(0)
    assert final.status & event == CordicIrqEvent(0)
