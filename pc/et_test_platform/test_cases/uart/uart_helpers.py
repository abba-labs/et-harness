# Formal Case本地Support模块。
#
# 职责：聚合本测试域的只读事实、Driver构造和小粒度复用操作。
# 边界：不隐藏完整Case、不拥有最终断言，也不改变公共Scheduling。
# 依赖：仅依赖本IP Driver、Profile事实和稳定公共工具。

from __future__ import annotations

from pathlib import Path

from ...results.recorder import write_json_result

DEFAULT_BAUDRATE = 115_200
DEFAULT_MAX_POLLS = 1_000_000
CAPTURE_TIMEOUT_S = 2.0


# Return deterministic data that exercises low and high byte values.
def make_pattern(length: int, *, seed: int = 0x35) -> bytes:

    if length <= 0:
        raise ValueError("UART pattern length must be positive")
    return bytes((seed + index * 37 + (index >> 2)) & 0xFF for index in range(length))


# Create stable JSON evidence for one Case result.
def result_payload(case_id: str, **fields: object) -> dict[str, object]:

    return {"case": case_id, "measurement_schema": "et.measurement.v1", **fields}


# Write one atomic result file and return its path.
def record_result(
    artifact_dir: Path,
    case_id: str,
    **fields: object,
) -> Path:

    return write_json_result(
        artifact_dir / f"{case_id}.json",
        result_payload(case_id, **fields),
    )
