# RIGOL DM3068 型号 Driver 聚合入口。
#
# 职责：把一个 ScpiSession 聚合成按能力命名的原子 Control，并暴露 Typed Operations 易用层。
# 边界：不隐藏 Test Case PASS/FAIL，不跨仪器编排，构造对象时不执行设备 I/O。
# 依赖：仅依赖公共 ScpiSession、本型号 controls 和本型号 Operations。

from __future__ import annotations

from ...common.scpi import ScpiSession
from .controls import (
    Dm3068CalculateControl,
    Dm3068CommonControl,
    Dm3068FunctionControl,
    Dm3068InterfaceControl,
    Dm3068MeasurementControl,
    Dm3068RateControl,
    Dm3068SecondaryDisplayControl,
    Dm3068StatusControl,
    Dm3068SystemControl,
    Dm3068TriggerControl,
)
from .operations import Dm3068Operations


# 聚合 DM3068 原生 RIGOL/Common 命令能力与常用 Operations；构造对象时不会访问仪器。
class Dm3068Driver:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session
        self.common = Dm3068CommonControl(session)
        self.status = Dm3068StatusControl(session)
        self.calculate = Dm3068CalculateControl(session)
        self.function = Dm3068FunctionControl(session)
        self.secondary_display = Dm3068SecondaryDisplayControl(session)
        self.measurement = Dm3068MeasurementControl(session)
        self.rate = Dm3068RateControl(session)
        self.system = Dm3068SystemControl(session)
        self.trigger = Dm3068TriggerControl(session)
        self.interface = Dm3068InterfaceControl(session)
        self.operations = Dm3068Operations(self)

    # 返回底层 Transport 的连接标识；只暴露通信身份，不探测或修改仪器状态。
    @property
    def identity(self) -> str:
        return self._session.identity

    # 打开当前 ScpiSession 的 Transport；不自动复位、不切换命令集或测量功能。
    def open(self) -> None:
        self._session.open()

    # 关闭当前 ScpiSession 的 Transport；不自动保存状态或修改仪器测量配置。
    def close(self) -> None:
        self._session.close()
