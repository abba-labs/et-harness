# 封装层入口：在厂商驱动之上补充的常用能力。
#
# 职责：导出封装层的台架对象、补充配置模型、波形分析与示例入口。
# 边界：不修改厂商驱动实现；导入本包不会打开仪器或发送任何 SCPI 命令。
# 依赖：仅依赖本库厂商包（mso5204）与封装层自身模块。

from .analysis import (
    Edge,
    Wave,
    burst_pulse_count,
    count_edges,
    dead_time_s,
    edge_offset_s,
    edge_position_s,
    high_level_v,
    low_level_v,
)
from .driver import create_wrapper_driver, install_wrapper_operations
from .models import (
    Mso5204AcquireConfig,
    Mso5204ChannelPlacement,
    Mso5204RawWaveform,
    Mso5204RawWaveformConfig,
    Mso5204TriggerConfig,
    Mso5204TwoChannelLayout,
)
from .operations import Mso5204WrapperOperations
from .scope import Mso5204Scope, open_scope

__all__ = [
    "Edge",
    "Mso5204AcquireConfig",
    "Mso5204ChannelPlacement",
    "Mso5204RawWaveform",
    "Mso5204RawWaveformConfig",
    "Mso5204Scope",
    "Mso5204TriggerConfig",
    "Mso5204TwoChannelLayout",
    "Mso5204WrapperOperations",
    "Wave",
    "burst_pulse_count",
    "count_edges",
    "create_wrapper_driver",
    "dead_time_s",
    "edge_offset_s",
    "edge_position_s",
    "high_level_v",
    "install_wrapper_operations",
    "low_level_v",
    "open_scope",
]
