# 测试 Measurement 与结果附件序列化层。
#
# 职责：把已观测事实整理为稳定 Measurement/JSON 附件，供报告和人工审阅使用。
# 边界：不执行设备操作、不重复计算 pytest 最终 PASS/FAIL，也不隐藏测试流程。
# 依赖：仅依赖不可变结果模型、JSON 和文件系统。

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# 提供 LatencySummary 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True, slots=True)
class LatencySummary:
    minimum_ms: float
    p50_ms: float
    p95_ms: float
    maximum_ms: float


# 提供 PayloadClassSummary 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True, slots=True)
class PayloadClassSummary:
    name: str
    payload_size: int
    transactions: int
    retry_count: int
    latency: LatencySummary


# 提供 FrameworkCommunicationStressResult 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True, slots=True)
class FrameworkCommunicationStressResult:
    transport: str
    chip_id: str
    firmware_build_id: str
    rounds: int
    transactions: int
    elapsed_seconds: float
    payload_bytes_round_trip: int
    payload_throughput_bytes_per_second: float
    error_count: int
    classes: tuple[PayloadClassSummary, ...]

    # 生成或描述 to measurements 对应的 Measurement/附件事实；不执行设备命令，也不形成第二套 PASS/FAIL。
    def to_measurements(self) -> dict[str, Any]:

        return {
            "measurement_schema": "et.measurement.v1",
            **asdict(self),
        }
