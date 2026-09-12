#!/usr/bin/env python3
# Validate each chip IP analysis against its stable public Feature/Case contract and summary.

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "test_case_doc"
_FEATURE_ID = re.compile(r"^[A-Z][A-Z0-9_]*_F_[0-9]{3}$")
_CASE_ID = re.compile(r"^[A-Z][A-Z0-9_]*_P[0-3]_[0-9]{3}$")
_PUBLIC_FEATURE_SECTION = re.compile(r"(?m)^##\s*1\.\s*Feature Catalog\s*$")
_PUBLIC_CASE_SECTION = re.compile(r"(?m)^##\s*2\.\s*Case Catalog\s*$")
_PUBLIC_MACHINE_SECTION = re.compile(r"(?m)^##\s*3\.\s*Machine-readable Case Contract\s*$")
_FEATURE_SECTION = re.compile(r"(?m)^#+\s*第五章[^\n]*Feature Mapping\s*$")
_CASE_SECTION = re.compile(r"(?m)^#+\s*第六章[^\n]*Case Adaptation\s*$")
_SUMMARY_SECTION = re.compile(r"(?m)^##\s*4\.\s*Chip Adaptation Summary\s*$")
_NEXT_PUBLIC_SECTION = re.compile(r"(?m)^##\s*5\.\s*Common Gap / Evolution\s*$")
_WORKING_TREE_FPGA_HIL = re.compile(r"(?m)^Working-tree FPGA HIL:\s*EXECUTED\b")
_STALE_CURRENT_SHA_FPGA_HIL = re.compile(
    r"(?m)^Current-SHA FPGA HIL:\s*NOT_EXECUTED\s*/\s*NOT_VERIFIED\s*$"
)
_TEST_STATUS_BEGIN = "<!-- ET_CHIP_TEST_STATUS_BEGIN -->"
_TEST_STATUS_END = "<!-- ET_CHIP_TEST_STATUS_END -->"
# 已废弃的原始执行目录：只读历史、允许清理，引用后必然断链。
_DEPRECATED_RUN_REF = re.compile(r"artifacts/runs(?:/|\b)")
_TEST_STATUS_UPDATED = re.compile(
    r"(?m)^状态更新时间：`(?P<value>\d{4}-\d{2}-\d{2} \d{2}:\d{2} CST)`\s*$"
)
_RUN_IDENTITY_HEADER = ("Lane", "测试时间", "Source Revision", "Source Dirty", "Evidence")
_RESULT_SUMMARY_HEADER = (
    "Lane",
    "注册Case",
    "已执行Case",
    "PASS",
    "FAIL",
    "SKIP",
    "NOT_EXECUTED",
    "Executions",
)
_NON_PASS_HEADER = (
    "Case ID",
    "Lane",
    "状态",
    "Feature",
    "测试现象",
    "原因/阻塞",
    "复测条件",
    "Evidence",
)
_FEATURE_HARDWARE = {"SUPPORTED", "UNSUPPORTED", "NEEDS_VERIFICATION"}
_FEATURE_PLATFORM = {
    "ADAPTED",
    "PARTIAL_ADAPTATION",
    "IMPLEMENTATION_GAP",
    "MAPPING_GAP",
    "NOT_APPLICABLE",
    "NEEDS_VERIFICATION",
}
_CASE_ADAPTATION = {
    "ADAPTED",
    "NOT_APPLICABLE",
    "IMPLEMENTATION_GAP",
    "MAPPING_GAP",
    "BENCH_GAP",
    "ENVIRONMENT_GAP",
    "NEEDS_VERIFICATION",
}
_STATUS_ORDER = (
    "ADAPTED",
    "PARTIAL_ADAPTATION",
    "IMPLEMENTATION_GAP",
    "MAPPING_GAP",
    "BENCH_GAP",
    "ENVIRONMENT_GAP",
    "NEEDS_VERIFICATION",
    "NOT_APPLICABLE",
)


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: Path
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path.relative_to(ROOT)}: {self.code} {self.message}"


def _section(text: str, start: re.Pattern[str], end: re.Pattern[str] | None = None) -> str:
    match = start.search(text)
    if match is None:
        return ""
    tail = text[match.end() :]
    if end is None:
        return tail
    end_match = end.search(tail)
    return tail[: end_match.start()] if end_match is not None else tail


def _table_ids(text: str, predicate: re.Pattern[str]) -> list[str]:
    values: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and predicate.fullmatch(cells[0]):
            values.append(cells[0])
    return values


def _catalog_ids(public_text: str) -> tuple[list[str], list[str]]:
    features = _table_ids(
        _section(public_text, _PUBLIC_FEATURE_SECTION, _PUBLIC_CASE_SECTION),
        _FEATURE_ID,
    )
    cases = _table_ids(
        _section(public_text, _PUBLIC_CASE_SECTION, _PUBLIC_MACHINE_SECTION),
        _CASE_ID,
    )
    return features, cases


def _mapping_rows(section: str, *, feature: bool) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    expected = _FEATURE_ID if feature else _CASE_ID
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if cells and expected.fullmatch(cells[0]):
            rows.append(cells)
    return rows


def _status_summary(statuses: list[str]) -> str:
    counts = Counter(statuses)
    ordered = [f"{status}={counts[status]}" for status in _STATUS_ORDER if counts[status]]
    ordered.extend(
        f"{status}={count}"
        for status, count in sorted(counts.items())
        if status not in _STATUS_ORDER
    )
    return "; ".join(ordered)


def _summary_rows(public_text: str) -> dict[str, tuple[str, str, str]]:
    section = _section(public_text, _SUMMARY_SECTION, _NEXT_PUBLIC_SECTION)
    rows: dict[str, tuple[str, str, str]] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if len(cells) < 5 or not re.fullmatch(r"ET[0-9]{3,}", cells[0], re.IGNORECASE):
            continue
        rows[cells[0].upper()] = (cells[1], cells[2], cells[4].strip("`"))
    return rows


def _validate_exact_ids(
    path: Path,
    *,
    label: str,
    actual: list[str],
    expected: list[str],
    duplicate_code: str,
    mismatch_code: str,
) -> list[Violation]:
    violations: list[Violation] = []
    if len(actual) != len(set(actual)):
        violations.append(Violation(path, duplicate_code, f"duplicate public {label} rows"))
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        violations.append(
            Violation(
                path, mismatch_code, f"{label} mapping mismatch; missing={missing}, extra={extra}"
            )
        )
    return violations


def _validate_feature_rows(
    path: Path, rows: list[tuple[str, ...]]
) -> tuple[list[Violation], list[str]]:
    violations: list[Violation] = []
    statuses: list[str] = []
    for row in rows:
        if len(row) < 5:
            violations.append(
                Violation(path, "ETCHIPDOC205", f"malformed Feature mapping row: {row[0]}")
            )
            continue
        if row[1] not in _FEATURE_HARDWARE:
            violations.append(
                Violation(path, "ETCHIPDOC206", f"{row[0]} invalid Hardware status {row[1]!r}")
            )
        if row[3] not in _FEATURE_PLATFORM:
            violations.append(
                Violation(path, "ETCHIPDOC207", f"{row[0]} invalid Platform status {row[3]!r}")
            )
        statuses.append(row[3])
    return violations, statuses


def _validate_case_rows(
    path: Path, rows: list[tuple[str, ...]]
) -> tuple[list[Violation], list[str]]:
    violations: list[Violation] = []
    statuses: list[str] = []
    for row in rows:
        if len(row) < 3:
            violations.append(
                Violation(path, "ETCHIPDOC208", f"malformed Case adaptation row: {row[0]}")
            )
            continue
        if row[1] not in _CASE_ADAPTATION:
            violations.append(
                Violation(path, "ETCHIPDOC209", f"{row[0]} invalid adaptation status {row[1]!r}")
            )
        statuses.append(row[1])
    return violations, statuses


def _validate_summary(
    public: Path,
    chip_doc: Path,
    public_text: str,
    feature_statuses: list[str],
    case_statuses: list[str],
) -> list[Violation]:
    chip = chip_doc.stem.split("_", 1)[0].upper()
    summary = _summary_rows(public_text).get(chip)
    if summary is None:
        return [
            Violation(public, "ETCHIPDOC301", f"missing Chip Adaptation Summary row for {chip}")
        ]

    violations: list[Violation] = []
    expected_feature = _status_summary(feature_statuses)
    expected_case = _status_summary(case_statuses)
    if summary[0] != expected_feature:
        violations.append(
            Violation(
                public,
                "ETCHIPDOC302",
                f"{chip} Feature summary must be {expected_feature!r}, got {summary[0]!r}",
            )
        )
    if summary[1] != expected_case:
        violations.append(
            Violation(
                public,
                "ETCHIPDOC303",
                f"{chip} Case summary must be {expected_case!r}, got {summary[1]!r}",
            )
        )
    if summary[2] != chip_doc.name:
        violations.append(
            Violation(
                public,
                "ETCHIPDOC304",
                f"{chip} detail link must target {chip_doc.name!r}",
            )
        )
    return violations


# 已声明执行过Working-tree HIL的芯片文档必须保留最小追溯信息，并且不能继续
# 使用旧的Current-SHA NOT_EXECUTED语句制造内部矛盾。
def _validate_hil_sync(path: Path, text: str) -> list[Violation]:
    if _WORKING_TREE_FPGA_HIL.search(text) is None:
        return []

    violations: list[Violation] = []
    required_markers = (
        "Logical Case result:",
        "HIL Evidence:",
        "Exact committed SHA FPGA HIL:",
    )
    for marker in required_markers:
        if marker not in text:
            violations.append(
                Violation(
                    path,
                    "ETSYNC202",
                    f"executed Working-tree FPGA HIL is missing {marker!r}",
                )
            )

    if _STALE_CURRENT_SHA_FPGA_HIL.search(text) is not None:
        violations.append(
            Violation(
                path,
                "ETSYNC203",
                "executed Working-tree FPGA HIL conflicts with stale Current-SHA NOT_EXECUTED",
            )
        )
    return violations


# 解析状态区域中的固定Markdown表；表头负责稳定机器契约，单元格内容仍面向人工审核。
def _status_table(block: str, header: tuple[str, ...]) -> list[tuple[str, ...]] | None:

    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if cells != header:
            continue
        rows: list[tuple[str, ...]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.startswith("|"):
                break
            rows.append(tuple(cell.strip() for cell in row_line.strip().strip("|").split("|")))
        return rows
    return None


def _plain_cell(value: str) -> str:

    return value.strip().strip("`").strip()


def _valid_timestamp(value: str) -> bool:

    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M CST")
    except ValueError:
        return False
    return True


# 提取唯一状态区域；缺失、重复或反向Marker均失败关闭。
def _test_status_block(
    path: Path, text: str, *, required: bool
) -> tuple[str | None, list[Violation]]:

    begin_count = text.count(_TEST_STATUS_BEGIN)
    end_count = text.count(_TEST_STATUS_END)
    if begin_count == 0 and end_count == 0:
        if required:
            return None, [Violation(path, "ETSYNC204", "missing ET_CHIP_TEST_STATUS block")]
        return None, []
    if begin_count != 1 or end_count != 1:
        return None, [Violation(path, "ETSYNC204", "ET_CHIP_TEST_STATUS markers must appear once")]

    begin = text.index(_TEST_STATUS_BEGIN) + len(_TEST_STATUS_BEGIN)
    end = text.index(_TEST_STATUS_END)
    if end <= begin:
        return None, [Violation(path, "ETSYNC204", "ET_CHIP_TEST_STATUS markers are reversed")]
    return text[begin:end], []


# 校验每个Lane最近一次运行的时间、Source身份和Evidence位置。
def _validate_identity_rows(
    path: Path, rows: list[tuple[str, ...]]
) -> tuple[set[str], list[Violation]]:

    lanes: set[str] = set()
    violations: list[Violation] = []
    for row in rows:
        if len(row) != len(_RUN_IDENTITY_HEADER):
            violations.append(Violation(path, "ETSYNC206", "malformed run identity row"))
            continue
        lane, tested_at, revision, source_dirty, evidence = map(_plain_cell, row)
        if not lane or lane in lanes:
            violations.append(Violation(path, "ETSYNC206", f"duplicate or empty Lane {lane!r}"))
        lanes.add(lane)
        if not _valid_timestamp(tested_at):
            violations.append(Violation(path, "ETSYNC205", f"invalid test time {tested_at!r}"))
        if not revision or source_dirty not in {"true", "false"} or not evidence:
            violations.append(
                Violation(path, "ETSYNC206", f"incomplete identity for Lane {lane!r}")
            )
    return lanes, violations


# 校验逻辑Case统计关系，并返回每个Lane的FAIL/SKIP/NOT_EXECUTED数量。
def _validate_summary_rows(
    path: Path, rows: list[tuple[str, ...]]
) -> tuple[dict[str, tuple[int, int, int]], list[Violation]]:

    summary: dict[str, tuple[int, int, int]] = {}
    violations: list[Violation] = []
    for row in rows:
        if len(row) != len(_RESULT_SUMMARY_HEADER):
            violations.append(Violation(path, "ETSYNC207", "malformed result summary row"))
            continue
        lane = _plain_cell(row[0])
        try:
            registered, executed, passed, failed, skipped, not_executed, executions = (
                int(_plain_cell(value)) for value in row[1:]
            )
        except ValueError:
            violations.append(Violation(path, "ETSYNC207", f"non-numeric result for Lane {lane!r}"))
            continue
        values = (registered, executed, passed, failed, skipped, not_executed, executions)
        if lane in summary or any(value < 0 for value in values):
            violations.append(Violation(path, "ETSYNC207", f"invalid summary for Lane {lane!r}"))
            continue
        if executed != passed + failed + skipped or registered != executed + not_executed:
            violations.append(
                Violation(path, "ETSYNC207", f"inconsistent Case counts for Lane {lane!r}")
            )
        if executions < executed:
            violations.append(
                Violation(path, "ETSYNC207", f"Executions below executed Cases for Lane {lane!r}")
            )
        summary[lane] = (failed, skipped, not_executed)
    return summary, violations


# 校验FAIL/SKIP明细与汇总一致，并允许记录仍需闭环的NOT_EXECUTED Case。
def _validate_non_pass_rows(
    path: Path,
    rows: list[tuple[str, ...]],
    summary: dict[str, tuple[int, int, int]],
) -> list[Violation]:

    violations: list[Violation] = []
    actual_non_pass: Counter[tuple[str, str]] = Counter()
    sentinel_rows = 0
    seen_cases: set[tuple[str, str]] = set()
    for row in rows:
        if len(row) != len(_NON_PASS_HEADER):
            violations.append(Violation(path, "ETSYNC208", "malformed non-PASS row"))
            continue
        case_id, lane, status, feature, phenomenon, reason, retest, evidence = map(_plain_cell, row)
        if case_id == "—" and status == "NONE":
            sentinel_rows += 1
            continue
        if (
            not _CASE_ID.fullmatch(case_id)
            or lane not in summary
            or status not in {"FAIL", "SKIP", "NOT_EXECUTED"}
        ):
            violations.append(
                Violation(path, "ETSYNC208", f"invalid non-PASS identity {row[:3]!r}")
            )
            continue
        if (lane, case_id) in seen_cases:
            violations.append(
                Violation(path, "ETSYNC208", f"duplicate non-PASS Case {lane}/{case_id}")
            )
        seen_cases.add((lane, case_id))
        if not all((feature, phenomenon, reason, retest, evidence)):
            violations.append(
                Violation(path, "ETSYNC208", f"incomplete non-PASS facts for {case_id}")
            )
        actual_non_pass[(lane, status)] += 1

    expected_executed_non_pass = sum(failed + skipped for failed, skipped, _ in summary.values())
    if expected_executed_non_pass == 0 and not actual_non_pass:
        if sentinel_rows != 1 or actual_non_pass:
            violations.append(Violation(path, "ETSYNC208", "zero non-PASS requires one NONE row"))
    elif sentinel_rows != 0:
        violations.append(Violation(path, "ETSYNC208", "NONE row conflicts with non-PASS results"))
    for lane, (failed, skipped, not_executed) in summary.items():
        if actual_non_pass[(lane, "FAIL")] != failed or actual_non_pass[(lane, "SKIP")] != skipped:
            violations.append(
                Violation(path, "ETSYNC208", f"non-PASS rows do not match {lane} summary")
            )
        if actual_non_pass[(lane, "NOT_EXECUTED")] > not_executed:
            violations.append(
                Violation(path, "ETSYNC208", f"NOT_EXECUTED rows exceed {lane} summary")
            )
    return violations


# 验证当前芯片测试状态的唯一时间戳、运行身份、逻辑Case统计和非PASS明细。
def _validate_test_status(path: Path, text: str, *, required: bool) -> list[Violation]:

    block, violations = _test_status_block(path, text, required=required)
    if block is None:
        return violations

    updated_match = _TEST_STATUS_UPDATED.search(block)
    if updated_match is None or not _valid_timestamp(updated_match.group("value")):
        violations.append(
            Violation(path, "ETSYNC205", "status update time must use YYYY-MM-DD HH:mm CST")
        )

    identity_rows = _status_table(block, _RUN_IDENTITY_HEADER)
    summary_rows = _status_table(block, _RESULT_SUMMARY_HEADER)
    non_pass_rows = _status_table(block, _NON_PASS_HEADER)
    if identity_rows is None or summary_rows is None or non_pass_rows is None:
        violations.append(Violation(path, "ETSYNC206", "test status tables are incomplete"))
        return violations
    if not identity_rows or not summary_rows:
        violations.append(Violation(path, "ETSYNC206", "identity and summary tables need rows"))
        return violations

    identity_lanes, identity_violations = _validate_identity_rows(path, identity_rows)
    summary, summary_violations = _validate_summary_rows(path, summary_rows)
    violations.extend(identity_violations)
    violations.extend(summary_violations)
    if set(summary) != identity_lanes:
        violations.append(Violation(path, "ETSYNC207", "identity and summary Lane sets differ"))
    violations.extend(_validate_non_pass_rows(path, non_pass_rows, summary))
    return violations


def _validate_deprecated_run_reference(path: Path, text: str) -> list[Violation]:
    """拒绝芯片文档引用已废弃的 artifacts/runs 目录。

    该目录是只读历史且允许被清理，引用必然断链；证据来源应写为不含路径的结论，
    或引用 records/<CHIP>/<IP>/current。
    """
    if not _DEPRECATED_RUN_REF.search(text):
        return []
    return [
        Violation(
            path,
            "ETCHIPDOC301",
            "chip analysis must not reference deprecated artifacts/runs evidence paths",
        )
    ]


def _validate_chip_doc(
    public: Path, chip_doc: Path, *, require_test_status: bool = False
) -> list[Violation]:
    public_text = public.read_text(encoding="utf-8-sig")
    chip_text = chip_doc.read_text(encoding="utf-8-sig")
    public_features, public_cases = _catalog_ids(public_text)
    feature_rows = _mapping_rows(_section(chip_text, _FEATURE_SECTION, _CASE_SECTION), feature=True)
    case_rows = _mapping_rows(_section(chip_text, _CASE_SECTION), feature=False)

    violations: list[Violation] = []
    if "ET_CASE_SPEC_BEGIN" in chip_text or "ET_CASE_PLAN_BEGIN" in chip_text:
        violations.append(
            Violation(
                chip_doc,
                "ETCHIPDOC101",
                "chip analysis must not contain public Case machine blocks",
            )
        )
    violations.extend(
        _validate_exact_ids(
            chip_doc,
            label="Feature",
            actual=[row[0] for row in feature_rows],
            expected=public_features,
            duplicate_code="ETCHIPDOC201",
            mismatch_code="ETCHIPDOC202",
        )
    )
    violations.extend(
        _validate_exact_ids(
            chip_doc,
            label="Case",
            actual=[row[0] for row in case_rows],
            expected=public_cases,
            duplicate_code="ETCHIPDOC203",
            mismatch_code="ETCHIPDOC204",
        )
    )
    feature_violations, feature_statuses = _validate_feature_rows(chip_doc, feature_rows)
    case_violations, case_statuses = _validate_case_rows(chip_doc, case_rows)
    violations.extend(feature_violations)
    violations.extend(case_violations)
    violations.extend(
        _validate_summary(public, chip_doc, public_text, feature_statuses, case_statuses)
    )
    violations.extend(_validate_hil_sync(chip_doc, chip_text))
    violations.extend(_validate_test_status(chip_doc, chip_text, required=require_test_status))
    violations.extend(_validate_deprecated_run_reference(chip_doc, chip_text))
    return violations


def check_documents(required_status_docs: set[Path] | None = None) -> list[Violation]:
    required_status_docs = {path.resolve() for path in (required_status_docs or set())}
    violations: list[Violation] = []
    discovered: set[Path] = set()
    for directory in sorted(path for path in DOC_ROOT.iterdir() if path.is_dir()):
        public = directory / f"{directory.name}.md"
        if not public.is_file():
            continue
        for chip_doc in sorted(directory.glob(f"ET*_{directory.name}.md")):
            discovered.add(chip_doc.resolve())
            violations.extend(
                _validate_chip_doc(
                    public,
                    chip_doc,
                    require_test_status=chip_doc.resolve() in required_status_docs,
                )
            )
    for missing in sorted(required_status_docs - discovered):
        violations.append(Violation(missing, "ETSYNC204", "required chip IP document not found"))
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate chip IP analysis documents.")
    parser.add_argument(
        "--require-test-status",
        action="append",
        default=[],
        metavar="CHIP_DOC",
        help="require a valid current test status block in this chip IP document",
    )
    args = parser.parse_args()
    required_status_docs: set[Path] = set()
    for value in args.require_test_status:
        candidate = Path(value)
        resolved = (candidate if candidate.is_absolute() else ROOT / candidate).resolve()
        try:
            resolved.relative_to(DOC_ROOT.resolve())
        except ValueError:
            parser.error(f"required chip document must stay under {DOC_ROOT.relative_to(ROOT)}")
        required_status_docs.add(resolved)

    violations = check_documents(required_status_docs)
    for violation in violations:
        print(violation.render(), file=sys.stderr)
    if violations:
        print(
            f"Chip IP document validation failed: {len(violations)} violation(s).", file=sys.stderr
        )
        return 1
    print("Chip IP document validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
