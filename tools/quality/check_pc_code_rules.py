# Lightweight AST architecture rules for the PC control plane.
#
# The checker enforces stable dependency and readability boundaries without
# executing project code. During migration the caller chooses an explicit scope;
# new files must never be hidden in an allowlist.

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

_CASE_COMMENT_SECTIONS = (
    "测试 Feature：",
    "测试方法：",
    "通过条件：",
)
_VAGUE_FILE_NAMES = {"base.py", "common.py", "helpers.py", "misc.py", "utils.py"}
_MODEL_FORBIDDEN_METHODS = {"decode", "encode", "request", "send"}
_NEUTRAL_EXECUTION_MAPPING_MODULES = {"dma_routes"}
_CHIP_ID_TOKEN = re.compile(r"\bet\d+\b", re.IGNORECASE)
_DRIVER_ENVIRONMENT_PACKAGES = {"profiles", "scheduling", "instruments"}


# One stable rule violation reported by path and source line.
@dataclass(frozen=True, slots=True, order=True)
class RuleViolation:
    path: Path
    line: int
    rule: str
    message: str

    # Render a deterministic compiler-style diagnostic.
    def render(self, root: Path) -> str:

        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}:{self.line}: {self.rule} {self.message}"


# Check Python files below explicit files/directories and return all violations.
def check_paths(paths: Iterable[Path], *, repository_root: Path) -> list[RuleViolation]:

    files: set[Path] = set()
    for path in paths:
        resolved = path if path.is_absolute() else repository_root / path
        if resolved.is_dir():
            files.update(resolved.rglob("*.py"))
        elif resolved.suffix == ".py" and resolved.is_file():
            files.add(resolved)
    violations: list[RuleViolation] = []
    for path in sorted(files):
        violations.extend(check_file(path, repository_root=repository_root))
    return sorted(violations)


# Check one Python module without importing or executing it.
def check_file(path: Path, *, repository_root: Path) -> list[RuleViolation]:

    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return [
            RuleViolation(
                path=path,
                line=error.lineno or 1,
                rule="ETPC000",
                message=f"syntax error: {error.msg}",
            )
        ]

    relative = _relative(path, repository_root)
    violations: list[RuleViolation] = []
    if not _leading_module_comment(source):
        violations.append(
            RuleViolation(path, 1, "ETPC001", "module is missing a leading # comment")
        )
    if path.name in _VAGUE_FILE_NAMES:
        violations.append(RuleViolation(path, 1, "ETPC411", "new vague file name is forbidden"))

    violations.extend(_check_no_docstrings(path, tree))
    violations.extend(_check_import_rules(path, relative, tree))
    violations.extend(_check_chip_literals(path, relative, tree))
    violations.extend(_check_model_methods(path, tree))
    violations.extend(_check_driver_struct_calls(path, relative, tree))
    violations.extend(_check_exception_and_assert_rules(path, relative, tree))
    violations.extend(_check_public_annotations(path, relative, tree))
    violations.extend(_check_public_comments(path, relative, source, tree))
    violations.extend(_check_hardware_cases(path, relative, source, tree))
    violations.extend(_check_hardware_case_layout(path, relative, source, tree))
    return violations


def _check_import_rules(
    path: Path,
    relative: Path,
    tree: ast.Module,
) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    production = _is_production(relative)
    current_driver = _driver_name(relative) if production else None
    is_codec = path.name == "codec.py"
    is_case = "test_cases" in relative.parts
    is_profile = production and "profiles" in relative.parts
    is_resolver = is_profile and "resolvers" in relative.parts

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        modules = _imported_modules(node)
        for module in modules:
            imported_driver = _imported_driver_name(module)
            module_parts = module.lstrip(".").split(".")
            imports_driver_package = "drivers" in module_parts
            imports_target_client = module_parts[-2:] == ["clients", "target"]
            imports_driver_environment = (
                bool(_DRIVER_ENVIRONMENT_PACKAGES.intersection(module_parts))
                or module.lstrip(".") == "pytest"
            )
            if (production or is_case) and _imports_chip_specific_execution_mapping(module):
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC212",
                        "chip-neutral PC code imports a chip-specific execution mapping",
                    )
                )
            if current_driver is not None and imports_driver_environment:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC214",
                        "Driver imports environment/test orchestration instead of staying single-IP",
                    )
                )
            if (
                current_driver is not None
                and imported_driver is not None
                and imported_driver != current_driver
            ):
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC006",
                        "Driver imports another IP Driver",
                    )
                )
            if is_codec and imports_target_client:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC206",
                        "Codec imports TargetClient",
                    )
                )
            if is_resolver and imports_driver_package:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC208",
                        "Resolver imports a Driver package instead of neutral facts/contracts",
                    )
                )
            elif is_profile and imports_driver_package:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC210",
                        "Profile/Capability imports a Driver package instead of neutral facts",
                    )
                )
            if is_resolver and imports_target_client:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC209",
                        "Resolver imports TargetClient and can execute hardware commands",
                    )
                )
            elif is_profile and imports_target_client:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC211",
                        "Profile/Capability imports TargetClient across the control-plane boundary",
                    )
                )
            if is_case and _case_import_is_forbidden(module):
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC207",
                        "Test Case imports Codec, Contract or Transport",
                    )
                )
    return violations


def _check_chip_literals(
    path: Path,
    relative: Path,
    tree: ast.Module,
) -> list[RuleViolation]:
    is_case = "test_cases" in relative.parts
    if not (_is_production(relative) or is_case) or _is_chip_extension(relative):
        return []
    violations: list[RuleViolation] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _CHIP_ID_TOKEN.search(node.value)
        ):
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC213",
                    "chip-neutral PC code hard-codes a concrete chip ID",
                )
            )
    return violations


def _check_model_methods(path: Path, tree: ast.Module) -> list[RuleViolation]:
    if path.name != "models.py":
        return []
    return [
        RuleViolation(
            path,
            node.lineno,
            "ETPC202",
            f"Model defines forbidden method {node.name}()",
        )
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in _MODEL_FORBIDDEN_METHODS
    ]


def _check_driver_struct_calls(
    path: Path,
    relative: Path,
    tree: ast.Module,
) -> list[RuleViolation]:
    if not _is_driver_implementation(relative):
        return []
    violations: list[RuleViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "struct"
            and node.func.attr in {"pack", "unpack", "pack_into", "unpack_from"}
        ):
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC205",
                    "Driver directly calls struct.pack/unpack",
                )
            )
    return violations


def _check_exception_and_assert_rules(
    path: Path,
    relative: Path,
    tree: ast.Module,
) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    production = _is_production(relative)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ExceptHandler)
            and _is_exception_handler(node)
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Pass)
        ):
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC401",
                    "except Exception: pass hides a failure",
                )
            )
        if production and isinstance(node, ast.Assert):
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC403",
                    "production code must not use assert",
                )
            )
    return violations


def _check_public_annotations(
    path: Path,
    relative: Path,
    tree: ast.Module,
) -> list[RuleViolation]:
    if not _is_production(relative):
        return []
    violations: list[RuleViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        missing_argument = any(
            argument.arg not in {"self", "cls"} and argument.annotation is None
            for argument in arguments
        )
        if node.args.vararg is not None and node.args.vararg.annotation is None:
            missing_argument = True
        if node.args.kwarg is not None and node.args.kwarg.annotation is None:
            missing_argument = True
        if missing_argument or node.returns is None:
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC410",
                    f"public API {node.name}() lacks complete type annotations",
                )
            )
    return violations


# Require useful leading comments on public production entry points only.
def _check_public_comments(
    path: Path,
    relative: Path,
    source: str,
    tree: ast.Module,
) -> list[RuleViolation]:

    if not _is_production(relative):
        return []
    public_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_nodes.append(node)
            continue
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        public_nodes.extend(
            child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not child.name.startswith("_")
        )

    violations: list[RuleViolation] = []
    for node in public_nodes:
        comment = _leading_case_comment(source, node).strip()
        if not comment:
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC412",
                    f"public API {node.name}() is missing a leading responsibility comment",
                )
            )
            continue
        comment_text = " ".join(line.lstrip("# ") for line in comment.splitlines()).strip()
        if len(comment_text) < 24 or comment_text.lower() in {"todo", "tbd", "none"}:
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC413",
                    f"public API {node.name}() leading comment is too weak to explain behavior",
                )
            )
    return violations


# Reject module, class and function docstrings in project-owned Python.
def _check_no_docstrings(path: Path, tree: ast.Module) -> list[RuleViolation]:

    violations: list[RuleViolation] = []
    owners: list[ast.AST] = [tree]
    owners.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )
    for owner in owners:
        if ast.get_docstring(owner, clean=False) is None:
            continue
        line = getattr(owner, "lineno", 1)
        name = getattr(owner, "name", "module")
        violations.append(
            RuleViolation(
                path,
                line,
                "ETPC414",
                f"{name} documentation must use a leading # comment, not a docstring",
            )
        )
    return violations


# Return the file-header comment block before the first Python statement.
def _leading_module_comment(source: str) -> str:

    lines = source.splitlines()
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    block: list[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            if block:
                break
            index += 1
            continue
        if not stripped.startswith("#"):
            break
        block.append(lines[index])
        index += 1
    return "\n".join(block)


# Return the contiguous comment block immediately before a Case definition.
def _leading_case_comment(source: str, node: ast.AST) -> str:

    lines = source.splitlines()
    decorators = getattr(node, "decorator_list", ())
    anchor = min((decorator.lineno for decorator in decorators), default=node.lineno) - 1
    index = anchor - 1
    block: list[str] = []
    while index >= 0:
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            break
        block.append(lines[index])
        index -= 1
    return "\n".join(reversed(block))


def _has_numbered_case_items(block: str, heading: str, next_heading: str | None) -> bool:
    start = block.find(heading)
    if start < 0:
        return False
    end = block.find(next_heading, start + len(heading)) if next_heading else len(block)
    section = block[start : end if end >= 0 else len(block)]
    return re.search(r"(?m)^#\s+1\.\s+\S", section) is not None


def _check_hardware_cases(
    path: Path,
    relative: Path,
    source: str,
    tree: ast.Module,
) -> list[RuleViolation]:
    if "test_cases" not in relative.parts or "pytest.mark.hardware" not in source:
        return []
    violations: list[RuleViolation] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        comment = _leading_case_comment(source, node)
        missing_comments = [section for section in _CASE_COMMENT_SECTIONS if section not in comment]
        comment_is_complete = not missing_comments
        if comment_is_complete:
            numbered_methods = _has_numbered_case_items(
                comment,
                _CASE_COMMENT_SECTIONS[1],
                _CASE_COMMENT_SECTIONS[2],
            )
            numbered_conditions = _has_numbered_case_items(
                comment,
                _CASE_COMMENT_SECTIONS[2],
                None,
            )
            if not numbered_methods or not numbered_conditions:
                violations.append(
                    RuleViolation(
                        path,
                        node.lineno,
                        "ETPC104",
                        "hardware Case methods and pass conditions must use numbered # comments",
                    )
                )
            continue

        violations.append(
            RuleViolation(
                path,
                node.lineno,
                "ETPC104",
                "hardware Case comments miss: " + ", ".join(missing_comments),
            )
        )
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        for node in tree.body
    ):
        violations.append(RuleViolation(path, 1, "ETPC301", "hardware module has no test Case"))
    return violations


# Enforce the small set of Case-body layout rules that are deterministic.
def _check_hardware_case_layout(
    path: Path,
    relative: Path,
    source: str,
    tree: ast.Module,
) -> list[RuleViolation]:

    if "test_cases" not in relative.parts or "pytest.mark.hardware" not in source:
        return []
    lines = source.splitlines()
    violations: list[RuleViolation] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_") or not node.body:
            continue
        signature_end = _function_signature_end(lines, node)
        if signature_end >= len(lines) or lines[signature_end].strip():
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC105",
                    "hardware Case signature must be followed by one blank line",
                )
            )
        body_lines = lines[signature_end + 1 : node.end_lineno]
        if not any(line.lstrip().startswith("#") for line in body_lines):
            violations.append(
                RuleViolation(
                    path,
                    node.lineno,
                    "ETPC105",
                    "hardware Case body must contain business-purpose # comments",
                )
            )
        for loop in ast.walk(node):
            if not isinstance(loop, (ast.For, ast.While)):
                continue
            if not _previous_significant_line_is_comment(lines, loop.lineno):
                violations.append(
                    RuleViolation(
                        path,
                        loop.lineno,
                        "ETPC106",
                        "explicit Case loop must have an immediately preceding business comment",
                    )
                )
    return violations


# Return the zero-based line immediately after a function signature.
def _function_signature_end(
    lines: list[str],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:

    first_body_line = node.body[0].lineno - 1
    for index in range(node.lineno - 1, first_body_line):
        if lines[index].rstrip().endswith(":"):
            return index + 1
    return first_body_line


# Return whether the nearest nonblank line before a statement is a comment.
def _previous_significant_line_is_comment(lines: list[str], line_number: int) -> bool:

    index = line_number - 2
    while index >= 0 and not lines[index].strip():
        index -= 1
    return index >= 0 and lines[index].lstrip().startswith("#")


def _relative(path: Path, repository_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return path


def _driver_name(relative: Path) -> str | None:
    if "drivers" not in relative.parts:
        return None
    index = relative.parts.index("drivers")
    if index + 1 >= len(relative.parts):
        return None
    candidate = relative.parts[index + 1]
    if candidate == "__init__.py":
        return None
    return Path(candidate).stem


# Return whether a path is a monolithic Driver or package driver.py.
def _is_driver_implementation(relative: Path) -> bool:

    if "drivers" not in relative.parts:
        return False
    index = relative.parts.index("drivers")
    trailing = relative.parts[index + 1 :]
    if len(trailing) == 1:
        return trailing[0].endswith(".py") and trailing[0] != "__init__.py"
    return len(trailing) == 2 and trailing[1] == "driver.py"


def _imported_modules(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    prefix = "." * node.level
    module = node.module or ""
    return (prefix + module,)


def _imported_driver_name(module: str) -> str | None:
    normalized = module.lstrip(".")
    parts = normalized.split(".")
    if "drivers" not in parts:
        return None
    index = parts.index("drivers")
    return parts[index + 1] if index + 1 < len(parts) else None


def _imports_chip_specific_execution_mapping(module: str) -> bool:
    parts = [part for part in module.lstrip(".").split(".") if part]
    if "chip_execution_mappings" not in parts:
        return False
    index = parts.index("chip_execution_mappings")
    if index + 1 >= len(parts):
        return False
    return parts[index + 1] not in _NEUTRAL_EXECUTION_MAPPING_MODULES


def _is_chip_extension(relative: Path) -> bool:
    parts = relative.parts
    for marker in ("chip_capabilities", "chip_execution_mappings"):
        if marker not in parts:
            continue
        index = parts.index(marker)
        if index + 1 < len(parts) and _CHIP_ID_TOKEN.fullmatch(parts[index + 1]):
            return True
    return False


def _case_import_is_forbidden(module: str) -> bool:
    parts = module.lstrip(".").split(".")
    return (
        "codec" in parts
        or "contract" in parts
        or ("communication" in parts and "protocols" in parts)
        or parts[-2:] == ["communication", "transport"]
        or "transports" in parts
    )


def _is_exception_handler(node: ast.ExceptHandler) -> bool:
    if node.type is None:
        return False
    return isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}


def _is_production(relative: Path) -> bool:
    parts = relative.parts
    return (
        len(parts) >= 3
        and parts[0:2] == ("pc", "et_test_platform")
        and "framework_validation" not in parts
        and "test_cases" not in parts
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check PC architecture and code rules.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


# Run the checker CLI and return a shell-compatible exit status.
def main(argv: Sequence[str] | None = None) -> int:

    args = _parse_args(argv)
    root = args.root.resolve()
    violations = check_paths(args.paths, repository_root=root)
    for violation in violations:
        print(violation.render(root))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
