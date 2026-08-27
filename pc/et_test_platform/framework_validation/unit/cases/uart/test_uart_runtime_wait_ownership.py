# Framework Validation测试模块。
#
# 职责：验证test_uart_runtime_wait_ownership 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[6]
UART_ROOT = ROOT / "pc/et_test_platform/test_cases/uart"
UART_CASE_FILES = (
    "test_uart_p0.py",
    "test_uart_p1.py",
    "test_uart_p2.py",
    "test_uart_p3.py",
)

_ALLOWED_CASE_SLEEP = {
    ("test_uart_p1.py", "test_uart_p1_010_break_send_and_detect"),
    ("test_uart_p2.py", "test_uart_p2_006_automatic_flow_control"),
}


def _time_sleep_owners(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    owners: set[tuple[str, str]] = set()
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "time"
                and node.func.attr == "sleep"
            ):
                owners.add((path.name, function.name))
    return owners


def test_uart_case_sleep_is_limited_to_explicit_feature_stimulus_or_observation() -> None:
    owners = set()
    for filename in UART_CASE_FILES:
        owners.update(_time_sleep_owners(UART_ROOT / filename))
    assert owners == _ALLOWED_CASE_SLEEP


def test_uart_cases_call_driver_capture_wait_directly() -> None:
    helper_source = (UART_ROOT / "uart_helpers.py").read_text(encoding="utf-8")
    assert "wait_capture" not in helper_source
    assert "capture_wait(" not in helper_source

    direct_wait_calls = 0
    legacy_wait_calls = 0
    for filename in UART_CASE_FILES:
        source = (UART_ROOT / filename).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filename)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "wait_capture":
                legacy_wait_calls += 1
            if isinstance(node.func, ast.Attribute) and node.func.attr == "capture_wait":
                direct_wait_calls += 1

    assert legacy_wait_calls == 0
    assert direct_wait_calls > 0


def test_uart_case_completion_wait_does_not_reimplement_capture_polling() -> None:
    helpers = (UART_ROOT / "uart_helpers.py").read_text(encoding="utf-8")
    assert "capture_get()" not in helpers
    assert "irq_state_get()" not in helpers
    assert "time.sleep(" not in helpers
