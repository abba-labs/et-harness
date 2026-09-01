# RIGOL MSO5204 水平时基原子控制。
#
# 职责：映射 TIMebase 命令组中的延迟扫描、主时基、模式、水平参考和细调控制。
# 边界：不自动根据采集状态修正动态 offset，也不联动触发、采样或波形读取流程。
# 依赖：仅依赖公共 ScpiSession、时基枚举和基础 SCPI 格式化/解析/校验函数。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Mso5204TimebaseMode
from ..validation import (
    _command,
    _parse_bool,
    _parse_float,
    _parse_int,
    _query_command,
    _validate_finite,
    _validate_float_range,
    _validate_positive_finite,
    _validate_scpi_token,
)


# 提供 MSO5204 水平系统的一条命令对应一个 API 的访问方式。
class Mso5204TimebaseControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭延迟扫描；只发送一次 TIMebase:DELay:ENABle 命令。
    def delay_enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":TIMebase:DELay:ENABle", enabled))

    # 查询延迟扫描开关；只执行一次 TIMebase:DELay:ENABle? Query。
    def delay_enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":TIMebase:DELay:ENABle?"))

    # 设置延迟时基偏移，单位为 s；其动态范围依赖主时基，本层只拒绝非有限值。
    def delay_offset_set(self, offset_s: float) -> None:
        value = _validate_finite(offset_s, "delayed timebase offset")
        self._session.write(_command(":TIMebase:DELay:OFFSet", value))

    # 查询延迟时基偏移；只执行一次 TIMebase:DELay:OFFSet? Query，不修改水平时基配置。
    def delay_offset_get(self) -> float:
        return _parse_float(self._session.query_text(":TIMebase:DELay:OFFSet?"))

    # 设置延迟时基刻度，单位为 s/div；动态边界依赖主时基，原子层只拒绝非正或非有限值。
    def delay_scale_set(self, scale_s: float) -> None:
        value = _validate_positive_finite(scale_s, "delayed timebase scale")
        self._session.write(_command(":TIMebase:DELay:SCALe", value))

    # 查询延迟时基刻度，返回以 s/div 为单位的浮点值。
    def delay_scale_get(self) -> float:
        return _parse_float(self._session.query_text(":TIMebase:DELay:SCALe?"))

    # 设置主时基水平偏移，单位为 s；手册范围随模式和 RUN/STOP 状态变化，本层只校验有限性。
    def main_offset_set(self, offset_s: float) -> None:
        value = _validate_finite(offset_s, "main timebase offset")
        self._session.write(_command(":TIMebase:MAIN:OFFSet", value))

    # 查询主时基水平偏移，返回以 s 为单位的浮点值。
    def main_offset_get(self) -> float:
        return _parse_float(self._session.query_text(":TIMebase:MAIN:OFFSet?"))

    # 设置主时基刻度，单位为 s/div；MSO5204 手册总范围为 2 ns/div 至 1000 s/div。
    def main_scale_set(self, scale_s: float) -> None:
        value = _validate_float_range(scale_s, "main timebase scale", 2e-9, 1000.0)
        self._session.write(_command(":TIMebase:MAIN:SCALe", value))

    # 查询主时基刻度，返回以 s/div 为单位的浮点值。
    def main_scale_get(self) -> float:
        return _parse_float(self._session.query_text(":TIMebase:MAIN:SCALe?"))

    # 设置水平时基模式；YT 对应手册命令参数 MAIN，另外支持 XY 和 ROLL。
    def mode_set(self, mode: Mso5204TimebaseMode | str) -> None:
        normalized = _validate_scpi_token(
            mode,
            tuple(item.value for item in Mso5204TimebaseMode),
            "timebase mode",
        )
        self._session.write(_command(":TIMebase:MODE", normalized))

    # 查询水平时基模式；保留仪器返回的 MAIN、XY 或 ROLL 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":TIMebase:MODE?")

    # 设置水平参考模式；只接受 CENTer、LB、RB、TRIG 或 USER 手册值。
    def reference_mode_set(self, mode: str) -> None:
        normalized = _validate_scpi_token(
            mode,
            ("CENTer", "LB", "RB", "TRIG", "USER"),
            "horizontal reference mode",
        )
        self._session.write(_command(":TIMebase:HREFerence:MODE", normalized))

    # 查询水平参考模式；只执行一次 TIMebase:HREFerence:MODE? Query。
    def reference_mode_get(self) -> str:
        return self._session.query_text(":TIMebase:HREFerence:MODE?")

    # 设置 USER 水平参考位置；只发送一次 TIMebase:HREFerence:POSition 命令。
    def reference_position_set(self, position: int) -> None:
        number = int(position)
        if not -500 <= number <= 500:
            raise ValueError("horizontal reference position must be -500..500")
        self._session.write(_command(":TIMebase:HREFerence:POSition", number))

    # 查询 USER 水平参考位置；返回 -500 至 500 的整数位置值。
    def reference_position_get(self) -> int:
        return _parse_int(self._session.query_text(":TIMebase:HREFerence:POSition?"))

    # 打开或关闭水平时基细调；只发送一次 TIMebase:VERNier 命令。
    def vernier_set(self, enabled: bool) -> None:
        self._session.write(_command(":TIMebase:VERNier", enabled))

    # 查询水平时基细调开关；只执行一次 TIMebase:VERNier? Query。
    def vernier_get(self) -> bool:
        return _parse_bool(self._session.query_text(_query_command(":TIMebase:VERNier")))
