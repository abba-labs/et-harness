# RIGOL MSO5204 波形传输原子控制。
#
# 职责：完整映射 WAVeform 命令组，支持波形来源/模式/格式/范围配置、二进制数据块读取和前导参数解析。
# 边界：不自动 STOP 仪器、不分批读取深存储，也不把 ADC 码转换成最终测试判定。
# 依赖：仅依赖公共 ScpiSession、波形模型和基础 SCPI 格式化/解析/校验辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..models import Mso5204WaveformFormat, Mso5204WaveformMode, Mso5204WaveformPreamble
from ..validation import (
    _command,
    _parse_float,
    _parse_int,
    _parse_preamble,
    _validate_int_range,
    _validate_measurement_source,
    _validate_scpi_token,
)

_MAX_MEMORY_POINTS = 200_000_000


# 提供 MSO5000 Programming Guide 全部 WAVeform 原子命令的稳定访问接口。
class Mso5204WaveformControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置波形读取来源；只接受 D0..D15、CHANnel1..4 或 MATH1..4 手册源。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":WAVeform:SOURce", _validate_measurement_source(source)))

    # 查询波形读取来源；保留仪器返回的 CHAN1、D0 或 MATH1 等字符串。
    def source_get(self) -> str:
        return self._session.query_text(":WAVeform:SOURce?")

    # 设置波形读取模式；只接受 NORMal、MAXimum 或 RAW，不自动改变采集运行状态。
    def mode_set(self, mode: Mso5204WaveformMode | str) -> None:
        normalized = _validate_scpi_token(
            mode,
            tuple(item.value for item in Mso5204WaveformMode),
            "waveform mode",
        )
        self._session.write(_command(":WAVeform:MODE", normalized))

    # 查询波形读取模式；保留仪器返回的 NORM、MAX 或 RAW 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":WAVeform:MODE?")

    # 设置波形返回格式；只接受 BYTE、WORD 或 ASCii，不改变读取点数。
    def format_set(self, data_format: Mso5204WaveformFormat | str) -> None:
        normalized = _validate_scpi_token(
            data_format,
            tuple(item.value for item in Mso5204WaveformFormat),
            "waveform format",
        )
        self._session.write(_command(":WAVeform:FORMat", normalized))

    # 查询波形返回格式；保留仪器返回的 WORD、BYTE 或 ASC 字符串。
    def format_get(self) -> str:
        return self._session.query_text(":WAVeform:FORMat?")

    # 设置本次读取的波形点数；原子层按设备 200 M 最大深度限制，模式特定边界由 Operation 再收紧。
    def points_set(self, points: int) -> None:
        number = _validate_int_range(points, "waveform points", 1, _MAX_MEMORY_POINTS)
        self._session.write(_command(":WAVeform:POINts", number))

    # 查询波形读取点数；只执行一次 WAVeform:POINts? Query，不改变波形来源、格式或读取范围。
    def points_get(self) -> int:
        return _parse_int(self._session.query_text(":WAVeform:POINts?"))

    # 读取当前格式下的波形数据负载；BYTE/WORD 已由 ScpiSession 去除 IEEE488.2 数据块头。
    def data_get(self, *, timeout_s: float | None = None) -> bytes:
        return self._session.query_bytes(":WAVeform:DATA?", timeout_s=timeout_s)

    # 查询相邻波形点的 X 方向时间间隔；返回当前源单位对应的浮点值。
    def x_increment_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:XINCrement?"))

    # 查询当前波形数据的 X 方向起始时间；返回浮点值。
    def x_origin_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:XORigin?"))

    # 查询波形数据的 X 参考位置；MSO5000 手册当前定义返回 0。
    def x_reference_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:XREFerence?"))

    # 查询 Y 方向一个 ADC 码对应的幅值增量；返回当前源幅值单位下的浮点值。
    def y_increment_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:YINCrement?"))

    # 查询 Y 方向原点参数；返回用于波形码值换算的浮点值。
    def y_origin_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:YORigin?"))

    # 查询 Y 方向参考位置；返回用于波形码值换算的浮点值。
    def y_reference_get(self) -> float:
        return _parse_float(self._session.query_text(":WAVeform:YREFerence?"))

    # 设置波形读取起始点；原子层按设备 200 M 最大深度限制，模式特定边界由 Operation 再收紧。
    def start_set(self, point: int) -> None:
        number = _validate_int_range(point, "waveform start point", 1, _MAX_MEMORY_POINTS)
        self._session.write(_command(":WAVeform:STARt", number))

    # 查询波形读取起始点；返回从 1 开始的整数位置。
    def start_get(self) -> int:
        return _parse_int(self._session.query_text(":WAVeform:STARt?"))

    # 设置波形读取结束点；原子层按设备 200 M 最大深度限制，模式特定边界由 Operation 再收紧。
    def stop_set(self, point: int) -> None:
        number = _validate_int_range(point, "waveform stop point", 1, _MAX_MEMORY_POINTS)
        self._session.write(_command(":WAVeform:STOP", number))

    # 查询波形读取结束点；返回从 1 开始的整数位置。
    def stop_get(self) -> int:
        return _parse_int(self._session.query_text(":WAVeform:STOP?"))

    # 一次查询并解析全部十项波形前导参数，供后续物理量换算使用。
    def preamble_get(self) -> Mso5204WaveformPreamble:
        return _parse_preamble(self._session.query_text(":WAVeform:PREamble?"))
