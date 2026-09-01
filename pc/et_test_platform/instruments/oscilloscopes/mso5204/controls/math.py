# RIGOL MSO5204 数学运算与 FFT/Filter 原子控制。
#
# 职责：完整映射 MATH<n> 命令组的算术、逻辑、函数、FFT、滤波和门限参数。
# 边界：每个公开 API 只发送一条 SCPI；不自动打开 MATH、不选择通道，也不解释结果为测试判定。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 参数格式化/响应解析辅助函数。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 MATH1..MATH4 全部公开稳定语义的一条命令对应一个 API 的控制接口。
class Mso5204MathControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _header(self, math: int, suffix: str) -> str:
        number = int(math)
        if number not in {1, 2, 3, 4}:
            raise ValueError("MATH channel must be 1..4")
        return f":MATH{number}:{suffix}"

    # 设置Math 波形显示开关；只修改指定 MATH 通道的 DISPlay 参数，不联动其他设置。
    def display_set(self, math: int, enabled: bool) -> None:
        self._session.write(_command(self._header(math, "DISPlay"), enabled))

    # 查询Math 波形显示开关；只读取指定 MATH 通道当前 DISPlay 参数。
    def display_get(self, math: int) -> bool:
        return _parse_bool(self._session.query_text(self._header(math, "DISPlay") + "?"))

    # 设置数学运算符；只修改指定 MATH 通道的 OPERator 参数，不联动其他设置。
    def operator_set(self, math: int, operator: str) -> None:
        self._session.write(_command(self._header(math, "OPERator"), operator))

    # 查询数学运算符；只读取指定 MATH 通道当前 OPERator 参数。
    def operator_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "OPERator") + "?")

    # 设置算术/函数/滤波 Source A；只修改指定 MATH 通道的 SOURce1 参数，不联动其他设置。
    def source_a_set(self, math: int, source: str) -> None:
        self._session.write(_command(self._header(math, "SOURce1"), source))

    # 查询算术/函数/滤波 Source A；只读取指定 MATH 通道当前 SOURce1 参数。
    def source_a_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "SOURce1") + "?")

    # 设置算术运算 Source B；只修改指定 MATH 通道的 SOURce2 参数，不联动其他设置。
    def source_b_set(self, math: int, source: str) -> None:
        self._session.write(_command(self._header(math, "SOURce2"), source))

    # 查询算术运算 Source B；只读取指定 MATH 通道当前 SOURce2 参数。
    def source_b_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "SOURce2") + "?")

    # 设置逻辑运算 Source A；只修改指定 MATH 通道的 LSOUrce1 参数，不联动其他设置。
    def logic_source_a_set(self, math: int, source: str) -> None:
        self._session.write(_command(self._header(math, "LSOUrce1"), source))

    # 查询逻辑运算 Source A；只读取指定 MATH 通道当前 LSOUrce1 参数。
    def logic_source_a_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "LSOUrce1") + "?")

    # 设置逻辑运算 Source B；只修改指定 MATH 通道的 LSOUrce2 参数，不联动其他设置。
    def logic_source_b_set(self, math: int, source: str) -> None:
        self._session.write(_command(self._header(math, "LSOUrce2"), source))

    # 查询逻辑运算 Source B；只读取指定 MATH 通道当前 LSOUrce2 参数。
    def logic_source_b_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "LSOUrce2") + "?")

    # 设置Math 垂直刻度；只修改指定 MATH 通道的 SCALe 参数，不联动其他设置。
    def scale_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "SCALe"), value))

    # 查询Math 垂直刻度；只读取指定 MATH 通道当前 SCALe 参数。
    def scale_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "SCALe") + "?"))

    # 设置Math 垂直偏置；只修改指定 MATH 通道的 OFFSet 参数，不联动其他设置。
    def offset_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "OFFSet"), value))

    # 查询Math 垂直偏置；只读取指定 MATH 通道当前 OFFSet 参数。
    def offset_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "OFFSet") + "?"))

    # 设置Math 反相显示；只修改指定 MATH 通道的 INVert 参数，不联动其他设置。
    def invert_set(self, math: int, enabled: bool) -> None:
        self._session.write(_command(self._header(math, "INVert"), enabled))

    # 查询Math 反相显示；只读取指定 MATH 通道当前 INVert 参数。
    def invert_get(self, math: int) -> bool:
        return _parse_bool(self._session.query_text(self._header(math, "INVert") + "?"))

    # 将指定 MATH 通道的运算结果刻度自动调整到合适范围；只发送一次 MATH<n>:RESet。
    def reset(self, math: int) -> None:
        self._session.write(self._header(math, "RESet"))

    # 设置FFT 来源；只修改指定 MATH 通道的 FFT:SOURce 参数，不联动其他配置。
    def fft_source_set(self, math: int, source: str) -> None:
        self._session.write(_command(self._header(math, "FFT:SOURce"), source))

    # 查询FFT 来源；只读取指定 MATH 通道当前 FFT:SOURce 参数。
    def fft_source_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "FFT:SOURce") + "?")

    # 设置FFT 窗函数；只修改指定 MATH 通道的 FFT:WINDow 参数，不联动其他配置。
    def fft_window_set(self, math: int, window: str) -> None:
        self._session.write(_command(self._header(math, "FFT:WINDow"), window))

    # 查询FFT 窗函数；只读取指定 MATH 通道当前 FFT:WINDow 参数。
    def fft_window_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "FFT:WINDow") + "?")

    # 设置FFT 幅值单位；只修改指定 MATH 通道的 FFT:UNIT 参数，不联动其他配置。
    def fft_unit_set(self, math: int, unit: str) -> None:
        self._session.write(_command(self._header(math, "FFT:UNIT"), unit))

    # 查询FFT 幅值单位；只读取指定 MATH 通道当前 FFT:UNIT 参数。
    def fft_unit_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "FFT:UNIT") + "?")

    # 设置FFT 垂直刻度；只修改指定 MATH 通道的 FFT:SCALe 参数，不联动其他配置。
    def fft_scale_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:SCALe"), value))

    # 查询FFT 垂直刻度；只读取指定 MATH 通道当前 FFT:SCALe 参数。
    def fft_scale_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FFT:SCALe") + "?"))

    # 设置FFT 垂直偏置；只修改指定 MATH 通道的 FFT:OFFSet 参数，不联动其他配置。
    def fft_offset_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:OFFSet"), value))

    # 查询FFT 垂直偏置；只读取指定 MATH 通道当前 FFT:OFFSet 参数。
    def fft_offset_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FFT:OFFSet") + "?"))

    # 设置FFT 水平频率刻度；只修改指定 MATH 通道的 FFT:HSCale 参数，不联动其他配置。
    def fft_horizontal_scale_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:HSCale"), value))

    # 查询FFT 水平频率刻度；只读取指定 MATH 通道当前 FFT:HSCale 参数。
    def fft_horizontal_scale_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FFT:HSCale") + "?"))

    # 设置FFT 中心频率；只修改指定 MATH 通道的 FFT:HCENter 参数，不联动其他配置。
    def fft_horizontal_center_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:HCENter"), value))

    # 查询FFT 中心频率；只读取指定 MATH 通道当前 FFT:HCENter 参数。
    def fft_horizontal_center_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FFT:HCENter") + "?"))

    # 设置FFT 起始频率；只修改指定 MATH 通道的 FFT:FREQuency:STARt 参数，不联动其他配置。
    def fft_frequency_start_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:FREQuency:STARt"), value))

    # 查询FFT 起始频率；只读取指定 MATH 通道当前 FFT:FREQuency:STARt 参数。
    def fft_frequency_start_get(self, math: int) -> float:
        return _parse_float(
            self._session.query_text(self._header(math, "FFT:FREQuency:STARt") + "?")
        )

    # 设置FFT 终止频率；只修改指定 MATH 通道的 FFT:FREQuency:END 参数，不联动其他配置。
    def fft_frequency_end_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:FREQuency:END"), value))

    # 查询FFT 终止频率；只读取指定 MATH 通道当前 FFT:FREQuency:END 参数。
    def fft_frequency_end_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FFT:FREQuency:END") + "?"))

    # 设置FFT Peak Search 开关；只修改指定 MATH 通道的 FFT:SEARch:ENABle 参数，不联动其他配置。
    def fft_search_enabled_set(self, math: int, enabled: bool) -> None:
        self._session.write(_command(self._header(math, "FFT:SEARch:ENABle"), enabled))

    # 查询FFT Peak Search 开关；只读取指定 MATH 通道当前 FFT:SEARch:ENABle 参数。
    def fft_search_enabled_get(self, math: int) -> bool:
        return _parse_bool(self._session.query_text(self._header(math, "FFT:SEARch:ENABle") + "?"))

    # 设置FFT Peak Search 峰值数量；只修改指定 MATH 通道的 FFT:SEARch:NUM 参数，不联动其他配置。
    def fft_search_count_set(self, math: int, count: int) -> None:
        value = int(count)
        if not 1 <= value <= 15:
            raise ValueError("FFT search count must be 1..15")
        self._session.write(_command(self._header(math, "FFT:SEARch:NUM"), value))

    # 查询FFT Peak Search 峰值数量；只读取指定 MATH 通道当前 FFT:SEARch:NUM 参数。
    def fft_search_count_get(self, math: int) -> int:
        return _parse_int(self._session.query_text(self._header(math, "FFT:SEARch:NUM") + "?"))

    # 设置FFT Peak Search 门限；只修改指定 MATH 通道的 FFT:SEARch:THReshold 参数，不联动其他配置。
    def fft_search_threshold_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:SEARch:THReshold"), value))

    # 查询FFT Peak Search 门限；只读取指定 MATH 通道当前 FFT:SEARch:THReshold 参数。
    def fft_search_threshold_get(self, math: int) -> float:
        return _parse_float(
            self._session.query_text(self._header(math, "FFT:SEARch:THReshold") + "?")
        )

    # 设置FFT Peak Search 峰值偏移；只修改指定 MATH 通道的 FFT:SEARch:EXCursion 参数，不联动其他配置。
    def fft_search_excursion_set(self, math: int, value: float) -> None:
        self._session.write(_command(self._header(math, "FFT:SEARch:EXCursion"), value))

    # 查询FFT Peak Search 峰值偏移；只读取指定 MATH 通道当前 FFT:SEARch:EXCursion 参数。
    def fft_search_excursion_get(self, math: int) -> float:
        return _parse_float(
            self._session.query_text(self._header(math, "FFT:SEARch:EXCursion") + "?")
        )

    # 设置FFT Peak Search 排序方式；只修改指定 MATH 通道的 FFT:SEARch:ORDer 参数，不联动其他配置。
    def fft_search_order_set(self, math: int, order: str) -> None:
        self._session.write(_command(self._header(math, "FFT:SEARch:ORDer"), order))

    # 查询FFT Peak Search 排序方式；只读取指定 MATH 通道当前 FFT:SEARch:ORDer 参数。
    def fft_search_order_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "FFT:SEARch:ORDer") + "?")

    # 设置数字滤波器类型；只修改指定 MATH 通道的 FILTer:TYPE 参数，不联动其他配置。
    def filter_type_set(self, math: int, filter_type: str) -> None:
        self._session.write(_command(self._header(math, "FILTer:TYPE"), filter_type))

    # 查询数字滤波器类型；只读取指定 MATH 通道当前 FILTer:TYPE 参数。
    def filter_type_get(self, math: int) -> str:
        return self._session.query_text(self._header(math, "FILTer:TYPE") + "?")

    # 设置数字滤波截止频率 W1；只修改指定 MATH 通道的 FILTer:W1 参数，不联动其他配置。
    def filter_frequency_1_set(self, math: int, frequency_hz: float) -> None:
        self._session.write(_command(self._header(math, "FILTer:W1"), frequency_hz))

    # 查询数字滤波截止频率 W1；只读取指定 MATH 通道当前 FILTer:W1 参数。
    def filter_frequency_1_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FILTer:W1") + "?"))

    # 设置数字滤波截止频率 W2；只修改指定 MATH 通道的 FILTer:W2 参数，不联动其他配置。
    def filter_frequency_2_set(self, math: int, frequency_hz: float) -> None:
        self._session.write(_command(self._header(math, "FILTer:W2"), frequency_hz))

    # 查询数字滤波截止频率 W2；只读取指定 MATH 通道当前 FILTer:W2 参数。
    def filter_frequency_2_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "FILTer:W2") + "?"))

    # 设置逻辑运算灵敏度；只修改指定 MATH 通道的 SENSitivity 参数，不联动其他配置。
    def sensitivity_set(self, math: int, divisions: float) -> None:
        value = float(divisions)
        if not 0.1 <= value <= 1.0:
            raise ValueError("MATH sensitivity must be 0.1..1 div")
        self._session.write(_command(self._header(math, "SENSitivity"), value))

    # 查询逻辑运算灵敏度；只读取指定 MATH 通道当前 SENSitivity 参数。
    def sensitivity_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "SENSitivity") + "?"))

    # 设置微分运算平滑窗口宽度；只修改指定 MATH 通道的 DISTance 参数，不联动其他配置。
    def distance_set(self, math: int, points: int) -> None:
        value = int(points)
        if not 5 <= value <= 10000:
            raise ValueError("MATH distance must be 5..10000")
        self._session.write(_command(self._header(math, "DISTance"), value))

    # 查询微分运算平滑窗口宽度；只读取指定 MATH 通道当前 DISTance 参数。
    def distance_get(self, math: int) -> int:
        return _parse_int(self._session.query_text(self._header(math, "DISTance") + "?"))

    # 设置逻辑运算 CH1 门限；只修改指定 MATH 通道的 THReshold1 参数，不联动其他配置。
    def threshold_1_set(self, math: int, voltage_v: float) -> None:
        self._session.write(_command(self._header(math, "THReshold1"), voltage_v))

    # 查询逻辑运算 CH1 门限；只读取指定 MATH 通道当前 THReshold1 参数。
    def threshold_1_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "THReshold1") + "?"))

    # 设置逻辑运算 CH2 门限；只修改指定 MATH 通道的 THReshold2 参数，不联动其他配置。
    def threshold_2_set(self, math: int, voltage_v: float) -> None:
        self._session.write(_command(self._header(math, "THReshold2"), voltage_v))

    # 查询逻辑运算 CH2 门限；只读取指定 MATH 通道当前 THReshold2 参数。
    def threshold_2_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "THReshold2") + "?"))

    # 设置逻辑运算 CH3 门限；只修改指定 MATH 通道的 THReshold3 参数，不联动其他配置。
    def threshold_3_set(self, math: int, voltage_v: float) -> None:
        self._session.write(_command(self._header(math, "THReshold3"), voltage_v))

    # 查询逻辑运算 CH3 门限；只读取指定 MATH 通道当前 THReshold3 参数。
    def threshold_3_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "THReshold3") + "?"))

    # 设置逻辑运算 CH4 门限；只修改指定 MATH 通道的 THReshold4 参数，不联动其他配置。
    def threshold_4_set(self, math: int, voltage_v: float) -> None:
        self._session.write(_command(self._header(math, "THReshold4"), voltage_v))

    # 查询逻辑运算 CH4 门限；只读取指定 MATH 通道当前 THReshold4 参数。
    def threshold_4_get(self, math: int) -> float:
        return _parse_float(self._session.query_text(self._header(math, "THReshold4") + "?"))
