#!/usr/bin/env python3
# Generate a human-review Formal Case report from ET_CASE_SPEC and canonical result JSON.

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PC_ROOT = REPOSITORY_ROOT / "pc"
if str(PC_ROOT) not in sys.path:
    sys.path.insert(0, str(PC_ROOT))

from et_test_platform.results.case_report import build_case_report_model  # noqa: E402

_HEADER_FILL = "#B5121B"
_SECTION_FILL = "#F3F4F6"
_PASS_FILL = "#E2F0D9"
_FAIL_FILL = "#F4CCCC"
_INCOMPLETE_FILL = "#FFF2CC"
_COMMENT_AUTHOR = "ET Automated Testing Platform"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a stable-Case human report from ET_CASE_SPEC and canonical result.json files."
    )
    parser.add_argument(
        "--document", required=True, help="IP Markdown containing ET_CASE_SPEC blocks"
    )
    parser.add_argument(
        "--results", required=True, help="pytest artifact directory containing session.json/cases"
    )
    parser.add_argument("--output", required=True, help="output .xlsx or .json path")
    parser.add_argument("--chip", help="optional chip display name override")
    return parser.parse_args(argv)


def _string(value: object) -> str:
    return "" if value is None else str(value)


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _multiline(values: object) -> str:
    if not isinstance(values, list):
        return _string(values)
    return "\n".join(str(value) for value in values)


def _numbered(values: object) -> str:
    if not isinstance(values, list):
        return _string(values)
    return "\n".join(f"{index}. {value}" for index, value in enumerate(values, start=1))


def _write_json(model: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")


def _report_result(status: object) -> str:
    normalized = str(status or "").upper()
    if normalized in {
        "PASS",
        "FAIL",
        "SKIP",
        "EVIDENCE_MISSING",
        "NOT_EXECUTED",
        "NOT_SELECTED",
        "RUN_ERROR",
    }:
        return normalized
    return "UNKNOWN"


def _review_method(row: dict[str, Any]) -> str:
    method = _string(row.get("method")).strip()
    criteria = _string(row.get("pass_criteria")).strip()
    parts: list[str] = []
    if method:
        parts.append(method)
    if criteria:
        parts.append(f"通过条件：\n{criteria}")
    return "\n\n".join(parts)


def _report_state(model: dict[str, Any]) -> tuple[str, int]:
    incomplete = sum(
        1
        for row in model.get("cases", [])
        if str(row.get("status")) != "NOT_SELECTED" and not bool(row.get("coverage_complete"))
    )
    if not bool(model.get("session_complete")):
        incomplete += 1
    if incomplete:
        return "不完整", incomplete
    return "完整", 0


def _add_report_sheet(workbook: Any, model: dict[str, Any]) -> None:
    sheet = workbook.add_worksheet("测试报告")
    cases = model["cases"]
    summary = model["summary"]
    session = model.get("session", {})
    status_counts = summary.get("status_counts", {})
    report_state, incomplete_count = _report_state(model)
    chip = model.get("chip_name") or "ET"
    ip_name = model.get("ip_name") or "IP"
    title = f"{chip}_{ip_name}测试报告"

    title_format = workbook.add_format(
        {
            "bg_color": _HEADER_FILL,
            "font_color": "#FFFFFF",
            "bold": True,
            "font_size": 16,
            "align": "center",
            "valign": "vcenter",
        }
    )
    section_format = workbook.add_format(
        {
            "bg_color": _SECTION_FILL,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
        }
    )
    metadata_format = workbook.add_format({"valign": "vcenter", "border": 1})
    header_format = workbook.add_format(
        {
            "bg_color": _HEADER_FILL,
            "font_color": "#FFFFFF",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "border": 1,
        }
    )
    body_format = workbook.add_format({"valign": "top", "text_wrap": True, "border": 1})
    center_format = workbook.add_format(
        {"align": "center", "valign": "vcenter", "text_wrap": True, "border": 1}
    )
    pass_format = workbook.add_format(
        {
            "bg_color": _PASS_FILL,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
        }
    )
    fail_format = workbook.add_format(
        {
            "bg_color": _FAIL_FILL,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
        }
    )
    incomplete_format = workbook.add_format(
        {
            "bg_color": _INCOMPLETE_FILL,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
        }
    )

    sheet.merge_range("A1:F1", title, title_format)
    sheet.set_row(0, 28)

    metadata = [
        ["报告状态", report_state, "芯片", chip, "IP", ip_name],
        [
            "Run ID",
            session.get("run_id"),
            "Target",
            session.get("target_id"),
            "Firmware",
            session.get("firmware_build_id"),
        ],
        [
            "Started",
            session.get("started_at"),
            "Finished",
            session.get("finished_at"),
            "Platform",
            session.get("platform_version"),
        ],
        [
            "Source",
            session.get("source_revision"),
            "Dirty",
            session.get("source_dirty"),
            "Spec SHA256",
            session.get("spec_sha256"),
        ],
    ]
    for row_index, row in enumerate(metadata, start=1):
        for column_index, value in enumerate(row):
            cell_format = section_format if column_index % 2 == 0 else metadata_format
            sheet.write(row_index, column_index, value, cell_format)
    sheet.write(1, 1, report_state, incomplete_format if incomplete_count else pass_format)

    summary_row = 5
    summary_values = [
        "稳定Case",
        summary.get("stable_case_count", 0),
        "PASS",
        status_counts.get("PASS", 0),
        "FAIL",
        status_counts.get("FAIL", 0),
    ]
    for column_index, value in enumerate(summary_values):
        sheet.write(summary_row, column_index, value, section_format)
    if incomplete_count:
        sheet.write(
            summary_row + 1,
            0,
            "说明",
            section_format,
        )
        sheet.merge_range(
            summary_row + 1,
            1,
            summary_row + 1,
            5,
            f"有 {incomplete_count} 个稳定 Case 未形成有效 DUT PASS/FAIL 结论；测试结果列显示明确状态，具体原因见备注。",
            incomplete_format,
        )

    header_row = 8
    headers = ["编号", "测试Feature", "测试方法", "测试Case ID", "测试结果", "备注"]
    sheet.write_row(header_row, 0, headers, header_format)

    start_row = header_row + 1
    for index, row in enumerate(cases, start=1):
        excel_row = start_row + index - 1
        result_text = _report_result(row.get("status"))
        values = [
            index,
            row.get("report_feature"),
            _review_method(row),
            row.get("case_id"),
            result_text,
            row.get("remark"),
        ]
        for column_index, value in enumerate(values):
            cell_format = center_format if column_index in {0, 4} else body_format
            sheet.write(excel_row, column_index, value, cell_format)
        if result_text == "PASS":
            sheet.write(excel_row, 4, result_text, pass_format)
        elif result_text == "FAIL":
            sheet.write(excel_row, 4, result_text, fail_format)
        else:
            sheet.write(excel_row, 4, result_text, incomplete_format)
        case_id = _string(row.get("case_id"))
        p_level = _string(row.get("p_level"))
        if case_id or p_level:
            sheet.write_comment(
                excel_row,
                3,
                f"Case名称: {_string(row.get('case_name'))}\nP级: {p_level}",
                {"author": _COMMENT_AUTHOR},
            )

    if cases:
        end_row = start_row + len(cases) - 1
        sheet.add_table(
            header_row,
            0,
            end_row,
            5,
            {
                "name": "StableCaseReport",
                "style": "Table Style Medium 2",
                "columns": [{"header": header} for header in headers],
            },
        )

    sheet.freeze_panes(start_row, 0)
    sheet.set_column("A:A", 7)
    sheet.set_column("B:B", 30)
    sheet.set_column("C:C", 64)
    sheet.set_column("D:D", 34)
    sheet.set_column("E:E", 12)
    sheet.set_column("F:F", 62)


def _add_execution_sheet(workbook: Any, model: dict[str, Any]) -> None:
    sheet = workbook.add_worksheet("执行明细")
    header_format = workbook.add_format(
        {
            "bg_color": _HEADER_FILL,
            "font_color": "#FFFFFF",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "border": 1,
        }
    )
    body_format = workbook.add_format({"valign": "top", "text_wrap": True, "border": 1})
    headers = [
        "Case ID",
        "Parameter ID",
        "Raw Status",
        "Duration(s)",
        "Evidence Complete",
        "Evidence Sources",
        "Missing Evidence",
        "Target",
        "Chip",
        "Firmware",
        "Measurements",
        "Observations",
        "工程诊断Error",
        "Result Path",
    ]
    sheet.write_row(0, 0, headers, header_format)

    executions = model["executions"]
    for row_index, row in enumerate(executions, start=1):
        values = [
            row["case_id"],
            row["parameter_id"],
            row["status"],
            row["duration_s"],
            row["evidence_complete"],
            _multiline(row["evidence_sources"]),
            _multiline(row["missing_evidence_sources"]),
            row["target_id"],
            row["chip_id"],
            row["firmware_build_id"],
            _json_text(row["measurements"]),
            _json_text(row["observations"]),
            row["error"],
            row["result_path"],
        ]
        sheet.write_row(row_index, 0, values, body_format)

    if executions:
        sheet.add_table(
            0,
            0,
            len(executions),
            len(headers) - 1,
            {
                "name": "ExecutionDetail",
                "style": "Table Style Medium 2",
                "columns": [{"header": header} for header in headers],
            },
        )
    sheet.freeze_panes(1, 0)
    widths = [16, 24, 18, 12, 18, 22, 22, 20, 18, 28, 60, 72, 72, 50]
    for column, width in enumerate(widths):
        sheet.set_column(column, column, width)


def _add_trace_sheet(workbook: Any, model: dict[str, Any]) -> None:
    sheet = workbook.add_worksheet("规格追溯")
    header_format = workbook.add_format(
        {
            "bg_color": _HEADER_FILL,
            "font_color": "#FFFFFF",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "border": 1,
        }
    )
    body_format = workbook.add_format({"valign": "top", "text_wrap": True, "border": 1})
    headers = [
        "Case ID",
        "P级",
        "测试Feature",
        "测试Case",
        "Feature Refs",
        "Inputs",
        "Steps",
        "Observations",
        "Pass Criteria",
        "Failure Observations",
        "Resources",
        "Backend",
    ]
    sheet.write_row(0, 0, headers, header_format)

    rows = model["spec_trace"]
    for row_index, row in enumerate(rows, start=1):
        failure_observations = "\n".join(
            f"{item.get('label')} [{item.get('key')}] <- {item.get('source')}"
            for item in row["failure_observations"]
        )
        values = [
            row["case_id"],
            row["p_level"],
            row["report_feature"],
            row["case_name"],
            _multiline(row["feature_refs"]),
            _multiline(row["inputs"]),
            _numbered(row["steps"]),
            _multiline(row["observations"]),
            _numbered(row["pass_criteria"]),
            failure_observations,
            _json_text(row["resources"]),
            _multiline(row["backend"]),
        ]
        sheet.write_row(row_index, 0, values, body_format)

    if rows:
        sheet.add_table(
            0,
            0,
            len(rows),
            len(headers) - 1,
            {
                "name": "CaseSpecTrace",
                "style": "Table Style Medium 2",
                "columns": [{"header": header} for header in headers],
            },
        )
    sheet.freeze_panes(1, 0)
    widths = [16, 7, 30, 34, 24, 42, 54, 42, 50, 50, 44, 20]
    for column, width in enumerate(widths):
        sheet.set_column(column, column, width)


# 供当前工作区发布复用同一报告版式；固定容器时间使相同输入不产生无意义写入。
def xlsx_bytes(model: dict[str, object]) -> bytes:
    try:
        import xlsxwriter
    except ImportError as exc:
        raise RuntimeError(
            'XLSX export requires the report extra; install with: pip install -e ".[report]"'
        ) from exc

    stream = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        stream,
        {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False},
    )
    workbook.set_properties({"created": datetime(1980, 1, 1)})
    try:
        _add_report_sheet(workbook, model)
        _add_execution_sheet(workbook, model)
        _add_trace_sheet(workbook, model)
    finally:
        workbook.close()
    return stream.getvalue()


def _write_xlsx(model: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(xlsx_bytes(model))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    model = build_case_report_model(args.document, args.results, chip_name=args.chip)
    output = Path(args.output).resolve()
    suffix = output.suffix.lower()
    if suffix == ".json":
        _write_json(model, output)
    elif suffix == ".xlsx":
        _write_xlsx(model, output)
    else:
        raise ValueError("--output must end with .json or .xlsx")
    print(f"Generated case report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
