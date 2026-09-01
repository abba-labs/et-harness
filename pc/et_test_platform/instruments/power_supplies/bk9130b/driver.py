# B&K Precision 9130B 外部仪器聚合 Driver。
#
# 职责：把同一 SCPI 会话上的原子能力 Control 和 Typed Operations 组合成稳定型号入口。
# 边界：不隐藏 Test Case PASS/FAIL，不执行 DUT/跨仪器编排，构造时不发送任何 SCPI。
# 依赖：仅依赖公共 ScpiSession、本型号各原子 Control 和本型号 Operations。

from __future__ import annotations

from ...common.scpi import ScpiSession
from .controls import (
    Bk9130bApplyControl,
    Bk9130bChannelControl,
    Bk9130bCommonControl,
    Bk9130bDisplayControl,
    Bk9130bMeasurementControl,
    Bk9130bOutputControl,
    Bk9130bSourceControl,
    Bk9130bStatusControl,
    Bk9130bSystemControl,
    Bk9130bTriggerControl,
)
from .operations import Bk9130bOperations


# 提供 9130B 型号级入口；所有能力对象共享一个会话，构造对象不会访问真实仪器。
class Bk9130bDriver:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session
        self.common = Bk9130bCommonControl(session)
        self.system = Bk9130bSystemControl(session)
        self.status = Bk9130bStatusControl(session)
        self.output = Bk9130bOutputControl(session)
        self.source = Bk9130bSourceControl(session)
        self.display = Bk9130bDisplayControl(session)
        self.trigger = Bk9130bTriggerControl(session)
        self.channel = Bk9130bChannelControl(session)
        self.measurement = Bk9130bMeasurementControl(session)
        self.apply = Bk9130bApplyControl(session)
        self.operations = Bk9130bOperations(self)

    # 返回底层连接标识；只读本地会话属性，不执行设备 I/O。
    @property
    def identity(self) -> str:
        return self._session.identity

    # 打开底层仪器连接；不会自动发送 *RST、*CLS 或其他设备命令。
    def open(self) -> None:
        self._session.open()

    # 关闭底层仪器连接；不会在断开前隐式改变输出状态。
    def close(self) -> None:
        self._session.close()
