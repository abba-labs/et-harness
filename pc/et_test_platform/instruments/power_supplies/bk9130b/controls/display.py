# B&K Precision 9130B 显示控制。
#
# 职责：映射显示开关、文本写入、文本查询和文本清除等单条显示命令。
# 边界：不修改电源输出、不执行组合显示流程，也不解释前面板渲染结果。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import format_bool, format_display_text, parse_bool


# 提供 9130B 显示单命令控制；每个 API 最多发送一条 SCPI 命令。
class Bk9130bDisplayControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭前面板显示；只修改显示状态，不影响输出配置。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(f"DISPlay:WINDow:STATe {format_bool(enabled)}")

    # 查询前面板显示开关状态；查询过程不会修改显示内容。
    def enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("DISPlay:WINDow:STATe?"))

    # 在前面板显示一行 ASCII 文本；只修改显示文本，不改变输出。
    def text_set(self, text: str) -> None:
        self._session.write(f'DISPlay:WINDow:TEXT:DATA "{format_display_text(text)}"')

    # 查询当前用户显示文本；查询过程不会清除或修改显示内容。
    def text_get(self) -> str:
        return self._session.query_text("DISPlay:WINDow:TEXT:DATA?").strip('"')

    # 清除用户显示文本并恢复正常显示；只发送一次 TEXT:CLEar。
    def text_clear(self) -> None:
        self._session.write("DISPlay:WINDow:TEXT:CLEar")
