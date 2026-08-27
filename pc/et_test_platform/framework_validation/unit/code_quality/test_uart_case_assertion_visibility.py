# Framework Validation测试模块。
#
# 职责：验证test_uart_case_assertion_visibility 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[5]
UART_ROOT = ROOT / "pc" / "et_test_platform" / "test_cases" / "uart"
UART_CASES = tuple(UART_ROOT / f"test_uart_p{level}.py" for level in range(4))


# Keep UART transfer PASS conditions directly readable in each Formal Case.
def test_uart_transfer_assertions_do_not_hide_behind_require_match() -> None:

    helper_tree = ast.parse((UART_ROOT / "uart_helpers.py").read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "require_match"
        for node in helper_tree.body
    )

    for path in UART_CASES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "require_match"
            for node in ast.walk(tree)
        )
