# 当前Canonical输入的只读内存模型。
# 职责：校验身份、Lane和原始结果，不保存长期副本。
# 边界：不推测问题根因，不读取设备，不跨版本合并测试状态。
# 依赖：标准库与记录序列化工具。

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from record_transaction import safe_name

LANES = frozenset({"sil", "fpga", "hil"})
STATUSES = frozenset({"PASS", "FAIL", "SKIP", "EVIDENCE_MISSING"})
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
    def status(self) -> str:
        return str(self.result["status"]) if self.result is not None else "NOT_EXECUTED"
