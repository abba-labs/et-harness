#!/usr/bin/env python3
# Read-only Firmware C readability gate for R330.

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = ROOT
QUALITY_ROOTS = tuple(
    ROOT / path
    for path in (
        "firmware/application",
        "firmware/boards",
        "firmware/framework",
        "firmware/services",
        "firmware/wrap",
    )
)
SOURCE_SUFFIXES = {".c", ".h"}
PLACEHOLDERS = {"", ".", "-", "todo", "tbd", "none", "n/a", "na"}
CONTROL_RE = re.compile(r"\b(?:if|for|while|switch|do|goto)\b")
FLOW_RE = re.compile(r"(?:(?:/\*+)|(?://))\s*(?:Phase|Step)\s+\d+\s*:", re.IGNORECASE)
NOISE_RE = re.compile(
    r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
    re.DOTALL,
)
INTEGER_LITERAL_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?P<literal>(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|[0-9]+)(?:[uUlL]+)?)"
    r"(?![A-Za-z0-9_])"
)
CODEC_HELPER_RE = re.compile(r"^(?:read|write|encode|decode|pack|unpack|bytes_to|words_to)")
PARAM_RE = re.compile(
    r"@param(?:\[(?P<direction>in|out|in,out)\])?\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*(?P<description>.*)",
    re.IGNORECASE,
)
IDENT_RE = re.compile(r"[A-Za-z_]\w*")
NAME_RE = re.compile(r"([A-Za-z_]\w*)\s*$")
FPARAM_RE = re.compile(r"\(\s*\*\s*([A-Za-z_]\w*)")
TYPE_WORDS = {
    "auto",
    "char",
    "const",
    "double",
    "enum",
    "extern",
    "float",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "short",
    "signed",
    "static",
    "struct",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "_Bool",
    "bool",
}
NON_FUNCTION_NAMES = {"if", "for", "while", "switch", "sizeof", "do"}


@dataclass(frozen=True, slots=True)
class Function:
    path: Path
    name: str
    return_prefix: str
    params: tuple[str, ...]
    start_line: int
    brace_line: int
    body: str


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: Path
    line: int
    code: str
    message: str

    def render(self) -> str:
        try:
            display = self.path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            display = self.path
        return f"{display}:{self.line}: {self.code} {self.message}"


def _controlled(path: Path) -> bool:
    path = path.resolve()
    return (
        path.is_file()
        and path.suffix.lower() in SOURCE_SUFFIXES
        and any(path.is_relative_to(root.resolve()) for root in QUALITY_ROOTS)
    )


def _all_sources() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for root in QUALITY_ROOTS
            if root.is_dir()
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
        )
    )


# Backward-compatible test helper name.
_discover_all_sources = _all_sources


def _requested_sources(values: Sequence[str]) -> tuple[Path, ...]:
    sources: set[Path] = set()
    for value in values:
        candidate = (ROOT / value).resolve()
        if candidate.is_dir():
            found = tuple(path for path in candidate.rglob("*") if _controlled(path))
            if not found:
                raise ValueError(f"no controlled Firmware sources under {value}")
            sources.update(found)
        elif _controlled(candidate):
            sources.add(candidate)
        else:
            raise ValueError(f"path is outside controlled Firmware quality roots: {value}")
    return tuple(sorted(sources))


def _run_git(command: Sequence[str]) -> list[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"git command failed: {' '.join(command)}: {detail}")
    return completed.stdout.splitlines()


def _changed_sources(base_ref: str | None) -> tuple[Path, ...]:
    values: list[str] = []
    if base_ref:
        values.extend(
            _run_git(("git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...HEAD"))
        )
        values.extend(_run_git(("git", "diff", "--name-only", "--diff-filter=ACMR")))
        values.extend(_run_git(("git", "diff", "--cached", "--name-only", "--diff-filter=ACMR")))
    else:
        for row in _run_git(("git", "status", "--porcelain=v1", "--untracked-files=all")):
            if len(row) < 4:
                continue
            value = row[3:]
            values.append(value.split(" -> ", 1)[-1])

    sources = {
        candidate for value in values if _controlled(candidate := (ROOT / value.strip()).resolve())
    }
    return tuple(sorted(sources))


def discover_sources(
    *,
    requested: Sequence[str] = (),
    base_ref: str | None = None,
    all_sources: bool = False,
) -> tuple[Path, ...]:
    if int(bool(requested)) + int(base_ref is not None) + int(all_sources) > 1:
        raise ValueError("paths, --base-ref and --all are mutually exclusive")
    if requested:
        return _requested_sources(requested)
    if all_sources:
        return _all_sources()
    return _changed_sources(base_ref)


def _blank(match: re.Match[str]) -> str:
    return "".join("\n" if char == "\n" else " " for char in match.group(0))


def _sanitize(source: str) -> str:
    source = NOISE_RE.sub(_blank, source)
    rendered: list[str] = []
    continuation = False
    for line in source.splitlines(keepends=True):
        preprocessor = continuation or line.lstrip().startswith("#")
        if preprocessor:
            continuation = line.rstrip().endswith("\\")
            rendered.append("".join("\n" if char == "\n" else " " for char in line))
        else:
            continuation = False
            rendered.append(line)
    return "".join(rendered)


def _open_paren(text: str, close: int) -> int | None:
    depth = 0
    for index in range(close, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                return index
    return None


def _split_params(text: str) -> tuple[str, ...]:
    text = text.strip()
    if not text or text == "void":
        return ()

    chunks: list[str] = []
    start = paren = bracket = 0
    for index, char in enumerate(text):
        if char == "(":
            paren += 1
        elif char == ")":
            paren = max(paren - 1, 0)
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket = max(bracket - 1, 0)
        elif char == "," and paren == 0 and bracket == 0:
            chunks.append(text[start:index].strip())
            start = index + 1
    chunks.append(text[start:].strip())

    names: list[str] = []
    for chunk in chunks:
        if not chunk or chunk == "...":
            continue
        pointer = FPARAM_RE.search(chunk)
        if pointer:
            names.append(pointer.group(1))
            continue
        chunk = re.sub(r"\[[^\]]*\]", "", chunk)
        candidates = [name for name in IDENT_RE.findall(chunk) if name not in TYPE_WORDS]
        if candidates:
            names.append(candidates[-1])
    return tuple(names)


def _parse_candidate(candidate: str) -> tuple[str, str, tuple[str, ...]] | None:
    close = candidate.rfind(")")
    if close < 0 or (opening := _open_paren(candidate, close)) is None:
        return None
    before = candidate[:opening].rstrip()
    match = NAME_RE.search(before)
    if match is None:
        return None

    name = match.group(1)
    prefix = before[: match.start(1)].strip()
    trailing = candidate[close + 1 :].strip()
    if (
        name in NON_FUNCTION_NAMES
        or not prefix
        or "=" in prefix
        or prefix.startswith(("typedef", "struct ", "enum ", "union "))
        or trailing.startswith("=")
    ):
        return None
    return name, prefix, _split_params(candidate[opening + 1 : close])


def _body_end(source: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(source) - 1


def _line(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def find_function_definitions(path: Path) -> tuple[Function, ...]:
    raw = path.read_text(encoding="utf-8")
    source = _sanitize(raw)
    functions: list[Function] = []
    depth = start = index = 0

    while index < len(source):
        char = source[index]
        if char == "{" and depth == 0:
            candidate = source[start:index].strip()
            parsed = _parse_candidate(candidate)
            if parsed is not None:
                name, prefix, params = parsed
                end = _body_end(source, index)
                offset = source.rfind(candidate, start, index)
                functions.append(
                    Function(
                        path=path,
                        name=name,
                        return_prefix=prefix,
                        params=params,
                        start_line=_line(raw, offset if offset >= 0 else start),
                        brace_line=_line(raw, index),
                        body=raw[index + 1 : end],
                    )
                )
                index = end + 1
                start = index
                continue
            depth = 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth = max(depth - 1, 0)
            if depth == 0:
                start = index + 1
        elif char == ";" and depth == 0:
            start = index + 1
        index += 1
    return tuple(functions)


def _doxygen(raw: str, start_line: int) -> tuple[str | None, int]:
    lines = raw.splitlines()
    index = start_line - 2
    while index >= 0 and not lines[index].strip():
        index -= 1
    if index < 0 or "*/" not in lines[index]:
        return None, start_line

    end = index
    while index >= 0:
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            return "\n".join(lines[index : end + 1]), index + 1
        if stripped != "*/" and not stripped.startswith("*"):
            return None, start_line
        index -= 1
    return None, start_line


def _doc_lines(block: str) -> tuple[str, ...]:
    result: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        line = line[3:] if line.startswith("/**") else line
        line = line[:-2] if line.endswith("*/") else line
        line = line.strip()
        line = line[1:].strip() if line.startswith("*") else line
        result.append(line)
    return tuple(result)


def _tag(lines: Sequence[str], tag: str) -> str | None:
    prefix = f"@{tag}"
    for index, line in enumerate(lines):
        if not line.lower().startswith(prefix.lower()):
            continue
        parts = [line[len(prefix) :].strip()]
        for following in lines[index + 1 :]:
            if following.startswith("@"):
                break
            if following:
                parts.append(following)
        return " ".join(parts).strip()
    return None


def _placeholder(value: str | None) -> bool:
    return value is None or re.sub(r"\s+", " ", value).strip().lower() in PLACEHOLDERS


def _params(lines: Sequence[str]) -> tuple[dict[str, tuple[str | None, str]], set[str]]:
    documented: dict[str, tuple[str | None, str]] = {}
    duplicates: set[str] = set()
    for index, line in enumerate(lines):
        if not line.lower().startswith("@param"):
            continue
        match = PARAM_RE.fullmatch(line)
        if match is None:
            continue
        description = [match.group("description").strip()]
        for following in lines[index + 1 :]:
            if following.startswith("@"):
                break
            if following:
                description.append(following)
        name = match.group("name")
        if name in documented:
            duplicates.add(name)
        direction = match.group("direction")
        documented[name] = (
            direction.lower() if direction else None,
            " ".join(description).strip(),
        )
    return documented, duplicates


def _void_return(function: Function) -> bool:
    prefix = re.sub(r"__attribute__\s*\(\(.*?\)\)", " ", function.return_prefix)
    prefix = re.sub(r"\b(?:static|inline|__STATIC_INLINE)\b", " ", prefix)
    return bool(re.search(r"\bvoid$", re.sub(r"\s+", " ", prefix).strip()))


def _effective_lines(function: Function) -> int:
    return sum(
        1
        for line in _sanitize(function.body).splitlines()
        if line.strip() and line.strip() not in {"{", "}"}
    )


def _is_complex(function: Function) -> bool:
    body = _sanitize(function.body)
    lines = _effective_lines(function)
    controls = len(CONTROL_RE.findall(body))
    goto = bool(re.search(r"\bgoto\b", body))
    return lines >= 70 or (lines >= 40 and controls >= 3) or (lines >= 20 and goto)


def _integer_literal_value(literal: str) -> int:
    token = re.sub(r"[uUlL]+$", "", literal)
    if token.lower().startswith("0x"):
        return int(token[2:], 16)
    if token.lower().startswith("0b"):
        return int(token[2:], 2)
    return int(token, 10)


def _is_codec_helper(function: Function) -> bool:
    return CODEC_HELPER_RE.match(function.name) is not None


def _literal_is_direct_array_index(body: str, start: int, end: int) -> bool:
    before = body[:start].rstrip()
    after = body[end:].lstrip()
    return before.endswith("[") and after.startswith("]")


def _literal_is_shift_width(body: str, start: int) -> bool:
    before = body[:start].rstrip()
    return before.endswith("<<") or before.endswith(">>")


def _magic_number_violations(function: Function) -> list[Violation]:
    body = _sanitize(function.body)
    codec_helper = _is_codec_helper(function)
    violations: list[Violation] = []
    for match in INTEGER_LITERAL_RE.finditer(body):
        literal = match.group("literal")
        if _integer_literal_value(literal) <= 1:
            continue
        if codec_helper and _literal_is_direct_array_index(body, match.start(), match.end()):
            continue
        if codec_helper and _literal_is_shift_width(body, match.start()):
            continue
        line = function.brace_line + body.count("\n", 0, match.start()) + 1
        violations.append(
            Violation(
                function.path,
                line,
                "ETFMT211",
                f"function {function.name} uses unnamed integer literal {literal}; "
                "use an existing symbol or a named semantic constant",
            )
        )
    return violations


def _validate_doxygen_shape(
    function: Function,
    block: str,
    doc_line: int,
) -> tuple[tuple[str, ...], list[Violation]]:
    violations: list[Violation] = []
    block_lines = block.splitlines()
    if len(block_lines) < 3 or block_lines[0].strip() != "/**" or block_lines[-1].strip() != "*/":
        violations.append(
            Violation(
                function.path,
                doc_line,
                "ETFMT208",
                f"function {function.name} requires a standard multi-line Doxygen block",
            )
        )

    lines = _doc_lines(block)
    if _placeholder(_tag(lines, "brief")):
        violations.append(
            Violation(function.path, doc_line, "ETFMT202", f"{function.name} needs @brief text")
        )
    if _placeholder(_tag(lines, "note")):
        violations.append(
            Violation(function.path, doc_line, "ETFMT207", f"{function.name} needs @note text")
        )
    if any(
        line.lower().startswith("@param") and PARAM_RE.fullmatch(line) is None for line in lines
    ):
        violations.append(
            Violation(function.path, doc_line, "ETFMT208", f"{function.name} has malformed @param")
        )
    return lines, violations


def _validate_parameters(
    function: Function,
    lines: Sequence[str],
    doc_line: int,
) -> list[Violation]:
    violations: list[Violation] = []
    documented, duplicates = _params(lines)
    actual = set(function.params)
    missing = sorted(actual - set(documented))
    extra = sorted(set(documented) - actual)

    if missing:
        violations.append(
            Violation(
                function.path,
                doc_line,
                "ETFMT203",
                f"{function.name} is missing @param for: {', '.join(missing)}",
            )
        )
    if extra or duplicates:
        details = []
        if extra:
            details.append("unknown=" + ",".join(extra))
        if duplicates:
            details.append("duplicate=" + ",".join(sorted(duplicates)))
        violations.append(
            Violation(
                function.path,
                doc_line,
                "ETFMT204",
                f"{function.name} has invalid @param bindings: {'; '.join(details)}",
            )
        )

    invalid = sorted(
        name
        for name, (direction, description) in documented.items()
        if name in actual
        and (direction not in {"in", "out", "in,out"} or _placeholder(description))
    )
    if invalid:
        violations.append(
            Violation(
                function.path,
                doc_line,
                "ETFMT205",
                f"{function.name} has invalid @param direction/description: {', '.join(invalid)}",
            )
        )
    return violations


def check_function(
    function: Function,
    raw: str,
    *,
    strict_magic: bool = False,
) -> list[Violation]:
    block, doc_line = _doxygen(raw, function.start_line)
    if block is None:
        return [
            Violation(
                function.path,
                function.start_line,
                "ETFMT201",
                f"function {function.name} is missing a leading Doxygen block",
            )
        ]

    lines, violations = _validate_doxygen_shape(function, block, doc_line)
    violations.extend(_validate_parameters(function, lines, doc_line))

    if not _void_return(function) and _placeholder(_tag(lines, "return")):
        violations.append(
            Violation(
                function.path,
                doc_line,
                "ETFMT206",
                f"non-void function {function.name} needs @return text",
            )
        )
    if _is_complex(function) and len(FLOW_RE.findall(function.body)) < 2:
        violations.append(
            Violation(
                function.path,
                function.brace_line,
                "ETFMT209",
                f"complex function {function.name} needs at least two Phase/Step comments",
            )
        )
    if strict_magic:
        violations.extend(_magic_number_violations(function))
    return violations


def check_file(path: Path, *, strict_magic: bool = False) -> list[Violation]:
    raw = path.read_text(encoding="utf-8")
    return sorted(
        violation
        for function in find_function_definitions(path)
        for violation in check_function(function, raw, strict_magic=strict_magic)
    )


def check_paths(paths: Iterable[Path], *, strict_magic: bool = False) -> list[Violation]:
    return sorted(
        violation
        for path in sorted(set(paths))
        for violation in check_file(path, strict_magic=strict_magic)
    )


def _args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check platform-owned Firmware C readability.")
    parser.add_argument("--base-ref")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--strict-magic",
        action="store_true",
        help="Reject unnamed integer literals above 1 outside codec mechanics",
    )
    parser.add_argument("paths", nargs="*")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _args(argv)
    try:
        sources = discover_sources(
            requested=args.paths,
            base_ref=args.base_ref,
            all_sources=args.all,
        )
    except (RuntimeError, ValueError) as error:
        print(f"ETFMT210 {error}", file=sys.stderr)
        return 1

    violations = check_paths(sources, strict_magic=args.strict_magic)
    for violation in violations:
        print(violation.render())
    if violations:
        return 1

    mode = "all" if args.all else ("base-ref" if args.base_ref else "changed")
    magic_mode = "strict" if args.strict_magic else "off"
    print(f"Firmware C quality validated: {len(sources)} file(s), mode={mode}, magic={magic_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
