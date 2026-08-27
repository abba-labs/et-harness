# Framework Validation测试模块。
#
# 职责：验证test_profile_dependency_rules 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[5]
CHECKER_PATH = REPOSITORY_ROOT / "tools" / "quality" / "check_pc_code_rules.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("et_profile_dependency_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PC rule checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, source: str) -> Path:
    path = root / "pc/et_test_platform/profiles/runtime_capabilities.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _rules(checker: ModuleType, path: Path, root: Path) -> set[str]:
    return {violation.rule for violation in checker.check_file(path, repository_root=root)}


def test_checker_rejects_profile_driver_and_target_dependencies(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Runtime capability facts."""\n'
        "from et_test_platform.clients.target import TargetClient\n"
        "from et_test_platform.drivers.framework import ServiceInfo\n",
    )

    assert {"ETPC210", "ETPC211"} <= _rules(checker, path, tmp_path)


def test_checker_accepts_profile_neutral_capability_dependencies(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Static capability facts."""\n'
        "from et_test_platform.profiles.capabilities import ChipCapabilities\n",
    )

    rules = _rules(checker, path, tmp_path)
    assert "ETPC210" not in rules
    assert "ETPC211" not in rules
