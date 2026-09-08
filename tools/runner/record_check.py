# 固定Case记录的离线完整性检查。
# 职责：验证目录成员、容量、原始附件及派生JSON和Markdown的一致性。
# 边界：只读，不修复文件，不重新判定测试结果。
# 依赖：标准库及记录存储模块。

from __future__ import annotations

from pathlib import Path

from record_model import MAX_CASE_BYTES, MAX_IP_BYTES, CaseRecord
from record_store import case_markdown, derived_files, load_records, report_enabled
from record_transaction import digest, safe_path


def inventory(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        raise ValueError(f"record directory does not exist: {root}")
    files: dict[str, bytes] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        safe_path(root, name)
        if path.is_dir():
            if name not in {"cases", "evidence"}:
                raise ValueError(f"unexpected record directory: {name}")
            continue
        if not path.is_file():
            raise ValueError(f"unsupported record entry: {name}")
        total += path.stat().st_size
        if total > MAX_IP_BYTES:
            raise ValueError("IP record capacity exceeds 256 MiB")
        files[name] = path.read_bytes()
    return files


def expected_names(records: dict[str, CaseRecord], *, write_report: bool = True) -> set[str]:
    return (
        {"README.md", "results.json"}
        | ({"test_report.xlsx"} if write_report else set())
        | {
            name
            for case in records
            for name in (f"cases/{case}.md", f"evidence/{case}.json", f"evidence/{case}.zip")
        }
    )


# 只返回通过成员、容量和原始字节校验的证据，供显式视图重建复用。
def load_checked_evidence(root: Path) -> tuple[dict[str, bytes], dict[str, CaseRecord]]:
    files = inventory(root)
    records, bundles = load_records(root)
    if not records:
        raise ValueError("record directory contains no Case evidence")
    enabled = report_enabled(root)
    expected = expected_names(records, write_report=enabled)
    if set(files) != expected:
        raise ValueError(
            f"record membership mismatch: missing={sorted(expected - set(files))}, "
            f"unexpected={sorted(set(files) - expected)}"
        )
    for case, blobs in bundles.items():
        size = len(files[f"evidence/{case}.json"]) + sum(len(data) for data in blobs.values())
        if size > MAX_CASE_BYTES:
            raise ValueError(f"Case evidence exceeds 25 MiB: {case}")
    return files, records


def check_records(root: Path) -> dict[str, object]:
    files, records = load_checked_evidence(root)
    derived = {
        **derived_files(root, records, write_report=report_enabled(root)),
        **{f"cases/{case}.md": case_markdown(root, record) for case, record in records.items()},
    }
    for name, data in derived.items():
        if data is None:
            continue
        actual = files[name]
        if name.endswith(".md"):
            actual = actual.replace(b"\r\n", b"\n")
        if data != actual:
            raise ValueError(f"stale or modified generated record: {name}")
    return {
        "schema": "et.record-check.v1",
        "status": "PASS",
        "chip": root.parent.name,
        "ip": root.name,
        "case_count": len(records),
        "file_count": len(files),
        "stored_bytes": sum(len(data) for data in files.values()),
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "snapshots": {
            case: sorted(snapshot.identity for snapshot in record.snapshots())
            for case, record in records.items()
        },
    }
