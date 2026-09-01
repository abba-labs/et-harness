# AES Formal Case 本地结果附件辅助模块。
#
# 职责：把 AES Case 已产生的真实观测值规范化并写入稳定 JSON 附件。
# 边界：不执行硬件操作、不隐藏测试步骤，也不拥有任何最终断言。
# 依赖：仅依赖公共结果记录器和 Python 标准库。

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from ...results.recorder import write_json_result


# 将 Case 观测值转换为可写入 JSON 的稳定类型。
def _json_value(value: object) -> Any:

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    return str(value)


# 组装单个 AES Case 的标准结果载荷，不增加测试流程逻辑。
def result_payload(case_id: str, **fields: object) -> dict[str, Any]:

    return {
        "case": case_id,
        "measurement_schema": "et.measurement.v1",
        **{key: _json_value(value) for key, value in fields.items()},
    }


# 按稳定 Case ID 写入 JSON 观测附件并返回附件路径。
def record_result(artifact_dir: Path, case_id: str, **fields: object) -> Path:

    return write_json_result(
        artifact_dir / f"{case_id}.json",
        result_payload(case_id, **fields),
    )
