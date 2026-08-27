# Framework Validation测试模块。
#
# 职责：验证test_pc_case_comment_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[6]
CASE_ROOT = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases"
REQUIRED_COMMENTS = ("测试 Feature：", "测试方法：", "通过条件：")


def _test_functions(path: Path) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _leading_comment(path: Path, function: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    anchor = (
        min(
            (decorator.lineno for decorator in function.decorator_list),
            default=function.lineno,
        )
        - 1
    )
    index = anchor - 1
    block: list[str] = []
    while index >= 0 and (not lines[index].strip() or lines[index].lstrip().startswith("#")):
        block.append(lines[index])
        index -= 1
    return "\n".join(reversed(block))


def _has_numbered_items(block: str, heading: str, next_heading: str | None) -> bool:
    start = block.find(heading)
    end = block.find(next_heading, start + len(heading)) if next_heading else len(block)
    section = block[start : end if end >= 0 else len(block)]
    return re.search(r"(?m)^#\s+1\.\s+\S", section) is not None


# Keep ownership, evidence, assertions and cleanup visible at the Case boundary.
def test_all_pc_cases_use_structured_reviewable_descriptions() -> None:

    violations: list[str] = []
    for path in sorted(CASE_ROOT.rglob("test_*.py")):
        for function in _test_functions(path):
            location = f"{path.relative_to(PROJECT_ROOT)}:{function.lineno}"
            comment = _leading_comment(path, function)
            if all(section in comment for section in REQUIRED_COMMENTS):
                indexes = [comment.find(section) for section in REQUIRED_COMMENTS]
                if indexes != sorted(indexes):
                    violations.append(f"{location}: Case comment sections are out of order")
                if not _has_numbered_items(comment, REQUIRED_COMMENTS[1], REQUIRED_COMMENTS[2]):
                    violations.append(f"{location}: test methods are not numbered")
                if not _has_numbered_items(comment, REQUIRED_COMMENTS[2], None):
                    violations.append(f"{location}: pass conditions are not numbered")
                continue

            missing = [section for section in REQUIRED_COMMENTS if section not in comment]
            violations.append(f"{location}: missing comment sections {missing}")

    assert violations == [], "PC Case description contract violations:\n" + "\n".join(violations)
