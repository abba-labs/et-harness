# 测试 Measurement 与结果附件序列化层。
#
# 职责：把已观测事实整理为稳定 Measurement/JSON 附件，供报告和人工审阅使用。
# 边界：不执行设备操作、不重复计算 pytest 最终 PASS/FAIL，也不隐藏测试流程。
# 依赖：仅依赖不可变结果模型、JSON 和文件系统。

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

_ARTIFACT_SINK: ContextVar[Callable[[Path], None] | None] = ContextVar(
    "et_result_artifact_sink",
    default=None,
)


# 把公共结果边界支持的值转换为JSON原生类型；未知类型必须失败，不能用字符串掩盖契约错误。
def normalize_json_value(value: object, *, field: str = "result") -> Any:

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field} contains a non-finite float")
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return list(bytes(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field} contains a non-string mapping key: {key!r}")
            normalized[key] = normalize_json_value(item, field=f"{field}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            normalize_json_value(item, field=f"{field}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, (set, frozenset)):
        raise TypeError(f"{field} contains an unordered collection")
    raise TypeError(f"{field} contains unsupported type {type(value).__name__}")


# 在一个 pytest Case 执行边界内绑定 canonical artifact 记录器。
# 该机制只登记路径，不解释任何 IP 字段，也不改变附件内容。
@contextmanager
def bind_result_artifact_sink(sink: Callable[[Path], None]) -> Iterator[None]:

    token = _ARTIFACT_SINK.set(sink)
    try:
        yield
    finally:
        _ARTIFACT_SINK.reset(token)


# 生成或描述 write json result 对应的 Measurement/附件事实；不执行设备命令，也不形成第二套 PASS/FAIL。
def write_json_result(path: str | Path, result: dict[str, Any]) -> Path:

    output = Path(path)
    normalized = normalize_json_value(result)
    if not isinstance(normalized, dict):
        raise TypeError("result must normalize to a JSON object")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(output)
    sink = _ARTIFACT_SINK.get()
    if sink is not None:
        sink(output.resolve())
    return output
