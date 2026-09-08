# Case当前台账的增量合并与有限证据保留。
# 职责：维护真实执行的来源、计数、最新结果和受保护非PASS快照。
# 边界：不重新判定PASS/FAIL，不读取设备，不把多版本结果拼成一次回归。
# 依赖：标准库与记录序列化工具。

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime

from record_transaction import digest, json_bytes, safe_name

SCHEMA = "et.case-record.v1"
LANES = frozenset({"sil", "fpga", "hil"})
STATUSES = frozenset({"PASS", "FAIL", "SKIP", "EVIDENCE_MISSING"})
MAX_PROTECTED = 64
MAX_CASE_BYTES = 25 * 1024 * 1024
MAX_IP_BYTES = 256 * 1024 * 1024


def object_value(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return value


def list_value(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def text_value(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value


def timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(text_value(value, "finished_at").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("finished_at must include a timezone")
    return parsed


@dataclass(frozen=True, slots=True)
class Snapshot:
    lane: str
    session: dict[str, object]
    result: dict[str, object] | None
    selection: dict[str, object]
    files: dict[str, str]
    origin: str

    def __post_init__(self) -> None:
        if self.lane not in LANES:
            raise ValueError(f"invalid evidence lane: {self.lane}")
        timestamp(self.session.get("finished_at"))
        text_value(self.session.get("run_id"), "session.run_id")
        if type(self.session.get("exitstatus")) is not int:
            raise ValueError("session exitstatus must be an integer")
        safe_name(text_value(self.selection.get("case_id"), "case_id"))
        parameter = self.selection.get("parameter_id")
        if parameter is not None and not isinstance(parameter, str):
            raise ValueError("parameter_id must be text or null")
        if self.result is not None:
            if self.result.get("status") not in STATUSES:
                raise ValueError("invalid canonical result status")
            if self.result.get("run_id") != self.session["run_id"]:
                raise ValueError("result and session run_id disagree")
            if str(self.result.get("case_id")).lower() != self.case_id:
                raise ValueError("result and selection case_id disagree")
            if self.result.get("parameter_id") != parameter:
                raise ValueError("result and selection parameter_id disagree")
            for field in (
                "target_id",
                "firmware_build_id",
                "registry_hash",
                "bench_sha256",
                "bitstream_id",
                "device_identity",
            ):
                actual, expected = self.result.get(field), self.session.get(field)
                if actual is not None and expected is not None and actual != expected:
                    raise ValueError(f"result and Session {field} disagree")
        for path, sha in self.files.items():
            text_value(path, "attachment path")
            if len(sha) != 64 or any(char not in "0123456789abcdef" for char in sha):
                raise ValueError("invalid attachment SHA256")

    @property
    def case_id(self) -> str:
        return str(self.selection["case_id"]).lower()

    @property
    def key(self) -> str:
        return (
            json_bytes(
                [self.lane, self.session.get("target_id"), self.selection.get("parameter_id")]
            )
            .decode()
            .strip()
        )

    @property
    def status(self) -> str:
        return str(self.result["status"]) if self.result is not None else "NOT_EXECUTED"

    @property
    def identity(self) -> str:
        return digest(json_bytes(self.payload()))

    @property
    def semantics(self) -> str:
        result = copy.deepcopy(self.result)
        if result is not None:
            for name in ("run_id", "case_run_id", "duration_s", "artifacts"):
                result.pop(name, None)
            for observation in list_value(result.get("observations", []), "observations"):
                object_value(observation, "observation").pop("artifacts", None)
        identity_fields = (
            "source_revision",
            "source_dirty",
            "spec_sha256",
            "firmware_build_id",
            "bitstream_id",
            "device_identity",
            "bench_sha256",
            "registry_hash",
        )
        return digest(
            json_bytes(
                [
                    self.key,
                    result,
                    sorted(
                        (name, sha)
                        for name, sha in self.files.items()
                        if name
                        not in {"source/session.json", "source/result.json", "source/manifest.json"}
                    ),
                    {name: self.session.get(name) for name in identity_fields},
                ]
            )
        )

    def payload(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "session": self.session,
            "result": self.result,
            "selection": self.selection,
            "files": self.files,
            "origin": self.origin,
        }

    @classmethod
    def parse(cls, value: object) -> Snapshot:
        payload = object_value(value, "snapshot")
        files = object_value(payload.get("files"), "snapshot.files")
        result = payload.get("result")
        return cls(
            lane=text_value(payload.get("lane"), "lane"),
            session=object_value(payload.get("session"), "session"),
            result=None if result is None else object_value(result, "result"),
            selection=object_value(payload.get("selection"), "selection"),
            files={name: text_value(sha, "attachment hash") for name, sha in files.items()},
            origin=text_value(payload.get("origin"), "origin"),
        )


# 只保存当前Case状态；保护快照的释放由验证过的归档操作单独负责。
@dataclass(frozen=True, slots=True)
class CaseRecord:
    payload: dict[str, object]

    @classmethod
    def empty(cls, chip: str, ip: str, case_id: str) -> CaseRecord:
        return cls(
            {
                "schema": SCHEMA,
                "chip": safe_name(chip).upper(),
                "ip": safe_name(ip).upper(),
                "case_id": safe_name(case_id).upper(),
                "executions": {},
                "protected": [],
            }
        )

    @classmethod
    def parse(cls, value: object) -> CaseRecord:
        payload = object_value(value, "case record")
        if payload.get("schema") != SCHEMA:
            raise ValueError("unsupported case record schema")
        for field in ("chip", "ip", "case_id"):
            safe_name(text_value(payload.get(field), field))
        executions = object_value(payload.get("executions"), "executions")
        protected = list_value(payload.get("protected"), "protected")
        if len(protected) > MAX_PROTECTED:
            raise ValueError("protected evidence limit exceeded; archive required")
        for key, value in executions.items():
            entry = object_value(value, "execution")
            snapshot = Snapshot.parse(entry.get("latest"))
            if snapshot.key != key:
                raise ValueError("execution key and latest snapshot disagree")
            counts = object_value(entry.get("status_counts"), "status_counts")
            if any(
                status not in STATUSES | {"NOT_EXECUTED"} or type(count) is not int or count < 0
                for status, count in counts.items()
            ):
                raise ValueError("invalid cumulative status count")
            if type(entry.get("attempts")) is not int or entry["attempts"] != sum(counts.values()):
                raise ValueError("attempt counter and status counts disagree")
            if entry["attempts"] < 1 or counts.get(snapshot.status, 0) < 1:
                raise ValueError("latest result is not represented in cumulative counts")
        held_ids = [Snapshot.parse(item).identity for item in protected]
        if len(held_ids) != len(set(held_ids)):
            raise ValueError("duplicate protected snapshot")
        record = cls(payload)
        for snapshot in record.snapshots():
            if (
                snapshot.case_id.upper() != payload["case_id"]
                or str(snapshot.session.get("chip_id")).upper() != payload["chip"]
            ):
                raise ValueError("snapshot does not belong to this chip/Case")
            if (
                snapshot.result is not None
                and str(snapshot.result.get("ip_id")).upper() != payload["ip"]
            ):
                raise ValueError("snapshot does not belong to this IP")
        return record

    def snapshots(self) -> list[Snapshot]:
        current = object_value(self.payload["executions"], "executions")
        return [
            Snapshot.parse(object_value(entry, "execution")["latest"]) for entry in current.values()
        ] + [Snapshot.parse(item) for item in list_value(self.payload["protected"], "protected")]

    def merge(self, incoming: list[Snapshot]) -> CaseRecord:
        payload = copy.deepcopy(self.payload)
        executions = object_value(payload["executions"], "executions")
        protected = list_value(payload["protected"], "protected")
        held = {Snapshot.parse(item).semantics for item in protected}
        for snapshot in incoming:
            previous = executions.get(snapshot.key)
            if previous is None:
                entry: dict[str, object] = {"attempts": 0, "status_counts": {}}
            else:
                entry = object_value(previous, "execution")
                old = Snapshot.parse(entry["latest"])
                if old.identity == snapshot.identity:
                    continue
                if old.session["run_id"] == snapshot.session["run_id"]:
                    raise ValueError("same Run identity has conflicting content")
                if timestamp(snapshot.session["finished_at"]) <= timestamp(
                    old.session["finished_at"]
                ):
                    raise ValueError("older evidence cannot replace the current record")
                if old.status != "PASS" and old.semantics not in held:
                    protected.append(old.payload())
                    held.add(old.semantics)
                if (
                    old.status != "PASS"
                    and snapshot.status == "PASS"
                    and snapshot.semantics not in held
                ):
                    protected.append(snapshot.payload())
                    held.add(snapshot.semantics)
            counts = object_value(entry["status_counts"], "status_counts")
            counts[snapshot.status] = int(counts.get(snapshot.status, 0)) + 1
            entry["attempts"] = int(entry["attempts"]) + 1
            entry["latest"] = snapshot.payload()
            executions[snapshot.key] = entry
        return CaseRecord.parse(payload)

    def protect(self, snapshots: list[Snapshot]) -> CaseRecord:
        payload = copy.deepcopy(self.payload)
        protected = list_value(payload["protected"], "protected")
        identities = {Snapshot.parse(item).identity for item in protected}
        for snapshot in snapshots:
            if snapshot.identity not in identities:
                protected.append(snapshot.payload())
                identities.add(snapshot.identity)
        return CaseRecord.parse(payload)
