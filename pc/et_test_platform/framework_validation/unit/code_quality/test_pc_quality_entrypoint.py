# Framework Validation测试模块。
#
# 职责：验证test_pc_quality_entrypoint 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[5]
VALIDATOR = REPOSITORY_ROOT / "tools" / "validate_pc.py"
PYPROJECT = REPOSITORY_ROOT / "pyproject.toml"


def test_quality_entrypoint_is_standalone_and_covers_the_complete_software_scope() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), "--help"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    source = VALIDATOR.read_text(encoding="utf-8")

    assert "Unified non-hardware software validation" in completed.stdout
    for required in (
        "pc/et_test_platform",
        "check_pc_code_rules.py",
        "check_case_orchestration_rules.py",
        "UNIT_TEST_ROOT",
        "FORMAL_CASE_ROOT",
        "materialize_keil_validation_record.py",
    ):
        assert required in source


def test_quality_entrypoint_discovers_all_chip_manifests() -> None:
    spec = importlib.util.spec_from_file_location("et_validate_pc", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    manifests = module.firmware_manifests()

    assert manifests
    assert manifests == tuple(sorted(REPOSITORY_ROOT.glob("firmware/chips/*/project.yaml")))


def test_pyproject_enables_required_ruff_rule_families_without_allowlists() -> None:
    source = PYPROJECT.read_text(encoding="utf-8")

    assert '"ruff>=0.12"' in source
    assert "[tool.ruff.lint]" in source
    for family in ('"F"', '"I"', '"B"', '"UP"', '"SIM"', '"C90"'):
        assert family in source
    assert "[tool.ruff.lint.mccabe]" in source
    assert "[tool.ruff.lint.per-file-ignores]" not in source
    assert "C901" not in source
