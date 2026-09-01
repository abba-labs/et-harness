# CORDIC P0 Formal Case。
#
# 职责：用独立数学 Golden 覆盖全部稳定数学函数入口和结果路径。
# 边界：只使用公共 CORDIC 数值语义和已审核误差预算，不包含芯片地址或 SDK 枚举。
# 依赖：CORDIC Driver、Runtime Capability 和公共证据工具。

from __future__ import annotations

import struct
from collections.abc import Callable
from pathlib import Path

import pytest

from ...drivers.cordic import (
    CordicConfig,
    CordicFeature,
    CordicFunction,
    CordicNumericMode,
    CordicResultCount,
    CordicStatus,
    CordicWidth,
    CordicWorkMode,
)
from ...drivers.crg import CrgPeripheral
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ._support import CordicSupportFactory, resolve_cordic_execution_semantics

pytestmark = [pytest.mark.hardware, pytest.mark.ip("cordic")]

_CORDIC_Q31_FRACTION_BITS = 31
_CORDIC_Q31_MAXIMUM = (1 << _CORDIC_Q31_FRACTION_BITS) - 1
# 历史 Unit/Functional/FPGA 参考测试共同采用 1e-4；这里将其冻结为公共 P0 绝对误差预算。
_CORDIC_P0_ABSOLUTE_TOLERANCE = 1.0e-4


# 把数学单位值编码为 CORDIC 32-bit Q1.31 Raw 字；边界 1.0 饱和到最大正值。
def _q31_raw(value: float) -> int:

    if value >= 1.0:
        return _CORDIC_Q31_MAXIMUM
    if value <= -1.0:
        return 1 << _CORDIC_Q31_FRACTION_BITS
    return int(round(value * (1 << _CORDIC_Q31_FRACTION_BITS))) & 0xFFFFFFFF


# 把公共 IEEE-754 Float32 数值转换为 CORDIC Driver 接受的原始字。
def _float32_raw(value: float) -> int:

    return struct.unpack("<I", struct.pack("<f", value))[0]


# 把硬件 Float32 Raw 解码为可与独立数学 Golden 比较的数值。
def _float32_value(raw: int) -> float:

    return struct.unpack("<f", struct.pack("<I", raw))[0]


# 把硬件 Q1.31 Raw 解码为有符号数值，避免对迭代近似结果做错误的逐位比较。
def _q31_value(raw: int) -> float:

    signed = raw if raw < (1 << 31) else raw - (1 << 32)
    return signed / float(1 << _CORDIC_Q31_FRACTION_BITS)


# 返回 CORDIC 数学结果是否满足已审核的公共绝对误差预算；最终断言仍由 Case 拥有。
def _within_p0_budget(actual: float, expected: float) -> bool:

    return abs(actual - expected) <= _CORDIC_P0_ABSOLUTE_TOLERANCE


# 测试 Feature：
# CORDIC Float32模式及九类数学函数的参数、完成状态和结果路径。
#
# 测试方法：
# 1. 为每类数学函数选择安全节点，并使用已审核的公共绝对误差预算判定结果。
# 2. 单参数函数提交一个参数；Phase/Modulus严格按x后y提交两个参数。
# 3. 每个函数独立配置、提交、等待COMPLETE、读取结果并清除状态。
#
# 通过条件：
# 1. Runtime声明的每类函数都在统一轮询上限内产生COMPLETE且没有错误状态。
# 2. 主结果与独立Float32 Golden的数值误差不超过预算，双结果函数也执行同一判定。
# 3. 每轮清除COMPLETE后状态归零，下一函数不会读取到上一轮残留。
@pytest.mark.parametrize(
    ("function", "arguments", "expected_primary", "expected_secondary"),
    (
        (CordicFunction.SINCOS, (0.0,), 1.0, 0.0),
        (CordicFunction.PHASE_MODULUS, (1.0, 0.0), 0.0, 1.0),
        (CordicFunction.ARCTAN, (0.0,), 0.0, None),
        (CordicFunction.HSINCOS, (0.0,), 1.0, 0.0),
        (CordicFunction.ATANH, (0.0,), 0.0, None),
        (CordicFunction.EXP, (0.0,), 1.0, None),
        (CordicFunction.LN, (1.0,), 0.0, None),
        (CordicFunction.SQRT, (1.0,), 1.0, None),
        (CordicFunction.TAN, (0.0,), 0.0, None),
    ),
    ids=lambda value: value.name.lower() if isinstance(value, CordicFunction) else None,
)
def test_cordic_p0_003_float32_function_matrix(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    function: CordicFunction,
    arguments: tuple[float, ...],
    expected_primary: float,
    expected_secondary: float | None,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：缺少某个数学函数是芯片能力差异，不得让其他函数覆盖冒充该Feature。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if function not in support.runtime.functions:
        pytest.skip(f"skip_by_runtime_capability: CORDIC function {function.name} is unavailable")

    # 配置：每个参数化节点都重建Float32 Polling状态并清除历史状态。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            work_mode=CordicWorkMode.POLLING,
            precision_cycles=support.runtime.maximum_precision_cycles,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：按当前函数的稳定参数顺序提交全部Float32 Raw参数。
    for argument in arguments:
        support.cordic.argument_submit(function, _float32_raw(argument))

    # 观测：由CORDIC Driver在统一Deadline内等待自然完成并保留查询次数。
    status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)

    result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    cleared = support.cordic.status_get()

    # 证据：记录函数身份、独立Golden、硬件Raw结果和完成状态。
    record_property("function", function.name)
    record_property("expected_primary_raw", _float32_raw(expected_primary))
    record_observation(
        record_property,
        key="actual_primary_raw",
        value=result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="actual_secondary_raw",
        value=result.secondary_raw,
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p0_003_float32_function_matrix.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p0_003",
            "function": function.name,
            "arguments": [_float32_raw(argument) for argument in arguments],
            "expected": {
                "primary_raw": _float32_raw(expected_primary),
                "secondary_raw": (
                    None if expected_secondary is None else _float32_raw(expected_secondary)
                ),
            },
            "actual": {
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
            },
            "status": {
                "before_clear": int(status),
                "after_clear": int(cleared),
                "poll_count": poll_count,
            },
        },
    )

    # 断言：数值结果满足公共误差预算，完成之外不得出现错误状态。
    assert _within_p0_budget(_float32_value(result.primary_raw), expected_primary)
    if expected_secondary is not None:
        assert _within_p0_budget(_float32_value(result.secondary_raw), expected_secondary)
    assert status & CordicStatus.COMPLETE
    assert status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert cleared & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC 外层 CRG 复位后的重新配置、状态隔离和数学运算恢复。
#
# 测试方法：
# 1. 配置 Float32、32-bit、Polling，执行复位前 SQRT(1.0) 基线并保存硬件结果。
# 2. 通过 CRG 专属 Driver/Service/Wrap 复位当前 CORDIC 实例，不让 CORDIC Wrap 跨 IP 访问 CRG。
# 3. 复位后重新配置并清除状态，执行相同数学函数，读取新的结果和完成状态。
# 4. 对比复位前后 Raw 结果、完成状态及清除后的状态，确认复位没有残留旧会话状态。
#
# 通过条件：
# 1. 复位前后两次 SQRT(1.0) 都返回 Float32 1.0 并产生 COMPLETE。
# 2. 复位后必须重新配置即可完成运算，不依赖复位前的客户端缓存状态。
# 3. 两轮清除后的 COMPLETE 都为零，且复位动作通过 CRG 专属接口完成。
def test_cordic_p0_004_reset_reconfigure_and_recovery(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    crg_driver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 能力门禁：当前恢复向量只要求稳定的 Float32、32-bit、Polling 和 SQRT 函数。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    required_features = CordicFeature.FLOAT32 | CordicFeature.WIDTH_32 | CordicFeature.POLLING
    if support.runtime.features & required_features != required_features:
        pytest.skip("skip_by_runtime_capability: CORDIC reset recovery prerequisites unavailable")
    if CordicFunction.SQRT not in support.runtime.functions:
        pytest.skip("skip_by_runtime_capability: CORDIC SQRT is unavailable")

    # 配置：建立复位前的独立 Float32、32-bit、Polling 会话并清理旧状态。
    config = CordicConfig(
        numeric_mode=CordicNumericMode.FLOAT32,
        argument_width=CordicWidth.BITS_32,
        result_width=CordicWidth.BITS_32,
        work_mode=CordicWorkMode.POLLING,
        precision_cycles=support.runtime.maximum_precision_cycles,
    )
    support.cordic.configure(config)
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：复位前执行可精确表示的 SQRT(1.0) 基线事务。
    support.cordic.argument_submit(CordicFunction.SQRT, _float32_raw(1.0))
    before_status, _ = support.cordic.wait_status(CordicStatus.COMPLETE)
    before_result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.ALL)
    before_cleared = support.cordic.status_get()

    # 复位：复位动作由 CRG 专属 PC Driver/Service/Wrap 执行，不跨层调用 CORDIC Wrap。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)

    # 复位后配置：重新提交完整配置，避免把 Driver 的 configured 缓存当作硬件状态。
    support.cordic.configure(config)
    support.cordic.status_clear(CordicStatus.ALL)

    # 复位后激励与观测：再次执行同一确定性向量，读取本轮硬件结果和完成状态。
    support.cordic.argument_submit(CordicFunction.SQRT, _float32_raw(1.0))
    after_status, _ = support.cordic.wait_status(CordicStatus.COMPLETE)
    after_result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.ALL)
    after_cleared = support.cordic.status_get()

    # 证据：保存复位前后 Raw 结果、状态快照和清除后的终态。
    record_property("expected_recovery_raw", _float32_raw(1.0))
    record_observation(
        record_property,
        key="pre_reset_result",
        value=before_result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="post_reset_result",
        value=after_result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="post_reset_status",
        value=int(after_status),
        source="dut",
        endpoint="STATUS.COMPLETE",
    )
    write_json_result(
        et_artifact_dir / "cordic_p0_004_reset_reconfigure_and_recovery.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p0_004",
            "expected_primary_raw": _float32_raw(1.0),
            "before_reset": {
                "primary_raw": before_result.primary_raw,
                "status": int(before_status),
                "after_clear": int(before_cleared),
            },
            "after_reset": {
                "primary_raw": after_result.primary_raw,
                "status": int(after_status),
                "after_clear": int(after_cleared),
            },
        },
    )

    # 断言：复位前后结果满足同一误差预算、状态完成且清理后没有残留。
    assert _within_p0_budget(_float32_value(before_result.primary_raw), 1.0)
    assert _within_p0_budget(_float32_value(after_result.primary_raw), 1.0)
    assert before_status == CordicStatus.COMPLETE
    assert after_status == CordicStatus.COMPLETE
    assert before_cleared == CordicStatus(0)
    assert after_cleared == CordicStatus(0)


# 测试 Feature：
# CORDIC Fixed 模式、九类数学函数及其公开定点缩放语义。
#
# 测试方法：
# 1. 使用目标Capability与芯片执行映射已经闭合的安全输入域，不在公共Case写死Codec。
# 2. 按函数配置Scale，并用映射提供的补偿因子把硬件定点结果还原为数学值。
# 3. 等待 COMPLETE，读取主/次结果和状态，清除状态后再执行下一个函数节点。
#
# 通过条件：
# 1. 九类函数都在有界轮询内完成，并且只产生 COMPLETE 状态。
# 2. 每个补偿后的数学结果满足公共误差预算，双结果函数同时检查两个结果。
# 3. 每个节点清除 COMPLETE 后状态归零，不把前一个函数的结果或状态带入下一节点。
@pytest.mark.parametrize("function", tuple(CordicFunction), ids=lambda value: value.name.lower())
def test_cordic_p0_002_fixed_function_matrix(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    function: CordicFunction,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：缺少 Fixed 或目标函数时，只跳过当前能力节点，不由其他函数冒充覆盖。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if not (support.runtime.features & CordicFeature.FIXED):
        pytest.skip("skip_by_runtime_capability: CORDIC Fixed mode is unavailable")
    if function not in support.runtime.functions:
        pytest.skip(f"skip_by_runtime_capability: CORDIC function {function.name} is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    vector = semantics.fixed_vectors[function]
    fraction_bits = semantics.fixed_fraction_bits[32]

    def fixed_raw(value: float) -> int:
        maximum = (1 << fraction_bits) - 1
        if value >= 1.0:
            return maximum
        if value <= -1.0:
            return 1 << fraction_bits
        return int(round(value * (1 << fraction_bits))) & 0xFFFFFFFF

    def fixed_value(raw: int) -> float:
        signed = raw if raw < (1 << fraction_bits) else raw - (1 << (fraction_bits + 1))
        return signed / float(1 << fraction_bits)

    # 配置：建立当前函数独立的Fixed、32-bit Polling会话。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FIXED,
            argument_width=CordicWidth.BITS_32,
            result_width=CordicWidth.BITS_32,
            scale=vector.scale,
            work_mode=CordicWorkMode.POLLING,
            precision_cycles=support.runtime.maximum_precision_cycles,
            sincos_result_count=CordicResultCount.TWO,
            phase_modulus_result_count=CordicResultCount.TWO,
            hsincos_result_count=CordicResultCount.TWO,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：严格按当前函数参数顺序提交由执行映射编码的Raw输入。
    for argument in vector.arguments:
        support.cordic.argument_submit(function, fixed_raw(argument))

    # 观测：等待硬件完成并读取当前事务的两个 Raw 结果。
    status, _ = support.cordic.wait_status(CordicStatus.COMPLETE)
    result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    cleared = support.cordic.status_get()

    # 证据：记录函数专用 Scale/补偿、独立数学 Golden、DUT Raw 结果和完成状态。
    record_property("function", function.name)
    record_property("scale", vector.scale)
    record_property("primary_compensation", vector.primary_compensation)
    record_property(
        "expected_primary_raw",
        fixed_raw(vector.expected_primary / vector.primary_compensation),
    )
    record_observation(
        record_property,
        key="actual_primary_raw",
        value=result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="actual_secondary_raw",
        value=result.secondary_raw,
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p0_002_fixed_function_matrix.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p0_002",
            "function": function.name,
            "arguments": [fixed_raw(argument) for argument in vector.arguments],
            "configuration": {
                "scale": vector.scale,
                "primary_compensation": vector.primary_compensation,
                "secondary_compensation": vector.secondary_compensation,
            },
            "expected": {
                "primary_value": vector.expected_primary,
                "secondary_value": vector.expected_secondary,
            },
            "actual": {
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
            },
            "status": {"before_clear": int(status), "after_clear": int(cleared)},
        },
    )

    # 断言：按函数语义补偿后的定点结果满足公共误差预算，状态闭环同时成立。
    assert (
        abs(fixed_value(result.primary_raw) * vector.primary_compensation - vector.expected_primary)
        <= semantics.absolute_tolerance
    )
    if vector.expected_secondary is not None:
        assert (
            abs(
                fixed_value(result.secondary_raw) * vector.secondary_compensation
                - vector.expected_secondary
            )
            <= semantics.absolute_tolerance
        )
    assert status & CordicStatus.COMPLETE
    assert status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert cleared & CordicStatus.COMPLETE == CordicStatus(0)
