# RIGOL DP711 内部状态/定时文件控制。
#
# 职责：把 MEMory 文件删除、载入、锁定、保存和有效性查询映射为原子 API。
# 边界：不组合保存后校验流程，不解释文件内容，也不访问本地文件系统。
# 依赖：仅依赖 ScpiSession、本型号 FileType 和位置校验。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dp711FileType
from ..validation import parse_yes_no, require_file_position


# 提供 DP711 内部非易失文件原子控制；该类型不隐藏多步仪器操作流程。
class Dp711MemoryControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 删除指定 RSF/RTF 位置；文件不存在或锁定时由设备报告错误。
    def delete(self, file_type: Dp711FileType, position: int) -> None:
        normalized = require_file_position(file_type, position)
        self._session.write(f":MEMory:DELete {file_type.value},{normalized}")

    # 把指定 RSF/RTF 文件载入仪器当前状态；只发送一次载入命令，不做后续状态确认。
    def load(self, file_type: Dp711FileType, position: int) -> None:
        normalized = require_file_position(file_type, position)
        self._session.write(f":MEMory:LOAD {file_type.value},{normalized}")

    # 设置指定 RSF/RTF 文件锁定状态；只修改该配置项，不执行额外仪器动作。
    def locked_set(self, file_type: Dp711FileType, position: int, locked: bool) -> None:
        normalized = require_file_position(file_type, position)
        state = "ON" if locked else "OFF"
        self._session.write(f":MEMory:LOCK {file_type.value},{normalized},{state}")

    # 查询指定 RSF/RTF 文件是否锁定；查询或解析过程不会修改仪器配置。
    def locked_get(self, file_type: Dp711FileType, position: int) -> bool:
        normalized = require_file_position(file_type, position)
        response = self._session.query_text(f":MEMory:LOCK? {file_type.value},{normalized}")
        return parse_yes_no(response)

    # 把当前仪器状态或 Timer 参数保存到指定 RSF/RTF 位置。
    def store(self, file_type: Dp711FileType, position: int) -> None:
        normalized = require_file_position(file_type, position)
        self._session.write(f":MEMory:STORe {file_type.value},{normalized}")

    # 查询指定 RSF/RTF 位置是否存在有效文件。
    def valid_get(self, file_type: Dp711FileType, position: int) -> bool:
        normalized = require_file_position(file_type, position)
        response = self._session.query_text(f":MEMory:VALid? {file_type.value},{normalized}")
        return parse_yes_no(response)
