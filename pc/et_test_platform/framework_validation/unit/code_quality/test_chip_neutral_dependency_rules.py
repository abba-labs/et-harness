# Framework Validation测试模块。
#
# 职责：验证test_chip_neutral_dependency_rules 对应的软件合同和回归行为。
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
    spec = importlib.util.spec_from_file_location("et_chip_neutral_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PC rule checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, source: str) -> Path:
    path = root / "pc/et_test_platform/scheduling/fixtures.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_case(root: Path, source: str) -> Path:
    path = root / "pc/et_test_platform/test_cases/dma/test_handshake.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_chip_extension(root: Path, source: str) -> Path:
    path = root / "pc/et_test_platform/profiles/chip_execution_mappings/et6801/dma_routes.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _rules(checker: ModuleType, path: Path, root: Path) -> set[str]:
    return {violation.rule for violation in checker.check_file(path, repository_root=root)}


def test_checker_rejects_common_chip_specific_execution_mapping_import(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Common fixture layer."""\n'
        "from et_test_platform.profiles.chip_execution_mappings.et6801 import "
        "DmaPeripheralDirection\n",
    )

    assert "ETPC212" in _rules(checker, path, tmp_path)


def test_checker_allows_chip_neutral_execution_mapping_import(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Common fixture layer."""\n'
        "from et_test_platform.profiles.chip_execution_mappings import DmaPeripheralDirection\n",
    )

    assert "ETPC212" not in _rules(checker, path, tmp_path)


def test_checker_rejects_case_chip_specific_execution_mapping_import(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        '"""DMA Case."""\n'
        "from et_test_platform.profiles.chip_execution_mappings.et6801 import "
        "DmaPeripheralDirection\n",
    )

    assert "ETPC212" in _rules(checker, path, tmp_path)


def test_checker_allows_case_chip_neutral_execution_mapping_import(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        '"""DMA Case."""\n'
        "from et_test_platform.profiles.chip_execution_mappings import "
        "DmaPeripheralDirection\n",
    )

    assert "ETPC212" not in _rules(checker, path, tmp_path)


def test_checker_rejects_concrete_chip_literal_in_common_production(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Common fixture layer."""\n\nDEFAULT_CHIP = "et6801"\n',
    )

    assert "ETPC213" in _rules(checker, path, tmp_path)


def test_checker_rejects_concrete_chip_literal_in_formal_case(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        '"""DMA Case for ET6801."""\n',
    )

    assert "ETPC213" in _rules(checker, path, tmp_path)


def test_checker_allows_chip_neutral_formal_case_wording(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        '"""DMA Case for the runtime-selected target chip."""\n',
    )

    assert "ETPC213" not in _rules(checker, path, tmp_path)


def test_checker_allows_runtime_chip_id_in_common_production(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        '"""Common fixture layer."""\n\n'
        "def select_chip(chip_id: str) -> str:\n"
        '    """Return the runtime chip identifier without specializing common code."""\n'
        "    return chip_id\n",
    )

    assert "ETPC213" not in _rules(checker, path, tmp_path)


def test_checker_allows_concrete_chip_literal_inside_chip_extension(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_chip_extension(
        tmp_path,
        '"""ET6801 execution facts.\n\n'
        "职责：保存 ET6801 已审核的芯片事实。\n"
        "边界：不执行硬件操作。\n"
        '依赖：仅依赖公共事实模型。\n"""\n\n'
        'CHIP_ID = "et6801"\n',
    )

    assert "ETPC213" not in _rules(checker, path, tmp_path)
