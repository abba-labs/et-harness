# CORDIC P1 Formal Case。
#
# 职责：验证 CORDIC IRQ Enable/Disable、Force、Mask/Unmask 和精确 Clear 语义。
# 边界：Case 直接编排稳定 Driver；不包含芯片事实、不把 Force 冒充自然事件。
# 依赖：CORDIC Support、公共清理/证据工具和 pytest。

from __future__ import annotations

import math
import struct
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.cordic import (
    CordicConfig,
    CordicConversionStatus,
    CordicFeature,
    CordicFunction,
    CordicInputRange,
    CordicIrqEvent,
    CordicNumericMode,
    CordicResultCount,
    CordicStatus,
    CordicWidth,
    CordicWorkMode,
)
from ...drivers.crg import CrgDriver, CrgPeripheral
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    CordicSupportFactory,
    require_cordic_runtime_irq_capability,
    require_cordic_static_irq_capability,
    resolve_cordic_execution_semantics,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("cordic")]

_CORDIC_SCALE_NODES = (0, 7)
_CORDIC_ABSOLUTE_TOLERANCE = 1.0e-4
_CORDIC_Q31_FRACTION_BITS = 31


# 把公共 IEEE-754 Float32 数值转换为 CORDIC Driver 接受的原始字。
def _float32_raw(value: float) -> int:

    return struct.unpack("<I", struct.pack("<f", value))[0]


# 把硬件 Float32 Raw 解码为数学值；CORDIC 近似结果不得按 Raw 逐位相等判定。
def _float32_value(raw: int) -> float:

    return struct.unpack("<f", struct.pack("<I", raw))[0]


# 把数学值编码为饱和 Q1.31 Raw 字，供 Fixed Range 与宽度 Case 使用。
def _q31_raw(value: float) -> int:

    if value >= 1.0:
        return (1 << _CORDIC_Q31_FRACTION_BITS) - 1
    if value <= -1.0:
        return 1 << _CORDIC_Q31_FRACTION_BITS
    return int(round(value * (1 << _CORDIC_Q31_FRACTION_BITS))) & 0xFFFFFFFF


# 把 Q1.31 Raw 解码为有符号数学值。
def _q31_value(raw: int) -> float:

    signed = raw if raw < (1 << 31) else raw - (1 << 32)
    return signed / float(1 << _CORDIC_Q31_FRACTION_BITS)


# 按执行映射声明的小数位解码有符号定点Raw；Case不在此猜测芯片格式。
def _signed_fixed_value(raw: int, fraction_bits: int) -> float:

    signed = raw if raw < (1 << fraction_bits) else raw - (1 << (fraction_bits + 1))
    return signed / float(1 << fraction_bits)


# 判断 CORDIC 近似数学结果是否满足历史验证共同采用的绝对误差预算。
def _within_cordic_budget(actual: float, expected: float) -> bool:

    return abs(actual - expected) <= _CORDIC_ABSOLUTE_TOLERANCE


# 测试 Feature：
# CORDIC三类双结果函数的单结果/双结果配置与已声明结果路径。
#
# 测试方法：
# 1. 分别选择SINCOS、PHASE_MODULUS和HSINCOS，每类函数执行ONE与TWO两种结果数量配置。
# 2. 使用结果可精确表示的Float32节点，按函数参数数量提交并等待COMPLETE。
# 3. ONE模式只判断已声明主结果；TWO模式同时判断主结果和第二结果，数学值使用CORDIC误差预算。
#
# 通过条件：
# 1. 六个配置节点均自然完成且没有CORDIC错误状态。
# 2. ONE/TWO模式的主结果一致；TWO模式第二结果与独立Float32 Golden一致。
# 3. 每轮COMPLETE清除后下一配置可独立运行。
@pytest.mark.parametrize(
    ("function", "arguments", "expected_primary", "expected_secondary", "result_count"),
    (
        (CordicFunction.SINCOS, (0.0,), 1.0, 0.0, CordicResultCount.ONE),
        (CordicFunction.SINCOS, (0.0,), 1.0, 0.0, CordicResultCount.TWO),
        (CordicFunction.PHASE_MODULUS, (1.0, 0.0), 0.0, 1.0, CordicResultCount.ONE),
        (CordicFunction.PHASE_MODULUS, (1.0, 0.0), 0.0, 1.0, CordicResultCount.TWO),
        (CordicFunction.HSINCOS, (0.0,), 1.0, 0.0, CordicResultCount.ONE),
        (CordicFunction.HSINCOS, (0.0,), 1.0, 0.0, CordicResultCount.TWO),
    ),
    ids=lambda value: (
        value.name.lower() if isinstance(value, (CordicFunction, CordicResultCount)) else None
    ),
)
def test_cordic_p1_005_result_count_paths(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    function: CordicFunction,
    arguments: tuple[float, ...],
    expected_primary: float,
    expected_secondary: float,
    result_count: CordicResultCount,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 配置：仅修改当前函数对应的结果数量字段，其他双结果函数保持TWO。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    config_values = {
        "sincos_result_count": CordicResultCount.TWO,
        "phase_modulus_result_count": CordicResultCount.TWO,
        "hsincos_result_count": CordicResultCount.TWO,
    }
    config_field = {
        CordicFunction.SINCOS: "sincos_result_count",
        CordicFunction.PHASE_MODULUS: "phase_modulus_result_count",
        CordicFunction.HSINCOS: "hsincos_result_count",
    }[function]
    config_values[config_field] = result_count
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            work_mode=CordicWorkMode.POLLING,
            **config_values,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：按当前函数稳定顺序提交一个或两个Float32参数。
    for argument in arguments:
        support.cordic.argument_submit(function, _float32_raw(argument))

    # 观测：等待自然完成并读取公共结果端点。
    status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
    result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    cleared = support.cordic.status_get()

    # 证据：明确记录函数、结果数量和当前声明的硬件结果。
    record_property("function", function.name)
    record_property("result_count", result_count.name)
    record_observation(
        record_property,
        key="primary_raw",
        value=result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="secondary_raw",
        value=result.secondary_raw,
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    write_json_result(
        et_artifact_dir
        / (
            "cordic_p1_005_result_count_paths_"
            f"{function.name.lower()}_{result_count.name.lower()}.json"
        ),
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_005",
            "configuration": {"function": function.name, "result_count": result_count.name},
            "expected": {
                "primary_raw": _float32_raw(expected_primary),
                "secondary_raw": _float32_raw(expected_secondary),
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

    # 断言：ONE和TWO都必须给出满足CORDIC预算的主结果；只有TWO要求第二结果。
    assert _within_cordic_budget(_float32_value(result.primary_raw), expected_primary)
    if result_count is CordicResultCount.TWO:
        assert _within_cordic_budget(_float32_value(result.secondary_raw), expected_secondary)
    assert status & CordicStatus.COMPLETE
    assert status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert cleared & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC Phase/Modulus双参数顺序、当前参数计数和结果消费后恢复。
#
# 测试方法：
# 1. 配置Float32 Polling路径并确认事务开始前ARG_COUNT.CURRENT为0。
# 2. 按x后y顺序提交Phase/Modulus参数，分别读取第一参数后和完成后的参数计数。
# 3. 读取phase/modulus结果并清除COMPLETE，再执行单参数SQRT确认后续事务恢复。
#
# 通过条件：
# 1. ARG_COUNT.CURRENT按0→1→0变化，证明双参数事务阶段清晰。
# 2. Phase/Modulus(1,0)返回phase=0、modulus=1且没有PM_ARG2_ERROR。
# 3. 结果消费后SQRT事务可独立完成，不继承前一事务参数状态。
def test_cordic_p1_006_phase_modulus_argument_count(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 配置：建立无历史状态的Float32 Polling会话。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    config = CordicConfig(
        numeric_mode=CordicNumericMode.FLOAT32,
        work_mode=CordicWorkMode.POLLING,
    )
    support.cordic.configure(config)
    support.cordic.status_clear(CordicStatus.ALL)
    initial_count = support.cordic.argument_count_get()

    # 双参数激励：提交x后读取等待阶段，再提交y并等待自然完成。
    support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _float32_raw(1.0))
    after_x_count = support.cordic.argument_count_get()
    support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _float32_raw(0.0))
    pm_status, pm_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    after_y_count = support.cordic.argument_count_get()
    pm_result = support.cordic.result_get()
    after_result_count = support.cordic.argument_count_get()

    # 恢复激励：清除完成状态后执行一个可区分的单参数事务。
    support.cordic.status_clear(CordicStatus.COMPLETE)
    support.cordic.argument_submit(CordicFunction.SQRT, _float32_raw(0.25))
    recovery_status, recovery_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    recovery_result = support.cordic.result_get()
    recovery_count = support.cordic.argument_count_get()

    # 证据：记录参数计数时间线、双参数结果与恢复结果。
    record_observation(
        record_property,
        key="argument_count_sequence",
        value=[initial_count, after_x_count, after_y_count, after_result_count, recovery_count],
        source="dut",
        endpoint="ARG_COUNT.CURRENT",
    )
    record_property("pm_poll_count", pm_polls)
    record_property("recovery_poll_count", recovery_polls)
    write_json_result(
        et_artifact_dir / "cordic_p1_006_phase_modulus_argument_count.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_006",
            "argument_counts": {
                "initial": initial_count,
                "after_x": after_x_count,
                "after_y": after_y_count,
                "after_result": after_result_count,
                "recovery": recovery_count,
            },
            "phase_modulus": {
                "status": int(pm_status),
                "primary_raw": pm_result.primary_raw,
                "secondary_raw": pm_result.secondary_raw,
            },
            "recovery": {
                "status": int(recovery_status),
                "primary_raw": recovery_result.primary_raw,
            },
        },
    )

    # 断言：参数计数必须体现完整0→1→0生命周期。
    assert initial_count == 0
    assert after_x_count == 1
    assert after_y_count == 0
    assert after_result_count == 0
    assert recovery_count == 0

    # 断言：双参数结果正确且恢复事务不携带参数顺序错误。
    assert pm_status & CordicStatus.COMPLETE
    assert pm_status & CordicStatus.PM_ARG2_ERROR == CordicStatus(0)
    assert _within_cordic_budget(_float32_value(pm_result.primary_raw), 0.0)
    assert _within_cordic_budget(_float32_value(pm_result.secondary_raw), 1.0)
    assert recovery_status & CordicStatus.COMPLETE
    assert _within_cordic_budget(_float32_value(recovery_result.primary_raw), 0.5)


# 测试 Feature：
# CORDIC Polling 工作模式、自然完成状态与 COMPLETE 精确 W1C。
#
# 测试方法：
# 1. 使用 Float32 精确向量分别执行单参数 SQRT 和双参数 Phase/Modulus。
# 2. 每个事务通过有界状态轮询等待 COMPLETE，并读取硬件 Raw 结果。
# 3. 对 COMPLETE 执行精确 Clear，确认下一事务从无残留状态开始。
#
# 通过条件：
# 1. 两个事务都在统一轮询上限内自然产生 COMPLETE。
# 2. SQRT(0.25) 与 Phase/Modulus(1,0) 返回精确 Float32 Raw 结果。
# 3. 每次 Clear 后 COMPLETE 均恢复为零，且不出现其他错误状态。
def test_cordic_p1_007_polling_completion_and_w1c(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 配置：选择公开的 Float32、32-bit 与 Polling 路径。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            work_mode=CordicWorkMode.POLLING,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 单参数刺激：执行 SQRT(0.25)，等待自然完成并读取结果。
    support.cordic.argument_submit(CordicFunction.SQRT, _float32_raw(0.25))
    sqrt_status, sqrt_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    sqrt_result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    sqrt_cleared = support.cordic.status_get()

    # 双参数刺激：按 x=1、y=0 顺序执行 Phase/Modulus。
    support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _float32_raw(1.0))
    support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _float32_raw(0.0))
    pm_status, pm_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    pm_result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    pm_cleared = support.cordic.status_get()

    # 证据：记录两种参数路径的 Raw 结果、轮询次数和 W1C 状态变化。
    record_property("expected_polling_results", "sqrt=0.5; phase=0.0; modulus=1.0")
    record_property("sqrt_poll_count", sqrt_polls)
    record_property("pm_poll_count", pm_polls)
    record_observation(
        record_property,
        key="complete_after_clear",
        value=int(pm_cleared & CordicStatus.COMPLETE),
        source="dut",
        endpoint="STATUS.COMPLETE",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_007_polling_completion_and_w1c.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_007",
            "sqrt": {
                "primary_raw": sqrt_result.primary_raw,
                "status_before_clear": int(sqrt_status),
                "status_after_clear": int(sqrt_cleared),
                "poll_count": sqrt_polls,
            },
            "phase_modulus": {
                "primary_raw": pm_result.primary_raw,
                "secondary_raw": pm_result.secondary_raw,
                "status_before_clear": int(pm_status),
                "status_after_clear": int(pm_cleared),
                "poll_count": pm_polls,
            },
        },
    )

    # 断言：精确向量、自然完成和 W1C 三条证据必须同时成立。
    assert _within_cordic_budget(_float32_value(sqrt_result.primary_raw), 0.5)
    assert _within_cordic_budget(_float32_value(pm_result.primary_raw), 0.0)
    assert _within_cordic_budget(_float32_value(pm_result.secondary_raw), 1.0)
    assert sqrt_status & CordicStatus.COMPLETE
    assert pm_status & CordicStatus.COMPLETE
    assert sqrt_status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert pm_status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert sqrt_cleared & CordicStatus.COMPLETE == CordicStatus(0)
    assert pm_cleared & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC Interrupt 工作模式、自然完成 IRQ Source 与真实 CPU Delivery。
#
# 测试方法：
# 1. 清除 CALCULATION_COMPLETE 历史状态并建立 Enable+Unmask IRQ 会话。
# 2. 执行 SQRT(0.25)，不使用 Force，有界等待 Service Event Count 增加。
# 3. 读取结果、硬件状态和 ISR Latch，随后精确清理目标 Source。
#
# 通过条件：
# 1. 自然计算使 Event Count 恰好增加一次，Last Event 指向 CALCULATION_COMPLETE。
# 2. STATUS.COMPLETE 置位且结果为 Float32 0.5。
# 3. Case 结束时目标 IRQ 和 COMPLETE 状态均被清除。
def test_cordic_p1_008_interrupt_mode_natural_completion(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：静态与 Runtime 都必须声明自然完成 IRQ Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    event = CordicIrqEvent.CALCULATION_COMPLETE
    require_cordic_static_irq_capability(
        target_capabilities,
        instance_id=cordic_instance_id,
        event=event,
    )
    require_cordic_runtime_irq_capability(support.runtime, event)
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("CORDIC complete status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
            ("CORDIC IRQ source disable", lambda: support.cordic.irq_disable(event)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(event)),
            ("CORDIC IRQ source unmask", lambda: support.cordic.irq_unmask(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立无历史状态的 Interrupt 会话。
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FLOAT32,
                work_mode=CordicWorkMode.INTERRUPT,
            )
        )
        configured = True
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.irq_clear(event)
        support.cordic.irq_unmask(event)
        support.cordic.irq_enable(event)
        baseline = support.cordic.irq_snapshot_get()

        # 刺激：执行真实运算并等待 ISR 交付，不调用软件 Force。
        support.cordic.argument_submit(CordicFunction.SQRT, _float32_raw(0.25))
        delivered = support.cordic.wait_irq(
            event,
            minimum_event_count=baseline.event_count + 1,
        )
        status = support.cordic.status_get()
        result = support.cordic.result_get()

        # 证据：分开记录硬件状态和 Service ISR Latch。
        record_property("expected_irq_source", event.name)
        record_property("event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="complete_status",
            value=bool(status & CordicStatus.COMPLETE),
            source="dut",
            endpoint="STATUS.COMPLETE",
        )
        record_observation(
            record_property,
            key="irq_delivery",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )
        write_json_result(
            et_artifact_dir / "cordic_p1_008_interrupt_mode_natural_completion.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_008",
                "expected_primary_raw": _float32_raw(0.5),
                "actual_primary_raw": result.primary_raw,
                "status": int(status),
                "irq": {
                    "event_count_before": baseline.event_count,
                    "event_count_after": delivered.event_count,
                    "raw": int(delivered.raw),
                    "status": int(delivered.status),
                    "last_event": int(delivered.last_event),
                    "last_raw": int(delivered.last_raw),
                },
            },
        )

        # 断言：自然硬件事件、Service交付和数学结果必须一致。
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw & event == event
        assert status & CordicStatus.COMPLETE
        assert _within_cordic_budget(_float32_value(result.primary_raw), 0.5)


# 测试 Feature：
# CORDIC Zero-Overhead 原子请求与连续结果归属。
#
# 测试方法：
# 1. 配置 Zero-Overhead 模式，通过单条命令执行 SQRT(0.25)。
# 2. 随后通过另一条独立命令执行 Phase/Modulus(1,0)。
# 3. 用两组可区分的精确 Raw Golden 检查当前请求结果未读取到前一事务。
#
# 通过条件：
# 1. SQRT 请求返回 Float32 0.5。
# 2. Phase/Modulus 请求返回 Float32 0.0 和 1.0。
# 3. 两个请求均由独立响应返回，不依赖固定等待或额外结果读取。
def test_cordic_p1_009_zero_overhead_atomic_requests(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 配置：只选择 Runtime 已声明的 Zero-Overhead 和 Float32 路径。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            work_mode=CordicWorkMode.ZERO_OVERHEAD,
        )
    )

    # 刺激：执行两个参数数量不同且结果可区分的原子请求。
    sqrt_result = support.cordic.zero_overhead_execute(
        CordicFunction.SQRT,
        (_float32_raw(0.25),),
    )
    pm_result = support.cordic.zero_overhead_execute(
        CordicFunction.PHASE_MODULUS,
        (_float32_raw(1.0), _float32_raw(0.0)),
    )

    # 证据：保留每个请求的独立 Raw 结果，便于定位串包或旧结果残留。
    record_property("expected_zero_overhead_sequence", "sqrt=0.5; phase=0.0; modulus=1.0")
    record_observation(
        record_property,
        key="sqrt_primary_raw",
        value=sqrt_result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_009_zero_overhead_atomic_requests.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_009",
            "sqrt": {
                "primary_raw": sqrt_result.primary_raw,
                "secondary_raw": sqrt_result.secondary_raw,
            },
            "phase_modulus": {
                "primary_raw": pm_result.primary_raw,
                "secondary_raw": pm_result.secondary_raw,
            },
        },
    )

    # 断言：每条原子响应只对应自己的数学结果，并满足统一CORDIC误差预算。
    assert _within_cordic_budget(_float32_value(sqrt_result.primary_raw), 0.5)
    assert _within_cordic_budget(_float32_value(pm_result.primary_raw), 0.0)
    assert _within_cordic_budget(_float32_value(pm_result.secondary_raw), 1.0)


# 测试 Feature：
# CORDIC PM_ARG2_ERROR 状态、自然 IRQ Source、真实 CPU Delivery 与恢复。
#
# 测试方法：
# 1. 为 PM_ARG2_ERROR 建立 Enable+Unmask 会话并记录 Event Count 基线。
# 2. 通过错误的第二参数来源自然触发状态，不调用软件 Force。
# 3. 核对硬件状态、ISR Latch和Event Count，清报告位后通过CRG复位恢复合法事务。
#
# 通过条件：
# 1. PM_ARG2_ERROR 状态置位且 Event Count 恰好增加一次。
# 2. Last Event 和 Last Raw 均指向 PM_ARG2_ERROR。
# 3. 状态与Raw清除、模块复位后可重新执行合法Phase/Modulus，不保留错误状态。
def test_cordic_p1_016_pm_arg2_error_natural_irq(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    crg_driver: CrgDriver,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 准备：静态和 Runtime 能力必须共同声明目标 Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    event = CordicIrqEvent.PM_ARG2_ERROR
    require_cordic_static_irq_capability(
        target_capabilities,
        instance_id=cordic_instance_id,
        event=event,
    )
    require_cordic_runtime_irq_capability(support.runtime, event)
    configured = False
    reset_completed = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        actions: list[CleanupAction] = [
            ("CORDIC IRQ source disable", lambda: support.cordic.irq_disable(event)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(event)),
            ("CORDIC IRQ source unmask", lambda: support.cordic.irq_unmask(event)),
            ("CORDIC status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
        ]
        if not reset_completed:
            actions.append(
                (
                    "CORDIC module reset",
                    lambda: crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：使用目标芯片适配资料已闭合的Fixed Zero-Overhead自然错误路径。
        config = CordicConfig(
            numeric_mode=CordicNumericMode.FIXED,
            work_mode=CordicWorkMode.ZERO_OVERHEAD,
            phase_modulus_result_count=CordicResultCount.TWO,
        )
        support.cordic.configure(config)
        configured = True
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.irq_clear(event)
        support.cordic.irq_unmask(event)
        support.cordic.irq_enable(event)
        baseline = support.cordic.irq_snapshot_get()

        # 刺激：用错误第二参数来源自然触发目标 Source。
        support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _q31_raw(0.5))
        waiting_count = support.cordic.argument_count_get()
        support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.5))
        delivered = support.cordic.wait_irq(
            event,
            minimum_event_count=baseline.event_count + 1,
        )
        error_status = support.cordic.status_get()

        # 恢复：清除错误状态和IRQ Raw，并读取错误来源函数产生的结果。
        support.cordic.status_clear(CordicStatus.PM_ARG2_ERROR)
        support.cordic.irq_clear(event)
        discarded_result = support.cordic.result_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)
        support.cordic.status_clear(CordicStatus.ALL)
        cleared_status = support.cordic.status_get()

        # 恢复：W1C只清报告位；通过CRG复位清除错误序列留下的内部事务状态。
        crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
        reset_completed = True

        # 再验证：复位后切回Polling并执行一笔全新的双参数PM事务。
        recovery_config = CordicConfig(
            numeric_mode=CordicNumericMode.FIXED,
            work_mode=CordicWorkMode.POLLING,
            phase_modulus_result_count=CordicResultCount.TWO,
        )
        support.cordic.configure(recovery_config)
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _q31_raw(0.5))
        support.cordic.argument_submit(CordicFunction.PHASE_MODULUS, _q31_raw(0.0))
        support.cordic.wait_status(CordicStatus.COMPLETE)
        recovery_result = support.cordic.result_get()
        recovery_status = support.cordic.status_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)

        # 证据：保存自然错误、真实投递与恢复结果。
        record_property("expected_arg2_error", True)
        record_property("expected_irq_source", event.name)
        record_property("event_count_delta", delivered.event_count - baseline.event_count)
        record_property("recovery_method", "crg_module_reset")
        record_observation(
            record_property,
            key="waiting_argument_count",
            value=waiting_count,
            source="dut",
            endpoint="ARG_COUNT.CURRENT",
        )
        record_observation(
            record_property,
            key="arg2_error_status",
            value=bool(error_status & CordicStatus.PM_ARG2_ERROR),
            source="dut",
            endpoint="STATUS.PM_ARG2_ERROR",
        )
        record_observation(
            record_property,
            key="irq_delivery",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )
        write_json_result(
            et_artifact_dir / "cordic_p1_016_pm_arg2_error_natural_irq.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_016",
                "error_status": int(error_status),
                "cleared_status": int(cleared_status),
                "waiting_argument_count": waiting_count,
                "discarded_result": {
                    "primary_raw": discarded_result.primary_raw,
                    "secondary_raw": discarded_result.secondary_raw,
                },
                "irq": {
                    "event_count_before": baseline.event_count,
                    "event_count_after": delivered.event_count,
                    "last_event": int(delivered.last_event),
                    "last_raw": int(delivered.last_raw),
                },
                "recovery": {
                    "method": "crg_module_reset",
                    "status": int(recovery_status),
                    "primary_raw": recovery_result.primary_raw,
                    "secondary_raw": recovery_result.secondary_raw,
                },
            },
        )

        # 断言：自然错误、IRQ交付和恢复三段都必须成立。
        assert error_status & CordicStatus.PM_ARG2_ERROR
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw & event == event
        assert cleared_status & CordicStatus.PM_ARG2_ERROR == CordicStatus(0)
        assert recovery_status & CordicStatus.PM_ARG2_ERROR == CordicStatus(0)
        assert _within_cordic_budget(_q31_value(recovery_result.primary_raw), 0.0)
        assert _within_cordic_budget(_q31_value(recovery_result.secondary_raw), 0.5)


# 测试 Feature：
# CORDIC 连续异构请求切换与结果边界。
#
# 测试方法：
# 1. 在同一实例上依次执行 SQRT、EXP、LN、ARCTAN 和 TAN 五种单参数函数。
# 2. 每次都等待自然完成、立即读取结果并清除 COMPLETE。
# 3. 使用独立数学Golden和统一CORDIC误差预算检查当前结果属于当前请求，不残留上一函数结果。
#
# 通过条件：
# 1. 五种函数均在统一轮询上限内完成且没有错误状态。
# 2. 各结果分别为 sqrt(0.25)=0.5、exp(0)=1、ln(1)=0、atan(0)=0、tan(0)=0。
# 3. 每次 Clear 后下一请求均能独立完成。
def test_cordic_p1_020_sequential_request_boundaries(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 配置：使用无需芯片专用定点 Codec 的 Float32 Polling 路径。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FLOAT32,
            work_mode=CordicWorkMode.POLLING,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 输入矩阵：每个函数选择能产生精确 Float32 Golden 的安全节点。
    requests = (
        (CordicFunction.SQRT, 0.25, 0.5),
        (CordicFunction.EXP, 0.0, 1.0),
        (CordicFunction.LN, 1.0, 0.0),
        (CordicFunction.ARCTAN, 0.0, 0.0),
        (CordicFunction.TAN, 0.0, 0.0),
    )
    observations: list[dict[str, int | float | str]] = []

    # 执行：逐请求提交、等待、读取并清理，保持边界清晰。
    for function, argument, expected in requests:
        support.cordic.argument_submit(function, _float32_raw(argument))
        status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
        result = support.cordic.result_get()
        observations.append(
            {
                "function": function.name,
                "expected_raw": _float32_raw(expected),
                "actual_raw": result.primary_raw,
                "expected_value": expected,
                "actual_value": _float32_value(result.primary_raw),
                "status": int(status),
                "poll_count": poll_count,
            }
        )
        support.cordic.status_clear(CordicStatus.COMPLETE)

    # 证据：保留请求顺序和每个请求的独立硬件结果。
    record_property("expected_request_count", len(requests))
    record_property("actual_request_count", len(observations))
    write_json_result(
        et_artifact_dir / "cordic_p1_020_sequential_request_boundaries.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_020",
            "requests": observations,
        },
    )

    # 断言：每个请求的结果、完成状态和清理边界都必须独立成立。
    assert len(observations) == len(requests)
    assert all(
        _within_cordic_budget(float(item["actual_value"]), float(item["expected_value"]))
        for item in observations
    )
    assert all(int(item["status"]) & int(CordicStatus.COMPLETE) for item in observations)
    assert support.cordic.status_get() & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC IRQ Source Enable/Disable、软件 Force 与真实 CPU Delivery。
#
# 测试方法：
# 1. 参数化全部稳定 IRQ Source，在 Enable+Unmask 状态下 Force 一次。
# 2. 读取 ISR Event Count、Last Event、Raw/Status，证明 Force 到达目标 Source。
# 3. Clear并Disable同一Source后再次Force，确认Raw可保留但不再产生CPU Delivery。
#
# 通过条件：
# 1. Enable阶段 Event Count 恰好增加一次，Last Event/Last Raw只包含当前Source。
# 2. Disable阶段再次Force后 Event Count 不增加，目标Source不形成有效Status。
# 3. 每个参数分支结束后清除Pending、解除Mask并关闭Source。
@pytest.mark.parametrize(
    "event",
    (
        CordicIrqEvent.ARG_OVERFLOW,
        CordicIrqEvent.CALCULATION_COMPLETE,
        CordicIrqEvent.PM_ARG2_ERROR,
    ),
)
def test_cordic_p1_017_irq_force_enable_disable(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    event: CordicIrqEvent,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只使用当前静态和Runtime都声明的Source，并选择IRQ工作模式。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    require_cordic_static_irq_capability(
        target_capabilities,
        instance_id=cordic_instance_id,
        event=event,
    )
    require_cordic_runtime_irq_capability(support.runtime, event)
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("CORDIC IRQ sources disable", lambda: support.cordic.irq_disable(event)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(event)),
            ("CORDIC IRQ sources unmask", lambda: support.cordic.irq_unmask(event)),
            ("CORDIC status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立无历史Pending的单Source IRQ会话。
        support.cordic.configure(CordicConfig(work_mode=CordicWorkMode.INTERRUPT))
        configured = True
        support.cordic.irq_clear(event)
        support.cordic.irq_unmask(event)
        support.cordic.irq_enable(event)
        before = support.cordic.irq_snapshot_get()

        # Enable刺激：Force当前Source并取得硬件与ISR快照。
        support.cordic.irq_force(event)
        delivered = support.cordic.irq_snapshot_get()

        # Disable刺激：清除旧事件并关闭Source，再执行一次相同Force。
        support.cordic.irq_clear(event)
        support.cordic.irq_disable(event)
        disabled_before = support.cordic.irq_snapshot_get()
        support.cordic.irq_force(event)
        disabled_after = support.cordic.irq_snapshot_get()

        # 证据：分别记录硬件Raw/Status和Service ISR事实，不把两者混为一个端点。
        record_property("expected_irq_source", event.name)
        record_property("expected_irq_control", "enabled delivery=1; disabled delivery=0")
        record_property("event_count_delta", delivered.event_count - before.event_count)
        record_property(
            "disabled_event_count_delta",
            disabled_after.event_count - disabled_before.event_count,
        )
        record_observation(
            record_property,
            key="irq_raw",
            value=bool(delivered.raw & event),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="irq_status",
            value=bool(delivered.status & event),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )
        record_observation(
            record_property,
            key="irq_delivery",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )

        # 附件：在决定性断言前保存两阶段完整快照，失败时仍可复盘硬件现象。
        write_json_result(
            et_artifact_dir / f"cordic_p1_017_{event.name.lower()}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_017",
                "event": event.name,
                "enabled": {
                    "event_count_before": before.event_count,
                    "event_count_after": delivered.event_count,
                    "raw": int(delivered.raw),
                    "status": int(delivered.status),
                    "last_event": int(delivered.last_event),
                    "last_raw": int(delivered.last_raw),
                },
                "disabled": {
                    "event_count_before": disabled_before.event_count,
                    "event_count_after": disabled_after.event_count,
                    "raw": int(disabled_after.raw),
                    "status": int(disabled_after.status),
                },
            },
        )

        # 断言：Enable只投递目标Source；Disable后不得形成有效Status或新Delivery。
        # Raw是否置位属于具体硬件实现行为，只作为证据记录，不作为公共Case契约。
        assert delivered.event_count == before.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw & event == event
        assert disabled_after.event_count == disabled_before.event_count
        assert disabled_after.status & event == CordicIrqEvent(0)


# 测试 Feature：
# CORDIC IRQ Mask/Unmask 对 Raw、Status 和真实 Delivery 的分层控制。
#
# 测试方法：
# 1. Enable后Mask CALCULATION_COMPLETE，并Force一次构造Raw Pending。
# 2. Mask状态读取Raw/Status/Event Count，随后不重复Force直接Unmask同一Pending。
# 3. 读取Unmask后的ISR Latch与Event Count，并显式Clear恢复。
#
# 通过条件：
# 1. Mask阶段Raw置位、Status为零且Event Count不增加。
# 2. Unmask同一Pending后Event Count增加一次且Last Event为目标Source。
# 3. Clear后不保留目标Pending，清理动作不改变其他Source。
def test_cordic_p1_018_irq_mask_unmask(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择可安全Force的CALCULATION_COMPLETE Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    event = CordicIrqEvent.CALCULATION_COMPLETE
    require_cordic_static_irq_capability(
        target_capabilities,
        instance_id=cordic_instance_id,
        event=event,
    )
    require_cordic_runtime_irq_capability(support.runtime, event)
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("CORDIC IRQ source disable", lambda: support.cordic.irq_disable(event)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(event)),
            ("CORDIC IRQ source unmask", lambda: support.cordic.irq_unmask(event)),
            ("CORDIC status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：Enable目标Source并在清洁状态下施加Mask。
        support.cordic.configure(CordicConfig(work_mode=CordicWorkMode.INTERRUPT))
        configured = True
        support.cordic.irq_clear(event)
        support.cordic.irq_enable(event)
        support.cordic.irq_mask(event)
        baseline = support.cordic.irq_snapshot_get()

        # Mask刺激：Force后读取同一时刻的Raw、Status与Event Count。
        support.cordic.irq_force(event)
        masked = support.cordic.irq_snapshot_get()

        # Unmask刺激：保留同一Pending，解除Mask并读取真实ISR投递证据。
        support.cordic.irq_unmask(event)
        delivered = support.cordic.irq_snapshot_get()

        # 证据：Raw、Status和Service Delivery分别进入Canonical Observation。
        record_property("expected_mask_state", "masked raw=1/status=0; unmask delivery=1")
        record_property("masked_event_count_delta", masked.event_count - baseline.event_count)
        record_property("unmasked_event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="raw_masked",
            value=bool(masked.raw & event),
            source="dut",
            endpoint="IRQ_RAW.CALCULATION_COMPLETE",
        )
        record_observation(
            record_property,
            key="status_masked",
            value=bool(masked.status & event),
            source="dut",
            endpoint="IRQ_STATUS.CALCULATION_COMPLETE",
        )
        record_observation(
            record_property,
            key="irq_delivery",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )

        # 附件：在断言前保存Mask和Unmask两阶段快照。
        write_json_result(
            et_artifact_dir / "cordic_p1_018_irq_mask_unmask.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_018",
                "masked": {
                    "raw": int(masked.raw),
                    "status": int(masked.status),
                    "event_count": masked.event_count,
                },
                "unmasked": {
                    "raw": int(delivered.raw),
                    "status": int(delivered.status),
                    "event_count": delivered.event_count,
                    "last_event": int(delivered.last_event),
                    "last_raw": int(delivered.last_raw),
                },
            },
        )

        # 断言：Mask只抑制有效状态和Delivery，不删除Raw；Unmask释放同一Pending。
        assert masked.raw & event == event
        assert masked.status & event == CordicIrqEvent(0)
        assert masked.event_count == baseline.event_count
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw & event == event


# 测试 Feature：
# CORDIC 多 IRQ Source Raw Pending 共存时的单Source精确Clear。
#
# 测试方法：
# 1. Enable并Mask target和neighbor，Clear后分别Force两个Source。
# 2. 读取双Source共存Raw位图，只Clear target后再次读取位图。
# 3. 最后Clear neighbor并确认两个Source都恢复为零。
#
# 通过条件：
# 1. Clear前target和neighbor Raw均置位且没有ISR Delivery。
# 2. Clear target后仅target归零，neighbor保持Pending。
# 3. Clear neighbor后两个Source Raw均为零，全程Status保持被Mask抑制。
def test_cordic_p1_019_irq_precise_clear(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择两个稳定且可安全Force的独立Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    target = CordicIrqEvent.CALCULATION_COMPLETE
    neighbor = CordicIrqEvent.ARG_OVERFLOW
    events = target | neighbor

    # 能力门禁：两个Source必须分别由静态和Runtime能力声明。
    for event in (target, neighbor):
        require_cordic_static_irq_capability(
            target_capabilities,
            instance_id=cordic_instance_id,
            event=event,
        )
        require_cordic_runtime_irq_capability(support.runtime, event)
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("CORDIC IRQ sources disable", lambda: support.cordic.irq_disable(events)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(events)),
            ("CORDIC IRQ sources unmask", lambda: support.cordic.irq_unmask(events)),
            ("CORDIC status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：Mask两个Source，避免ISR自动清除破坏Raw共存现场。
        support.cordic.configure(CordicConfig(work_mode=CordicWorkMode.INTERRUPT))
        configured = True
        support.cordic.irq_enable(events)
        support.cordic.irq_mask(events)
        support.cordic.irq_clear(events)
        baseline = support.cordic.irq_snapshot_get()

        # 双Source刺激：分别Force并读取Clear前共存Raw位图。
        support.cordic.irq_force(target)
        support.cordic.irq_force(neighbor)
        before_clear = support.cordic.irq_snapshot_get()

        # 精确Clear：只清target并保留neighbor，随后完成最终清理观测。
        support.cordic.irq_clear(target)
        after_target_clear = support.cordic.irq_snapshot_get()
        support.cordic.irq_clear(neighbor)
        final = support.cordic.irq_snapshot_get()

        # 证据：保存三个时刻的Raw硬件位图和Mask后的有效状态。
        record_property("expected_clear_bitmap", "before=target|neighbor; after=neighbor; final=0")
        record_observation(
            record_property,
            key="raw_before_clear",
            value=int(before_clear.raw),
            source="dut",
            endpoint="IRQ_RAW.ALL",
        )
        record_observation(
            record_property,
            key="raw_after_target_clear",
            value=int(after_target_clear.raw),
            source="dut",
            endpoint="IRQ_RAW.ALL",
        )
        record_observation(
            record_property,
            key="raw_final",
            value=int(final.raw),
            source="dut",
            endpoint="IRQ_RAW.ALL",
        )

        # 附件：在断言前保存完整位图，保证失败时能区分共存、误清和残留。
        write_json_result(
            et_artifact_dir / "cordic_p1_019_irq_precise_clear.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_019",
                "expected": {
                    "before": int(events),
                    "after_target_clear": int(neighbor),
                    "final": 0,
                },
                "actual": {
                    "before": int(before_clear.raw),
                    "after_target_clear": int(after_target_clear.raw),
                    "final": int(final.raw),
                },
                "status": {
                    "before": int(before_clear.status),
                    "after_target_clear": int(after_target_clear.status),
                    "final": int(final.status),
                },
            },
        )

        # 断言：目标Clear不得误清邻居，两个Mask Source全程不形成有效Status/Delivery。
        assert baseline.event_count == before_clear.event_count == final.event_count
        assert before_clear.raw & events == events
        assert before_clear.status & events == CordicIrqEvent(0)
        assert after_target_clear.raw & target == CordicIrqEvent(0)
        assert after_target_clear.raw & neighbor == neighbor
        assert final.raw & events == CordicIrqEvent(0)


# 测试 Feature：
# CORDIC Normalized 与 Direct Angle 两种输入范围模式。
#
# 测试方法：
# 1. 选择逻辑角度π/2，分别按Chip Execution Mapping编码Normalized和Direct Angle输入。
# 2. 两条路径都配置Fixed、Polling和SINCOS双结果，只改变Range与对应Codec。
# 3. 按映射解码两种路径的cos/sin结果，清除COMPLETE后比较同一数学结果。
#
# 通过条件：
# 1. 两种输入范围配置都能自然完成且没有错误状态。
# 2. 两种路径都在CORDIC误差预算内返回cos=0、sin=1。
# 3. 两种编码均正确解释为同一数学角度，证明Range配置真实生效。
@pytest.mark.parametrize(
    "input_range",
    (CordicInputRange.NORMALIZED, CordicInputRange.DIRECT_ANGLE),
    ids=("normalized", "direct_angle"),
)
def test_cordic_p1_001_input_range_equivalence(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    input_range: CordicInputRange,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：两种Range都必须由当前Runtime独立声明。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    required_feature = (
        CordicFeature.NORMALIZED_RANGE
        if input_range is CordicInputRange.NORMALIZED
        else CordicFeature.DIRECT_ANGLE_RANGE
    )
    if not (support.runtime.features & required_feature):
        pytest.skip(f"skip_by_runtime_capability: CORDIC range {input_range.name} is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    logical_angle = math.pi / 2.0
    if input_range is CordicInputRange.NORMALIZED:
        fraction_bits = semantics.fixed_fraction_bits[32]
        encoded_value = logical_angle / semantics.normalized_angle_divisor
        encoding = "normalized_fixed"
    else:
        fraction_bits = semantics.direct_angle_fraction_bits[32]
        encoded_value = logical_angle
        encoding = "direct_angle_fixed"
    argument_raw = int(round(encoded_value * (1 << fraction_bits))) & 0xFFFFFFFF

    # 配置：建立本Range独立的Fixed、32-bit、Polling会话。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FIXED,
            input_range=input_range,
            work_mode=CordicWorkMode.POLLING,
            sincos_result_count=CordicResultCount.TWO,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：按当前Range的编码语义提交同一逻辑角度 π/2。
    support.cordic.argument_submit(CordicFunction.SINCOS, argument_raw)

    # 观测：等待硬件完成并读取SINCOS的两个Raw结果。
    status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
    result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    cleared = support.cordic.status_get()

    # 证据：记录Range、输入编码、数学Golden和硬件Raw结果。
    record_property("input_range", input_range.name)
    record_property("logical_angle_radians", math.pi / 2.0)
    record_observation(
        record_property,
        key="range_primary_raw",
        value=result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="range_secondary_raw",
        value=result.secondary_raw,
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_001_input_range_equivalence.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_001",
            "input_range": input_range.name,
            "encoding": encoding,
            "argument_raw": argument_raw,
            "expected": {"primary": 0.0, "secondary": 1.0},
            "actual": {
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
            },
            "status": {
                "before_clear": int(status),
                "after_clear": int(cleared),
                "polls": poll_count,
            },
        },
    )

    # 断言：两种输入范围都必须在统一误差预算内实现同一π/2数学结果。
    result_fraction_bits = semantics.fixed_fraction_bits[32]
    primary_signed = (
        result.primary_raw
        if result.primary_raw < (1 << result_fraction_bits)
        else result.primary_raw - (1 << (result_fraction_bits + 1))
    )
    secondary_signed = (
        result.secondary_raw
        if result.secondary_raw < (1 << result_fraction_bits)
        else result.secondary_raw - (1 << (result_fraction_bits + 1))
    )
    assert (
        abs(primary_signed / float(1 << result_fraction_bits) - 0.0) <= semantics.absolute_tolerance
    )
    assert (
        abs(secondary_signed / float(1 << result_fraction_bits) - 1.0)
        <= semantics.absolute_tolerance
    )
    assert status & CordicStatus.COMPLETE
    assert status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert cleared & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC 16-bit/32-bit 参数宽度、结果宽度和双结果16-bit打包。
#
# 测试方法：
# 1. 遍历参数宽度与结果宽度的四种组合，使用非零SINCOS(π/4)区分Codec路径。
# 2. 读取32-bit结果路径的完整Raw字，读取16-bit结果路径时按SVD拆分RES1低/高16-bit。
# 3. 每组清除COMPLETE并记录输入宽度、输出宽度、Raw结果和拆包值。
#
# 通过条件：
# 1. 四种宽度组合都能完成，不出现参数宽度或结果宽度配置错误。
# 2. 结果按Chip Execution Mapping声明的小数位解码后，均在误差预算内得到cos(π/4)、sin(π/4)。
# 3. 所有组合的状态都只包含COMPLETE，清除后COMPLETE归零。
@pytest.mark.parametrize(
    ("argument_width", "result_width"),
    (
        (CordicWidth.BITS_16, CordicWidth.BITS_16),
        (CordicWidth.BITS_16, CordicWidth.BITS_32),
        (CordicWidth.BITS_32, CordicWidth.BITS_16),
        (CordicWidth.BITS_32, CordicWidth.BITS_32),
    ),
    ids=("arg16_res16", "arg16_res32", "arg32_res16", "arg32_res32"),
)
def test_cordic_p1_002_width_and_packed_results(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    argument_width: CordicWidth,
    result_width: CordicWidth,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：当前组合要求同时声明对应的参数和结果宽度能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    width_features = {
        CordicWidth.BITS_16: CordicFeature.WIDTH_16,
        CordicWidth.BITS_32: CordicFeature.WIDTH_32,
    }
    if not (support.runtime.features & width_features[argument_width]) or not (
        support.runtime.features & width_features[result_width]
    ):
        pytest.skip("skip_by_runtime_capability: requested CORDIC width is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    argument_bits = 16 if argument_width is CordicWidth.BITS_16 else 32
    result_bits = 16 if result_width is CordicWidth.BITS_16 else 32
    logical_angle = math.pi / 4.0
    normalized_argument = logical_angle / semantics.normalized_angle_divisor
    argument_fraction_bits = semantics.fixed_fraction_bits[argument_bits]
    argument_raw = (
        int(round(normalized_argument * (1 << argument_fraction_bits)))
        << semantics.argument_storage_shift[argument_bits]
    ) & 0xFFFFFFFF
    expected_primary = math.cos(logical_angle)
    expected_secondary = math.sin(logical_angle)

    # 配置：建立当前宽度组合的Fixed、Normalized、Polling会话。
    support.cordic.configure(
        CordicConfig(
            numeric_mode=CordicNumericMode.FIXED,
            argument_width=argument_width,
            result_width=result_width,
            work_mode=CordicWorkMode.POLLING,
            sincos_result_count=CordicResultCount.TWO,
        )
    )
    support.cordic.status_clear(CordicStatus.ALL)

    # 激励：使用非零角度区分16/32-bit参数Codec，避免零值掩盖存储位置错误。
    support.cordic.argument_submit(CordicFunction.SINCOS, argument_raw)

    # 观测：等待完成并读取硬件Raw结果，保留16-bit打包的原始字。
    status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
    result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)
    cleared = support.cordic.status_get()
    packed_primary = result.primary_raw & 0xFFFFFFFF
    result1_16 = packed_primary & 0xFFFF
    result2_16 = (packed_primary >> 16) & 0xFFFF

    # 证据：记录宽度组合、Raw结果和SVD规定的16-bit拆包值。
    record_property("argument_width", argument_width.name)
    record_property("result_width", result_width.name)
    record_property("logical_angle_radians", logical_angle)
    record_observation(
        record_property,
        key="width_primary_raw",
        value=packed_primary,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="width_packed_values",
        value={"result1_16": result1_16, "result2_16": result2_16},
        source="dut",
        endpoint="RESULT.PRIMARY.PACKED16",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_002_width_and_packed_results.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_002",
            "argument_width": argument_width.name,
            "result_width": result_width.name,
            "argument_raw": argument_raw,
            "expected": {
                "primary": expected_primary,
                "secondary": expected_secondary,
            },
            "actual": {
                "primary_raw": packed_primary,
                "secondary_raw": result.secondary_raw,
                "result16_low": result1_16,
                "result16_high": result2_16,
            },
            "status": {
                "before_clear": int(status),
                "after_clear": int(cleared),
                "polls": poll_count,
            },
        },
    )

    # 断言：按芯片映射声明的结果小数位解码，16-bit路径同时证明双结果打包。
    result_fraction_bits = semantics.fixed_fraction_bits[result_bits]
    if result_width is CordicWidth.BITS_32:
        primary_signed = (
            packed_primary
            if packed_primary < (1 << result_fraction_bits)
            else packed_primary - (1 << (result_fraction_bits + 1))
        )
        secondary_signed = (
            result.secondary_raw
            if result.secondary_raw < (1 << result_fraction_bits)
            else result.secondary_raw - (1 << (result_fraction_bits + 1))
        )
        actual_primary = primary_signed / float(1 << result_fraction_bits)
        actual_secondary = secondary_signed / float(1 << result_fraction_bits)
    else:
        sign_bit = 1 << result_fraction_bits
        result1_signed = result1_16 if result1_16 < sign_bit else result1_16 - (sign_bit << 1)
        result2_signed = result2_16 if result2_16 < sign_bit else result2_16 - (sign_bit << 1)
        actual_primary = result1_signed / float(1 << result_fraction_bits)
        actual_secondary = result2_signed / float(1 << result_fraction_bits)
    assert abs(actual_primary - expected_primary) <= semantics.absolute_tolerance
    assert abs(actual_secondary - expected_secondary) <= semantics.absolute_tolerance
    assert status & CordicStatus.COMPLETE
    assert status & ~CordicStatus.COMPLETE == CordicStatus(0)
    assert cleared & CordicStatus.COMPLETE == CordicStatus(0)


# 测试 Feature：
# CORDIC Scale 配置以及对不受Scale影响的 Sin/Cos路径隔离。
#
# 测试方法：
# 1. 遍历Runtime公布的Scale范围，保持Float32、SINCOS和输入0不变。
# 2. 每个Scale节点独立配置、提交一次SINCOS、等待COMPLETE并读取两个Raw结果。
# 3. 用SVD明确的“不受Scale影响”规则，将每个节点与Scale=0基线比较。
#
# 通过条件：
# 1. Execution Mapping公布的平台计划Scale节点都能完成，且不出现错误状态。
# 2. 所有节点的cos/sin结果与Scale=0基线逐位一致，且数学结果满足CORDIC误差预算。
# 3. 每个节点清除COMPLETE后再进入下一节点，避免状态残留影响比较。
def test_cordic_p1_003_scale_isolation(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：Scale节点和Float32函数必须由Runtime公布。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if CordicFunction.SINCOS not in support.runtime.functions:
        pytest.skip("skip_by_runtime_capability: CORDIC SINCOS is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    if semantics.scale_affected_function not in support.runtime.functions:
        pytest.skip("skip_by_runtime_capability: mapped Scale function is unavailable")
    if support.runtime.maximum_scale < semantics.scale_maximum:
        pytest.skip("skip_by_runtime_capability: runtime Scale range is narrower than mapping")
    scale_nodes = tuple(range(semantics.scale_maximum + 1))

    scale_results: list[dict[str, int]] = []
    affected_results: list[dict[str, int | float]] = []

    # 节点循环：Scale只改变配置字段，输入和函数保持完全不变。
    for scale in scale_nodes:
        # 配置：为当前Scale节点建立独立Float32 Polling会话。
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FLOAT32,
                scale=scale,
                work_mode=CordicWorkMode.POLLING,
                sincos_result_count=CordicResultCount.TWO,
            )
        )
        support.cordic.status_clear(CordicStatus.ALL)

        # 激励：提交不受Scale影响的零角度SINCOS。
        support.cordic.argument_submit(CordicFunction.SINCOS, _float32_raw(0.0))

        # 观测：等待完成并读取当前Scale节点的Raw结果。
        status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
        result = support.cordic.result_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)
        cleared = support.cordic.status_get()
        scale_results.append(
            {
                "scale": scale,
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
                "status": int(status),
                "cleared": int(cleared),
                "poll_count": poll_count,
            }
        )

    fraction_bits = semantics.fixed_fraction_bits[32]
    affected_argument_raw = int(round(semantics.scale_argument * (1 << fraction_bits))) & 0xFFFFFFFF

    # 受影响路径：按芯片执行语义固定一个ARCTAN输入，验证Scale的输入和输出补偿公式。
    for scale in scale_nodes:
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FIXED,
                scale=scale,
                work_mode=CordicWorkMode.POLLING,
            )
        )
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.argument_submit(
            semantics.scale_affected_function,
            affected_argument_raw,
        )
        status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
        result = support.cordic.result_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)
        cleared = support.cordic.status_get()
        signed_raw = (
            result.primary_raw
            if result.primary_raw < (1 << fraction_bits)
            else result.primary_raw - (1 << (fraction_bits + 1))
        )
        actual = (
            signed_raw
            / float(1 << fraction_bits)
            * semantics.scale_output_multiplier_base**scale
            * semantics.scale_output_angle_unit
        )
        expected = math.atan(
            semantics.scale_argument * semantics.scale_input_multiplier_base**scale
        )
        affected_results.append(
            {
                "scale": scale,
                "primary_raw": result.primary_raw,
                "actual": actual,
                "expected": expected,
                "status": int(status),
                "cleared": int(cleared),
                "poll_count": poll_count,
            }
        )

    # 证据：每条Observation只绑定一个CORDIC硬件端点；节点身份随原始值一并保留。
    record_property(
        "expected_scale_values",
        {"primary_raw": _float32_raw(1.0), "secondary_raw": _float32_raw(0.0)},
    )
    record_observation(
        record_property,
        key="scale_unaffected_primary_raw",
        value=[{"scale": item["scale"], "value": item["primary_raw"]} for item in scale_results],
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="scale_unaffected_secondary_raw",
        value=[{"scale": item["scale"], "value": item["secondary_raw"]} for item in scale_results],
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    record_observation(
        record_property,
        key="scale_affected_primary_raw",
        value=[{"scale": item["scale"], "value": item["primary_raw"]} for item in affected_results],
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="scale_status_before_clear",
        value=[
            {"path": "unaffected", "scale": item["scale"], "value": item["status"]}
            for item in scale_results
        ]
        + [
            {"path": "affected", "scale": item["scale"], "value": item["status"]}
            for item in affected_results
        ],
        source="dut",
        endpoint="STATUS",
    )
    record_observation(
        record_property,
        key="scale_status_after_clear",
        value=[
            {"path": "unaffected", "scale": item["scale"], "value": item["cleared"]}
            for item in scale_results
        ]
        + [
            {"path": "affected", "scale": item["scale"], "value": item["cleared"]}
            for item in affected_results
        ],
        source="dut",
        endpoint="STATUS",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_003_scale_isolation.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_003",
            "unaffected_path": {
                "expected": {
                    "primary_raw": _float32_raw(1.0),
                    "secondary_raw": _float32_raw(0.0),
                },
                "actual": scale_results,
            },
            "affected_path": {
                "function": semantics.scale_affected_function.name,
                "argument_raw": affected_argument_raw,
                "actual": affected_results,
            },
        },
    )

    # 断言：SVD规定不受Scale影响的SINCOS结果必须逐位保持不变。
    assert scale_results
    baseline = scale_results[0]

    # 逐节点断言：同时验证数学正确性、Raw一致性和完成状态。
    for result in scale_results:
        assert _within_cordic_budget(_float32_value(result["primary_raw"]), 1.0)
        assert _within_cordic_budget(_float32_value(result["secondary_raw"]), 0.0)
        assert result["primary_raw"] == baseline["primary_raw"]
        assert result["secondary_raw"] == baseline["secondary_raw"]
        assert result["status"] & int(CordicStatus.COMPLETE)
        assert result["status"] & ~int(CordicStatus.COMPLETE) == 0
        assert result["cleared"] & int(CordicStatus.COMPLETE) == 0

    # 受影响路径断言：每个Scale节点按映射公式还原后均满足独立数学Golden。
    for result in affected_results:
        assert abs(float(result["actual"]) - float(result["expected"])) <= (
            semantics.absolute_tolerance
        )
        assert int(result["status"]) & int(CordicStatus.COMPLETE)
        assert int(result["status"]) & ~int(CordicStatus.COMPLETE) == 0
        assert int(result["cleared"]) & int(CordicStatus.COMPLETE) == 0


# 测试 Feature：
# CORDIC Iteration/Precision 配置的完成性和精度收敛趋势。
#
# 测试方法：
# 1. 遍历Runtime公布的precision_cycles范围，使用Fixed Normalized SINCOS(π/6)非平凡向量。
# 2. 每个精度节点独立配置、提交输入、等待COMPLETE并解码cos/sin结果。
# 3. 比较最低和最高精度误差，验证迭代配置对结果收敛的真实影响。
#
# 通过条件：
# 1. 所有公开precision节点都能在有界轮询内完成。
# 2. 最高精度节点满足CORDIC误差预算，且总误差小于最低精度节点。
# 3. 每个节点W1C后COMPLETE归零，节点之间没有前一轮状态残留。
def test_cordic_p1_004_precision_completion(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：当前函数和Runtime公布的精度上限必须存在。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if CordicFunction.SINCOS not in support.runtime.functions:
        pytest.skip("skip_by_runtime_capability: CORDIC SINCOS is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    precision_nodes = semantics.precision_cycles
    if not precision_nodes or support.runtime.maximum_precision_cycles < precision_nodes[-1]:
        pytest.skip("skip_by_runtime_capability: mapped precision range is unavailable")

    expected_cos = math.cos(math.pi / 6.0)
    expected_sin = math.sin(math.pi / 6.0)
    fraction_bits = semantics.fixed_fraction_bits[32]
    normalized_argument = (math.pi / 6.0) / semantics.normalized_angle_divisor
    argument_raw = int(round(normalized_argument * (1 << fraction_bits))) & 0xFFFFFFFF
    precision_results: list[dict[str, int | float]] = []

    # 节点循环：只改变precision_cycles，保持函数、格式和输入完全一致。
    for precision_cycles in precision_nodes:
        # 配置：建立当前迭代周期节点的Fixed Normalized Polling会话。
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FIXED,
                precision_cycles=precision_cycles,
                work_mode=CordicWorkMode.POLLING,
                sincos_result_count=CordicResultCount.TWO,
            )
        )
        support.cordic.status_clear(CordicStatus.ALL)

        # 激励：提交π/6非平凡角度，使低/高迭代配置产生可观测精度差异。
        support.cordic.argument_submit(CordicFunction.SINCOS, argument_raw)

        # 观测：等待当前precision节点完成并读取定点cos/sin Raw结果。
        status, poll_count = support.cordic.wait_status(CordicStatus.COMPLETE)
        result = support.cordic.result_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)
        cleared = support.cordic.status_get()
        precision_results.append(
            {
                "precision_cycles": precision_cycles,
                "primary_raw": result.primary_raw,
                "secondary_raw": result.secondary_raw,
                "cos_error": abs(
                    _signed_fixed_value(result.primary_raw, fraction_bits) - expected_cos
                ),
                "sin_error": abs(
                    _signed_fixed_value(result.secondary_raw, fraction_bits) - expected_sin
                ),
                "status": int(status),
                "cleared": int(cleared),
                "poll_count": poll_count,
            }
        )

    # 证据：按硬件端点拆分Raw结果和状态采样，避免一个Observation混合多个来源。
    record_property("expected_cos", expected_cos)
    record_property("expected_sin", expected_sin)
    record_property("expected_precision_budget", semantics.absolute_tolerance)
    record_observation(
        record_property,
        key="precision_primary_raw",
        value=[
            {"precision_cycles": item["precision_cycles"], "value": item["primary_raw"]}
            for item in precision_results
        ],
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    record_observation(
        record_property,
        key="precision_secondary_raw",
        value=[
            {"precision_cycles": item["precision_cycles"], "value": item["secondary_raw"]}
            for item in precision_results
        ],
        source="dut",
        endpoint="RESULT.SECONDARY",
    )
    record_observation(
        record_property,
        key="precision_status_before_clear",
        value=[
            {"precision_cycles": item["precision_cycles"], "value": item["status"]}
            for item in precision_results
        ],
        source="dut",
        endpoint="STATUS",
    )
    record_observation(
        record_property,
        key="precision_status_after_clear",
        value=[
            {"precision_cycles": item["precision_cycles"], "value": item["cleared"]}
            for item in precision_results
        ],
        source="dut",
        endpoint="STATUS",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_004_precision_completion.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_004",
            "argument_raw": argument_raw,
            "expected": {"cos": expected_cos, "sin": expected_sin},
            "actual": precision_results,
        },
    )

    # 断言：所有公开精度节点都必须完成，最高节点还必须满足数学精度预算。
    assert precision_results

    # 逐节点断言：低精度允许较大误差，但不允许未完成或产生错误状态。
    for result in precision_results:
        assert result["status"] & int(CordicStatus.COMPLETE)
        assert result["status"] & ~int(CordicStatus.COMPLETE) == 0
        assert result["cleared"] & int(CordicStatus.COMPLETE) == 0

    # 精度断言：最高精度满足预算，并且相比最低精度产生严格收敛。
    lowest_error = float(precision_results[0]["cos_error"]) + float(
        precision_results[0]["sin_error"]
    )
    highest_error = float(precision_results[-1]["cos_error"]) + float(
        precision_results[-1]["sin_error"]
    )
    assert float(precision_results[-1]["cos_error"]) <= semantics.absolute_tolerance
    assert float(precision_results[-1]["sin_error"]) <= semantics.absolute_tolerance
    assert highest_error < lowest_error


# 测试 Feature：
# CORDIC 参数数量溢出状态与清除后恢复。
#
# 测试方法：
# 1. 配置Fixed Polling并完成一次SINCOS基线，随后不消费结果地连续提交四个SINCOS参数。
# 2. 有界轮询ARG_OVERFLOW，读取状态并记录触发前后的参数提交数量。
# 3. 清除ARG_OVERFLOW并消费占用的结果槽，重新配置后执行SINCOS(0)，确认错误路径可恢复。
#
# 通过条件：
# 1. 连续超容量提交自然置位ARG_OVERFLOW，不能用Force代替自然刺激。
# 2. W1C后ARG_OVERFLOW归零。
# 3. 恢复SINCOS事务按执行映射解码后返回cos=1、sin=0并自然完成。
def test_cordic_p1_011_argument_overflow_recovery(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：目标状态必须由Runtime声明。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if not (support.runtime.features & CordicFeature.STATUS):
        pytest.skip("skip_by_runtime_capability: CORDIC status is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )

    # 配置：使用目标芯片适配资料已闭合的Fixed SINCOS结果容量路径。
    config = CordicConfig(
        numeric_mode=CordicNumericMode.FIXED,
        work_mode=CordicWorkMode.POLLING,
        sincos_result_count=CordicResultCount.TWO,
    )
    support.cordic.configure(config)
    support.cordic.status_clear(CordicStatus.ALL)

    # 基线：先完成并消费一个正常事务，证明Overflow不是历史残留。
    support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
    support.cordic.wait_status(CordicStatus.COMPLETE)
    baseline_result = support.cordic.result_get()
    support.cordic.status_clear(CordicStatus.COMPLETE)

    # 激励：连续写入四个单参数请求且暂不消费结果，确定性超过硬件结果容量。
    for _ in range(semantics.argument_overflow_submit_count):
        support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
    overflow_status, overflow_polls = support.cordic.wait_status(CordicStatus.ARG_OVERFLOW)

    # 恢复：先消费两个已占用结果槽，再清除状态并重新配置。
    discarded_results = tuple(
        support.cordic.result_get() for _ in range(semantics.argument_overflow_result_read_count)
    )
    support.cordic.status_clear(CordicStatus.ARG_OVERFLOW)
    cleared = support.cordic.status_get()
    support.cordic.configure(config)
    support.cordic.status_clear(CordicStatus.ALL)
    support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
    recovery_status, recovery_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    recovery_result = support.cordic.result_get()

    # 证据：记录提交次数、错误状态、清除状态和恢复结果。
    record_observation(
        record_property,
        key="overflow_status",
        value=int(overflow_status),
        source="dut",
        endpoint="STATUS.ARG_OVERFLOW",
    )
    record_observation(
        record_property,
        key="recovery_result",
        value=recovery_result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_011_argument_overflow_recovery.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_011",
            "submitted_arguments": semantics.argument_overflow_submit_count,
            "baseline": {
                "primary_raw": baseline_result.primary_raw,
                "secondary_raw": baseline_result.secondary_raw,
            },
            "overflow": {"status": int(overflow_status), "polls": overflow_polls},
            "discarded_results": [
                {
                    "primary_raw": item.primary_raw,
                    "secondary_raw": item.secondary_raw,
                }
                for item in discarded_results
            ],
            "cleared_status": int(cleared),
            "recovery": {
                "status": int(recovery_status),
                "primary_raw": recovery_result.primary_raw,
                "polls": recovery_polls,
            },
        },
    )

    # 断言：自然Overflow、W1C清除和后续恢复必须完整成立。
    assert overflow_status & CordicStatus.ARG_OVERFLOW
    assert cleared & CordicStatus.ARG_OVERFLOW == CordicStatus(0)
    assert recovery_status & CordicStatus.COMPLETE
    assert recovery_status & CordicStatus.ARG_OVERFLOW == CordicStatus(0)
    fraction_bits = semantics.fixed_fraction_bits[32]
    assert (
        abs(_signed_fixed_value(recovery_result.primary_raw, fraction_bits) - 1.0)
        <= semantics.absolute_tolerance
    )
    assert (
        abs(_signed_fixed_value(recovery_result.secondary_raw, fraction_bits) - 0.0)
        <= semantics.absolute_tolerance
    )


# 测试 Feature：
# CORDIC Float-to-Fixed 转换 Overflow/Underflow 状态和边界恢复。
#
# 测试方法：
# 1. 使用芯片适配资料闭合的SQRT(2.5)提交越界大值，读取并记录OVF状态。
# 2. 消费该事务结果并清除OVF，再提交SQRT(0.01)读取UDF状态，分别验证W1C。
# 3. 清除转换状态并执行SQRT(1.0)恢复节点，确认普通路径不再携带转换错误。
#
# 通过条件：
# 1. 大值自然置位OVERFLOW，小值自然置位UNDERFLOW，两个状态不互相冒充。
# 2. 每个状态都可通过对应W1C清除。
# 3. 恢复节点正常完成并返回Float32 1.0。
def test_cordic_p1_013_float_to_fixed_conversion_status(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：转换状态属于独立Runtime Feature，缺失则只跳过本Case。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    if not (support.runtime.features & CordicFeature.FLOAT32):
        pytest.skip("skip_by_runtime_capability: CORDIC Float32 is unavailable")
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    function = semantics.conversion_function
    if function not in support.runtime.functions:
        pytest.skip("skip_by_runtime_capability: mapped conversion function is unavailable")

    # 配置：建立Float32 Polling会话并清除历史转换状态。
    config = CordicConfig(numeric_mode=CordicNumericMode.FLOAT32, work_mode=CordicWorkMode.POLLING)
    support.cordic.configure(config)
    support.cordic.conversion_status_clear(CordicConversionStatus.ALL)

    # Overflow激励：SQRT(2.5)是目标芯片适配资料已覆盖的确定性边界外节点。
    support.cordic.argument_submit(function, _float32_raw(semantics.conversion_overflow_input))
    overflow_status = support.cordic.wait_conversion_status(CordicConversionStatus.OVERFLOW)
    overflow_result = support.cordic.result_get()
    support.cordic.conversion_status_clear(CordicConversionStatus.OVERFLOW)
    overflow_cleared = support.cordic.conversion_status_get()

    # Underflow激励：SQRT(0.01)是目标芯片适配资料已覆盖的确定性边界外节点。
    support.cordic.argument_submit(
        function,
        _float32_raw(semantics.conversion_underflow_input),
    )
    underflow_status = support.cordic.wait_conversion_status(CordicConversionStatus.UNDERFLOW)
    underflow_result = support.cordic.result_get()
    support.cordic.conversion_status_clear(CordicConversionStatus.UNDERFLOW)
    underflow_cleared = support.cordic.conversion_status_get()

    # 恢复：清空转换状态并执行可精确表示的普通输入。
    support.cordic.configure(config)
    support.cordic.argument_submit(
        function,
        _float32_raw(semantics.conversion_recovery_input),
    )
    recovery_status, recovery_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
    recovery_result = support.cordic.result_get()

    # 证据：分别记录OVF/UDF状态、清除结果和恢复硬件结果。
    record_observation(
        record_property,
        key="conversion_overflow_status",
        value=int(overflow_status),
        source="dut",
        endpoint="RPT_CORDIC_FLOAT2FIXED.OVF",
    )
    record_observation(
        record_property,
        key="conversion_underflow_status",
        value=int(underflow_status),
        source="dut",
        endpoint="RPT_CORDIC_FLOAT2FIXED.UDF",
    )
    record_observation(
        record_property,
        key="conversion_recovery_result",
        value=recovery_result.primary_raw,
        source="dut",
        endpoint="RESULT.PRIMARY",
    )
    write_json_result(
        et_artifact_dir / "cordic_p1_013_float_to_fixed_conversion_status.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "cordic_p1_013",
            "overflow": {
                "input_raw": _float32_raw(semantics.conversion_overflow_input),
                "status": int(overflow_status),
                "result_raw": overflow_result.primary_raw,
                "after_clear": int(overflow_cleared),
            },
            "underflow": {
                "input_raw": _float32_raw(semantics.conversion_underflow_input),
                "status": int(underflow_status),
                "result_raw": underflow_result.primary_raw,
                "after_clear": int(underflow_cleared),
            },
            "recovery": {
                "status": int(recovery_status),
                "primary_raw": recovery_result.primary_raw,
                "polls": recovery_polls,
            },
        },
    )

    # 断言：OVF/UDF独立产生且可清除，恢复路径不带错误状态。
    assert overflow_status & CordicConversionStatus.OVERFLOW
    assert overflow_status & CordicConversionStatus.UNDERFLOW == CordicConversionStatus(0)
    assert overflow_cleared & CordicConversionStatus.OVERFLOW == CordicConversionStatus(0)
    assert underflow_status & CordicConversionStatus.UNDERFLOW
    assert underflow_status & CordicConversionStatus.OVERFLOW == CordicConversionStatus(0)
    assert underflow_cleared & CordicConversionStatus.UNDERFLOW == CordicConversionStatus(0)
    assert recovery_status & CordicStatus.COMPLETE
    assert (
        abs(
            _float32_value(recovery_result.primary_raw)
            - math.sqrt(semantics.conversion_recovery_input)
        )
        <= semantics.absolute_tolerance
    )


# 测试 Feature：
# CORDIC ARG_OVERFLOW IRQ自然投递、Service事件计数和错误恢复。
#
# 测试方法：
# 1. 建立ARG_OVERFLOW的Enable+Unmask IRQ会话，读取事件计数基线。
# 2. 完成一次SINCOS基线后连续提交四个未消费请求，自然触发硬件Overflow，不调用IRQ Force。
# 3. 读取状态与Service ISR快照，消费占用结果并清除错误/IRQ后执行SINCOS恢复事务。
#
# 通过条件：
# 1. ARG_OVERFLOW状态置位且Event Count增加，Last Event/Raw指向ARG_OVERFLOW。
# 2. Clear后ARG_OVERFLOW和目标IRQ Raw均清零。
# 3. 恢复SINCOS按执行映射解码后返回cos=1、sin=0且不再产生ARG_OVERFLOW。
def test_cordic_p1_015_argument_overflow_natural_irq(
    cordic_support_for: CordicSupportFactory,
    cordic_instance_id: int,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 能力门禁：静态Profile和Runtime必须共同声明ARG_OVERFLOW IRQ Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CORDIC, instance=cordic_instance_id)
    resource_driver.reset()

    support = cordic_support_for(cordic_instance_id)
    event = CordicIrqEvent.ARG_OVERFLOW
    require_cordic_static_irq_capability(
        target_capabilities,
        instance_id=cordic_instance_id,
        event=event,
    )
    require_cordic_runtime_irq_capability(support.runtime, event)
    semantics = resolve_cordic_execution_semantics(
        target_capabilities,
        instance_id=cordic_instance_id,
    )
    configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not configured:
            return ()
        return (
            ("CORDIC status clear", lambda: support.cordic.status_clear(CordicStatus.ALL)),
            ("CORDIC IRQ source disable", lambda: support.cordic.irq_disable(event)),
            ("CORDIC IRQ pending clear", lambda: support.cordic.irq_clear(event)),
            ("CORDIC IRQ source unmask", lambda: support.cordic.irq_unmask(event)),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：建立Interrupt会话并清除目标Source的历史Raw/Status。
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FIXED,
                work_mode=CordicWorkMode.POLLING,
                sincos_result_count=CordicResultCount.TWO,
            )
        )
        configured = True
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.irq_clear(event)
        support.cordic.irq_unmask(event)
        support.cordic.irq_enable(event)
        baseline = support.cordic.irq_snapshot_get()

        # 基线：先完成并消费一次正常SINCOS，排除历史状态对IRQ因果的影响。
        support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
        support.cordic.wait_status(CordicStatus.COMPLETE)
        baseline_result = support.cordic.result_get()
        support.cordic.status_clear(CordicStatus.COMPLETE)

        # 激励：连续提交四个未消费的SINCOS请求，依靠硬件容量自然触发Overflow。
        for _ in range(semantics.argument_overflow_submit_count):
            support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
        delivered = support.cordic.wait_irq(
            event,
            minimum_event_count=baseline.event_count + 1,
        )
        error_status = support.cordic.status_get()

        # 恢复：消费两个占用结果槽，清除错误和目标IRQ，再执行合法SINCOS事务。
        discarded_results = tuple(
            support.cordic.result_get()
            for _ in range(semantics.argument_overflow_result_read_count)
        )
        support.cordic.status_clear(CordicStatus.ARG_OVERFLOW)
        support.cordic.irq_clear(event)
        support.cordic.configure(
            CordicConfig(
                numeric_mode=CordicNumericMode.FIXED,
                work_mode=CordicWorkMode.POLLING,
                sincos_result_count=CordicResultCount.TWO,
            )
        )
        support.cordic.status_clear(CordicStatus.ALL)
        support.cordic.argument_submit(CordicFunction.SINCOS, _q31_raw(0.0))
        recovery_status, recovery_polls = support.cordic.wait_status(CordicStatus.COMPLETE)
        recovery_result = support.cordic.result_get()
        final_snapshot = support.cordic.irq_snapshot_get()

        # 证据：硬件Raw/Status、Service锁存源和软件事件计数分别记录。
        record_property("arg_overflow_irq_event_count", delivered.event_count)
        record_observation(
            record_property,
            key="arg_overflow_status",
            value=int(error_status),
            source="dut",
            endpoint="STATUS.ARG_OVERFLOW",
        )
        record_observation(
            record_property,
            key="arg_overflow_irq_raw",
            value=bool(delivered.raw & event),
            source="dut",
            endpoint="IRQ_RAW.ARG_OVERFLOW",
        )
        record_observation(
            record_property,
            key="arg_overflow_irq_status",
            value=bool(delivered.status & event),
            source="dut",
            endpoint="IRQ_STATUS.ARG_OVERFLOW",
        )
        record_observation(
            record_property,
            key="arg_overflow_irq_latched_source",
            value=int(delivered.last_event),
            source="dut",
            endpoint="IRQ_DELIVERY.LATCHED_SOURCE",
        )
        write_json_result(
            et_artifact_dir / "cordic_p1_015_argument_overflow_natural_irq.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p1_015",
                "error_status": int(error_status),
                "baseline_result": {
                    "primary_raw": baseline_result.primary_raw,
                    "secondary_raw": baseline_result.secondary_raw,
                },
                "discarded_results": [
                    {
                        "primary_raw": item.primary_raw,
                        "secondary_raw": item.secondary_raw,
                    }
                    for item in discarded_results
                ],
                "irq": {
                    "baseline_event_count": baseline.event_count,
                    "delivered_event_count": delivered.event_count,
                    "last_event": int(delivered.last_event),
                    "last_raw": int(delivered.last_raw),
                    "final_raw": int(final_snapshot.raw),
                },
                "recovery": {
                    "status": int(recovery_status),
                    "primary_raw": recovery_result.primary_raw,
                    "polls": recovery_polls,
                },
            },
        )

        # 断言：自然错误、真实IRQ Delivery、清理和恢复必须同时成立。
        assert error_status & CordicStatus.ARG_OVERFLOW
        assert delivered.event_count > baseline.event_count
        assert delivered.last_event & event == event
        assert delivered.last_raw & event == event
        assert final_snapshot.raw & event == CordicIrqEvent(0)
        assert recovery_status & CordicStatus.COMPLETE
        assert recovery_status & CordicStatus.ARG_OVERFLOW == CordicStatus(0)
        fraction_bits = semantics.fixed_fraction_bits[32]
        assert (
            abs(_signed_fixed_value(recovery_result.primary_raw, fraction_bits) - 1.0)
            <= semantics.absolute_tolerance
        )
        assert (
            abs(_signed_fixed_value(recovery_result.secondary_raw, fraction_bits) - 0.0)
            <= semantics.absolute_tolerance
        )
