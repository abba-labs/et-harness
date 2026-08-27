#!/usr/bin/env python3
# Reject Test Case helpers that hide lifecycle orchestration or conclusions.
# Formal Cases keep device lifecycle visible: only the common cleanup scope
# and pytest.raises() may use ``with`` in a test body.

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

_HELPER_EXEMPT_FILES = {
    "__init__.py",
    "case_cleanup.py",
    "conftest.py",
    "deferred_features.py",
}
_FORBIDDEN_CASE_HELPERS = {
    "_cleanup_all",
    "execute_dma_transfer_done_interrupt",
    "execute_framework_echo_stress",
    "execute_m2m_transfer",
    "execute_peripheral_transfer",
    "cleanup_uart",
    "uart_cleanup_scope",
    "require_uart_runtime_feature",
}
_BLOCKED_HELPER_NAMES = {"_design_blocked", "_blocked_by_observability"}
_BLOCKED_SKIP_PREFIXES = ("blocked_by_design", "blocked_by_observability")
_SUPPORT_DRIVERS = {"framework", "resource"}
_ALLOWED_FORMAL_CASE_CONTEXTS = {"case_cleanup_scope"}
_PHASE_CALLS = {
    "arrange": {
        "create",
        "fill",
        "initialize",
        "open",
        "reset",
        "write",
    },
    "configure": {
        "capture_start",
        "configure",
        "configure_route",
        "controller_enable",
        "dma_enable_set",
        "fifo_config",
        "irq_enable",
        "loopback_set",
    },
    "start": {
        "echo",
        "exchange",
        "start",
        "start_channels",
        "write_9bit",
    },
    "observe": {
        "capture_get",
        "capture_wait",
        "channel_status",
        "irq_result_get",
        "read",
        "read_9bit",
        "status_get",
        "wait_capture",
        "wait_channel_free",
        "wait_for_irq_count",
    },
    "cleanup": {
        "break_set",
        "capture_cancel",
        "close",
        "controller_disable",
        "deconfigure",
        "deinitialize",
        "dma_enable_set",
        "dma_mode_set",
        "flow_control_set",
        "halt_set",
        "interrupt_mask_disable",
        "irq_disable",
        "irq_config",
        "loopback_set",
        "nine_bit_config",
        "release_dma_request",
        "release_routes",
        "reset",
        "stop",
    },
}
_SUPPORT_FORBIDDEN_CALLS = {
    call_name for phase_calls in _PHASE_CALLS.values() for call_name in phase_calls
} | {
    "capture_mode",
    "configured_channel",
    "controller_mode",
    "initialized_mode",
    "irq_mode",
    "loopback_disable_on_exit",
}


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: Path
    line: int
    code: str
    message: str

    def render(self, root: Path) -> str:
        try:
            display = self.path.resolve().relative_to(root.resolve())
        except ValueError:
            display = self.path
        return f"{display}:{self.line}: {self.code} {self.message}"


def _called_attributes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _phases(calls: set[str]) -> set[str]:
    return {phase for phase, phase_calls in _PHASE_CALLS.items() if calls.intersection(phase_calls)}


def _forbidden_calls(path: Path, tree: ast.Module) -> list[Violation]:
    return [
        Violation(
            path,
            node.lineno,
            "ETORCH101",
            f"formal Case calls forbidden complete helper {node.func.id}()",
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FORBIDDEN_CASE_HELPERS
    ]


# Keep TargetClient and Driver construction out of the Case layer.
def _control_plane_construction_violations(path: Path, tree: ast.Module) -> list[Violation]:

    if "test_cases" not in path.parts:
        return []
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith("clients.target") and any(
                alias.name == "TargetClient" for alias in node.names
            ):
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        "ETORCH210",
                        "Case layer imports TargetClient; use Fixture/Support-provided Drivers",
                    )
                )
            continue
        if not isinstance(node, ast.Call):
            continue
        constructor = None
        if isinstance(node.func, ast.Name):
            constructor = node.func.id
        elif isinstance(node.func, ast.Attribute):
            constructor = node.func.attr
        if constructor == "TargetClient":
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETORCH210",
                    "Case layer constructs TargetClient; communication belongs to Fixture/Support",
                )
            )
        elif (
            constructor is not None
            and constructor.endswith("Driver")
            and not _is_ip_local_support(path)
        ):
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETORCH211",
                    f"Case layer constructs {constructor}; Driver construction belongs to Fixture/Support",
                )
            )
    return violations


# Return whether *path* is the narrowly approved IP-local Support boundary.
def _is_ip_local_support(path: Path) -> bool:

    try:
        test_cases_index = path.parts.index("test_cases")
    except ValueError:
        return False
    relative_parts = path.parts[test_cases_index + 1 :]
    return len(relative_parts) == 2 and path.name in {"_support.py", "conftest.py"}


# Keep IP-local Support limited to gates, facts, resolution and Driver construction.
def _ip_local_support_violations(path: Path, tree: ast.Module) -> list[Violation]:

    if not _is_ip_local_support(path):
        return []
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETORCH213",
                    "IP-local Support owns a final assert; conclusions belong to the formal Case",
                )
            )
            continue
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _SUPPORT_FORBIDDEN_CALLS:
            continue
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH212",
                f"IP-local Support calls {node.func.attr}(); hardware workflow belongs to the formal Case",
            )
        )
    return violations


def _raises_conclusion_with_case_id(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    has_case_id = any(
        argument.arg == "case_id"
        for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    )
    return has_case_id and any(isinstance(item, ast.Raise) for item in ast.walk(node))


def _helper_violation_checks(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Violation]:
    calls = _called_attributes(node)
    phases = _phases(calls)
    violations: list[Violation] = []
    has_assert = any(isinstance(item, ast.Assert) for item in ast.walk(node))
    has_finally = any(isinstance(item, ast.Try) and item.finalbody for item in ast.walk(node))
    raises_assertion = any(
        isinstance(item, ast.Raise)
        and isinstance(item.exc, ast.Call)
        and isinstance(item.exc.func, ast.Name)
        and item.exc.func.id == "AssertionError"
        for item in ast.walk(node)
    )
    if node.name in _BLOCKED_HELPER_NAMES:
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH208",
                f"blocked feature helper {node.name}() must live in deferred_features.py",
            )
        )
    if has_assert or raises_assertion:
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH201",
                f"helper {node.name}() owns a final assertion/conclusion",
            )
        )
    if len(phases) >= 3:
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH202",
                f"helper {node.name}() hides Case phases: {', '.join(sorted(phases))}",
            )
        )
    if has_finally and len(phases) >= 2:
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH203",
                f"helper {node.name}() owns lifecycle cleanup",
            )
        )
    if node.name.startswith("execute_") and phases:
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH204",
                f"execute_* helper {node.name}() is forbidden for formal Cases",
            )
        )
    if _raises_conclusion_with_case_id(node):
        violations.append(
            Violation(
                path,
                node.lineno,
                "ETORCH207",
                f"helper {node.name}() raises a Case-specific conclusion; return facts instead",
            )
        )
    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue
        if (
            not _is_ip_local_support(path)
            and isinstance(item.func, ast.Attribute)
            and isinstance(item.func.value, ast.Name)
            and item.func.value.id == "pytest"
            and item.func.attr == "skip"
        ):
            violations.append(
                Violation(
                    path,
                    item.lineno,
                    "ETORCH209",
                    f"helper {node.name}() owns pytest.skip; capability decisions belong to the Case",
                )
            )
    return violations


def _imported_driver_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        parts = node.module.split(".")
        if "drivers" not in parts:
            continue
        index = parts.index("drivers")
        if index + 1 < len(parts):
            names.add(parts[index + 1])
        elif index + 1 == len(parts):
            names.update(alias.name for alias in node.names)
    return {name for name in names if name not in _SUPPORT_DRIVERS}


def _cross_ip_helper_violation(path: Path, tree: ast.Module) -> list[Violation]:
    if (
        path.name.startswith("test_")
        or path.name in _HELPER_EXEMPT_FILES
        or _is_ip_local_support(path)
    ):
        return []
    drivers = _imported_driver_names(tree)
    if len(drivers) <= 1:
        return []
    return [
        Violation(
            path,
            1,
            "ETORCH205",
            "helper module imports multiple IP Drivers and hides cross-IP orchestration: "
            + ", ".join(sorted(drivers)),
        )
    ]


def _nested_helpers(
    test_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(test_node):
        if node is test_node or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "cleanup_actions":
            continue
        yield node


# Return the stable leaf name of a called context manager.
def _context_call_name(expression: ast.expr) -> str | None:

    if not isinstance(expression, ast.Call):
        return None
    if isinstance(expression.func, ast.Name):
        return expression.func.id
    if isinstance(expression.func, ast.Attribute):
        return expression.func.attr
    return None


# Keep lifecycle orchestration visible in every Formal Case.
def _formal_case_context_manager_violations(
    path: Path,
    test_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Violation]:

    violations: list[Violation] = []
    for node in ast.walk(test_node):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            expression = item.context_expr
            name = _context_call_name(expression)
            if name in _ALLOWED_FORMAL_CASE_CONTEXTS:
                continue
            if (
                name == "raises"
                and isinstance(expression, ast.Call)
                and isinstance(expression.func, ast.Attribute)
                and isinstance(expression.func.value, ast.Name)
                and expression.func.value.id == "pytest"
            ):
                continue
            violations.append(
                Violation(
                    path,
                    expression.lineno,
                    "ETORCH214",
                    "formal Case uses a hidden context-manager lifecycle; use direct "
                    "Driver calls with try/finally or case_cleanup_scope()",
                )
            )
    return violations


def _blocked_formal_case_violations(
    path: Path,
    test_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(test_node):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_HELPER_NAMES:
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETORCH208",
                    "formal test_* must not represent an unapproved design/observability requirement",
                )
            )
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest"
            and node.func.attr == "skip"
        ):
            continue
        messages = [
            item.value
            for item in node.args
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if any(message.startswith(_BLOCKED_SKIP_PREFIXES) for message in messages):
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETORCH208",
                    "blocked design/observability requirement must move to deferred_features.py",
                )
            )
    return violations


def check_file(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = _forbidden_calls(path, tree)
    violations.extend(_control_plane_construction_violations(path, tree))
    violations.extend(_ip_local_support_violations(path, tree))
    violations.extend(_cross_ip_helper_violation(path, tree))
    if path.name in _HELPER_EXEMPT_FILES:
        return violations

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("test_"):
            violations.extend(_blocked_formal_case_violations(path, node))
            violations.extend(_formal_case_context_manager_violations(path, node))
            for nested in _nested_helpers(node):
                violations.extend(_helper_violation_checks(path, nested))
            continue
        violations.extend(_helper_violation_checks(path, node))
    return violations


def check_paths(paths: Iterable[Path], *, root: Path) -> list[Violation]:
    files: set[Path] = set()
    for supplied in paths:
        path = supplied if supplied.is_absolute() else root / supplied
        if path.is_dir():
            files.update(path.rglob("*.py"))
        elif path.suffix == ".py" and path.is_file():
            files.add(path)
    violations: list[Violation] = []
    for path in sorted(files):
        violations.extend(check_file(path))
    return sorted(violations)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Formal Case orchestration boundaries.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.root.resolve()
    violations = check_paths(args.paths, root=root)
    for violation in violations:
        print(violation.render(root))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
