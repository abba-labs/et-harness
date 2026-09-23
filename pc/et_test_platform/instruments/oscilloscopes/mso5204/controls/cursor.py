# RIGOL MSO5204 游标测量原子控制。
#
# 职责：完整映射 CURSor 命令组中的 Measure、Manual、Track 和 XY 游标设置与查询。
# 边界：每个公开 API 只发送一条 SCPI；不切换时基、不自动选择信号源，也不执行测试判定。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 参数格式化/响应解析辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 CURSor 全部公开稳定语义的一条命令对应一个 API 的控制接口。
class Mso5204CursorControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _pixel(self, value: int, maximum: int, name: str) -> int:
        number = int(value)
        if not 0 <= number <= maximum:
            raise ValueError(f"{name} must be 0..{maximum}")
        return number

    # 打开或关闭 Measure 模式自动游标指示；只修改 MEASure:INDicator 开关。
    def measure_indicator_set(self, enabled: bool) -> None:
        self._session.write(_command(":CURSor:MEASure:INDicator", enabled))

    # 查询 Measure 模式自动游标指示开关；只读取当前状态，不改变游标模式。
    def measure_indicator_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CURSor:MEASure:INDicator?"))

    # 设置游标总模式；接受 OFF、MANual、TRACk、XY 或 MEASure 等手册值。
    def mode_set(self, mode: str) -> None:
        self._session.write(_command(":CURSor:MODE", mode))

    # 查询当前游标总模式；保留仪器返回的 OFF、MAN、TRAC、XY 或 MEAS 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":CURSor:MODE?")

    # 设置 Manual 游标类型为 TIME 或 AMPLitude；只改变该模式下游标类型。
    def manual_type_set(self, cursor_type: str) -> None:
        self._session.write(_command(":CURSor:MANual:TYPE", cursor_type))

    # 查询 Manual 游标类型；保留仪器返回的 TIME 或 AMPL 字符串。
    def manual_type_get(self) -> str:
        return self._session.query_text(":CURSor:MANual:TYPE?")

    # 设置 Manual 游标测量来源；接受模拟通道、MATH、LA 或 NONE 等手册值。
    def manual_source_set(self, source: str) -> None:
        self._session.write(_command(":CURSor:MANual:SOURce", source))

    # 查询 Manual 游标测量来源；只读取当前 source，不自动打开对应通道。
    def manual_source_get(self) -> str:
        return self._session.query_text(":CURSor:MANual:SOURce?")

    # 设置 Manual 水平结果单位；接受 SECond、HZ、DEGRee 或 PERCent。
    def manual_time_unit_set(self, unit: str) -> None:
        self._session.write(_command(":CURSor:MANual:TUNit", unit))

    # 查询 Manual 水平结果单位；保留仪器返回的 SEC、HZ、DEGR 或 PERC。
    def manual_time_unit_get(self) -> str:
        return self._session.query_text(":CURSor:MANual:TUNit?")

    # 设置 Manual 垂直结果单位；接受 SOURce 或 PERCent，不修改通道自身单位。
    def manual_vertical_unit_set(self, unit: str) -> None:
        self._session.write(_command(":CURSor:MANual:VUNit", unit))

    # 查询 Manual 垂直结果单位；保留仪器返回的 SOUR 或 PERC 字符串。
    def manual_vertical_unit_get(self) -> str:
        return self._session.query_text(":CURSor:MANual:VUNit?")

    # 设置 Manual Cursor A 水平像素位置；手册有效范围为 0..999。
    def manual_cursor_a_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:MANual:CAX", self._pixel(position, 999, "position")))

    # 查询 Manual Cursor A 水平像素位置；返回 0..999 的整数。
    def manual_cursor_a_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:MANual:CAX?"))

    # 设置 Manual Cursor B 水平像素位置；手册有效范围为 0..999。
    def manual_cursor_b_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:MANual:CBX", self._pixel(position, 999, "position")))

    # 查询 Manual Cursor B 水平像素位置；返回 0..999 的整数。
    def manual_cursor_b_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:MANual:CBX?"))

    # 设置 Manual Cursor A 垂直像素位置；手册有效范围为 0..479。
    def manual_cursor_a_y_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:MANual:CAY", self._pixel(position, 479, "position")))

    # 查询 Manual Cursor A 垂直像素位置；返回 0..479 的整数。
    def manual_cursor_a_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:MANual:CAY?"))

    # 设置 Manual Cursor B 垂直像素位置；手册有效范围为 0..479。
    def manual_cursor_b_y_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:MANual:CBY", self._pixel(position, 479, "position")))

    # 查询 Manual Cursor B 垂直像素位置；返回 0..479 的整数。
    def manual_cursor_b_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:MANual:CBY?"))

    # 查询 Manual Cursor A 的 X 物理量值；单位由当前水平单位配置决定。
    def manual_cursor_a_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:AXValue?"))

    # 查询 Manual Cursor A 的 Y 物理量值；LA 来源时仪器返回加权整数，也按数值返回。
    def manual_cursor_a_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:AYValue?"))

    # 查询 Manual Cursor B 的 X 物理量值；单位由当前水平单位配置决定。
    def manual_cursor_b_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:BXValue?"))

    # 查询 Manual Cursor B 的 Y 物理量值；LA 来源时仪器返回加权整数，也按数值返回。
    def manual_cursor_b_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:BYValue?"))

    # 查询 Manual 两个 X 游标的差值；单位由当前水平单位配置决定。
    def manual_x_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:XDELta?"))

    # 查询 Manual X 游标绝对差值的倒数；单位由当前水平单位配置决定。
    def manual_inverse_x_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:IXDelta?"))

    # 查询 Manual 两个 Y 游标的差值；单位由当前垂直单位配置决定。
    def manual_y_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:MANual:YDELta?"))

    # 设置 Track Cursor A 的信号源；只改变 Source1，不修改 Cursor B 来源。
    def track_source_a_set(self, source: str) -> None:
        self._session.write(_command(":CURSor:TRACk:SOURce1", source))

    # 查询 Track Cursor A 的信号源；保留 CHAN、MATH 或 NONE 原生字符串。
    def track_source_a_get(self) -> str:
        return self._session.query_text(":CURSor:TRACk:SOURce1?")

    # 设置 Track Cursor B 的信号源；只改变 Source2，不修改 Cursor A 来源。
    def track_source_b_set(self, source: str) -> None:
        self._session.write(_command(":CURSor:TRACk:SOURce2", source))

    # 查询 Track Cursor B 的信号源；保留 CHAN、MATH 或 NONE 原生字符串。
    def track_source_b_get(self) -> str:
        return self._session.query_text(":CURSor:TRACk:SOURce2?")

    # 设置 Track Cursor A 的水平像素位置；手册有效范围为 0..999。
    def track_cursor_a_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:TRACk:CAX", self._pixel(position, 999, "position")))

    # 查询 Track Cursor A 的水平像素位置；返回 0..999 的整数。
    def track_cursor_a_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:TRACk:CAX?"))

    # 设置 Track Cursor B 的水平像素位置；手册有效范围为 0..999。
    def track_cursor_b_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:TRACk:CBX", self._pixel(position, 999, "position")))

    # 查询 Track Cursor B 的水平像素位置；返回 0..999 的整数。
    def track_cursor_b_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:TRACk:CBX?"))

    # 查询 Track Cursor A 跟踪后的垂直像素位置；该值由波形和 CAX 共同决定。
    def track_cursor_a_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:TRACk:CAY?"))

    # 查询 Track Cursor B 跟踪后的垂直像素位置；该值由波形和 CBX 共同决定。
    def track_cursor_b_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:TRACk:CBY?"))

    # 查询 Track Cursor A 的 X 物理量值；单位由当前对应来源决定。
    def track_cursor_a_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:AXValue?"))

    # 查询 Track Cursor A 的 Y 物理量值；单位与当前对应来源的幅值单位一致。
    def track_cursor_a_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:AYValue?"))

    # 查询 Track Cursor B 的 X 物理量值；单位由当前对应来源决定。
    def track_cursor_b_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:BXValue?"))

    # 查询 Track Cursor B 的 Y 物理量值；单位与当前对应来源的幅值单位一致。
    def track_cursor_b_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:BYValue?"))

    # 查询 Track 两个 X 游标的差值；仪器按科学计数法返回当前值。
    def track_x_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:XDELta?"))

    # 查询 Track 两个 Y 游标的差值；单位与当前对应来源的幅值单位一致。
    def track_y_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:YDELta?"))

    # 查询 Track X 游标绝对差值的倒数；手册默认单位为 Hz。
    def track_inverse_x_delta_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:TRACk:IXDelta?"))

    # 设置 XY Cursor A 的水平像素位置；XY 区域横纵坐标有效范围均为 0..479。
    def xy_cursor_a_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:XY:AX", self._pixel(position, 479, "position")))

    # 查询 XY Cursor A 的水平像素位置；返回 0..479 的整数。
    def xy_cursor_a_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:XY:AX?"))

    # 设置 XY Cursor B 的水平像素位置；XY 区域横纵坐标有效范围均为 0..479。
    def xy_cursor_b_x_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:XY:BX", self._pixel(position, 479, "position")))

    # 查询 XY Cursor B 的水平像素位置；返回 0..479 的整数。
    def xy_cursor_b_x_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:XY:BX?"))

    # 设置 XY Cursor A 的垂直像素位置；XY 区域横纵坐标有效范围均为 0..479。
    def xy_cursor_a_y_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:XY:AY", self._pixel(position, 479, "position")))

    # 查询 XY Cursor A 的垂直像素位置；返回 0..479 的整数。
    def xy_cursor_a_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:XY:AY?"))

    # 设置 XY Cursor B 的垂直像素位置；XY 区域横纵坐标有效范围均为 0..479。
    def xy_cursor_b_y_set(self, position: int) -> None:
        self._session.write(_command(":CURSor:XY:BY", self._pixel(position, 479, "position")))

    # 查询 XY Cursor B 的垂直像素位置；返回 0..479 的整数。
    def xy_cursor_b_y_get(self) -> int:
        return _parse_int(self._session.query_text(":CURSor:XY:BY?"))

    # 查询 XY Cursor A 所在点的 X 物理量值；单位由对应 X 轴来源决定。
    def xy_cursor_a_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:XY:AXValue?"))

    # 查询 XY Cursor A 所在点的 Y 物理量值；单位由对应 Y 轴来源决定。
    def xy_cursor_a_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:XY:AYValue?"))

    # 查询 XY Cursor B 所在点的 X 物理量值；单位由对应 X 轴来源决定。
    def xy_cursor_b_x_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:XY:BXValue?"))

    # 查询 XY Cursor B 所在点的 Y 物理量值；单位由对应 Y 轴来源决定。
    def xy_cursor_b_y_value_get(self) -> float:
        return _parse_float(self._session.query_text(":CURSor:XY:BYValue?"))
