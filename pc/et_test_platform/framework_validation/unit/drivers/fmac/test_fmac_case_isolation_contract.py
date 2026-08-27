# FMAC Formal Case隔离合同测试。
#
# 职责：保证每个FMAC Case显式建立相同的三步隔离基线。
# 边界：只解析Case源码，不打开串口、不执行Formal Case。
# 依赖：仅依赖标准库AST和FMAC Case源码。

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[6]
FMAC_CASE_ROOT = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases" / "fmac"


# 将Attribute调用转换为便于匹配的点分名称；其他表达式返回空字符串。
def _call_name(node: ast.AST) -> str:

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


# 收集一个Case函数内部全部调用的源码行号和点分名称。
def _calls(function: ast.FunctionDef) -> tuple[tuple[int, str], ...]:

    return tuple(
        (node.lineno, _call_name(node.func))
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    )


# 测试Feature：全部FMAC Formal Case显式执行硬件、Service和Resource三步复位。
#
# 测试方法：解析P0至P3源码，逐函数定位三类reset调用的第一处源码行。
#
# 通过条件：23个Case均满足CRG reset早于state_reset，state_reset早于Resource reset。
def test_every_fmac_case_starts_with_visible_isolation_sequence() -> None:

    case_count = 0

    for path in sorted(FMAC_CASE_ROOT.glob("test_fmac_p*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for function in (
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_fmac_")
        ):
            case_count += 1
            calls = _calls(function)
            crg_lines = [line for line, name in calls if name.endswith(".crg.reset")]
            state_lines = [line for line, name in calls if name.endswith(".fmac.state_reset")]
            resource_lines = [line for line, name in calls if name.endswith(".resource.reset")]

            assert crg_lines, f"{function.name}缺少CRG FMAC复位"
            assert state_lines, f"{function.name}缺少FMAC Service状态复位"
            assert resource_lines, f"{function.name}缺少Resource Pool整池复位"
            assert min(crg_lines) < min(state_lines) < min(resource_lines), (
                f"{function.name}三步复位顺序错误"
            )

    assert case_count == 23
