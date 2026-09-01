# RIGOL MSO5204 Pass/Fail Mask 原子控制。
#
# 职责：完整映射 MASK 命令组的总开关、来源、运行状态、Mask 调节、统计查询和重置动作。
# 边界：每个公开 API 只发送一条 SCPI；不自动创建 Mask、不改变来源通道，也不判定测试结果。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 参数格式化/响应解析辅助函数。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 MASK 全部公开稳定语义的一条命令对应一个 API 的控制接口。
class Mso5204MaskControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭 Pass/Fail Test 功能；只修改 MASK 总开关。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":MASK:ENABle", enabled))

    # 查询 Pass/Fail Test 功能开关；只读取当前状态，不修改运行状态。
    def enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":MASK:ENABle?"))

    # 设置 Pass/Fail Test 测量来源；接受 CHANnel1..4，不自动启用通道。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":MASK:SOURce", source))

    # 查询 Pass/Fail Test 测量来源；保留仪器返回的 CHAN1..CHAN4。
    def source_get(self) -> str:
        return self._session.query_text(":MASK:SOURce?")

    # 设置 Pass/Fail Test 为 RUN 或 STOP；只改变当前运行状态。
    def operate_set(self, operation: str) -> None:
        self._session.write(_command(":MASK:OPERate", operation))

    # 查询 Pass/Fail Test 当前运行状态；保留仪器返回的 RUN 或 STOP。
    def operate_get(self) -> str:
        return self._session.query_text(":MASK:OPERate?")

    # 打开或关闭 Pass/Fail 统计显示；只修改 MDISplay 开关。
    def statistics_display_set(self, enabled: bool) -> None:
        self._session.write(_command(":MASK:MDISplay", enabled))

    # 查询 Pass/Fail 统计显示开关；只读取当前状态。
    def statistics_display_get(self) -> bool:
        return _parse_bool(self._session.query_text(":MASK:MDISplay?"))

    # 设置 Mask 水平调节量，单位 div；手册有效范围为 0.01..2 div。
    def x_adjust_set(self, divisions: float) -> None:
        value = float(divisions)
        if not 0.01 <= value <= 2.0:
            raise ValueError("MASK X adjustment must be 0.01..2 div")
        self._session.write(_command(":MASK:X", value))

    # 查询 Mask 水平调节量；返回以 div 为单位的浮点值。
    def x_adjust_get(self) -> float:
        return _parse_float(self._session.query_text(":MASK:X?"))

    # 设置 Mask 垂直调节量，单位 div；手册有效范围为 0.04..2 div。
    def y_adjust_set(self, divisions: float) -> None:
        value = float(divisions)
        if not 0.04 <= value <= 2.0:
            raise ValueError("MASK Y adjustment must be 0.04..2 div")
        self._session.write(_command(":MASK:Y", value))

    # 查询 Mask 垂直调节量；返回以 div 为单位的浮点值。
    def y_adjust_get(self) -> float:
        return _parse_float(self._session.query_text(":MASK:Y?"))

    # 按当前 X/Y 调节参数创建 Pass/Fail Mask；只发送一次 CREate 动作。
    def create(self) -> None:
        self._session.write(":MASK:CREate")

    # 查询累计通过帧数；只读取 PASSed? 计数，不重置统计值。
    def passed_count_get(self) -> int:
        return _parse_int(self._session.query_text(":MASK:PASSed?"))

    # 查询累计失败帧数；只读取 FAILed? 计数，不重置统计值。
    def failed_count_get(self) -> int:
        return _parse_int(self._session.query_text(":MASK:FAILed?"))

    # 查询 Pass/Fail Test 累计总帧数；只读取 TOTal? 计数。
    def total_count_get(self) -> int:
        return _parse_int(self._session.query_text(":MASK:TOTal?"))

    # 重置通过、失败和总帧数统计；只发送一次 MASK:RESet 动作。
    def reset(self) -> None:
        self._session.write(":MASK:RESet")
