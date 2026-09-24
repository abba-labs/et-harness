# 封装层模型：在厂商稳定模型之上补充的配置与结果类型。
#
# 职责：定义常用触发/采集/RAW 读取配置，以及波形排布结果，供台架层与封装操作使用。
# 边界：只描述参数与结果，不生成 SCPI、不访问 Transport，也不执行 PASS/FAIL 判定。
# 依赖：仅依赖本库厂商模型层（mso5204.models）的枚举类型。

from __future__ import annotations

from dataclasses import dataclass

from ..mso5204.models import (
    Mso5204AcquireType,
    Mso5204AnalogChannel,
    Mso5204MemoryDepth,
    Mso5204TriggerCoupling,
    Mso5204TriggerMode,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
)


# 表示常用触发配置；None 字段保持仪器当前状态，不发生隐式修改。
@dataclass(frozen=True, slots=True)
class Mso5204TriggerConfig:
    mode: Mso5204TriggerMode | None = None
    sweep: Mso5204TriggerSweep | None = None
    coupling: Mso5204TriggerCoupling | None = None
    holdoff_s: float | None = None
    edge_source: int | Mso5204AnalogChannel | None = None
    edge_slope: Mso5204TriggerSlope | None = None
    edge_level_v: float | None = None
    noise_reject: bool | None = None


# 表示常用采集配置；average_count 只在 AVERage 类型下合法，其余 None 字段不修改仪器。
@dataclass(frozen=True, slots=True)
class Mso5204AcquireConfig:
    acquire_type: Mso5204AcquireType | None = None
    average_count: int | None = None
    memory_depth: Mso5204MemoryDepth | int | None = None
    anti_alias: bool | None = None


# 表示 RAW 深存储波形读取选项；stop_first 与 restart_run 控制对仪器运行状态的临时影响。
@dataclass(frozen=True, slots=True)
class Mso5204RawWaveformConfig:
    channel: int | Mso5204AnalogChannel
    start: int | None = None
    stop: int | None = None
    read_timeout_s: float = 30.0
    acquire_timeout_s: float = 6.0
    stop_first: bool = True
    restart_run: bool = True


# 表示一次 RAW 深存储波形读取结果；点数可达百万级，时间轴按增量保存而非展开成元组。
@dataclass(frozen=True, slots=True)
class Mso5204RawWaveform:
    channel: int
    samples: tuple[float, ...]
    x_increment_s: float
    x_origin_s: float

    # 返回第 index 个采样点对应的物理时间，单位 s；不做边界截断，越界由调用方判断。
    def time_at(self, index: int) -> float:

        return self.x_origin_s + index * self.x_increment_s


# 表示单个通道的屏幕排布：垂直量程与偏移；用于把两路波形在屏幕上分开显示。
@dataclass(frozen=True, slots=True)
class Mso5204ChannelPlacement:
    channel: int
    scale_v: float
    offset_v: float
    scale_changed: bool
    offset_changed: bool


# 表示两路波形的屏幕排布结果；upper 占上半屏、lower 占下半屏，互不重叠。
@dataclass(frozen=True, slots=True)
class Mso5204TwoChannelLayout:
    upper: Mso5204ChannelPlacement
    lower: Mso5204ChannelPlacement
    divisions: float


__all__ = [
    "Mso5204AcquireConfig",
    "Mso5204ChannelPlacement",
    "Mso5204RawWaveform",
    "Mso5204RawWaveformConfig",
    "Mso5204TriggerConfig",
    "Mso5204TwoChannelLayout",
]
