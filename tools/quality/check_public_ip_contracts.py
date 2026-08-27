#!/usr/bin/env python3
# Reject concrete-chip physical facts from stable public IP contracts.

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "test_case_doc"
_CHIP_ID = re.compile(r"\bET[0-9]{3,}\b", re.IGNORECASE)
_FIXED_INSTANCE = re.compile(
    r"\b(?:UART|DMA|ADC|CAN|SPI|I2C|I3C|TIMER|GPIO|QSPI)[0-9]+\b|"
    r"\b(?:CRC|AES|CORDIC)[0-7]\b",
    re.IGNORECASE,
)
_PHYSICAL_IRQ = re.compile(
    r"\b(?:UART|DMA|CRC|ADC|CAN|SPI|I2C|I3C|TIMER|GPIO|CORDIC|AES|QSPI)[A-Z0-9_]*_IRQn\b"
)
_CHIP_HEADER = re.compile(r"\bet[0-9]{3,}\.h\b", re.IGNORECASE)
_PHYSICAL_ADDRESS_WORD = re.compile(
    r"\bbase\s+address\b|\bregister\s+offset\b|基地址|寄存器地址", re.IGNORECASE
)
_REGISTER_FIELD = re.compile(
    r"\b[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*\b|\b[A-Z][A-Z0-9_]*\[[0-9]+:[0-9]+\]"
)
_REGISTER_WORD = re.compile(r"寄存器|\bregister\b", re.IGNORECASE)
_SUMMARY_HEADING = re.compile(r"(?m)^##\s+4\.\s*Chip Adaptation Summary\s*$")
_FEATURE_HEADING = re.compile(r"(?m)^##\s+1\.\s*Feature Catalog\s*$")
_CASE_HEADING = re.compile(r"(?m)^##\s+2\.\s*Case Catalog\s*$")


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: Path
    code: str
    token: str

    def render(self) -> str:
        relative = self.path.relative_to(ROOT)
        return f"{relative}: {self.code} chip/physical detail in stable public contract: {self.token!r}"


def _public_documents() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path / f"{path.name}.md"
            for path in DOC_ROOT.iterdir()
            if path.is_dir() and (path / f"{path.name}.md").is_file()
        )
    )


def _stable_section(text: str) -> str:
    match = _SUMMARY_HEADING.search(text)
    return text[: match.start()] if match is not None else text


def _feature_section(stable: str) -> str:
    start = _FEATURE_HEADING.search(stable)
    end = _CASE_HEADING.search(stable)
    if start is None or end is None or start.end() >= end.start():
        return ""
    return stable[start.end() : end.start()]


def _matches(code: str, pattern: re.Pattern[str], text: str, path: Path) -> list[Violation]:
    return [Violation(path, code, match.group(0)) for match in pattern.finditer(text)]


def check_documents() -> list[Violation]:
    violations: list[Violation] = []
    for path in _public_documents():
        stable = _stable_section(path.read_text(encoding="utf-8-sig"))
        feature = _feature_section(stable)
        for code, pattern in (
            ("ETIPDOC101", _CHIP_ID),
            ("ETIPDOC102", _FIXED_INSTANCE),
            ("ETIPDOC103", _PHYSICAL_IRQ),
            ("ETIPDOC104", _CHIP_HEADER),
            ("ETIPDOC105", _PHYSICAL_ADDRESS_WORD),
        ):
            violations.extend(_matches(code, pattern, stable, path))
        for code, pattern in (
            ("ETIPDOC111", _REGISTER_FIELD),
            ("ETIPDOC112", _REGISTER_WORD),
        ):
            violations.extend(_matches(code, pattern, feature, path))
    return sorted(set(violations))


def main() -> int:
    violations = check_documents()
    for violation in violations:
        print(violation.render(), file=sys.stderr)
    if violations:
        print(f"Public IP contract check failed: {len(violations)} violation(s).", file=sys.stderr)
        return 1
    print(f"Public IP contract check passed: {len(_public_documents())} document(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
