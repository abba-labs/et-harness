# RIGOL MSO5204 内置频率计原子控制。
#
# 职责：完整映射 COUNter 命令组中的当前值、开关、来源、模式、分辨率和累计计数控制。
# 边界：不自动选择触发源或量程，也不解释频率计结果是否满足测试规范。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 MSO5000 内置频率计全部公开命令的稳定原子接口。
class Mso5204CounterControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询频率计当前测量值；只执行一次 COUNter:CURRent? Query。
    def current_get(self) -> float:
        return _parse_float(self._session.query_text(":COUNter:CURRent?"))

    # 打开或关闭频率计；只发送一次 COUNter:ENABle 命令。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":COUNter:ENABle", enabled))

    # 查询频率计开关；只执行一次 COUNter:ENABle? Query。
    def enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":COUNter:ENABle?"))

    # 设置频率计来源；参数接受 D0..D15 或 CHANnel1..4 等手册值。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":COUNter:SOURce", source))

    # 查询频率计来源；保留仪器返回的 D0..D15 或 CHAN1..CHAN4 字符串。
    def source_get(self) -> str:
        return self._session.query_text(":COUNter:SOURce?")

    # 设置频率计模式；参数接受 FREQuency、PERiod 或 TOTalize。
    def mode_set(self, mode: str) -> None:
        self._session.write(_command(":COUNter:MODE", mode))

    # 查询频率计模式；保留仪器返回的 FREQ、PER 或 TOT 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":COUNter:MODE?")

    # 设置频率/周期显示分辨率位数；手册范围为 3..6。
    def digits_set(self, digits: int) -> None:
        value = int(digits)
        if not 3 <= value <= 6:
            raise ValueError("counter digits must be 3..6")
        self._session.write(_command(":COUNter:NDIGits", value))

    # 查询频率计显示分辨率位数；返回 3..6 的整数。
    def digits_get(self) -> int:
        return _parse_int(self._session.query_text(":COUNter:NDIGits?"))

    # 打开或关闭频率/周期统计功能；只发送一次 COUNter:TOTalize:ENABle 命令。
    def statistics_enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":COUNter:TOTalize:ENABle", enabled))

    # 查询频率计统计功能开关；只执行一次 COUNter:TOTalize:ENABle? Query。
    def statistics_enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":COUNter:TOTalize:ENABle?"))

    # 清除累计计数；只发送一次 COUNter:TOTalize:CLEar 命令。
    def totalize_clear(self) -> None:
        self._session.write(":COUNter:TOTalize:CLEar")
