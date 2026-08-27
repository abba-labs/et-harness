# FRAMEWORK PC Driver Package 的models层。
#
# 职责：提供 FRAMEWORK 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from __future__ import annotations

from dataclasses import dataclass


# 表示 HelloInfo 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class HelloInfo:
    protocol_version: int
    chip_id: str
    firmware_build_id: str
    registry_hash: str


# 表示 VersionInfo 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class VersionInfo:
    protocol_version: int
    firmware_build_id: str


# 表示 ServiceInfo 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class ServiceInfo:
    service_id: int
    instance_id: int


# 表示 ProtocolStatistics 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class ProtocolStatistics:
    rx_frames: int
    tx_frames: int
    parse_errors: int
    duplicate_requests: int


# 表示 EchoExchange 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True, slots=True)
class EchoExchange:
    response: bytes
    latency_ms: float
    retry_count: int
