#!/usr/bin/env python3
# Enforce reviewer-facing method and report Feature grammar for every public IP Case/Plan.

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.quality import validate_case_docs, validate_case_plans  # noqa: E402

_REQUIRED_METHOD_LISTS = ("inputs", "steps", "observations", "pass_criteria")
_LINE_SEPARATOR = "："
_MIN_STEPS = 6
_MAX_STEPS = 8
_FORBIDDEN_SUMMARIES = frozenset({"测试过程", "功能验证", "数据处理", "其他"})
_NUMBERED_GENERIC_SUMMARY = re.compile(r"^(?:输入|步骤|观测|判据)\s*[0-9０-９]+$")
_FEATURE_REPORT_ROW = re.compile(
    r"^\|\s*([A-Z][A-Z0-9_]*_F_[0-9]{3})\s*\|\s*([^|\r\n]+?)\s*\|",
    re.MULTILINE,
)
_CASE_ID_LINE = re.compile(r"(?m)^case_id:\s*([A-Z][A-Z0-9_]*_P[0-3]_[0-9]{3})\s*$")
_REPORT_FEATURE_BLOCK = re.compile(r"(?m)^report_feature:\s*\|-\s*$")


@dataclass(frozen=True, slots=True, order=True)
class MethodContractViolation:
    path: Path
    code: str
    message: str

    def render(self, root: Path) -> str:
        try:
            display = self.path.resolve().relative_to(root.resolve())
        except ValueError:
            display = self.path
        return f"{display}: {self.code} {self.message}"


def _line_violation_reason(value: str) -> str | None:
    if "\n" in value or "\r" in value:
        return "must be one physical line using '<摘要>：<正文>'"
    if _LINE_SEPARATOR not in value:
        return "must use the full-width '：' separator in '<摘要>：<正文>'"

    summary, _, body = value.partition(_LINE_SEPARATOR)
    summary = summary.strip()
    body = body.strip()
    if not summary:
        return "summary before '：' must be non-empty"
    if not body:
        return "body after '：' must be non-empty"
    if ":" in summary:
        return (
            "ASCII ':' is not allowed in the summary; use one canonical full-width '：' separator"
        )
    if summary in _FORBIDDEN_SUMMARIES or _NUMBERED_GENERIC_SUMMARY.fullmatch(summary):
        return f"summary {summary!r} is generic and cannot describe reviewer intent"
    return None


def _validate_method_payload(
    path: Path,
    payload: dict[str, Any],
    *,
    case_id: str,
    kind: str,
) -> list[MethodContractViolation]:
    if kind == "spec":
        line_code = "ETCASE430"
        count_code = "ETCASE431"
    elif kind == "plan":
        line_code = "ETPLAN223"
        count_code = "ETPLAN224"
    else:
        raise ValueError(f"unsupported method contract kind: {kind}")

    method = payload.get("method")
    if not isinstance(method, dict):
        return []

    violations: list[MethodContractViolation] = []
    for field in _REQUIRED_METHOD_LISTS:
        values = method.get(field)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values, start=1):
            if not isinstance(value, str):
                continue
            reason = _line_violation_reason(value)
            if reason is None:
                continue
            violations.append(
                MethodContractViolation(
                    path,
                    line_code,
                    f"{case_id} method.{field}[{index}] {reason}",
                )
            )

    steps = method.get("steps")
    if isinstance(steps, list) and not _MIN_STEPS <= len(steps) <= _MAX_STEPS:
        violations.append(
            MethodContractViolation(
                path,
                count_code,
                f"{case_id} method.steps must contain {_MIN_STEPS}..{_MAX_STEPS} real actions, found {len(steps)}",
            )
        )
    return violations


# Build the only stable mapping used to render report_feature: Feature ID -> report name.
def _feature_report_names(document: str) -> dict[str, str]:
    return {
        feature_id: report_name.strip()
        for feature_id, report_name in _FEATURE_REPORT_ROW.findall(document)
    }


# Keep raw YAML by Case ID so the checker can enforce the required block-scalar form.
def _raw_blocks_by_case_id(pattern: re.Pattern[str], document: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for match in pattern.finditer(document):
        block = match.group(1)
        case_match = _CASE_ID_LINE.search(block)
        if case_match is not None:
            blocks[case_match.group(1)] = block
    return blocks


# Verify report_feature is a deterministic numbered projection of feature_refs.
def _validate_report_feature_payload(
    path: Path,
    payload: dict[str, Any],
    *,
    case_id: str,
    kind: str,
    feature_names: dict[str, str],
    raw_block: str | None,
) -> list[MethodContractViolation]:
    if kind == "spec":
        refs_code = "ETCASE432"
        mapping_code = "ETCASE433"
        value_code = "ETCASE434"
        style_code = "ETCASE435"
    elif kind == "plan":
        refs_code = "ETPLAN225"
        mapping_code = "ETPLAN226"
        value_code = "ETPLAN227"
        style_code = "ETPLAN228"
    else:
        raise ValueError(f"unsupported report feature contract kind: {kind}")

    feature_refs = payload.get("feature_refs")
    if (
        not isinstance(feature_refs, list)
        or not feature_refs
        or not all(isinstance(item, str) and item.strip() for item in feature_refs)
    ):
        return [
            MethodContractViolation(
                path,
                refs_code,
                f"{case_id} feature_refs must contain at least one Feature ID",
            )
        ]

    missing_names = [feature_id for feature_id in feature_refs if feature_id not in feature_names]
    if missing_names:
        return [
            MethodContractViolation(
                path,
                mapping_code,
                f"{case_id} Feature Catalog report name is missing for: {', '.join(missing_names)}",
            )
        ]

    expected = "\n".join(
        f"{index}. {feature_names[feature_id]}"
        for index, feature_id in enumerate(feature_refs, start=1)
    )
    violations: list[MethodContractViolation] = []
    if payload.get("report_feature") != expected:
        violations.append(
            MethodContractViolation(
                path,
                value_code,
                f"{case_id} report_feature must exactly match numbered feature_refs report names",
            )
        )
    if raw_block is None or _REPORT_FEATURE_BLOCK.search(raw_block) is None:
        violations.append(
            MethodContractViolation(
                path,
                style_code,
                f"{case_id} report_feature must use a YAML '|-' block scalar",
            )
        )
    return violations


def _public_case_documents(root: Path) -> tuple[Path, ...]:
    case_root = root / "test_case_doc"
    if not case_root.is_dir():
        return ()
    return tuple(path for path in sorted(case_root.glob("*/*.md")) if path.parent.name == path.stem)


def validate_document(path: Path) -> list[MethodContractViolation]:
    document = path.read_text(encoding="utf-8-sig")
    specs, _ = validate_case_docs._load_spec_blocks(path)
    plans, _ = validate_case_plans._load_plans(path)
    feature_names = _feature_report_names(document)
    spec_blocks = _raw_blocks_by_case_id(validate_case_docs._SPEC_BLOCK, document)
    plan_blocks = _raw_blocks_by_case_id(validate_case_plans._PLAN_BLOCK, document)
    violations: list[MethodContractViolation] = []

    for payload in specs:
        case_id = str(payload.get("case_id") or "<missing>")
        violations.extend(_validate_method_payload(path, payload, case_id=case_id, kind="spec"))
        violations.extend(
            _validate_report_feature_payload(
                path,
                payload,
                case_id=case_id,
                kind="spec",
                feature_names=feature_names,
                raw_block=spec_blocks.get(case_id),
            )
        )
    for payload in plans:
        case_id = str(payload.get("case_id") or "<missing>")
        violations.extend(_validate_method_payload(path, payload, case_id=case_id, kind="plan"))
        violations.extend(
            _validate_report_feature_payload(
                path,
                payload,
                case_id=case_id,
                kind="plan",
                feature_names=feature_names,
                raw_block=plan_blocks.get(case_id),
            )
        )
    return violations


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate canonical reviewer-facing Case method and report Feature grammar."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional public <ip>.md files. Without paths, validate every public IP document.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    paths = tuple(args.paths) if args.paths else _public_case_documents(REPOSITORY_ROOT)
    violations: list[MethodContractViolation] = []
    for path in paths:
        resolved = path if path.is_absolute() else REPOSITORY_ROOT / path
        if not resolved.is_file():
            violations.append(
                MethodContractViolation(
                    resolved,
                    "ETCASE430",
                    "public Case document does not exist",
                )
            )
            continue
        violations.extend(validate_document(resolved))

    for violation in sorted(violations):
        print(violation.render(REPOSITORY_ROOT))
    if violations:
        print(f"Case method human-review contract failed: {len(violations)} violation(s).")
        return 1
    print("Case method human-review contract valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
