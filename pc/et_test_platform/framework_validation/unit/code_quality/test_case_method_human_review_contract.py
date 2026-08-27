# Public IP Case人审行语法回归测试。
#
# 职责：验证R120冻结的方法行格式、步骤数量和report_feature确定性生成在SPEC/PLAN门禁中失败关闭。
# 边界：只检查可确定静态判断的格式，不评价摘要专业性、Oracle充分性或测试语义质量。
# 依赖：正式Case method checker和pytest。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[5]
METHOD_VALIDATOR = ROOT / "tools" / "quality" / "validate_case_method_contract.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _valid_method(*, step_count: int = 6) -> dict[str, list[str]]:
    return {
        "inputs": [
            "参数矩阵：覆盖代表性合法参数组合。",
            "测试数据：使用确定性输入并生成独立Expected。",
        ],
        "steps": [
            f"执行阶段{index}：完成第{index}个真实测试动作。" for index in range(1, step_count + 1)
        ],
        "observations": [
            "硬件状态：读取稳定硬件端点并保存Actual。",
            "硬件数据：读取真实输出并与Expected建立对应关系。",
        ],
        "pass_criteria": [
            "覆盖完整性：计划参数实例全部执行。",
            "数据正确性：Actual必须与Expected一致。",
        ],
    }


@pytest.mark.parametrize("kind", ["spec", "plan"])
def test_valid_summary_body_grammar_is_accepted(kind: str) -> None:
    validator = _load(METHOD_VALIDATOR, f"method_validator_valid_{kind}")
    payload = {"method": _valid_method()}

    violations = validator._validate_method_payload(
        Path("test_case_doc/test/test.md"),
        payload,
        case_id="TEST_P0_001",
        kind=kind,
    )

    assert violations == []


@pytest.mark.parametrize(
    "line",
    [
        "直接执行测试动作。",
        "测试准备: 使用ASCII冒号。",
        "：正文存在但摘要为空。",
        "测试准备：",
        "步骤1：不能用编号占位摘要。",
        "测试过程：空泛摘要不能通过。",
        "测试准备：第一行\n第二行",
    ],
)
@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE430"), ("plan", "ETPLAN223")],
)
def test_invalid_method_line_fails_closed(
    line: str,
    kind: str,
    expected_code: str,
) -> None:
    validator = _load(METHOD_VALIDATOR, f"method_validator_line_{kind}_{abs(hash(line))}")
    method = _valid_method()
    method["inputs"] = [line]

    codes = {
        item.code
        for item in validator._validate_method_payload(
            Path("test_case_doc/test/test.md"),
            {"method": method},
            case_id="TEST_P0_001",
            kind=kind,
        )
    }

    assert expected_code in codes


@pytest.mark.parametrize("step_count", [5, 9])
@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE431"), ("plan", "ETPLAN224")],
)
def test_step_count_outside_six_to_eight_fails_closed(
    step_count: int,
    kind: str,
    expected_code: str,
) -> None:
    validator = _load(METHOD_VALIDATOR, f"method_validator_count_{kind}_{step_count}")

    codes = {
        item.code
        for item in validator._validate_method_payload(
            Path("test_case_doc/test/test.md"),
            {"method": _valid_method(step_count=step_count)},
            case_id="TEST_P0_001",
            kind=kind,
        )
    }

    assert expected_code in codes


def test_body_may_contain_additional_full_width_colons() -> None:
    validator = _load(METHOD_VALIDATOR, "method_validator_additional_colon")

    assert validator._line_violation_reason("状态读取：读取STATUS：期望FINISH=1。") is None


@pytest.mark.parametrize("kind", ["spec", "plan"])
def test_numbered_report_feature_projection_is_accepted(kind: str) -> None:
    validator = _load(METHOD_VALIDATOR, f"report_feature_valid_{kind}")
    payload = {
        "feature_refs": ["DMA_F_003", "DMA_F_005", "DMA_F_007"],
        "report_feature": (
            "1. DMA Channel Enable/Disable\n2. DMA Channel FREE状态\n3. DMA M2M传输"
        ),
    }
    feature_names = {
        "DMA_F_003": "DMA Channel Enable/Disable",
        "DMA_F_005": "DMA Channel FREE状态",
        "DMA_F_007": "DMA M2M传输",
    }

    violations = validator._validate_report_feature_payload(
        Path("test_case_doc/dma/dma.md"),
        payload,
        case_id="DMA_P0_001",
        kind=kind,
        feature_names=feature_names,
        raw_block="report_feature: |-\n  1. DMA Channel Enable/Disable",
    )

    assert violations == []


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE432"), ("plan", "ETPLAN225")],
)
def test_report_feature_requires_feature_refs(kind: str, expected_code: str) -> None:
    validator = _load(METHOD_VALIDATOR, f"report_feature_refs_{kind}")

    violations = validator._validate_report_feature_payload(
        Path("test_case_doc/test/test.md"),
        {"feature_refs": [], "report_feature": "1. TEST状态"},
        case_id="TEST_P0_001",
        kind=kind,
        feature_names={"TEST_F_001": "TEST状态"},
        raw_block="report_feature: |-\n  1. TEST状态",
    )

    assert {item.code for item in violations} == {expected_code}


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE433"), ("plan", "ETPLAN226")],
)
def test_every_feature_ref_requires_a_catalog_report_name(
    kind: str,
    expected_code: str,
) -> None:
    validator = _load(METHOD_VALIDATOR, f"report_feature_mapping_{kind}")

    violations = validator._validate_report_feature_payload(
        Path("test_case_doc/test/test.md"),
        {
            "feature_refs": ["TEST_F_001", "TEST_F_002"],
            "report_feature": "1. TEST状态\n2. TEST模式",
        },
        case_id="TEST_P0_001",
        kind=kind,
        feature_names={"TEST_F_001": "TEST状态"},
        raw_block="report_feature: |-\n  1. TEST状态\n  2. TEST模式",
    )

    assert {item.code for item in violations} == {expected_code}


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE434"), ("plan", "ETPLAN227")],
)
def test_report_feature_text_and_order_must_match_catalog(
    kind: str,
    expected_code: str,
) -> None:
    validator = _load(METHOD_VALIDATOR, f"report_feature_value_{kind}")

    violations = validator._validate_report_feature_payload(
        Path("test_case_doc/test/test.md"),
        {"feature_refs": ["TEST_F_001", "TEST_F_002"], "report_feature": "自由总结"},
        case_id="TEST_P0_001",
        kind=kind,
        feature_names={"TEST_F_001": "TEST模式", "TEST_F_002": "TEST状态"},
        raw_block="report_feature: |-\n  自由总结",
    )

    assert expected_code in {item.code for item in violations}


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [("spec", "ETCASE435"), ("plan", "ETPLAN228")],
)
def test_report_feature_requires_block_scalar(kind: str, expected_code: str) -> None:
    validator = _load(METHOD_VALIDATOR, f"report_feature_style_{kind}")

    violations = validator._validate_report_feature_payload(
        Path("test_case_doc/test/test.md"),
        {"feature_refs": ["TEST_F_001"], "report_feature": "1. TEST状态"},
        case_id="TEST_P0_001",
        kind=kind,
        feature_names={"TEST_F_001": "TEST状态"},
        raw_block='report_feature: "1. TEST状态"',
    )

    assert expected_code in {item.code for item in violations}
