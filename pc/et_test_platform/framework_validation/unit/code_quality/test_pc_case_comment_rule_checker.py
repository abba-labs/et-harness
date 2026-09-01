# Framework Validation测试模块。
#
# 职责：验证test_pc_case_comment_rule_checker 对应的软件合同和回归行为。
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
    spec = importlib.util.spec_from_file_location("et_pc_case_comment_rule_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PC rule checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_case(tmp_path: Path, comments: str, docstring: str) -> Path:
    path = tmp_path / "pc/et_test_platform/test_cases/dma/test_dma_p1.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    body_docstring = f'    """{docstring}"""\n' if docstring else ""
    path.write_text(
        "# DMA P1 hardware Cases。\n\n"
        "import pytest\n\n"
        "pytestmark = pytest.mark.hardware\n\n\n"
        f"{comments}"
        "def test_dma_p1_001() -> None:\n"
        "\n"
        "    # 执行：完成一个最小硬件动作并检查结果。\n"
        f"{body_docstring}"
        "    assert True\n",
        encoding="utf-8",
    )
    return path


def _rules(checker: ModuleType, path: Path, root: Path) -> set[str]:
    return {violation.rule for violation in checker.check_file(path, repository_root=root)}


def test_checker_accepts_numbered_codex_dev_case_comments(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        "# 测试 Feature：\n"
        "# DMA 基础传输。\n"
        "# 测试方法：\n"
        "# 1. 配置 DMA。\n"
        "# 2. 启动并观测。\n"
        "# 通过条件：\n"
        "# 1. 数据匹配。\n"
        "# 2. Channel Free。\n",
        "",
    )

    assert "ETPC104" not in _rules(checker, path, tmp_path)


def test_checker_rejects_unnumbered_codex_dev_case_comments(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        "# 测试 Feature：\n"
        "# DMA 基础传输。\n"
        "# 测试方法：\n"
        "# 配置 DMA 并启动。\n"
        "# 通过条件：\n"
        "# 数据匹配。\n",
        "",
    )

    assert "ETPC104" in _rules(checker, path, tmp_path)


def test_checker_rejects_legacy_eight_section_docstring(tmp_path: Path) -> None:
    checker = _load_checker()
    legacy_docstring = " ".join(
        (
            "测试 Feature：DMA。",
            "主要测试主体：DMA。",
            "参与/支撑 IP：Framework。",
            "前置条件：Hardware Gate。",
            "测试步骤：执行 DMA。",
            "观测证据：状态。",
            "通过条件：数据匹配。",
            "清理要求：恢复状态。",
        )
    )
    path = _write_case(tmp_path, "", legacy_docstring)

    assert "ETPC104" in _rules(checker, path, tmp_path)


def test_checker_rejects_missing_blank_line_and_body_comment(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        "# 测试 Feature：\n"
        "# DMA 基础传输。\n"
        "# 测试方法：\n"
        "# 1. 配置并启动。\n"
        "# 通过条件：\n"
        "# 1. 数据匹配。\n",
        "",
    )
    source = path.read_text(encoding="utf-8")
    source = source.replace(
        "def test_dma_p1_001() -> None:\n\n    # 执行：完成一个最小硬件动作并检查结果。\n",
        "def test_dma_p1_001() -> None:\n",
    )
    path.write_text(source, encoding="utf-8")

    assert "ETPC105" in _rules(checker, path, tmp_path)


def test_checker_rejects_explicit_loop_without_business_comment(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write_case(
        tmp_path,
        "# 测试 Feature：\n"
        "# DMA 基础传输。\n"
        "# 测试方法：\n"
        "# 1. 遍历配置并启动。\n"
        "# 通过条件：\n"
        "# 1. 数据匹配。\n",
        "",
    )
    source = path.read_text(encoding="utf-8").replace(
        "    assert True\n",
        "    values = []\n    for value in range(2):\n        values.append(value)\n",
    )
    path.write_text(source, encoding="utf-8")

    assert "ETPC106" in _rules(checker, path, tmp_path)
