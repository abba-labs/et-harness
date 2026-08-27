# Public IP Machine Contract资源等级回归测试。
#
# 职责：验证R120定义的R0-R5资源等级在SPEC和PLAN机器门禁中失败关闭。
# 边界：不加载业务Case、不执行硬件或报告。
# 依赖：正式SPEC/PLAN校验器和pytest。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[5]
CASE_DOC_VALIDATOR = ROOT / "tools" / "quality" / "validate_case_docs.py"
CASE_PLAN_VALIDATOR = ROOT / "tools" / "quality" / "validate_case_plans.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("minimum_level", "full_coverage_level", "must_fail"),
    [("R0", "R5", False), ("R9", "R9", True), ("R3", "R2", True)],
)
def test_case_spec_resource_levels_fail_closed(
    minimum_level: str,
    full_coverage_level: str,
    must_fail: bool,
) -> None:
    validator = _load(CASE_DOC_VALIDATOR, "case_doc_resource_level_validator")
    spec = {
        "timeout": "1 s",
        "cleanup": [],
        "resources": {
            "minimum_level": minimum_level,
            "full_coverage_level": full_coverage_level,
            "board": "无额外要求",
            "bench": "无额外要求",
        },
        "backend": ["FPGA"],
        "evidence": ["canonical result"],
        "gap": [],
    }

    codes = {
        item.code
        for item in validator._validate_execution_contract(
            Path("test_case_doc/test/test.md"), spec, case_id="TEST_P0_001"
        )
    }

    assert ("ETCASE418" in codes) is must_fail


@pytest.mark.parametrize(
    ("minimum_level", "full_coverage_level", "must_fail"),
    [("R0", "R5", False), ("R9", "R9", True), ("R3", "R2", True)],
)
def test_case_plan_resource_levels_fail_closed(
    minimum_level: str,
    full_coverage_level: str,
    must_fail: bool,
) -> None:
    validator = _load(CASE_PLAN_VALIDATOR, "case_plan_resource_level_validator")
    plan = {
        "resources": {
            "minimum_level": minimum_level,
            "full_coverage_level": full_coverage_level,
            "board": "无额外要求",
            "bench": "无额外要求",
        },
        "backend": ["FPGA"],
        "evidence": ["planned evidence"],
        "failure_observations": [{"role": "actual", "format": "text"}],
        "gap": [],
    }

    codes = {
        item.code
        for item in validator._validate_resource_contract(
            Path("test_case_doc/test/test.md"), plan, case_id="TEST_P0_001"
        )
    }

    assert ("ETPLAN222" in codes) is must_fail
