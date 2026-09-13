#!/usr/bin/env python3
# Enforce the PC documentation contract from R220_python_style_quality.md.

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

_CJK = re.compile(r"[\u4e00-\u9fff]")
_MODULE_SECTIONS = ("职责：", "边界：", "依赖：")
_GENERIC_DOC_FRAGMENTS = (
    "while preserving this module's documented responsibility boundary",
    "execute ``",
    "对应的运行时测试上下文事实",
)
_OPERATION_SEMANTICS = ("等待", "不等待", "Deadline", "超时", "失败", "异常", "拒绝", "错误")


@dataclass(frozen=True, slots=True, order=True)
class DocumentationViolation:
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


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def _is_project_module(relative: Path) -> bool:
    parts = relative.parts
    return len(parts) >= 3 and parts[:2] == ("pc", "et_test_platform")


def _requires_public_api_comments(relative: Path) -> bool:
    parts = relative.parts
    return (
        _is_project_module(relative)
        and "framework_validation" not in parts
        and "test_cases" not in parts
    )


def _is_behavior_module(relative: Path) -> bool:
    parts = relative.parts
    if parts[-2:] == ("clients", "target.py"):
        return True
    return "drivers" in parts and relative.name == "driver.py"


def _has_property_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(isinstance(item, ast.Name) and item.id == "property" for item in node.decorator_list)


def _public_nodes(tree: ast.Module) -> Iterable[ast.AST]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                yield node
                for child in node.body:
                    if isinstance(
                        child, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not child.name.startswith("_"):
                        yield child
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            yield node


# Return the contiguous # comment immediately before a definition.
def _leading_comment(source: str, node: ast.AST) -> str:

    lines = source.splitlines()
    decorators = getattr(node, "decorator_list", ())
    anchor = min((item.lineno for item in decorators), default=getattr(node, "lineno", 1)) - 1
    index = anchor - 1
    block: list[str] = []
    while index >= 0:
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            break
        if stripped.startswith("#"):
            block.append(stripped.lstrip("# "))
        elif block:
            break
        index -= 1
    return "\n".join(reversed(block))


# Return the leading module # comment after an optional shebang.
def _module_comment(source: str) -> str:

    lines = source.splitlines()
    index = 1 if lines and lines[0].startswith("#!") else 0
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
        block.append(stripped.lstrip("# "))
        index += 1
    return "\n".join(block)


def check_file(path: Path, *, repository_root: Path) -> list[DocumentationViolation]:
    relative = _relative(path, repository_root)
    if not _is_project_module(relative):
        return []
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations: list[DocumentationViolation] = []
    module_comment = _module_comment(source)
    if not _CJK.search(module_comment):
        violations.append(
            DocumentationViolation(
                path, 1, "ETDOC101", "project module leading comment must be Chinese"
            )
        )
    missing_sections = [section for section in _MODULE_SECTIONS if section not in module_comment]
    if missing_sections:
        violations.append(
            DocumentationViolation(
                path,
                1,
                "ETDOC102",
                "module leading comment must state " + ", ".join(missing_sections),
            )
        )

    if not _requires_public_api_comments(relative):
        return violations

    behavior_module = _is_behavior_module(relative)
    for node in _public_nodes(tree):
        name = getattr(node, "name", "<public>")
        comment = _leading_comment(source, node).strip()
        line = getattr(node, "lineno", 1)
        if not comment:
            violations.append(
                DocumentationViolation(
                    path, line, "ETDOC201", f"public API {name} has no leading comment"
                )
            )
            continue
        if not _CJK.search(comment):
            violations.append(
                DocumentationViolation(
                    path,
                    line,
                    "ETDOC202",
                    f"public API {name} leading comment must be Chinese",
                )
            )
        lowered = comment.lower()
        if any(fragment in lowered for fragment in _GENERIC_DOC_FRAGMENTS):
            violations.append(
                DocumentationViolation(
                    path,
                    line,
                    "ETDOC203",
                    f"public API {name} uses a generic generated leading comment",
                )
            )
        if len(comment) < 24:
            violations.append(
                DocumentationViolation(
                    path,
                    line,
                    "ETDOC204",
                    f"public API {name} leading comment is too short to explain behavior",
                )
            )
        if (
            behavior_module
            and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not _has_property_decorator(node)
            and not any(keyword in comment for keyword in _OPERATION_SEMANTICS)
        ):
            violations.append(
                DocumentationViolation(
                    path,
                    line,
                    "ETDOC205",
                    f"operation API {name} must explain wait/deadline/failure semantics",
                )
            )
    return violations


def check_paths(paths: Iterable[Path], *, root: Path) -> list[DocumentationViolation]:
    files: set[Path] = set()
    for supplied in paths:
        path = supplied if supplied.is_absolute() else root / supplied
        if path.is_dir():
            files.update(path.rglob("*.py"))
        elif path.is_file() and path.suffix == ".py":
            files.add(path)
    violations: list[DocumentationViolation] = []
    for path in sorted(files):
        violations.extend(check_file(path, repository_root=root))
    return sorted(violations)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check PC leading-comment documentation rules.")
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
