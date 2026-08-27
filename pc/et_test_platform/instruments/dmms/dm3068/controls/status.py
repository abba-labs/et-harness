# RIGOL DM3068 Status Register 原子控制。
#
# 职责：映射 Common Command System 中 OPERation 与 QUEStionable 状态寄存器命令。
# 边界：只读写状态寄存器，不执行测量、复位、错误恢复或测试判定。
# 依赖：仅依赖公共 ScpiSession 和整数响应解析。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import _parse_int


# 提供 DM3068 OPERation/QUEStionable 状态树的单命令访问接口。
class Dm3068StatusControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询 OPERation Condition 寄存器；只读取当前条件位，不修改使能掩码。
    def operation_condition_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:OPERation:CONDition?"))

    # 设置 OPERation Enable 寄存器；只写入一条状态使能命令。
    def operation_enable_set(self, value: int) -> None:
        self._session.write(f":STATus:OPERation:ENABle {value}")

    # 查询 OPERation Enable 寄存器；只读取当前使能掩码。
    def operation_enable_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:OPERation:ENABle?"))

    # 读取 OPERation Event 寄存器；只执行该事件寄存器 Query。
    def operation_event_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:OPERation:EVENt?"))

    # 恢复状态子系统预设值；只发送 STATus:PRESet，不执行仪器复位。
    def preset(self) -> None:
        self._session.write(":STATus:PRESet")

    # 查询 QUEStionable Condition 寄存器；只读取当前条件位。
    def questionable_condition_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:QUEStionable:CONDition?"))

    # 设置 QUEStionable Enable 寄存器；只写入一条状态使能命令。
    def questionable_enable_set(self, value: int) -> None:
        self._session.write(f":STATus:QUEStionable:ENABle {value}")

    # 查询 QUEStionable Enable 寄存器；只读取当前使能掩码。
    def questionable_enable_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:QUEStionable:ENABle?"))

    # 读取 QUEStionable Event 寄存器；只执行该事件寄存器 Query。
    def questionable_event_get(self) -> int:
        return _parse_int(self._session.query_text(":STATus:QUEStionable:EVENt?"))
