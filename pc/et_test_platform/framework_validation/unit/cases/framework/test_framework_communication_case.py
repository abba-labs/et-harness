# Framework Validation测试模块。
#
# 职责：验证test_framework_communication_case 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
import struct
from pathlib import Path

from et_test_platform.results.communication import (
    FrameworkCommunicationStressResult,
    LatencySummary,
    PayloadClassSummary,
)
from et_test_platform.results.recorder import write_json_result
from et_test_platform.test_cases.framework_communication.stress_case import (
    FORMAL_STRESS_PLAN,
    CommunicationStressPlan,
    PayloadClass,
    payload_for_round,
    percentile,
)

ROOT = Path(__file__).parents[6]
FORMAL_CASE = (
    ROOT
    / "pc/et_test_platform/test_cases/framework_communication/test_framework_communication_p3.py"
)


def test_formal_stress_plan_is_fixed_to_20_mixed_rounds() -> None:
    assert FORMAL_STRESS_PLAN.rounds == 20
    assert [(item.name, item.size) for item in FORMAL_STRESS_PLAN.payload_classes] == [
        ("small", 16),
        ("medium", 256),
        ("large", 2048),
    ]


def test_stress_plan_rejects_invalid_shapes() -> None:
    try:
        CommunicationStressPlan(rounds=0, payload_classes=(PayloadClass("small", 8),))
    except ValueError as error:
        assert "rounds" in str(error)
    else:
        raise AssertionError("zero rounds must be rejected")


def test_payload_generation_is_deterministic_and_self_identifying() -> None:
    payload = payload_for_round(7, 2, 16)
    assert len(payload) == 16
    assert struct.unpack("<II", payload[:8]) == (7, 2)
    assert payload == payload_for_round(7, 2, 16)
    assert payload != payload_for_round(8, 2, 16)


def test_percentile_is_pure_and_bounded() -> None:
    values = [5.0, 1.0, 3.0, 2.0, 4.0]
    assert percentile(values, 0.0) == 1.0
    assert percentile(values, 0.5) == 3.0
    assert percentile(values, 1.0) == 5.0
    assert values == [5.0, 1.0, 3.0, 2.0, 4.0]


def test_formal_case_directly_owns_echo_loop_and_assertions() -> None:
    source = FORMAL_CASE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "test_framework_communication_p3_001_echo_mixed_payload_stress"
    )
    calls = {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "echo" in calls
    assert any(isinstance(node, ast.Assert) for node in ast.walk(function))
    assert "expected_transactions = FORMAL_STRESS_PLAN.rounds" in source
    assert "expected_total_bytes = FORMAL_STRESS_PLAN.rounds" in source
    assert "assert transactions == 60" not in source
    assert "assert total_bytes == 92_800" not in source
    assert "execute_framework_echo_stress" not in source


def test_measurement_model_contains_no_independent_conclusion(tmp_path: Path) -> None:
    result = FrameworkCommunicationStressResult(
        transport="fake:target",
        chip_id="fake-chip",
        firmware_build_id="fake-build",
        rounds=2,
        transactions=6,
        elapsed_seconds=1.0,
        payload_bytes_round_trip=144,
        payload_throughput_bytes_per_second=144.0,
        error_count=0,
        classes=(
            PayloadClassSummary(
                name="small",
                payload_size=8,
                transactions=2,
                retry_count=0,
                latency=LatencySummary(1.0, 1.0, 1.0, 1.0),
            ),
        ),
    )
    payload = result.to_measurements()
    assert payload["measurement_schema"] == "et.measurement.v1"
    assert "status" not in payload
    assert "failure_reason" not in payload
    output = write_json_result(tmp_path / "result.json", payload)
    assert output.is_file()
    assert not (tmp_path / "result.json.tmp").exists()
