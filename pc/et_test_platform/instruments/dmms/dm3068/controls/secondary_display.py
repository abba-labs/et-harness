# RIGOL DM3068 双显示 FUNCtion2 原子控制。
#
# 职责：映射 DM3068 原生 FUNCtion2 帮助页明确列出的双显示查询和控制命令。
# 边界：不扩展 Agilent 兼容命令、不自动配置主显示，也不执行测试判定。
# 依赖：仅依赖公共 ScpiSession 和基础响应解析。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import _parse_bool, _parse_float


# 提供 DM3068 原生 FUNCtion2 双显示能力的单命令访问接口。
class Dm3068SecondaryDisplayControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询当前副显示功能；只执行 FUNCtion2? Query，不改变主副显示配置。
    def function_get(self) -> str:
        return self._session.query_text(":FUNCtion2?").strip()

    # 清除当前副显示功能；只发送 FUNCtion2:CLEar，不改变主显示测量功能。
    def clear(self) -> None:
        self._session.write(":FUNCtion2:CLEar")

    # 选择副显示频率功能；只发送 FUNCtion2:FREQuency，不追加其他配置。
    def frequency_select(self) -> None:
        self._session.write(":FUNCtion2:FREQuency")

    # 查询副显示是否开启；只读取 FUNCtion2:ON? 当前状态。
    def enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":FUNCtion2:ON?"))

    # 查询双显示第一个数值；只读取 FUNCtion2:VALUe1? 返回值。
    def value1_get(self) -> float:
        return _parse_float(self._session.query_text(":FUNCtion2:VALUe1?"))

    # 查询双显示第二个数值；只读取 FUNCtion2:VALUe2? 返回值。
    def value2_get(self) -> float:
        return _parse_float(self._session.query_text(":FUNCtion2:VALUe2?"))
