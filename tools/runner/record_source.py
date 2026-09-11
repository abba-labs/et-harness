# 读取已完成的Canonical Session，形成可移植的Case证据输入。
# 职责：核对Selection/Result、原始附件和测试方法Hash。
# 边界：不运行Case，不改写原始结果，不猜测缺失身份。
# 依赖：标准库、现有报告模型和记录数据模型。

from __future__ import annotations

import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from et_test_platform.results.case_report import build_case_report_model, iter_canonical_results
from et_test_platform.scheduling.run_context import (
    case_dir_name,
    execution_slot,
    stable_case_run_id,
)
from record_model import MAX_IP_BYTES, Snapshot, list_value, object_value, text_value, timestamp
from record_transaction import digest, json_object, safe_name, safe_path


@dataclass(frozen=True, slots=True)
class RecordInput:
    chip: str
    ip: str
    cases: dict[str, list[Snapshot]]
    blobs: dict[str, bytes]
    report_model: dict[str, object] = field(default_factory=dict)


def _bounded_read(path: Path) -> bytes:
    if path.stat().st_size > MAX_IP_BYTES:
        raise ValueError(f"input exceeds evidence capacity: {path}")
    return path.read_bytes()


def _attachment_paths(result: dict[str, object]) -> set[str]:
    paths: set[str] = set()
    for value in object_value(result.get("artifacts", {}), "artifacts").values():
        values = [value] if isinstance(value, str) else list_value(value, "artifact paths")
        paths.update(text_value(item, "artifact path") for item in values)
    for value in list_value(result.get("observations", []), "observations"):
        observation = object_value(value, "observation")
        paths.update(
            text_value(item, "observation artifact")
            for item in list_value(observation.get("artifacts", []), "observation.artifacts")
        )
    return paths


# Git归一化可能丢失Windows混合换行；只接受能重建Session精确Hash的字节候选。
def _historical_specification(data: bytes, current: bytes, expected: str) -> bytes:
    lf = data.replace(b"\r\n", b"\n")
    candidates = [data, lf.replace(b"\n", b"\r\n")]
    lines, template = lf.splitlines(keepends=True), current.splitlines(keepends=True)
    if len(lines) == len(template):
        endings = [
            b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
            for line in template
        ]
        candidates.append(
            b"".join(
                line.rstrip(b"\r\n") + ending for line, ending in zip(lines, endings, strict=True)
            )
        )
    for candidate in candidates:
        if digest(candidate) == expected:
            return candidate
    raise ValueError("historical specification hash is unavailable; keep the source Run")


# 当前文档Hash不匹配时只查本地精确提交；查不到就停止，不能拿新方法解释旧结果。
def _specification(
    repository: Path, document: Path, session: dict[str, object], *, snapshot: Path | None = None
) -> bytes:
    expected = text_value(session.get("spec_sha256"), "spec_sha256")
    if snapshot is not None and snapshot.is_file():
        saved = _bounded_read(snapshot)
        if digest(saved) != expected:
            raise ValueError("current specification snapshot hash mismatch")
        return saved
    current = _bounded_read(document)
    if digest(current) == expected:
        return current
    revision = text_value(session.get("source_revision"), "source_revision")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("cannot recover the exact historical specification without a Git SHA")
    relative = document.resolve().relative_to(repository.resolve()).as_posix()
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=repository, capture_output=True, check=False
    )
    if completed.returncode:
        raise ValueError(
            "historical specification Git revision is unavailable; keep the source Run"
        )
    return _historical_specification(completed.stdout, current, expected)


def _validate_selection(
    selection: dict[str, object], chosen: dict[tuple[str, object], dict[str, object]]
) -> None:
    counts = [
        selection.get(name) for name in ("collected_count", "selected_count", "deselected_count")
    ]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("Selection counts must be non-negative integers")
    if counts[1] != len(chosen) or counts[0] != counts[1] + counts[2]:
        raise ValueError("Selection counts disagree with selected executions")
    case_ids = list_value(selection.get("selected_case_ids"), "selected_case_ids")
    if {text_value(case, "selected Case").lower() for case in case_ids} != {
        key[0] for key in chosen
    }:
        raise ValueError("Selection Case identities disagree with selected executions")


# 把Session选择的execution展开为(case_id, parameter_id)到条目的映射；拒绝重复项。
def _chosen_executions(selection: dict[str, object]) -> dict[tuple[str, object], dict[str, object]]:
    chosen: dict[tuple[str, object], dict[str, object]] = {}
    for item in list_value(selection.get("selected_executions"), "selected_executions"):
        entry = object_value(item, "selected execution")
        if entry.get("parameter_id") is not None and not isinstance(entry["parameter_id"], str):
            raise ValueError("parameter_id must be text or null")
        key = (text_value(entry.get("case_id"), "case_id").lower(), entry.get("parameter_id"))
        if key in chosen:
            raise ValueError("duplicate selected execution")
        chosen[key] = entry
    if not chosen:
        raise ValueError("no selected Case executions to update")
    return chosen


# 校验单个Canonical Result的身份与其所在目录形状一致；legacy与nested分别校验，不重判业务结果。
def _validate_result_identity(
    path: Path, result: dict[str, object], layout: str, source: Path
) -> None:
    if result.get("schema_version") != 1:
        raise ValueError(f"invalid canonical result identity: {path}")
    if layout == "legacy":
        if result.get("case_run_id") != path.parent.name:
            raise ValueError(f"invalid canonical result identity: {path}")
        return
    parameter_id = result.get("parameter_id")
    if parameter_id is not None and not isinstance(parameter_id, str):
        raise ValueError("parameter_id must be text or null")
    slot_parameter = parameter_id if isinstance(parameter_id, str) else None
    try:
        expected_case = case_dir_name(text_value(result.get("case_id"), "case_id"))
        expected_slot = execution_slot(slot_parameter)
        expected_run = stable_case_run_id(
            text_value(result.get("case_id"), "case_id"), slot_parameter
        )
    except ValueError as exc:
        raise ValueError(f"invalid canonical result identity: {path}") from exc
    if path.parent.name != expected_slot or path.parent.parent.name != expected_case:
        raise ValueError(f"invalid canonical result identity: {path}")
    if result.get("case_run_id") != expected_run:
        raise ValueError(f"invalid canonical result identity: {path}")


# 读取source下全部Canonical Result，校验它们属于本次Selection并绑定当前IP与芯片。
def _collect_selected_results(
    source: Path,
    session: dict[str, object],
    ip: str,
    chosen: dict[tuple[str, object], dict[str, object]],
) -> tuple[dict[tuple[str, object], dict[str, object]], dict[tuple[str, object], bytes]]:
    results: dict[tuple[str, object], dict[str, object]] = {}
    raw: dict[tuple[str, object], bytes] = {}
    layout, paths = iter_canonical_results(source / "cases")
    for path in paths:
        safe_path(source, path.relative_to(source).as_posix())
        data = _bounded_read(path)
        result = json_object(data)
        if result.get("parameter_id") is not None and not isinstance(result["parameter_id"], str):
            raise ValueError("parameter_id must be text or null")
        key = (text_value(result.get("case_id"), "case_id").lower(), result.get("parameter_id"))
        _validate_result_identity(path, result, layout, source)
        if key not in chosen or key in results or result.get("ip_id") != ip:
            raise ValueError(f"unselected, duplicate or wrong-IP result: {path}")
        if result.get("chip_id") not in {None, session.get("chip_id")}:
            raise ValueError("result chip identity conflicts with Session")
        result["_result_path"] = path.relative_to(source).as_posix()
        results[key], raw[key] = result, data
    return results, raw


def _selected_results(
    source: Path, session: dict[str, object], ip: str
) -> tuple[
    dict[tuple[str, object], dict[str, object]],
    dict[tuple[str, object], dict[str, object]],
    dict[tuple[str, object], bytes],
]:
    selection = object_value(session.get("selection"), "selection")
    chosen = _chosen_executions(selection)
    _validate_selection(selection, chosen)
    results, raw = _collect_selected_results(source, session, ip, chosen)
    counts = dict(Counter(str(result.get("status")) for result in results.values()))
    declared = object_value(session.get("status_counts"), "Session status_counts")
    if counts != declared or any(type(value) is not int for value in declared.values()):
        raise ValueError("Session status_counts disagree with actual results")
    if session.get("exitstatus") == 0 and (
        set(results) != set(chosen)
        or any(status in counts for status in ("FAIL", "EVIDENCE_MISSING"))
    ):
        raise ValueError("successful Session has missing or failing results")
    return chosen, results, raw


def _manifest_files(
    manifest: Path | None, session: dict[str, object], lane: str
) -> dict[str, bytes]:
    shared: dict[str, bytes] = {}
    if manifest is not None:
        safe_path(manifest.parent, manifest.name)
        manifest_bytes = _bounded_read(manifest)
        metadata = json_object(manifest_bytes)
        expected_lane = {"fpga": "fpga", "silicon": "hil", "renode": "sil"}.get(
            str(metadata.get("target_kind"))
        )
        if expected_lane is not None and lane != expected_lane:
            raise ValueError("Lane conflicts with the original Run manifest")
        if metadata.get("source_revision") != session.get("source_revision"):
            raise ValueError("manifest and Session source revisions disagree")
        shared["source/manifest.json"] = manifest_bytes
        config = metadata.get("configuration_snapshot")
        if isinstance(config, str):
            config_bytes = _bounded_read(safe_path(manifest.parent, config))
            if digest(config_bytes) != metadata.get("configuration_sha256"):
                raise ValueError("configuration snapshot hash mismatch")
            shared["source/configuration.yaml"] = config_bytes
    return shared


# 输入可以不完整，但Session必须已终止；未执行参数没有伪造的Canonical Result。
def load_input(
    repository: Path, source: Path, *, ip: str, lane: str, work: Path, manifest: Path | None = None
) -> RecordInput:
    ip = safe_name(ip).lower()
    source = source.absolute()
    session_bytes = _bounded_read(safe_path(source, "session.json"))
    session = json_object(session_bytes)
    if session.get("schema_version") != 1:
        raise ValueError("unsupported canonical Session schema")
    timestamp(session.get("finished_at"))
    chip = safe_name(text_value(session.get("chip_id"), "chip_id")).upper()
    chosen, results, raw = _selected_results(source, session, ip)
    document = repository / "test_case_doc" / ip / f"{ip}.md"
    spec_bytes = _specification(
        repository, document, session, snapshot=safe_path(source, "specification.md")
    )
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="method-", dir=work) as directory:
        method_path = Path(directory) / f"{ip}.md"
        method_path.write_bytes(spec_bytes)
        model = build_case_report_model(method_path, source, chip_name=chip)
    methods = {str(row["case_id"]).lower(): row for row in model["cases"]}
    shared = {"source/session.json": session_bytes, "source/specification.md": spec_bytes}
    shared.update(_manifest_files(manifest, session, lane))
    log = safe_path(source, "pytest.log")
    if log.is_file():
        shared["source/pytest.log"] = _bounded_read(log)
    blobs = {digest(data): data for data in shared.values()}
    cases: dict[str, list[Snapshot]] = {}
    origin = source.resolve().relative_to(repository.resolve()).as_posix()
    for key, entry in chosen.items():
        if key[0] not in methods:
            raise ValueError("selected Case does not exist in the original method contract")
        files = {name: digest(data) for name, data in shared.items()}
        result = results.get(key)
        if result is not None:
            files["source/result.json"] = digest(raw[key])
            blobs[digest(raw[key])] = raw[key]
            for relative in _attachment_paths(result):
                data = _bounded_read(safe_path(source, relative))
                files["artifacts/" + relative] = digest(data)
                blobs[digest(data)] = data
        method = methods[key[0]]
        selected = dict(entry)
        selected["method"] = method.get("method")
        selected["pass_criteria"] = method.get("pass_criteria")
        selected["case_name"] = method.get("case_name")
        snapshot = Snapshot(lane, session, result, selected, files, origin)
        cases.setdefault(snapshot.case_id.upper(), []).append(snapshot)
    if sum(len(data) for data in blobs.values()) > MAX_IP_BYTES:
        raise ValueError("incoming evidence exceeds IP capacity; source Run was retained")
    return RecordInput(chip, ip.upper(), cases, blobs, model)
