# RIGOL MSO5204 采集系统原子控制。
#
# 职责：映射 ACQuire 命令组中的平均次数、存储深度、采集类型、采样率和抗混叠控制。
# 边界：不自动停止采集、不根据通道数替调用方选择存储深度，也不执行测试判定。
# 依赖：仅依赖公共 ScpiSession、采集枚举和参数解析/校验辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..models import Mso5204AcquireType, Mso5204MemoryDepth
from ..validation import (
    _command,
    _normalize_memory_depth,
    _parse_bool,
    _parse_float,
    _parse_int,
    _query_command,
    _validate_average_count,
    _validate_scpi_token,
)


# 提供 MSO5000 采集系统手册命令的一条命令对应一个 API 的访问方式。
class Mso5204AcquireControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置平均采集次数；手册只允许 2^n，n=1..16，即 2..65536。
    def averages_set(self, count: int) -> None:
        self._session.write(_command(":ACQuire:AVERages", _validate_average_count(count)))

    # 查询平均采集次数；只执行一次 ACQuire:AVERages? Query。
    def averages_get(self) -> int:
        return _parse_int(self._session.query_text(":ACQuire:AVERages?"))

    # 设置采集存储深度；只接受手册 AUTO/1k..200M 离散值或对应整数点数。
    def memory_depth_set(self, depth: Mso5204MemoryDepth | str | int) -> None:
        self._session.write(_command(":ACQuire:MDEPth", _normalize_memory_depth(depth)))

    # 查询当前采集存储深度；返回仪器以科学计数法报告的点数。
    def memory_depth_get(self) -> float:
        return _parse_float(self._session.query_text(":ACQuire:MDEPth?"))

    # 设置采集模式；只发送一次 ACQuire:TYPE，不调整平均次数或其他参数。
    def type_set(self, acquire_type: Mso5204AcquireType | str) -> None:
        value = _validate_scpi_token(
            acquire_type,
            tuple(item.value for item in Mso5204AcquireType),
            "acquisition type",
        )
        self._session.write(_command(":ACQuire:TYPE", value))

    # 查询当前采集模式；保留仪器返回的原生字符串表示。
    def type_get(self) -> str:
        return self._session.query_text(":ACQuire:TYPE?")

    # 查询当前模拟采样率；只执行一次 ACQuire:SRATe? Query。
    def sample_rate_get(self) -> float:
        return _parse_float(self._session.query_text(":ACQuire:SRATe?"))

    # 查询逻辑分析仪当前采样率；只执行一次 ACQuire:LA:SRATe? Query。
    def logic_sample_rate_get(self) -> float:
        return _parse_float(self._session.query_text(":ACQuire:LA:SRATe?"))

    # 查询逻辑分析仪当前存储深度；只执行一次 ACQuire:LA:MDEPth? Query。
    def logic_memory_depth_get(self) -> float:
        return _parse_float(self._session.query_text(":ACQuire:LA:MDEPth?"))

    # 启用或关闭抗混叠功能；只发送一次 ACQuire:AALias 命令。
    def anti_alias_set(self, enabled: bool) -> None:
        self._session.write(_command(":ACQuire:AALias", enabled))

    # 查询抗混叠功能开关；只执行一次 ACQuire:AALias? Query。
    def anti_alias_get(self) -> bool:
        return _parse_bool(self._session.query_text(_query_command(":ACQuire:AALias")))
