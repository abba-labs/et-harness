# 当前Case档案的确定性Excel视图。
# 职责：展示各场景最近观测、实际方法版本及受保护快照。
# 边界：只转换已校验的记录，不汇编成虚构的单次回归，不重新判定结果。
# 依赖：标准库、项目既有XlsxWriter报告依赖和记录模型。

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from record_model import CaseRecord, Snapshot, list_value, object_value, timestamp

if TYPE_CHECKING:
    from xlsxwriter import Workbook

FIELDS = (
    ("case_id", "Case ID", 22),
    ("lane", "Lane", 10),
    ("parameter_id", "参数", 28),
    ("status", "原始结果", 20),
    ("finished_at", "测试时间 (CST)", 23),
    ("target_id", "Target", 14),
    ("source_revision", "Source SHA", 43),
    ("source_dirty", "Dirty", 10),
    ("firmware_build_id", "Firmware Build", 38),
    ("bitstream_id", "FPGA Bitstream", 24),
    ("spec_sha256", "规范 SHA256", 66),
    ("run_id", "Run ID", 39),
    ("attempts", "累计次数", 12),
    ("status_counts", "累计结果计数", 40),
    ("protected_count", "Case保护快照数", 18),
    ("case_document", "Case文档", 40),
    ("evidence", "原始记录", 40),
)


def _value(value: object, field: str = "") -> object:
    if value is None:
        return "未知" if field != "parameter_id" else "无参数"
    if field == "finished_at":
        return timestamp(value).astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    if isinstance(value, dict):
        return "；".join(f"{key}: {_value(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return "\n".join(str(_value(item)) for item in value)
    if isinstance(value, str) and len(value) > 32767:
        raise ValueError("record text exceeds Excel cell capacity")
    return value


def _sheet(
    workbook: Workbook,
    name: str,
    title: str,
    input_sha: str,
    columns: Sequence[tuple[str, int]],
    rows: Sequence[Sequence[object]],
) -> None:
    sheet = workbook.add_worksheet(name)
    title_format = workbook.add_format({"bold": True, "font_size": 14})
    header = workbook.add_format(
        {"bg_color": "#B5121B", "font_color": "white", "bold": True, "text_wrap": True}
    )
    body = workbook.add_format({"valign": "top", "text_wrap": True})
    date = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss", "valign": "top"})
    sheet.write(0, 0, title, title_format)
    sheet.write(1, 0, "各场景最近观测，不代表同一版本的完整回归。")
    sheet.write(2, 0, "输入 SHA256")
    sheet.write(2, 1, input_sha)
    sheet.write_row(4, 0, [label for label, _ in columns], header)
    sheet.set_row(4, 30)
    for row_number, row in enumerate(rows, start=5):
        for column, value in enumerate(row):
            converted = _value(value)
            if isinstance(converted, datetime):
                sheet.write_datetime(row_number, column, converted, date)
            else:
                sheet.write(row_number, column, converted, body)
        sheet.set_row(row_number, 48 if name != "测试方法" else 180)
    for column, (_, width) in enumerate(columns):
        sheet.set_column(column, column, width)
    if rows:
        sheet.autofilter(4, 0, 4 + len(rows), len(columns) - 1)
    sheet.freeze_panes(5, 1)
    sheet.hide_gridlines(2)


def report_bytes(view: Mapping[str, object], records: Mapping[str, CaseRecord]) -> bytes:
    from xlsxwriter import Workbook

    stream = io.BytesIO()
    with Workbook(
        stream, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}
    ) as workbook:
        workbook.set_properties({"created": datetime(1980, 1, 1)})
        first = next(iter(records.values())).payload
        title = f"{first['chip']} {first['ip']} 当前测试档案"
        sha = str(view["inputs_sha256"])
        rows = [
            [_value(object_value(row, "execution").get(field), field) for field, _, _ in FIELDS]
            for row in list_value(view["executions"], "executions")
        ]
        _sheet(
            workbook, "当前场景", title, sha, [(label, width) for _, label, width in FIELDS], rows
        )
        methods: dict[tuple[str, str], list[object]] = {}
        protected: list[list[object]] = []
        for case, record in sorted(records.items()):
            for snapshot in record.snapshots():
                spec = str(snapshot.session.get("spec_sha256"))
                methods[(case, spec)] = [
                    case,
                    spec,
                    snapshot.selection.get("method"),
                    snapshot.selection.get("pass_criteria"),
                ]
            for item in list_value(record.payload["protected"], "protected"):
                snapshot = Snapshot.parse(item)
                protected.append(
                    [
                        case,
                        snapshot.lane,
                        snapshot.selection.get("parameter_id") or "无参数",
                        snapshot.status,
                        _value(snapshot.session["finished_at"], "finished_at"),
                        snapshot.identity,
                    ]
                )
        _sheet(
            workbook,
            "测试方法",
            "实际使用的方法版本",
            sha,
            [("Case ID", 22), ("规范 SHA256", 66), ("测试方法", 90), ("通过条件", 65)],
            [row for _, row in sorted(methods.items())],
        )
        if protected:
            _sheet(
                workbook,
                "受保护证据",
                "受保护历史快照",
                sha,
                [
                    ("Case ID", 22),
                    ("Lane", 10),
                    ("参数", 28),
                    ("原始结果", 20),
                    ("测试时间 (CST)", 23),
                    ("快照 SHA256", 66),
                ],
                protected,
            )
    return stream.getvalue()
