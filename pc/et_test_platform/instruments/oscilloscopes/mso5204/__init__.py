# RIGOL MSO5204 外部仪器驱动包公共入口。
#
# 职责：导出型号 Driver、VISA 连接构造、稳定枚举/配置/结果模型和常用 Operations。
# 边界：导入本包不会打开仪器、不扫描 VISA 资源，也不会发送任何 SCPI 命令。
# 依赖：仅依赖本型号 connection、driver、models 和 operations 模块。

from .connection import create_mso5204_visa_driver
from .driver import Mso5204Driver
from .models import (
    Mso5204AcquireType,
    Mso5204AnalogChannel,
    Mso5204BandwidthLimit,
    Mso5204ChannelCoupling,
    Mso5204ChannelUnit,
    Mso5204EdgeCaptureConfig,
    Mso5204Identification,
    Mso5204MeasurementItem,
    Mso5204MeasurementStatistic,
    Mso5204MemoryDepth,
    Mso5204SignalMeasurements,
    Mso5204SystemError,
    Mso5204TimebaseMode,
    Mso5204TriggerCoupling,
    Mso5204TriggerMode,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
    Mso5204Waveform,
    Mso5204WaveformFormat,
    Mso5204WaveformMode,
    Mso5204WaveformPreamble,
    Mso5204WaveformReadConfig,
    Mso5204WaveformSource,
)
from .observer import (
    Mso5204ObserverBinding,
    Mso5204SignalObserver,
    create_mso5204_signal_observer,
)
from .operations import (
    Mso5204Operations,
    configure_edge_capture,
    measure_signal,
    read_screen_waveform,
)

__all__ = [
    "Mso5204AcquireType",
    "Mso5204AnalogChannel",
    "Mso5204BandwidthLimit",
    "Mso5204ChannelCoupling",
    "Mso5204ChannelUnit",
    "Mso5204Driver",
    "Mso5204EdgeCaptureConfig",
    "Mso5204Identification",
    "Mso5204MeasurementItem",
    "Mso5204MeasurementStatistic",
    "Mso5204MemoryDepth",
    "Mso5204Operations",
    "Mso5204ObserverBinding",
    "Mso5204SignalObserver",
    "Mso5204SignalMeasurements",
    "Mso5204SystemError",
    "Mso5204TimebaseMode",
    "Mso5204TriggerCoupling",
    "Mso5204TriggerMode",
    "Mso5204TriggerSlope",
    "Mso5204TriggerSweep",
    "Mso5204Waveform",
    "Mso5204WaveformFormat",
    "Mso5204WaveformMode",
    "Mso5204WaveformPreamble",
    "Mso5204WaveformReadConfig",
    "Mso5204WaveformSource",
    "configure_edge_capture",
    "create_mso5204_visa_driver",
    "create_mso5204_signal_observer",
    "measure_signal",
    "read_screen_waveform",
]
