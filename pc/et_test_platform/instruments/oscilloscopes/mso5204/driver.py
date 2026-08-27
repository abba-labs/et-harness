# RIGOL MSO5204 型号 Driver 聚合入口。
#
# 职责：把同一 ScpiSession 聚合成完整的 MSO5204 原子 Control 命名空间和常用 Operations 易用层。
# 边界：不隐藏 Test Case PASS/FAIL、不跨仪器编排，也不在构造对象时发送任何 SCPI 命令。
# 依赖：仅依赖公共 ScpiSession、本型号 controls 和本型号 Operations。

from __future__ import annotations

from ...common.scpi import ScpiSession
from .controls import (
    Mso5204AcquireControl,
    Mso5204AdvancedTriggerControl,
    Mso5204BasicControl,
    Mso5204BodePlotControl,
    Mso5204BusControl,
    Mso5204ChannelControl,
    Mso5204CounterControl,
    Mso5204CursorControl,
    Mso5204DisplayControl,
    Mso5204DvmControl,
    Mso5204HistogramControl,
    Mso5204Ieee488Control,
    Mso5204LanControl,
    Mso5204LogicAnalyzerControl,
    Mso5204MaskControl,
    Mso5204MathControl,
    Mso5204MeasurementControl,
    Mso5204PowerControl,
    Mso5204ProtocolTriggerControl,
    Mso5204QuickControl,
    Mso5204RecordControl,
    Mso5204ReferenceControl,
    Mso5204SaveLoadControl,
    Mso5204SearchControl,
    Mso5204SourceControl,
    Mso5204SystemControl,
    Mso5204TimebaseControl,
    Mso5204TraceControl,
    Mso5204TriggerControl,
    Mso5204WaveformControl,
)
from .operations import Mso5204Operations


# 聚合 MSO5204 全部已建模能力；构造对象本身不连接硬件，也不会发送任何 SCPI 命令。
class Mso5204Driver:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session
        self.basic = Mso5204BasicControl(session)
        self.common = Mso5204Ieee488Control(session)
        self.acquire = Mso5204AcquireControl(session)
        self.bodeplot = Mso5204BodePlotControl(session)
        self.channel = Mso5204ChannelControl(session)
        self.timebase = Mso5204TimebaseControl(session)
        self.trigger = Mso5204TriggerControl(session)
        self.trigger_advanced = Mso5204AdvancedTriggerControl(session)
        self.trigger_protocol = Mso5204ProtocolTriggerControl(session)
        self.bus = Mso5204BusControl(session)
        self.measurement = Mso5204MeasurementControl(session)
        self.waveform = Mso5204WaveformControl(session)
        self.display = Mso5204DisplayControl(session)
        self.dvm = Mso5204DvmControl(session)
        self.counter = Mso5204CounterControl(session)
        self.cursor = Mso5204CursorControl(session)
        self.histogram = Mso5204HistogramControl(session)
        self.logic_analyzer = Mso5204LogicAnalyzerControl(session)
        self.lan = Mso5204LanControl(session)
        self.mask = Mso5204MaskControl(session)
        self.math = Mso5204MathControl(session)
        self.power = Mso5204PowerControl(session)
        self.quick = Mso5204QuickControl(session)
        self.record = Mso5204RecordControl(session)
        self.reference = Mso5204ReferenceControl(session)
        self.save_load = Mso5204SaveLoadControl(session)
        self.search = Mso5204SearchControl(session)
        self.source = Mso5204SourceControl(session)
        self.trace = Mso5204TraceControl(session)
        self.system = Mso5204SystemControl(session)
        self.operations = Mso5204Operations(self)

    # 返回底层通信资源的稳定连接标识；只读通信身份，不向示波器发送任何 SCPI 命令。
    @property
    def identity(self) -> str:
        return self._session.identity

    # 打开底层 Transport；按 Transport 自身连接流程等待完成，连接失败或超时异常直接向上层传播。
    def open(self) -> None:
        self._session.open()

    # 关闭底层 Transport；等待底层关闭调用返回，关闭异常直接传播且不隐式修改示波器运行状态。
    def close(self) -> None:
        self._session.close()
