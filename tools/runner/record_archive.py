# 单文件阶段归档与已归档保护证据的显式释放。
# 职责：校验完整快照、拒绝覆盖归档、生成有界整理事务。
# 边界：不删除旧Run，不自动关闭问题，不改变当前结果或累计次数。
# 依赖：标准库和固定记录检查、存储模块。

from __future__ import annotations

import copy
import io
import os
import tempfile
import zipfile
from pathlib import Path

from record_check import check_records, inventory
from record_model import MAX_IP_BYTES, CaseRecord, Snapshot, list_value, object_value, text_value
from record_store import (
    case_markdown,
    derived_files,
    load_records,
    pack_blobs,
    report_enabled,
    required_blobs,
)
from record_transaction import digest, json_bytes, json_object, safe_name, safe_path

ARCHIVE_SCHEMA = "et.record-archive.v1"
MAX_ARCHIVES = 16
MAX_ARCHIVE_DIRECTORY_BYTES = 1024 * 1024 * 1024


# 归档不信任ZIP路径；先限容、校验成员，再在临时目录执行同一完整性检查。
def verify_archive(data: bytes, work: Path) -> dict[str, object]:
    if len(data) > MAX_IP_BYTES + 1024 * 1024:
        raise ValueError("archive exceeds capacity")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(names) > 10000
            or len(names) != len(set(names))
            or sum(entry.file_size for entry in entries) > MAX_IP_BYTES + 1024 * 1024
        ):
            raise ValueError("duplicate or oversized archive members")
        manifest = json_object(archive.read("archive.json"))
        if manifest.get("schema") != ARCHIVE_SCHEMA:
            raise ValueError("unsupported archive schema")
        expected = object_value(manifest.get("check"), "archive.check")
        hashes = object_value(expected.get("files"), "archive files")
        if set(names) != {"archive.json", *hashes}:
            raise ValueError("archive member list mismatch")
        chip = safe_name(text_value(expected.get("chip"), "chip"))
        ip = safe_name(text_value(expected.get("ip"), "ip"))
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="archive-check-", dir=work) as directory:
            root = Path(directory) / chip / ip
            for name, sha in hashes.items():
                path = safe_path(root, name)
                content = archive.read(name)
                if digest(content) != sha:
                    raise ValueError(f"archive hash mismatch: {name}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            if check_records(root) != expected:
                raise ValueError("archive metadata and actual records disagree")
    return manifest


def create_archive(root: Path, output: Path, work: Path) -> dict[str, object]:
    safe_path(output.parent, output.name)
    if output.suffix.lower() != ".zip" or output.exists():
        raise ValueError("archive must be a new explicitly named .zip file")
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive must be outside the current IP record directory")
    check = check_records(root)
    files = inventory(root)
    if {name: digest(data) for name, data in files.items()} != check["files"]:
        raise ValueError("records changed during archive preparation")
    manifest = {"schema": ARCHIVE_SCHEMA, "label": output.stem, "check": check}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted({**files, "archive.json": json_bytes(manifest)}.items()):
            entry = zipfile.ZipInfo(name)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content)
    data = stream.getvalue()
    verify_archive(data, work)
    siblings = list(output.parent.glob("*.zip"))
    if len(siblings) >= MAX_ARCHIVES or (
        sum(path.stat().st_size for path in siblings) + len(data) > MAX_ARCHIVE_DIRECTORY_BYTES
    ):
        raise ValueError("archive destination budget exceeded; manage existing archives explicitly")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as destination:
        destination.write(data)
        destination.flush()
        os.fsync(destination.fileno())
    verified = verify_archive(output.read_bytes(), work)
    return {"archive": str(output), "sha256": digest(data), "manifest": verified}


def prepare_prune(
    root: Path, archive_data: bytes, work: Path, cases: list[str]
) -> tuple[dict[str, object], dict[str, bytes | None]]:
    check_records(root)
    manifest = verify_archive(archive_data, work)
    check = object_value(manifest["check"], "archive.check")
    if check["chip"] != root.parent.name or check["ip"] != root.name:
        raise ValueError("archive belongs to a different chip/IP")
    archived = object_value(check["snapshots"], "archived snapshots")
    records, bundles = load_records(root)
    requested = {safe_name(case).upper() for case in cases}
    if not requested or requested - set(records):
        raise ValueError("prune requires explicit existing Case identifiers")
    released: dict[str, list[str]] = {}
    files: dict[str, bytes | None] = {}
    for case in sorted(requested):
        payload = copy.deepcopy(records[case].payload)
        held = list_value(payload["protected"], "protected")
        covered = set(list_value(archived.get(case, []), "archived snapshots"))
        selected = [Snapshot.parse(item).identity for item in held]
        if set(selected) - covered:
            raise ValueError(f"archive does not cover every protected snapshot: {case}")
        if not selected:
            continue
        payload["protected"] = []
        record = CaseRecord.parse(payload)
        records[case] = record
        blobs = {sha: bundles[case][sha] for sha in required_blobs(record)}
        files[f"evidence/{case}.json"] = json_bytes(record.payload)
        files[f"evidence/{case}.zip"] = pack_blobs(blobs)
        files[f"cases/{case}.md"] = case_markdown(root, record)
        released[case] = selected
    if files:
        files.update(derived_files(root, records, write_report=report_enabled(root)))
    return {
        "operation": "release_archived_protected_snapshots",
        "archive_sha256": digest(archive_data),
        "released": released,
        "changed_files": sorted(files),
    }, files
