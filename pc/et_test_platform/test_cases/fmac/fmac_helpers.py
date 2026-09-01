# FMAC Formal Case 本地纯软件辅助函数。
#
# 职责：提供确定性数据打包、简单Q15参考运算和标准结果附件写入。
# 边界：不访问目标、不隐藏硬件动作、不替代Case最终断言。
# 依赖：仅依赖标准库和公共Result辅助接口。

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ...drivers.fmac import FmacConfig, FmacWatermark
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation as _record_observation

Q15_MAX = 0x7FFF
Q15_MIN = -0x8000


# 返回三区域互不重叠的最小公共FMAC配置；Case可用replace只改变目标字段。
def default_config(*, x1_size: int = 16, x2_size: int = 16, y_size: int = 16) -> FmacConfig:

    return FmacConfig(
        x1_start=0,
        x1_size=x1_size,
        x1_full_watermark=FmacWatermark.ITEMS_1,
        x2_start=32,
        x2_size=x2_size,
        y_start=64,
        y_size=y_size,
        y_empty_watermark=FmacWatermark.ITEMS_1,
    )


# 把Case真实观测转换为稳定JSON类型。
def _json_value(value: object) -> Any:

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    return str(value)


# 先把FMAC Driver快照转换为Canonical JSON，再交给公共Observation记录入口。
def record_fmac_observation(
    record_property: Callable[[str, object], None],
    *,
    key: str,
    value: object,
    source: str,
    endpoint: str,
    device_id: str | None = None,
    artifacts: tuple[str, ...] = (),
) -> None:

    _record_observation(
        record_property,
        key=key,
        value=_json_value(value),
        source=source,
        endpoint=endpoint,
        device_id=device_id,
        artifacts=artifacts,
    )


# 按稳定Case ID写入结构化观测附件。
def record_result(artifact_dir: Path, case_id: str, **fields: object) -> Path:

    return write_json_result(
        artifact_dir / f"{case_id}.json",
        {
            "case": case_id,
            "measurement_schema": "et.measurement.v1",
            **{key: _json_value(value) for key, value in fields.items()},
        },
    )


# 将有符号Q15样本编码为目标侧小端Resource字节流。
def pack_q15(values: list[int] | tuple[int, ...]) -> bytes:

    if not values:
        raise ValueError("Q15 sequence must not be empty")
    if any(value < Q15_MIN or value > Q15_MAX for value in values):
        raise ValueError("Q15 value is outside signed 16-bit range")
    return struct.pack(f"<{len(values)}h", *values)


# 从目标侧Resource字节流严格解码有符号Q15样本。
def unpack_q15(data: bytes) -> tuple[int, ...]:

    if not data or len(data) % 2:
        raise ValueError("Q15 payload length must be a positive multiple of two")
    return struct.unpack(f"<{len(data) // 2}h", data)


# 将Float32样本编码为目标侧小端Resource字节流。
def pack_float32(values: list[float] | tuple[float, ...]) -> bytes:

    if not values:
        raise ValueError("Float32 sequence must not be empty")
    return struct.pack(f"<{len(values)}f", *values)


# 从目标侧Resource字节流严格解码Float32样本。
def unpack_float32(data: bytes) -> tuple[float, ...]:

    if not data or len(data) % 4:
        raise ValueError("Float32 payload length must be a positive multiple of four")
    return struct.unpack(f"<{len(data) // 4}f", data)


# 把Float值按FMAC公开语义转换为饱和Q15参考值。
def float_to_q15(value: float) -> int:

    scaled = int(round(value * 32768.0))
    return min(Q15_MAX, max(Q15_MIN, scaled))


# 按FMAC Q15 Direct Form 1语义计算独立软件Oracle。
def iir_direct_form1_q15(
    samples: tuple[int, ...],
    feedback: tuple[int, ...],
    feedforward: tuple[int, ...],
) -> tuple[int, ...]:

    if not samples or not feedback or len(feedforward) != len(feedback) + 1:
        raise ValueError("IIR Direct Form 1 vectors are incomplete")
    if any(value < Q15_MIN or value > Q15_MAX for value in (*samples, *feedback, *feedforward)):
        raise ValueError("IIR Direct Form 1 value is outside signed Q15 range")

    output: list[int] = []

    # 每拍先累加当前和历史输入的前馈项，再累加历史输出的正反馈项。
    for sample_index in range(len(samples)):
        accumulator = sum(
            coefficient * samples[sample_index - tap]
            for tap, coefficient in enumerate(feedforward)
            if tap <= sample_index
        )
        accumulator += sum(
            coefficient * output[sample_index - tap - 1]
            for tap, coefficient in enumerate(feedback)
            if tap < sample_index
        )
        output.append(max(Q15_MIN, min(Q15_MAX, accumulator >> 15)))

    return tuple(output)
