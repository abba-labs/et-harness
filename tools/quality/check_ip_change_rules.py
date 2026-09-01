#!/usr/bin/env python3
# Enforce lightweight IP contract synchronization and chip-neutral public code.

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.quality.service_factory_contract import (
        FACTORY_REGION_BEGIN,
        FACTORY_REGION_END,
        strip_valid_factory_regions,
    )
    from tools.quality.service_factory_contract import (
        strip_c_comments as _strip_c_comments,
    )
except ModuleNotFoundError:
    from service_factory_contract import (
        FACTORY_REGION_BEGIN,
        FACTORY_REGION_END,
        strip_valid_factory_regions,
    )
    from service_factory_contract import (
        strip_c_comments as _strip_c_comments,
    )

_FACTORY_REGION_BEGIN = FACTORY_REGION_BEGIN
_FACTORY_REGION_END = FACTORY_REGION_END

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DOC_ROOT = ROOT / "test_case_doc"
_CHIP_ID = re.compile(r"\bET[0-9]{3,}\b", re.IGNORECASE)
_FIXED_INSTANCE = re.compile(
    r"\b(?:UART|DMA|ADC|CAN|SPI|I2C|I3C|TIMER|GPIO|QSPI)[0-9]+\b|"
    r"\b(?:CRC|AES|CORDIC)[0-7]\b",
    re.IGNORECASE,
)
_PHYSICAL_IRQ = re.compile(
    r"\b(?:UART|DMA|CRC|ADC|CAN|SPI|I2C|I3C|TIMER|GPIO|CORDIC|AES|QSPI)[A-Z0-9_]*_IRQn\b"
)
_CHIP_HEADER = re.compile(r"(?:#include\s*[<\"]|from\s+|import\s+)[^\n]*et[0-9]{3,}", re.IGNORECASE)
_SERVICE_FILE = re.compile(r"et_(?P<ip>[a-z0-9_]+)_service\.(?:c|h)$")
_WRAP_FILE = re.compile(r"et_(?P<ip>[a-z0-9_]+)_wrap\.(?:c|h)$")
_CAPABILITY_PATH = re.compile(
    r"^pc/et_test_platform/profiles/chip_capabilities/(?P<chip>[^/]+)/ip/(?P<ip>[^/]+)\.yaml$"
)
_CHIP_EXECUTION_PATH = re.compile(
    r"^pc/et_test_platform/profiles/chip_execution_mappings/(?P<chip>[^/]+)/(?P<rest>.+)$"
)
_BOARD_PATH = re.compile(r"^firmware/boards/(?P<board>[^/]+)/(?P<rest>.+)$")
_CHIP_NAME = re.compile(r"^et[0-9]{3,}$", re.IGNORECASE)
_TEXT_SUFFIXES = {".py", ".c", ".h", ".yaml", ".yml", ".json", ".md", ".txt"}


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.code} {self.message}"


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else ""


def _working_tree_paths() -> set[str]:
    paths: set[str] = set()
    for line in _git("status", "--porcelain", "--untracked-files=all").splitlines():
        if len(line) < 4:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.add(value.replace("\\", "/"))
    return paths


def _last_commit_paths() -> set[str]:
    if not _git("rev-parse", "HEAD^").strip():
        return set()
    return {
        line.strip().replace("\\", "/")
        for line in _git("diff", "--name-only", "HEAD^", "HEAD").splitlines()
        if line.strip()
    }


def _base_diff_paths(base_ref: str) -> set[str]:
    if not _git("rev-parse", "--verify", f"{base_ref}^{{commit}}").strip():
        raise ValueError(f"invalid Git base revision: {base_ref!r}")
    return {
        line.strip().replace("\\", "/")
        for line in _git("diff", "--name-only", f"{base_ref}...HEAD").splitlines()
        if line.strip()
    }


def changed_paths(*, base_ref: str | None = None) -> set[str]:
    # CI 必须检查整个 PR/Push 差异，本地则保留“工作树优先、最后一次提交兜底”的轻量行为。
    working = _working_tree_paths()
    if base_ref:
        return working | _base_diff_paths(base_ref)
    return working if working else _last_commit_paths()


def _public_ips() -> tuple[str, ...]:
    values = {
        path.name
        for path in PUBLIC_DOC_ROOT.iterdir()
        if path.is_dir() and (path / f"{path.name}.md").is_file()
    }
    case_root = ROOT / "pc/et_test_platform/test_cases"
    if case_root.is_dir():
        values.update(path.name for path in case_root.iterdir() if path.is_dir())
    return tuple(sorted(values, key=len, reverse=True))


def _public_ip_for_path(path: str) -> str | None:
    parts = Path(path).parts
    if len(parts) >= 5 and parts[:3] == ("pc", "et_test_platform", "test_cases"):
        return parts[3] if parts[3] not in {"integration"} else None
    if len(parts) >= 5 and parts[:3] == ("pc", "et_test_platform", "drivers"):
        return parts[3]
    name = Path(path).name
    for pattern in (_SERVICE_FILE, _WRAP_FILE):
        match = pattern.fullmatch(name)
        if match is not None:
            return match.group("ip")
    return None


def _mentioned_ips(
    path: str,
    known_ips: tuple[str, ...],
    *,
    changed_text: str | None = None,
) -> set[str]:
    lowered = path.lower()
    values = {
        ip for ip in known_ips if re.search(rf"(?:^|[/_.-]){re.escape(ip)}(?:[/_.-]|$)", lowered)
    }
    # 专用文件的路径已经给出唯一IP身份，不能再由文件中原有的跨IP文字扩大同步范围。
    if values:
        return values
    if changed_text is not None:
        text = changed_text.lower()
    else:
        file_path = ROOT / path
        if not file_path.is_file() or file_path.suffix.lower() not in _TEXT_SUFFIXES:
            return values
        text = file_path.read_text(encoding="utf-8-sig", errors="replace").lower()

    # 通用配置文件优先使用带Owner语义的符号识别IP，避免把
    # ``ET_CHIP_AES_DMA_MODE`` 中的DMA功能词误判成DMA IP适配变化。
    explicit = {
        ip
        for ip in known_ips
        if any(
            re.search(pattern, text)
            for pattern in (
                rf"et_chip_{re.escape(ip)}(?:_|[^a-z0-9])",
                rf"et_crg_wrap_peripheral_{re.escape(ip)}(?:_|[^a-z0-9])",
                rf"crg_periph_(?:ahb)?{re.escape(ip)}[0-9]*(?:_|[^a-z0-9])",
                rf"(?:^|[^a-z0-9]){re.escape(ip)}[0-9]*_irqn(?:[^a-z0-9]|$)",
            )
        )
    }
    if explicit:
        return explicit
    for ip in known_ips:
        if re.search(rf"(?:^|[^a-z0-9]){re.escape(ip)}(?:[^a-z0-9]|$)", text):
            values.add(ip)
    return values


def _container_line_signature(line: str) -> str:
    return line.strip(" \t,\\{}")


def _semantic_changed_lines(output: str) -> list[str]:
    removed: list[str] = []
    added: list[str] = []
    for line in output.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])

    # 表项从末项变成中间项时，Git会把同一正文显示为删除/新增，差异只有
    # 花括号、逗号和续行符。抵消这种容器标点变化，真实标识符、数值和运算符变化仍保留。
    removable = Counter(_container_line_signature(line) for line in removed) & Counter(
        _container_line_signature(line) for line in added
    )
    remaining = removable.copy()
    semantic_removed: list[str] = []
    for line in removed:
        signature = _container_line_signature(line)
        if remaining[signature]:
            remaining[signature] -= 1
        else:
            semantic_removed.append(line)

    remaining = removable.copy()
    semantic_added: list[str] = []
    for line in added:
        signature = _container_line_signature(line)
        if remaining[signature]:
            remaining[signature] -= 1
        else:
            semantic_added.append(line)
    return [*semantic_removed, *semantic_added]


def _diff_changed_text(path: str, *revisions: str) -> str:
    output = _git("diff", "--unified=0", "--no-ext-diff", *revisions, "--", path)
    return "\n".join(_semantic_changed_lines(output))


# 返回本次逻辑变更真正新增或删除的文本；通用芯片配置文件不得扫描未改动的历史内容。
def _changed_text_for_path(path: str, *, base_ref: str | None) -> str:
    parts: list[str] = []
    if base_ref:
        parts.append(_diff_changed_text(path, f"{base_ref}...HEAD"))
        parts.append(_diff_changed_text(path, "HEAD"))
    elif path in _working_tree_paths():
        parts.append(_diff_changed_text(path, "HEAD"))
    else:
        parts.append(_diff_changed_text(path, "HEAD^", "HEAD"))

    if not any(part.strip() for part in parts):
        untracked = _git("ls-files", "--others", "--exclude-standard", "--", path).strip()
        file_path = ROOT / path
        if untracked and file_path.is_file() and file_path.suffix.lower() in _TEXT_SUFFIXES:
            parts.append(file_path.read_text(encoding="utf-8-sig", errors="replace"))
    return "\n".join(parts)


# C formatting and explanatory comments are not semantic; Python remains path-conservative.
def _normalized_c_contract_text(text: str, *, path: str | None = None) -> str:
    without_factories = text
    service_match = _SERVICE_FILE.fullmatch(Path(path).name) if path is not None else None
    if service_match is not None:
        without_factories, _ = strip_valid_factory_regions(
            text,
            ip=service_match.group("ip"),
            suffix=Path(path).suffix.lower(),
        )
    preprocessed = re.sub(r"\\\s*\r?\n", "", without_factories)
    without_comments = _strip_c_comments(preprocessed)
    return "".join(without_comments.split())


def _revision_text(revision: str, path: str) -> str:
    return _git("show", f"{revision}:{path}")


def _current_text(path: str) -> str:
    file_path = ROOT / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8-sig", errors="replace")


# Decide whether a changed public C/H file altered IP semantics rather than formatting/factory glue.
def _public_contract_semantics_changed(path: str, *, base_ref: str | None) -> bool:
    if Path(path).suffix.lower() not in {".c", ".h"}:
        return True

    working = path in _working_tree_paths()
    if base_ref:
        revision = _git("merge-base", base_ref, "HEAD").strip()
        before = _revision_text(revision, path) if revision else ""
        after = _current_text(path) if working else _revision_text("HEAD", path)
    elif working:
        before = _revision_text("HEAD", path)
        after = _current_text(path)
    else:
        before = _revision_text("HEAD^", path)
        after = _revision_text("HEAD", path)

    return _normalized_c_contract_text(before, path=path) != _normalized_c_contract_text(
        after, path=path
    )


def _board_chip(board: str) -> str | None:
    candidate = board.split("_", 1)[0]
    return candidate if _CHIP_NAME.fullmatch(candidate) else None


def _is_chip_fact_path(path: str) -> bool:
    if _CAPABILITY_PATH.fullmatch(path) is not None:
        return True
    parts = Path(path).parts
    if len(parts) >= 3 and parts[:2] == ("firmware", "chips"):
        return _CHIP_NAME.fullmatch(parts[2]) is not None
    if _CHIP_EXECUTION_PATH.fullmatch(path) is not None:
        return True
    board_match = _BOARD_PATH.fullmatch(path)
    return board_match is not None and _board_chip(board_match.group("board")) is not None


def _chip_ips_for_path(
    path: str,
    known_ips: tuple[str, ...],
    *,
    changed_text: str | None = None,
) -> set[tuple[str, str]]:
    capability = _CAPABILITY_PATH.fullmatch(path)
    if capability is not None:
        return {(capability.group("chip"), capability.group("ip"))}

    parts = Path(path).parts
    if len(parts) >= 3 and parts[:2] == ("firmware", "chips"):
        chip = parts[2]
        if _CHIP_NAME.fullmatch(chip) is None:
            return set()
        return {(chip, ip) for ip in _mentioned_ips(path, known_ips, changed_text=changed_text)}

    execution = _CHIP_EXECUTION_PATH.fullmatch(path)
    if execution is not None:
        chip = execution.group("chip")
        return {(chip, ip) for ip in _mentioned_ips(path, known_ips, changed_text=changed_text)}

    board_match = _BOARD_PATH.fullmatch(path)
    if board_match is not None:
        chip = _board_chip(board_match.group("board"))
        if chip is not None:
            return {(chip, ip) for ip in _mentioned_ips(path, known_ips, changed_text=changed_text)}
    return set()


def _required_contracts(paths: set[str], *, base_ref: str | None = None) -> list[Violation]:
    violations: list[Violation] = []
    known_ips = _public_ips()
    for path in sorted(paths):
        public_ip = _public_ip_for_path(path)
        if (
            public_ip is not None
            and public_ip in known_ips
            and _public_contract_semantics_changed(path, base_ref=base_ref)
        ):
            required = f"test_case_doc/{public_ip}/{public_ip}.md"
            if required not in paths:
                violations.append(
                    Violation(
                        path,
                        "ETSYNC101",
                        f"public {public_ip} implementation changed without synchronizing {required}",
                    )
                )

        changed_text = (
            _changed_text_for_path(path, base_ref=base_ref) if _is_chip_fact_path(path) else ""
        )
        for chip, ip in sorted(_chip_ips_for_path(path, known_ips, changed_text=changed_text)):
            chip_doc = f"test_case_doc/{ip}/{chip.upper()}_{ip}.md"
            if chip_doc not in paths:
                violations.append(
                    Violation(
                        path,
                        "ETSYNC201",
                        f"chip-specific {chip}/{ip} fact changed without synchronizing {chip_doc}",
                    )
                )
    return violations


def _is_public_code(path: str) -> bool:
    return (
        path.startswith("pc/et_test_platform/test_cases/")
        or path.startswith("pc/et_test_platform/drivers/")
        or path.startswith("firmware/services/")
        or path.startswith("firmware/wrap/")
    )


def _chip_neutrality(paths: set[str], *, scan_all: bool) -> list[Violation]:
    if scan_all:
        candidates = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for root in (
                ROOT / "pc/et_test_platform/test_cases",
                ROOT / "pc/et_test_platform/drivers",
                ROOT / "firmware/services",
                ROOT / "firmware/wrap",
            )
            if root.is_dir()
            for path in root.rglob("*")
            if path.is_file() and path.suffix in {".py", ".c", ".h"}
        }
    else:
        candidates = {path for path in paths if _is_public_code(path)}

    checks = (
        ("ETCHIP101", _CHIP_ID, "concrete chip ID is forbidden in public IP code"),
        (
            "ETCHIP102",
            _FIXED_INSTANCE,
            "fixed physical IP instance is forbidden in public IP code",
        ),
        ("ETCHIP103", _PHYSICAL_IRQ, "physical IRQ symbol is forbidden in public IP code"),
        (
            "ETCHIP104",
            _CHIP_HEADER,
            "chip-specific SDK/header dependency is forbidden in public IP code",
        ),
    )
    violations: list[Violation] = []
    for relative in sorted(candidates):
        path = ROOT / relative
        if not path.is_file() or path.suffix not in {".py", ".c", ".h"}:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for code, pattern, message in checks:
            match = pattern.search(text)
            if match is not None:
                violations.append(Violation(relative, code, f"{message}: {match.group(0)!r}"))
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check IP doc/code synchronization and chip-neutral public implementation."
    )
    parser.add_argument(
        "--all-chip-neutral",
        action="store_true",
        help="audit all public IP code instead of only changed files",
    )
    parser.add_argument(
        "--base-ref",
        help="inspect the complete merge-base diff from this Git revision through HEAD",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        paths = changed_paths(base_ref=args.base_ref)
    except ValueError as exc:
        print(f"IP change rule check failed: {exc}", file=sys.stderr)
        return 2
    violations = _required_contracts(paths, base_ref=args.base_ref)
    violations.extend(_chip_neutrality(paths, scan_all=args.all_chip_neutral))
    for violation in sorted(set(violations)):
        print(violation.render(), file=sys.stderr)
    if violations:
        print(f"IP change rule check failed: {len(violations)} violation(s).", file=sys.stderr)
        return 1
    scope = "all public code" if args.all_chip_neutral else f"{len(paths)} changed path(s)"
    print(f"IP change rule check passed: {scope} inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
