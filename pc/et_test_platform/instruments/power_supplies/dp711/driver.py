# RIGOL DP711 仪器 Driver 聚合入口。
#
# 职责：持有一个 SCPI Session，并按能力暴露原子 Control 与常用 Operations 易用层。
# 边界：不隐藏 Test Case PASS/FAIL，不执行跨仪器编排，构造对象时不发送任何 SCPI。
# 依赖：仅依赖公共 ScpiSession、本型号各原子 Control 和本型号 Operations。

from __future__ import annotations

from ...common.scpi import ScpiSession
from .controls.basic import Dp711BasicControl
from .controls.measurement import Dp711MeasurementControl
from .controls.memory import Dp711MemoryControl
from .controls.output import Dp711OutputControl
from .controls.source import Dp711SourceControl
from .controls.system import Dp711SystemControl
from .controls.timer import Dp711TimerControl
from .operations import Dp711Operations


# 提供 DP711 单仪器稳定入口；所有能力对象共享一个连接，构造时不执行设备 I/O。
class Dp711Driver:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session
        self.basic = Dp711BasicControl(session)
        self.measurement = Dp711MeasurementControl(session)
        self.memory = Dp711MemoryControl(session)
        self.output = Dp711OutputControl(session)
        self.source = Dp711SourceControl(session)
        self.system = Dp711SystemControl(session)
        self.timer = Dp711TimerControl(session)
        self.operations = Dp711Operations(self)

    # 返回当前连接标识；不执行设备 I/O；读取过程不会访问仪器硬件。
    @property
    def identity(self) -> str:
        return self._session.identity

    # 打开底层连接；不自动查询设备或修改输出状态；连接失败由底层 Transport 直接上抛。
    def open(self) -> None:
        self._session.open()

    # 关闭底层连接；不向仪器发送额外清理命令；关闭失败由底层 Transport 直接上抛。
    def close(self) -> None:
        self._session.close()
