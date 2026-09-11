# 测试运行上下文、Evidence 与产物路径管理。
#
# 职责：维护一次 pytest Session/Case 的元数据、证据来源和结果附件路径。
# 边界：不决定 IP 测试逻辑、不发送设备命令，也不形成第二套 PASS/FAIL 判定。
# 依赖：仅依赖配置、文件系统和稳定 Evidence/Result 数据模型。

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from ..results.recorder import normalize_json_value, write_json_result
from .test_registry import RegistryError, case_id_from_item, ip_id_from_item

SCHEMA_VERSION = 1
EVIDENCE_PROPERTY = "evidence_sources"
REQUIRED_EVIDENCE_PROPERTY = "required_evidence_sources"
OBSERVATION_PROPERTY = "et_observation"
ALLOWED_EVIDENCE_SOURCES = frozenset({"dut", "peer", "fpga", "instrument", "observer"})
DEFAULT_SLOT = "noparam"
RESERVED_SLOTS = frozenset({DEFAULT_SLOT, "artifacts"})
_WINDOWS_DEVICE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(10)),
        *(f"LPT{i}" for i in range(10)),
    }
)


# 描述一次execution的目录身份：Formal用稳定Case/slot，非Formal仍用UUID隔离。
@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    layout: Literal["nested", "uuid"]
    case_id: str | None
    ip_id: str | None
    parameter_id: str | None
    slot: str | None
    case_run_id: str
    execution_dir: Path


def _safe_component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError(f"unsafe execution path component: {value!r}")
    if value.endswith(".") or value.split(".")[0].upper() in _WINDOWS_DEVICE_NAMES:
        raise ValueError(f"reserved execution path component: {value!r}")
    return value


# 返回Case在cases/下的稳定目录名；只做安全字符规范化和大写，不做身份判断。
def case_dir_name(case_id: str) -> str:
    return _safe_component(case_id).upper()


# 返回参数execution的目录slot；无参数时使用固定noparam，拒绝与保留名冲突。
def execution_slot(parameter_id: str | None) -> str:
    if parameter_id is None:
        return DEFAULT_SLOT
    name = _safe_component(parameter_id)
    if name.casefold() in {item.casefold() for item in RESERVED_SLOTS}:
        raise ValueError(f"parameter_id {parameter_id!r} collides with a reserved slot")
    return name


# 返回大小写不敏感的执行唯一键；只用于同Session内重复目录检测，不写盘。
def filesystem_execution_key(case_id: str, parameter_id: str | None) -> tuple[str, str]:
    return case_dir_name(case_id).casefold(), execution_slot(parameter_id).casefold()


# 返回Formal execution的稳定case_run_id；由Case与slot派生，不随Session变化。
def stable_case_run_id(case_id: str, parameter_id: str | None) -> str:
    return f"{case_dir_name(case_id)}--{execution_slot(parameter_id)}"


# 返回Formal execution的固定结果目录；只计算结果路径，不创建目录或写入文件。
def execution_dir(artifact_dir: Path, case_id: str, parameter_id: str | None) -> Path:
    return Path(artifact_dir) / "cases" / case_dir_name(case_id) / execution_slot(parameter_id)


# 构造非Formal执行的UUID隔离身份；只校验路径分量安全，不解释Case语义。
def uuid_identity(artifact_dir: Path, case_run_id: str) -> ExecutionIdentity:
    if Path(case_run_id).name != case_run_id or case_run_id in {"", ".", ".."}:
        raise ValueError("case_run_id must be a single safe path component")
    return ExecutionIdentity(
        layout="uuid",
        case_id=None,
        ip_id=None,
        parameter_id=None,
        slot=None,
        case_run_id=case_run_id,
        execution_dir=Path(artifact_dir) / "cases" / case_run_id,
    )


# 读取已安装平台版本；源码未安装为 Package 时返回 ``unpackaged``。
def platform_version() -> str:

    try:
        return metadata.version("et-automated-testing-platform")
    except metadata.PackageNotFoundError:
        return "unpackaged"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return None
    return digest.hexdigest()


def _safe_attr(value: object | None, name: str) -> Any:
    try:
        return getattr(value, name)
    except (AttributeError, RuntimeError):
        return None


# 将 pytest Property 收敛为可稳定写入 JSON 的值，不解释任何 IP 业务语义。
def _json_result_value(value: object) -> Any:

    return normalize_json_value(value, field="pytest_property")


# 读取平台注册表定义的稳定 Case/IP 身份；非正式测试保留 pytest nodeid 作为诊断身份。
def _case_identity(item: object) -> tuple[str, str | None]:

    try:
        case_id = case_id_from_item(item)
        ip_id = ip_id_from_item(item)
    except (AttributeError, RegistryError):
        return (
            str(_safe_attr(item, "nodeid") or _safe_attr(item, "name") or "unknown"),
            None,
        )
    return case_id, ip_id


# 汇总 Case 已通过 record_property 显式登记的测量值和附件路径。
def _case_recorded_outputs(item: object) -> tuple[dict[str, Any], dict[str, Any]]:

    measurements: dict[str, Any] = {}
    artifacts: dict[str, Any] = {}
    properties = getattr(item, "user_properties", ())
    ignored = {EVIDENCE_PROPERTY, REQUIRED_EVIDENCE_PROPERTY, OBSERVATION_PROPERTY}
    for name, value in properties:
        if name in ignored:
            continue
        destination = artifacts if name.endswith("_result") else measurements
        normalized = _json_result_value(value)
        if name not in destination:
            destination[name] = normalized
        elif isinstance(destination[name], list):
            destination[name].append(normalized)
        else:
            destination[name] = [destination[name], normalized]
    return measurements, artifacts


# 提取 Case 通过公共接口登记的真实观测；只做 JSON 归一化，不解释 IP 或设备语义。
def _case_observations(item: object) -> list[dict[str, Any]]:

    observations: list[dict[str, Any]] = []
    for name, value in getattr(item, "user_properties", ()):
        if name != OBSERVATION_PROPERTY or not isinstance(value, dict):
            continue
        normalized = _json_result_value(value)
        if isinstance(normalized, dict):
            observations.append(normalized)
    return observations


# 参数化 Case 仅记录 pytest 的稳定参数 ID，避免把 Driver/Fixture 对象序列化进结果。
def _case_parameters(item: object) -> dict[str, Any]:

    callspec = _safe_attr(item, "callspec")
    parameter_id = _safe_attr(callspec, "id")
    if not isinstance(parameter_id, str) or not parameter_id:
        return {}
    return {"parameter_id": parameter_id}


# 管理一次 pytest Session 的 Run ID、状态计数、元数据和统一结果目录。
@dataclass
class RunContext:
    artifact_dir: Path
    run_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: str = field(default_factory=_timestamp)
    _status_counts: dict[str, int] = field(default_factory=dict, init=False)
    _finished_at: str | None = field(default=None, init=False)
    _session_metadata: dict[str, Any] = field(default_factory=dict, init=False)
    _execution_keys: set[tuple[str, str]] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self.artifact_dir = Path(self.artifact_dir).resolve()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    # 仅在配置了 ``--et-artifact-dir`` 时创建运行上下文，否则保持插件无副作用。
    @classmethod
    def from_config(cls, config: object) -> RunContext | None:

        option = getattr(config, "option", None)
        configured = getattr(option, "et_artifact_dir", None)
        if not configured:
            return None
        context = cls(Path(configured))
        context._session_metadata.update(
            {
                "source_revision": getattr(option, "et_source_revision", None),
                "source_dirty": bool(getattr(option, "et_source_dirty", False)),
                "spec_sha256": getattr(option, "et_spec_sha256", None),
            }
        )
        return context

    # 返回当前运行唯一的 ``session.json`` 绝对路径，不创建额外结果文件。
    @property
    def session_path(self) -> Path:

        return self.artifact_dir / "session.json"

    # 为一次收集到的 execution 分配目录身份；Formal 用稳定 Case/slot，其余仍 UUID 隔离。
    def allocate_execution(self, item: object) -> ExecutionIdentity:

        case_id, ip_id = _case_identity(item)
        parameter_id = _case_parameters(item).get("parameter_id")
        if isinstance(parameter_id, str) and not parameter_id:
            parameter_id = None
        if ip_id is not None:
            key = filesystem_execution_key(case_id, parameter_id)
            if key in self._execution_keys:
                raise ValueError(
                    "duplicate Formal execution directory for "
                    f"case_id={case_id!r} parameter_id={parameter_id!r}"
                )
            self._execution_keys.add(key)
            return ExecutionIdentity(
                layout="nested",
                case_id=case_id,
                ip_id=ip_id,
                parameter_id=parameter_id,
                slot=execution_slot(parameter_id),
                case_run_id=stable_case_run_id(case_id, parameter_id),
                execution_dir=execution_dir(self.artifact_dir, case_id, parameter_id),
            )
        return uuid_identity(self.artifact_dir, str(uuid4()))

    # 把当前 execution 产生的附件固化到专属目录，并返回 Run-relative 路径。
    # 源附件必须位于本次 Run 内；复制出本 execution artifacts 后删除源，避免 Session 根残留阻断 seal。
    # 源已在本 execution artifacts 下则不删除。参数化复用同名源文件时，下一发重新创建源。
    def bind_case_artifact(self, identity: ExecutionIdentity, artifact_path: str | Path) -> str:

        source = Path(artifact_path)
        if not source.is_absolute():
            source = self.artifact_dir / source
        source = source.resolve()
        try:
            source_relative = source.relative_to(self.artifact_dir)
        except ValueError as exc:
            if not source.is_file():
                raise ValueError(f"case artifact does not exist: {source}") from exc
            raise ValueError("case artifact must be located inside the current run") from exc

        destination_root = identity.execution_dir / "artifacts"
        try:
            source.relative_to(destination_root)
        except ValueError:
            destination = destination_root / source_relative
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(f"{destination.name}.tmp")
                shutil.copyfile(source, temporary)
                temporary.replace(destination)
                source.unlink()
            elif not destination.is_file():
                raise ValueError(f"case artifact does not exist: {source}") from None
        else:
            if not source.is_file():
                raise ValueError(f"case artifact does not exist: {source}")
            destination = source

        return destination.relative_to(self.artifact_dir).as_posix()

    # 写入 Session 汇总；给出 exitstatus 时同时记录结束时间和最终进程状态。
    def write_session(self, *, exitstatus: int | None = None) -> Path:

        if exitstatus is not None:
            self._finished_at = _timestamp()
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "platform_version": platform_version(),
            "started_at": self.started_at,
            "finished_at": self._finished_at,
            "status_counts": dict(self._status_counts),
            "chip_id": None,
            "firmware_build_id": None,
            "registry_hash": None,
            "target_id": None,
            "bench_path": None,
            "bench_sha256": None,
            "config_hash": None,
            "transport_identity": None,
            "bitstream_id": None,
            "device_identity": None,
            "source_revision": None,
            "source_dirty": None,
            "spec_sha256": None,
        }
        payload.update(self._session_metadata)
        payload["chip"] = payload["chip_id"]
        payload["firmware"] = payload["firmware_build_id"]
        payload["target"] = payload["target_id"]
        payload["bench"] = payload["bench_path"]
        if exitstatus is not None:
            payload["exitstatus"] = exitstatus
        return write_json_result(self.session_path, payload)

    # 累加一个统一 Case Status，用于 Session 汇总，不重新解释 PASS/FAIL。
    def record_status(self, status: str) -> None:

        self._status_counts[status] = self._status_counts.get(status, 0) + 1

    # 记录注册表过滤后的实际执行集合，供报告区分“未选择”和“选择后未完成”。
    def record_selection(
        self,
        items: list[object],
        *,
        collected_count: int,
        deselected_count: int,
    ) -> None:

        executions: list[dict[str, str | None]] = []
        for item in items:
            case_id, ip_id = _case_identity(item)
            if ip_id is None:
                continue
            executions.append(
                {
                    "case_id": case_id,
                    "parameter_id": _case_parameters(item).get("parameter_id"),
                    "node_id": str(_safe_attr(item, "nodeid") or ""),
                }
            )
        self._session_metadata["selection"] = {
            "collected_count": collected_count,
            "selected_count": len(executions),
            "deselected_count": deselected_count,
            "selected_case_ids": list(dict.fromkeys(str(entry["case_id"]) for entry in executions)),
            "selected_executions": executions,
        }
        self.write_session()

    # 把一个 Case 的统一结果写入专属目录，并提取首个可用目标元数据到 Session。
    def write_case_result(self, identity: ExecutionIdentity, result: dict[str, Any]) -> Path:

        payload = dict(result)
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload["run_id"] = self.run_id
        payload["case_run_id"] = identity.case_run_id
        self._update_session_metadata(payload)
        output = identity.execution_dir / "result.json"
        return write_json_result(output, payload)

    # Copy only first-available target metadata into the run record.
    def _update_session_metadata(self, result: dict[str, Any]) -> None:

        for key in (
            "chip_id",
            "firmware_build_id",
            "registry_hash",
            "target_id",
            "bench_path",
            "bench_sha256",
            "config_hash",
            "transport_identity",
            "bitstream_id",
            "device_identity",
        ):
            if key not in self._session_metadata and result.get(key) is not None:
                self._session_metadata[key] = result[key]


# 解析 Bench 路径并计算 SHA-256；文件不可读时保留路径并返回空 Hash。
def bench_metadata(path_value: object | None) -> tuple[str | None, str | None]:

    if not path_value:
        return None, None
    path = Path(str(path_value)).resolve()
    return str(path), _sha256(path)


# 从 pytest ``user_properties`` 读取已登记且受支持的 Evidence Source，保持去重顺序。
def case_evidence_sources(item: object) -> list[str]:

    properties = getattr(item, "user_properties", ())
    values = [value for name, value in properties if name == EVIDENCE_PROPERTY]
    return _normalise_sources(values, strict=False)


# 校验 Evidence Source 后写入 pytest Property；未知来源或空输入立即拒绝。
def record_evidence(record_property: Any, *sources: str) -> None:

    normalized = _normalise_sources(sources, strict=True)
    if not normalized:
        raise ValueError("at least one evidence source is required")
    record_property(EVIDENCE_PROPERTY, normalized)


# 记录一次可审计的真实设备观测，并把该设备来源登记到现有 Evidence Gate。
def record_observation(
    record_property: Any,
    *,
    key: str,
    value: object,
    source: str,
    endpoint: str,
    device_id: str | None = None,
    artifacts: tuple[str, ...] = (),
) -> None:

    normalized_sources = _normalise_sources((source,), strict=True)
    if not isinstance(key, str) or not key.strip():
        raise ValueError("observation key must be a non-empty string")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("observation endpoint must be a non-empty string")
    if device_id is not None and (not isinstance(device_id, str) or not device_id.strip()):
        raise ValueError("observation device_id must be a non-empty string when provided")
    if source != "dut" and device_id is None:
        raise ValueError(f"observation source {source!r} requires device_id")
    if not isinstance(artifacts, tuple) or any(
        not isinstance(path, str) or not path.strip() for path in artifacts
    ):
        raise ValueError("observation artifacts must be a tuple of non-empty relative paths")
    if any(Path(path).is_absolute() or ".." in Path(path).parts for path in artifacts):
        raise ValueError("observation artifacts must be run-relative paths")

    payload = {
        "key": key.strip(),
        "value": _json_result_value(value),
        "source": normalized_sources[0],
        "device_id": device_id.strip() if device_id is not None else "dut",
        "endpoint": endpoint.strip(),
        "artifacts": list(artifacts),
    }
    record_property(OBSERVATION_PROPERTY, payload)
    record_evidence(record_property, source)


# 声明 Case 必须消费的 Evidence Source；不登记实际证据，也不依赖具体 Fixture 名。
def require_evidence(record_property: Any, *sources: str) -> None:

    normalized = _normalise_sources(sources, strict=True)
    if not normalized:
        raise ValueError("at least one required evidence source is required")
    record_property(REQUIRED_EVIDENCE_PROPERTY, normalized)


# 从通用 pytest Property 读取 Required Evidence，不耦合任何 IP Fixture 名。
def required_evidence_sources(item: object) -> list[str]:

    properties = getattr(item, "user_properties", ())
    values = [value for name, value in properties if name == REQUIRED_EVIDENCE_PROPERTY]
    return _normalise_sources(values, strict=False)


def _normalise_sources(values: object, *, strict: bool) -> list[str]:
    if isinstance(values, str) or not isinstance(values, (list, tuple, set, frozenset)):
        values = [values]
    normalized: list[str] = []
    for value in values:
        if isinstance(value, str):
            parts = value.split(",")
        elif isinstance(value, (list, tuple, set, frozenset)):
            parts = [str(item) for item in value]
        else:
            continue
        for part in parts:
            source = part.strip()
            if not source:
                if strict:
                    raise ValueError("evidence source must be a non-empty string")
                continue
            if source not in ALLOWED_EVIDENCE_SOURCES:
                if strict:
                    raise ValueError(
                        f"unsupported evidence source: {source!r}; "
                        f"allowed={sorted(ALLOWED_EVIDENCE_SOURCES)!r}"
                    )
                continue
            if source not in normalized:
                normalized.append(source)
    return normalized


# 合并 pytest 三阶段报告、目标元数据与 Evidence，生成唯一 Case Result Payload。
def case_result_payload(
    *,
    item: object,
    reports: dict[str, object],
    framework: object | None,
    target_id: object | None,
    bench_path: object | None,
    case_run_id: str,
    run_id: str,
) -> dict[str, Any]:

    ordered = [reports.get("setup"), reports.get("call"), reports.get("teardown")]
    failed = [report for report in ordered if _safe_attr(report, "failed")]
    skipped = next((report for report in ordered if _safe_attr(report, "skipped")), None)
    status = "FAIL" if failed else "SKIP" if skipped is not None else "PASS"
    error_parts = [
        f"[{phase}] {_safe_attr(report, 'longrepr')}"
        for phase, report in zip(("setup", "call", "teardown"), ordered, strict=True)
        if report is not None and _safe_attr(report, "failed")
    ]
    if not error_parts and skipped is not None:
        skipped_phase = next(
            phase
            for phase, report in zip(("setup", "call", "teardown"), ordered, strict=True)
            if report is skipped
        )
        error_parts.append(f"[{skipped_phase}] {_safe_attr(skipped, 'longrepr')}")
    error = "\n".join(error_parts) or None
    duration_s = sum(float(_safe_attr(report, "duration") or 0.0) for report in ordered)
    resolved_bench, bench_hash = bench_metadata(bench_path)
    chip_id = _safe_attr(framework, "chip_id")
    firmware_build_id = _safe_attr(framework, "firmware_build_id")
    actual_evidence = case_evidence_sources(item)
    required_evidence = required_evidence_sources(item)
    case_id, ip_id = _case_identity(item)
    parameters = _case_parameters(item)
    measurements, artifacts = _case_recorded_outputs(item)
    observations = _case_observations(item)
    missing_evidence = [source for source in required_evidence if source not in actual_evidence]
    evidence_complete = not missing_evidence
    if missing_evidence:
        missing_message = "missing required evidence sources: " + ", ".join(missing_evidence)
        if status == "PASS":
            status = "EVIDENCE_MISSING"
            error = missing_message
        elif error is not None and status == "FAIL":
            error = f"{error}\n[evidence] {missing_message}"
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "case_run_id": case_run_id,
        "case_id": case_id,
        "status": status,
        "duration_s": duration_s,
        "platform_version": platform_version(),
        "chip_id": chip_id,
        "chip": chip_id,
        "firmware_build_id": firmware_build_id,
        "firmware": firmware_build_id,
        "registry_hash": _safe_attr(framework, "registry_hash"),
        "transport_identity": _safe_attr(framework, "transport_identity"),
        "bench_path": resolved_bench,
        "bench": resolved_bench,
        "bench_sha256": bench_hash,
        "config_hash": bench_hash,
        "target_id": str(target_id) if target_id is not None else None,
        "bitstream_id": None,
        "device_identity": None,
        "feature": case_id if ip_id is not None else None,
        "ip_id": ip_id,
        "parameter_id": parameters.get("parameter_id"),
        "parameters": parameters,
        "measurements": measurements,
        "observations": observations,
        "artifacts": artifacts,
        "required_evidence_sources": required_evidence,
        "evidence_sources": actual_evidence,
        "evidence_complete": evidence_complete,
        "missing_evidence_sources": missing_evidence,
        "error": error,
    }
