# 固定芯片/IP目录的Case证据存储。
# 职责：读写有界JSON与固定附件包，检查Hash，生成当前台账和Case文档。
# 边界：不扫描历史Run猜测结论，不自动解除证据保护。
# 依赖：标准库、记录模型和文件事务。

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable, Mapping
from datetime import timedelta, timezone
from pathlib import Path

from record_model import MAX_CASE_BYTES, MAX_IP_BYTES, CaseRecord, Snapshot, object_value, timestamp
from record_report import report_bytes
from record_source import RecordInput
from record_transaction import digest, json_bytes, json_object, publish, safe_name, safe_path

BEGIN = "<!-- ET_RECORD_AUTO_BEGIN -->"
END = "<!-- ET_RECORD_AUTO_END -->"
VIEW_SCHEMA = "et.ip-record-view.v1"


def record_root(repository: Path, chip: str, ip: str) -> Path:
    return safe_path(
        repository, f"artifacts/records/{safe_name(chip).upper()}/{safe_name(ip).upper()}"
    )


def working_root(repository: Path, chip: str, ip: str) -> Path:
    return safe_path(
        repository,
        f"artifacts/runs/record-maintenance/{safe_name(chip).upper()}_{safe_name(ip).upper()}",
    )


def pack_blobs(blobs: Mapping[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for sha, data in sorted(blobs.items()):
            if digest(data) != sha:
                raise ValueError("attachment content hash mismatch")
            info = zipfile.ZipInfo(sha)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return stream.getvalue()


def unpack_blobs(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if (
            len(names) != len(set(names))
            or sum(item.file_size for item in archive.infolist()) > MAX_CASE_BYTES
        ):
            raise ValueError("duplicate or oversized evidence package")
        result = {name: archive.read(name) for name in names}
    if any(len(name) != 64 or digest(value) != name for name, value in result.items()):
        raise ValueError("evidence package contains damaged or unknown members")
    return result


def required_blobs(record: CaseRecord) -> set[str]:
    return {sha for snapshot in record.snapshots() for sha in snapshot.files.values()}


def load_records(root: Path) -> tuple[dict[str, CaseRecord], dict[str, dict[str, bytes]]]:
    records: dict[str, CaseRecord] = {}
    blobs: dict[str, dict[str, bytes]] = {}
    safe_path(root, "evidence")
    if not root.exists():
        return records, blobs
    for path in sorted((root / "evidence").glob("*.json")):
        safe_path(root, "evidence/" + path.name)
        if path.stat().st_size > MAX_CASE_BYTES:
            raise ValueError(f"Case record capacity exceeded: {path}")
        record = CaseRecord.parse(json_object(path.read_bytes()))
        case = str(record.payload["case_id"])
        if (
            path.stem != case
            or record.payload["chip"] != root.parent.name
            or record.payload["ip"] != root.name
        ):
            raise ValueError(f"Case identity does not match the record directory: {path}")
        package = safe_path(root, f"evidence/{case}.zip")
        data = unpack_blobs(package.read_bytes())
        if set(data) != required_blobs(record):
            raise ValueError(f"missing or unreferenced attachment in {package}")
        for snapshot in record.snapshots():
            session = data.get(snapshot.files.get("source/session.json", ""))
            result = data.get(snapshot.files.get("source/result.json", ""))
            if session is None or json_object(session) != snapshot.session:
                raise ValueError(f"Session bytes and record disagree: {case}")
            if snapshot.files.get("source/specification.md") != snapshot.session.get("spec_sha256"):
                raise ValueError(f"specification attachment and Session hash disagree: {case}")
            if snapshot.result is not None and (
                result is None or json_object(result) != snapshot.result
            ):
                raise ValueError(f"Canonical Result bytes and record disagree: {case}")
        records[case], blobs[case] = record, data
    return records, blobs


def build_view(
    records: Mapping[str, CaseRecord], *, write_report: bool = True
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for case, record in sorted(records.items()):
        held = record.payload["protected"]
        for entry_value in object_value(record.payload["executions"], "executions").values():
            entry = object_value(entry_value, "execution")
            snapshot = Snapshot.parse(entry["latest"])
            rows.append(
                {
                    "case_id": case,
                    "lane": snapshot.lane,
                    "parameter_id": snapshot.selection.get("parameter_id"),
                    "status": snapshot.status,
                    "finished_at": snapshot.session["finished_at"],
                    "source_revision": snapshot.session.get("source_revision"),
                    "source_dirty": snapshot.session.get("source_dirty"),
                    "firmware_build_id": snapshot.session.get("firmware_build_id"),
                    "bitstream_id": snapshot.session.get("bitstream_id"),
                    "target_id": snapshot.session.get("target_id"),
                    "spec_sha256": snapshot.session.get("spec_sha256"),
                    "run_id": snapshot.session["run_id"],
                    "attempts": entry["attempts"],
                    "status_counts": entry["status_counts"],
                    "protected_count": len(held),
                    "evidence": f"evidence/{case}.json",
                    "case_document": f"cases/{case}.md",
                }
            )
    rows.sort(
        key=lambda row: (
            str(row["case_id"]),
            str(row["lane"]),
            str(row["target_id"]),
            str(row["parameter_id"]),
        )
    )
    return {
        "schema": VIEW_SCHEMA,
        "view": "latest_observations_not_a_single_run",
        "report_enabled": write_report,
        "inputs_sha256": digest(
            json_bytes({case: record.payload for case, record in sorted(records.items())})
        ),
        "executions": rows,
    }


def _cell(value: object) -> str:
    return (
        str(value if value is not None else "未知")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


# 只替换明确的机器区域；Agent分析区逐字保留并限制大小，损坏标记时失败关闭。
def replace_generated(existing: str | None, generated: str, *, title: str) -> bytes:
    if existing is None:
        existing = f"# {title}\n\n{BEGIN}\n{END}\n\n## 方法补充与问题分析\n\n尚未补充人工分析；结果以证据为准。\n\n## 关键变化\n\n仅保留最近3条关键变化；较早关键结论归档后再整理。\n"
    if existing.count(BEGIN) != 1 or existing.count(END) != 1:
        raise ValueError("record Markdown has missing or duplicate generated markers")
    prefix, remainder = existing.split(BEGIN)
    _, suffix = remainder.split(END)
    if len((prefix + suffix).encode("utf-8")) > 16 * 1024:
        raise ValueError("manual analysis exceeds 16 KiB; consolidate or archive it first")
    return (prefix + BEGIN + "\n\n" + generated.strip() + "\n\n" + END + suffix).encode("utf-8")


def case_markdown(root: Path, record: CaseRecord) -> bytes:
    case = str(record.payload["case_id"])
    path = safe_path(root, f"cases/{case}.md")
    lines = [
        "## 当前测试",
        "",
        "下表是各场景最近观测，不代表同一版本的完整回归；未复测场景保留原日期。",
        "",
        "| Lane / Target | 参数 | 原始结果 | 测试时间 | Source / Dirty |",
        "|---|---|---|---|---|",
    ]
    methods: dict[str, Snapshot] = {}
    for _, entry in sorted(object_value(record.payload["executions"], "executions").items()):
        snapshot = Snapshot.parse(object_value(entry, "execution")["latest"])
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    f"{snapshot.lane} / {snapshot.session.get('target_id')}",
                    snapshot.selection.get("parameter_id") or "无参数",
                    snapshot.status,
                    timestamp(snapshot.session["finished_at"])
                    .astimezone(timezone(timedelta(hours=8)))
                    .strftime("%Y-%m-%d %H:%M CST"),
                    f"{snapshot.session.get('source_revision')} / {snapshot.session.get('source_dirty')}",
                )
            )
            + " |"
        )
        methods[str(snapshot.session.get("spec_sha256"))] = snapshot
    lines.extend(
        [
            "",
            f"[完整结果与版本](../evidence/{case}.json) · [原始证据包](../evidence/{case}.zip)",
            "",
            f"受保护历史快照：{len(record.payload['protected'])}。原始结果的失败、缺失或SKIP不会被历史PASS遮盖。",
            "",
            "## 测试方法版本",
        ]
    )
    for sha, snapshot in sorted(methods.items()):
        lines.extend(
            [
                "",
                f"规范SHA256：`{sha}`；原始规范已保存在证据包中。",
                "",
                str(snapshot.selection.get("method") or "方法见原始规范。"),
                "",
                "通过条件：",
                "",
                str(snapshot.selection.get("pass_criteria") or "见原始规范。"),
            ]
        )
    return replace_generated(
        path.read_text(encoding="utf-8") if path.exists() else None, "\n".join(lines), title=case
    )


def summary_markdown(
    root: Path, records: Mapping[str, CaseRecord], *, write_report: bool = True
) -> bytes:
    lines = [
        "## Case索引",
        "",
        "当前台账按Lane和参数增量维护；Excel与results.json均由原始记录生成。",
        "",
        "| Case | 当前场景数 | 受保护快照 |",
        "|---|---:|---:|",
    ]
    for case, record in sorted(records.items()):
        lines.append(
            f"| [{case}](cases/{case}.md) | {len(record.payload['executions'])} | {len(record.payload['protected'])} |"
        )
    lines.extend(
        [
            "",
            "[结构化台账](results.json)"
            + (
                " · [当前测试报告](test_report.xlsx)" if write_report else "；本次未启用Excel导出。"
            ),
            "",
            "时间、Source、固件和FPGA身份均保存在具体记录中；身份未知不等于已验证。",
        ]
    )
    path = safe_path(root, "README.md")
    return replace_generated(
        path.read_text(encoding="utf-8") if path.exists() else None,
        "\n".join(lines),
        title=f"{root.parent.name} {root.name} 测试记录",
    )


# 全部输入先在内存完成校验；容量或保护限额超出时，正式目录完全不变。
def derived_files(
    root: Path, records: Mapping[str, CaseRecord], *, write_report: bool
) -> dict[str, bytes | None]:
    view = build_view(records, write_report=write_report)
    return {
        "results.json": json_bytes(view),
        "test_report.xlsx": report_bytes(view, records) if write_report else None,
        "README.md": summary_markdown(root, records, write_report=write_report),
    }


def report_enabled(root: Path) -> bool:
    path = safe_path(root, "results.json")
    enabled = json_object(path.read_bytes()).get("report_enabled") if path.exists() else True
    if not isinstance(enabled, bool):
        raise ValueError("record view report_enabled must be boolean")
    return enabled


def prepare_update(
    root: Path,
    incoming: RecordInput,
    *,
    protect_cases: tuple[str, ...] = (),
    write_report: bool = True,
) -> tuple[dict[str, CaseRecord], dict[str, bytes | None]]:
    records, bundles = load_records(root)
    protected = {safe_name(case).upper() for case in protect_cases}
    if protected - set(incoming.cases):
        raise ValueError("explicit protection requires a Case selected in this input")
    files: dict[str, bytes | None] = {}
    for case, snapshots in incoming.cases.items():
        old = records.get(case, CaseRecord.empty(incoming.chip, incoming.ip, case))
        record = old.merge(snapshots)
        if case in protected:
            record = record.protect(snapshots)
        if case in records and record.payload == old.payload:
            continue
        available = {**bundles.get(case, {}), **incoming.blobs}
        blobs = {sha: available[sha] for sha in required_blobs(record)}
        encoded = json_bytes(record.payload)
        if len(encoded) + sum(len(data) for data in blobs.values()) > MAX_CASE_BYTES:
            raise ValueError(f"Case evidence exceeds 25 MiB: {case}; archive before updating")
        records[case], bundles[case] = record, blobs
        files[f"evidence/{case}.json"] = encoded
        files[f"evidence/{case}.zip"] = pack_blobs(blobs)
        files[f"cases/{case}.md"] = case_markdown(root, record)
    if files or report_enabled(root) != write_report:
        files.update(derived_files(root, records, write_report=write_report))
    projected = sum(len(data) for data in files.values() if data is not None)
    if root.exists():
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            if path.is_file() and relative not in files:
                projected += path.stat().st_size
    if projected > MAX_IP_BYTES:
        raise ValueError("IP record capacity exceeds 256 MiB; archive before updating")
    return records, files


def publish_update(
    root: Path,
    work: Path,
    files: Mapping[str, bytes | None],
    *,
    validate: Callable[[], object] | None = None,
) -> int:
    return publish(root, work, files, validate=validate)
