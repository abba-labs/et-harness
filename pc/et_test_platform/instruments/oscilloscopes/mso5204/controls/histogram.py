# RIGOL MSO5204 直方图分析原子控制。
#
# 职责：完整映射 HISTogram 命令组的显示、类型、来源、尺寸、统计和边界参数。
# 边界：每个公开 API 只发送一条 SCPI；不自动启用来源通道，也不解释统计结果为 PASS/FAIL。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 参数格式化/响应解析辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 HISTogram 全部公开设置与查询的一条命令对应一个 API 的控制接口。
class Mso5204HistogramControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭 Histogram 功能；只修改直方图显示总开关。
    def display_set(self, enabled: bool) -> None:
        self._session.write(_command(":HISTogram:DISPlay", enabled))

    # 查询 Histogram 功能开关；只读取当前显示状态，不修改来源。
    def display_get(self) -> bool:
        return _parse_bool(self._session.query_text(":HISTogram:DISPlay?"))

    # 设置 Histogram 类型；接受 HORizontal、VERTical 或 MEAS。
    def type_set(self, histogram_type: str) -> None:
        self._session.write(_command(":HISTogram:TYPE", histogram_type))

    # 查询 Histogram 类型；保留仪器返回的 HOR、VERT 或 MEAS 字符串。
    def type_get(self) -> str:
        return self._session.query_text(":HISTogram:TYPE?")

    # 设置 Histogram 来源；接受 CHANnel1..4 或 OFF，不自动打开通道。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":HISTogram:SOURce", source))

    # 查询 Histogram 来源；保留仪器返回的 CHAN1..CHAN4 或 OFF。
    def source_get(self) -> str:
        return self._session.query_text(":HISTogram:SOURce?")

    # 设置 Histogram 显示高度；手册有效范围为 1..4。
    def size_set(self, size: int) -> None:
        number = int(size)
        if not 1 <= number <= 4:
            raise ValueError("histogram size must be 1..4")
        self._session.write(_command(":HISTogram:SIZE", number))

    # 查询 Histogram 显示高度；返回 1..4 的整数档位。
    def size_get(self) -> int:
        return _parse_int(self._session.query_text(":HISTogram:SIZE?"))

    # 打开或关闭 Histogram 统计功能；只修改 STATic 开关。
    def statistics_set(self, enabled: bool) -> None:
        self._session.write(_command(":HISTogram:STATic", enabled))

    # 查询 Histogram 统计功能开关；只读取当前统计状态。
    def statistics_get(self) -> bool:
        return _parse_bool(self._session.query_text(":HISTogram:STATic?"))

    # 重置 Histogram 统计结果；只发送一次 HISTogram:RESet 动作。
    def reset(self) -> None:
        self._session.write(":HISTogram:RESet")

    # 设置 Histogram 底边界；可用范围依赖当前通道 Scale 与 Offset。
    def bottom_limit_set(self, value: float) -> None:
        self._session.write(_command(":HISTogram:BLIMit", value))

    # 查询 Histogram 底边界；返回当前来源幅值单位下的浮点值。
    def bottom_limit_get(self) -> float:
        return _parse_float(self._session.query_text(":HISTogram:BLIMit?"))

    # 设置 Histogram 左边界；可用范围依赖当前 Timebase Scale 与 Offset。
    def left_limit_set(self, value: float) -> None:
        self._session.write(_command(":HISTogram:LLIMit", value))

    # 查询 Histogram 左边界；返回当前水平单位下的浮点值。
    def left_limit_get(self) -> float:
        return _parse_float(self._session.query_text(":HISTogram:LLIMit?"))

    # 设置 Histogram 右边界；可用范围依赖当前 Timebase Scale 与 Offset。
    def right_limit_set(self, value: float) -> None:
        self._session.write(_command(":HISTogram:RLIMit", value))

    # 查询 Histogram 右边界；返回当前水平单位下的浮点值。
    def right_limit_get(self) -> float:
        return _parse_float(self._session.query_text(":HISTogram:RLIMit?"))

    # 设置 Histogram 顶边界；可用范围依赖当前通道 Scale 与 Offset。
    def top_limit_set(self, value: float) -> None:
        self._session.write(_command(":HISTogram:TLIMit", value))

    # 查询 Histogram 顶边界；返回当前来源幅值单位下的浮点值。
    def top_limit_get(self) -> float:
        return _parse_float(self._session.query_text(":HISTogram:TLIMit?"))
