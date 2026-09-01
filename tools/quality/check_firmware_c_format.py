# Firmware平台自有C源码格式检查和自动修复入口。
# 职责：固定clang-format版本、限定格式化目录并检查复合块与逻辑段空行。
# 边界：不扫描芯片SDK和生成工程，不修改任何C语言业务语义。
# 依赖：标准库、仓库.clang-format和固定版本clang-format可执行文件。

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FORMAT_CONFIG = REPOSITORY_ROOT / ".clang-format"
REQUIRED_CLANG_FORMAT_VERSION = "20.1.8"
FIRMWARE_FORMAT_ROOTS = (
    REPOSITORY_ROOT / "firmware/application",
    REPOSITORY_ROOT / "firmware/framework",
    REPOSITORY_ROOT / "firmware/services",
    REPOSITORY_ROOT / "firmware/wrap",
)
SOURCE_SUFFIXES = {".c", ".h"}
COMMAND_FILE_LIMIT = 32
CASE_LABEL_PATTERN = re.compile(r"^\s*(?:case\b.*:|default\s*:)")
CONTROL_STATEMENT_PATTERN = re.compile(r"^\s*(?:if|for|while|switch)\s*\(")
RETURN_STATEMENT_PATTERN = re.compile(r"^\s*return(?:\s|;)")


# 解析自动修复开关；默认只检查，避免软件门禁修改工作树。
def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:

    parser = argparse.ArgumentParser(description="Check or format platform-owned Firmware C code.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="apply deterministic case blocks, clang-format and logical separators",
    )
    parser.add_argument(
        "--review-diff",
        action="store_true",
        help="classify changed controlled sources as format-only or semantic/new",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="optional controlled files or directories; omitted means all controlled sources",
    )
    return parser.parse_args(argv)


# 判断路径是否位于四个受控目录且属于C/H源码。
def _is_controlled_source(path: Path) -> bool:

    resolved = path.resolve()
    return (
        resolved.is_file()
        and resolved.suffix.lower() in SOURCE_SUFFIXES
        and any(resolved.is_relative_to(root.resolve()) for root in FIRMWARE_FORMAT_ROOTS)
    )


# 默认发现全部受控源码；显式路径只能缩小范围，不能越过固定目录边界。
def _discover_sources(requested: Sequence[str] = ()) -> tuple[Path, ...]:

    if not requested:
        return tuple(
            sorted(
                path
                for root in FIRMWARE_FORMAT_ROOTS
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
            )
        )

    sources: set[Path] = set()
    for value in requested:
        candidate = (REPOSITORY_ROOT / value).resolve()
        if candidate.is_dir():
            discovered = tuple(path for path in candidate.rglob("*") if _is_controlled_source(path))
            if not discovered:
                raise ValueError(f"no controlled Firmware sources under {value}")
            sources.update(discovered)
            continue

        if not _is_controlled_source(candidate):
            raise ValueError(f"path is outside controlled Firmware source roots: {value}")
        sources.add(candidate)

    return tuple(sorted(sources))


# 优先使用当前虚拟环境中的固定工具，避免依赖机器全局PATH版本。
def _clang_format_path() -> Path | None:

    executable_name = "clang-format.exe" if sys.platform == "win32" else "clang-format"
    venv_candidate = Path(sys.executable).resolve().parent / executable_name
    if venv_candidate.is_file():
        return venv_candidate

    discovered = shutil.which("clang-format")
    return Path(discovered).resolve() if discovered else None


# 分块执行以避免Windows命令行长度限制；失败输出保留具体文件事实。
def _run_clang_format(executable: Path, sources: Sequence[Path], *, fix: bool) -> list[str]:

    violations: list[str] = []
    for offset in range(0, len(sources), COMMAND_FILE_LIMIT):
        chunk = sources[offset : offset + COMMAND_FILE_LIMIT]
        operation = ["-i"] if fix else ["--dry-run", "--Werror"]
        completed = subprocess.run(
            [str(executable), "--style=file", *operation, *(str(path) for path in chunk)],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            violations.append(
                f"ETFMT102 clang-format mismatch in files {offset + 1}-{offset + len(chunk)}: "
                f"{detail or 'formatter returned a nonzero status'}"
            )
    return violations


# 找到紧邻case标签的说明注释起点；分隔空行必须位于注释之前。
def _case_branch_start(lines: Sequence[str], case_index: int) -> int:

    cursor = case_index - 1
    while cursor >= 0 and lines[cursor].strip() == "":
        cursor -= 1
    if cursor < 0:
        return case_index

    stripped = lines[cursor].strip()
    if stripped.startswith("//"):
        while cursor > 0 and lines[cursor - 1].strip().startswith("//"):
            cursor -= 1
        return cursor
    if stripped.endswith("*/"):
        while cursor > 0 and "/*" not in lines[cursor]:
            cursor -= 1
        if "/*" in lines[cursor]:
            return cursor
    return case_index


# 规范独立case分支空行；连续标签视为同一Fallthrough分支。
def _normalize_case_separators(lines: Sequence[str]) -> list[str]:

    remove_blank_indices: set[int] = set()
    insert_before_indices: set[int] = set()
    for case_index, line in enumerate(lines):
        if not CASE_LABEL_PATTERN.match(line) or case_index == 0:
            continue

        branch_start = _case_branch_start(lines, case_index)
        for index in range(branch_start, case_index):
            if lines[index].strip() == "":
                remove_blank_indices.add(index)

        cursor = branch_start - 1
        while cursor >= 0 and lines[cursor].strip() == "":
            remove_blank_indices.add(cursor)
            cursor -= 1
        previous = lines[cursor].strip() if cursor >= 0 else ""
        if cursor >= 0 and previous != "{" and not CASE_LABEL_PATTERN.match(previous):
            insert_before_indices.add(branch_start)

    normalized: list[str] = []
    for index, line in enumerate(lines):
        if index in insert_before_indices:
            normalized.append("")
        if index not in remove_blank_indices:
            normalized.append(line)
    return normalized


# 仅插入case分支分隔空行；保留clang-format生成的原始换行格式。
def _insert_case_separators(path: Path) -> bool:

    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    had_final_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()
    updated = _normalize_case_separators(lines)
    if updated == lines:
        return False
    rendered = newline.join(updated)
    if had_final_newline:
        rendered += newline
    path.write_bytes(rendered.encode("utf-8"))
    return True


# 找到紧邻语句的说明注释起点；新增空行必须位于说明注释之前。
def _statement_group_start(lines: Sequence[str], statement_index: int) -> int:

    cursor = statement_index - 1
    if cursor < 0 or lines[cursor].strip() == "":
        return statement_index

    stripped = lines[cursor].strip()
    if stripped.startswith("//"):
        while cursor > 0 and lines[cursor - 1].strip().startswith("//"):
            cursor -= 1
        return cursor
    if stripped.endswith("*/"):
        while cursor > 0 and "/*" not in lines[cursor]:
            cursor -= 1
        if "/*" in lines[cursor]:
            return cursor
    return statement_index


# 判断当前语句是否需要与前一逻辑段分隔。
def _requires_logical_separator(line: str) -> bool:

    return bool(CONTROL_STATEMENT_PATTERN.match(line) or RETURN_STATEMENT_PATTERN.match(line))


# 清除多行宏续行中的空行；空行没有续行反斜杠，会提前终止宏定义。
def _normalize_macro_continuation_blanks(lines: Sequence[str]) -> list[str]:

    normalized: list[str] = []
    in_macro = False
    for line in lines:
        stripped = line.strip()
        if in_macro and stripped == "":
            continue

        normalized.append(line)
        if not in_macro:
            in_macro = stripped.startswith("#define") and line.rstrip().endswith("\\")
        elif not line.rstrip().endswith("\\"):
            in_macro = False

    return normalized


# 标记多行宏的完整范围；逻辑段规则不得在宏续行内部插入普通空行。
def _macro_continuation_indices(lines: Sequence[str]) -> set[int]:

    indices: set[int] = set()
    in_macro = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not in_macro:
            if stripped.startswith("#define") and line.rstrip().endswith("\\"):
                in_macro = True
                indices.add(index)
            continue

        indices.add(index)
        if not line.rstrip().endswith("\\"):
            in_macro = False

    return indices


# 规范调用/赋值、控制语句、响应收口和return之间的单个逻辑空行。
def _normalize_logical_separators(lines: Sequence[str]) -> list[str]:

    lines = _normalize_macro_continuation_blanks(lines)
    macro_indices = _macro_continuation_indices(lines)
    insert_before_indices: set[int] = set()
    for statement_index, line in enumerate(lines):
        if (
            statement_index == 0
            or statement_index in macro_indices
            or not _requires_logical_separator(line)
        ):
            continue

        group_start = _statement_group_start(lines, statement_index)
        if group_start == 0 or lines[group_start - 1].strip() == "":
            continue

        previous = lines[group_start - 1].strip()
        if previous == "{" or CASE_LABEL_PATTERN.match(previous):
            continue
        insert_before_indices.add(group_start)

    # 一个控制块结束后，后续同级普通语句也属于新的逻辑段。
    for statement_index in range(1, len(lines)):
        if statement_index in macro_indices:
            continue

        line = lines[statement_index]
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("else", "while", "case ", "default:"))
            or stripped in {"}", ");", ";"}
        ):
            continue

        group_start = _statement_group_start(lines, statement_index)
        if group_start == 0 or lines[group_start - 1].strip() != "}":
            continue
        previous_indent = len(lines[group_start - 1]) - len(lines[group_start - 1].lstrip())
        current_indent = len(line) - len(line.lstrip())
        if previous_indent == current_indent:
            insert_before_indices.add(group_start)

    normalized: list[str] = []
    for index, line in enumerate(lines):
        if index in insert_before_indices and (not normalized or normalized[-1].strip() != ""):
            normalized.append("")
        normalized.append(line)
    return normalized


# 仅插入逻辑段空行；保留clang-format确定的其他排版和原文件换行风格。
def _insert_logical_separators(path: Path) -> bool:

    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    had_final_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()
    updated = _normalize_logical_separators(lines)
    if updated == lines:
        return False
    rendered = newline.join(updated)
    if had_final_newline:
        rendered += newline
    path.write_bytes(rendered.encode("utf-8"))
    return True


# 为未加括号的实际case执行体补复合块；连续标签只在最后一个标签后建立执行体。
def _normalize_case_blocks(lines: Sequence[str]) -> list[str]:

    insertions: list[tuple[int, str]] = []
    for case_index, line in enumerate(lines):
        if not CASE_LABEL_PATTERN.match(line):
            continue

        cursor = case_index + 1
        while cursor < len(lines) and lines[cursor].strip() == "":
            cursor += 1
        if cursor >= len(lines):
            continue

        next_code = lines[cursor].strip()
        if next_code == "{" or CASE_LABEL_PATTERN.match(next_code):
            continue

        case_indent = len(line) - len(line.lstrip())
        branch_end = len(lines)
        scan = cursor
        while scan < len(lines):
            candidate = lines[scan]
            candidate_indent = len(candidate) - len(candidate.lstrip())
            stripped = candidate.strip()
            if CASE_LABEL_PATTERN.match(candidate) and candidate_indent == case_indent:
                branch_end = _case_branch_start(lines, scan)
                while branch_end > cursor and lines[branch_end - 1].strip() == "":
                    branch_end -= 1
                break
            if stripped == "}" and candidate_indent < case_indent:
                branch_end = scan
                break
            scan += 1

        indentation = " " * case_indent
        insertions.append((case_index + 1, f"{indentation}{{"))
        insertions.append((branch_end, f"{indentation}}}"))

    normalized = list(lines)
    for index, content in sorted(insertions, reverse=True):
        normalized.insert(index, content)
    return normalized


# 以原文件换行风格写回复合块机械修复结果。
def _insert_case_blocks(path: Path) -> bool:

    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    had_final_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()
    updated = _normalize_case_blocks(lines)
    if updated == lines:
        return False
    rendered = newline.join(updated)
    if had_final_newline:
        rendered += newline
    path.write_bytes(rendered.encode("utf-8"))
    return True


# 检查所有文件的case分支空行，错误定位到稳定相对路径和行号。
def _case_separator_violations(sources: Iterable[Path]) -> list[str]:

    violations: list[str] = []
    for path in sources:
        lines = path.read_text(encoding="utf-8").splitlines()
        normalized = _normalize_case_separators(lines)
        if normalized != lines:
            relative = path.relative_to(REPOSITORY_ROOT).as_posix()
            violations.append(
                f"ETFMT103 {relative}: distinct case branches require one stable blank line"
            )
    return violations


# 检查case标签后的首个有效代码；连续标签允许Fallthrough，实际分支必须进入复合块。
def _case_block_violations(sources: Iterable[Path]) -> list[str]:

    violations: list[str] = []
    for path in sources:
        lines = path.read_text(encoding="utf-8").splitlines()
        for case_index, line in enumerate(lines):
            if not CASE_LABEL_PATTERN.match(line):
                continue

            cursor = case_index + 1
            while cursor < len(lines):
                stripped = lines[cursor].strip()
                if stripped == "" or stripped.startswith("//"):
                    cursor += 1
                    continue
                if stripped.startswith("/*"):
                    while cursor < len(lines) and "*/" not in lines[cursor]:
                        cursor += 1
                    cursor += 1
                    continue
                break

            if cursor >= len(lines):
                continue

            next_code = lines[cursor].strip()
            if next_code != "{" and not CASE_LABEL_PATTERN.match(next_code):
                try:
                    relative = path.relative_to(REPOSITORY_ROOT).as_posix()
                except ValueError:
                    relative = path.as_posix()
                violations.append(
                    f"ETFMT105 {relative}:{case_index + 1}: case branch requires a compound block"
                )
    return violations


# 检查控制语句和return是否按同一机械规则分隔。
def _logical_separator_violations(sources: Iterable[Path]) -> list[str]:

    violations: list[str] = []
    for path in sources:
        lines = path.read_text(encoding="utf-8").splitlines()
        if _normalize_logical_separators(lines) != lines:
            relative = path.relative_to(REPOSITORY_ROOT).as_posix()
            violations.append(
                f"ETFMT106 {relative}: logical statement groups require one stable blank line"
            )
    return violations


# 返回当前Git工作区中发生变化的受控源码，包括尚未跟踪的新文件。
def _changed_controlled_sources() -> tuple[Path, ...]:

    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("git status is unavailable")

    sources: set[Path] = set()
    for row in completed.stdout.splitlines():
        if len(row) < 4:
            continue

        value = row[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        candidate = (REPOSITORY_ROOT / value).resolve()
        if _is_controlled_source(candidate):
            sources.add(candidate)

    return tuple(sorted(sources))


# 在内存中执行与--fix相同的确定性流水线，用于比较格式化后的HEAD基线。
def _format_text(executable: Path, source: str, assume_filename: Path) -> str:

    had_final_newline = source.endswith(("\n", "\r"))
    normalized = "\n".join(_normalize_case_blocks(source.splitlines()))
    if had_final_newline:
        normalized += "\n"

    completed = subprocess.run(
        [
            str(executable),
            f"--style=file:{FORMAT_CONFIG}",
            f"--assume-filename={assume_filename}",
        ],
        cwd=REPOSITORY_ROOT,
        input=normalized,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "clang-format failed")

    lines = _normalize_case_separators(completed.stdout.splitlines())
    lines = _normalize_logical_separators(lines)
    rendered = "\n".join(lines)
    if completed.stdout.endswith(("\n", "\r")):
        rendered += "\n"
    return rendered


# 将当前变化分成纯格式文件和需要语义审查的文件，不修改源码或Git索引。
def _classify_review_diff(executable: Path) -> tuple[tuple[Path, ...], tuple[Path, ...]]:

    format_only: list[Path] = []
    semantic_or_new: list[Path] = []

    for path in _changed_controlled_sources():
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        baseline = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if baseline.returncode != 0:
            semantic_or_new.append(path)
            continue

        expected = _format_text(executable, baseline.stdout, path)
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        target = format_only if current == expected else semantic_or_new
        target.append(path)

    return tuple(format_only), tuple(semantic_or_new)


# 输出稳定的只读审查切片；注释和符号重命名归入语义审查而非纯格式。
def _print_review_diff(executable: Path) -> None:

    format_only, semantic_or_new = _classify_review_diff(executable)
    print(f"FORMAT_ONLY {len(format_only)}")
    for path in format_only:
        print(f"  {path.relative_to(REPOSITORY_ROOT).as_posix()}")

    print(f"SEMANTIC_COMMENT_OR_NEW {len(semantic_or_new)}")
    for path in semantic_or_new:
        print(f"  {path.relative_to(REPOSITORY_ROOT).as_posix()}")


def main(argv: Sequence[str] | None = None) -> int:

    args = _parse_args(argv)
    try:
        sources = _discover_sources(args.paths)
    except ValueError as error:
        print(f"ETFMT104 {error}", file=sys.stderr)
        return 1
    if not FORMAT_CONFIG.is_file() or not sources:
        print(
            "ETFMT104 formatter config or controlled Firmware sources are missing", file=sys.stderr
        )
        return 1

    executable = _clang_format_path()
    if executable is None:
        print("ETFMT101 clang-format executable is unavailable", file=sys.stderr)
        return 1

    version = subprocess.run(
        [str(executable), "--version"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if version.returncode != 0 or REQUIRED_CLANG_FORMAT_VERSION not in version.stdout:
        observed = (version.stdout or version.stderr).strip() or "unknown"
        print(
            f"ETFMT101 clang-format {REQUIRED_CLANG_FORMAT_VERSION} required, observed: {observed}",
            file=sys.stderr,
        )
        return 1

    if args.review_diff:
        if args.fix or args.paths:
            print("ETFMT104 --review-diff cannot be combined with --fix or paths", file=sys.stderr)
            return 1
        try:
            _print_review_diff(executable)
        except RuntimeError as error:
            print(f"ETFMT104 {error}", file=sys.stderr)
            return 1
        return 0

    if args.fix:
        for path in sources:
            _insert_case_blocks(path)
        violations = _run_clang_format(executable, sources, fix=True)
        if violations:
            print("\n".join(violations), file=sys.stderr)
            return 1
        for path in sources:
            _insert_case_separators(path)
            _insert_logical_separators(path)

    violations = _run_clang_format(executable, sources, fix=False)
    violations.extend(_case_separator_violations(sources))
    violations.extend(_case_block_violations(sources))
    violations.extend(_logical_separator_violations(sources))
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1

    action = "formatted" if args.fix else "validated"
    print(f"Firmware C format {action}: {len(sources)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
