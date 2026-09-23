# RIGOL MSO5204 Quick Key 原子控制。
#
# 职责：映射 QUICk:OPERation 的设置与查询。
# 边界：只配置前面板快捷键行为，不执行快捷键对应的保存、测量或复位动作。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 格式化辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command


# 提供 Quick 前面板快捷键配置接口；构造时仅保存 Session，不向仪器发送命令。
class Mso5204QuickControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置前面板 Quick 快捷键绑定的操作类型；只发送一次 OPERation 命令，不执行该动作。
    def operation_set(self, operation: str) -> None:
        self._session.write(_command(":QUICk:OPERation", operation))

    # 查询前面板 Quick 快捷键当前绑定的操作类型；只读取配置，不触发快捷操作。
    def operation_get(self) -> str:
        return self._session.query_text(":QUICk:OPERation?")
