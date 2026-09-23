# RIGOL MSO5204 触发系统核心原子控制。
#
# 职责：映射通用触发参数和最常用的 EDGE 触发源、斜率、门限控制。
# 边界：复杂 PULSE/SLOPE/VIDEO/BUS 等触发子系统由独立模块扩展，不隐藏组合动作。
# 依赖：仅依赖公共 ScpiSession、触发枚举和基础 SCPI 格式化/解析/校验辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..models import (
    Mso5204TriggerCoupling,
    Mso5204TriggerMode,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
)
from ..validation import (
    _command,
    _parse_bool,
    _parse_float,
    _validate_edge_source,
    _validate_finite,
    _validate_float_range,
    _validate_scpi_token,
)


# 提供触发系统公共参数和 EDGE 触发的一条命令对应一个 API 的访问方式。
class Mso5204TriggerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置触发类型；只接受 TRIGger:MODE 手册离散值，不自动配置该类型的子参数。
    def mode_set(self, mode: Mso5204TriggerMode | str) -> None:
        normalized = _validate_scpi_token(
            mode,
            tuple(item.value for item in Mso5204TriggerMode),
            "trigger mode",
        )
        self._session.write(_command(":TRIGger:MODE", normalized))

    # 查询当前触发类型；保留仪器返回的 EDGE、PULS、SLOP 等原生缩写。
    def mode_get(self) -> str:
        return self._session.query_text(":TRIGger:MODE?")

    # 设置边沿触发模拟通道耦合；只接受 AC/DC/HFReject/LFReject 手册离散值。
    def coupling_set(self, coupling: Mso5204TriggerCoupling | str) -> None:
        normalized = _validate_scpi_token(
            coupling,
            tuple(item.value for item in Mso5204TriggerCoupling),
            "trigger coupling",
        )
        self._session.write(_command(":TRIGger:COUPling", normalized))

    # 查询边沿触发耦合；保留仪器返回的 AC、DC、LFR 或 HFR 字符串。
    def coupling_get(self) -> str:
        return self._session.query_text(":TRIGger:COUPling?")

    # 查询当前触发状态；返回 TD、WAIT、RUN、AUTO 或 STOP 等仪器状态字符串。
    def status_get(self) -> str:
        return self._session.query_text(":TRIGger:STATus?")

    # 设置触发扫描方式；只接受 AUTO、NORMal 或 SINGle，不改变触发类型。
    def sweep_set(self, sweep: Mso5204TriggerSweep | str) -> None:
        normalized = _validate_scpi_token(
            sweep,
            tuple(item.value for item in Mso5204TriggerSweep),
            "trigger sweep",
        )
        self._session.write(_command(":TRIGger:SWEep", normalized))

    # 查询触发扫描方式；保留仪器返回的 AUTO、NORM 或 SING 字符串。
    def sweep_get(self) -> str:
        return self._session.query_text(":TRIGger:SWEep?")

    # 设置触发释抑时间，单位为 s；Programming Guide 范围为 8 ns..10 s。
    def holdoff_set(self, seconds: float) -> None:
        value = _validate_float_range(seconds, "trigger holdoff", 8e-9, 10.0)
        self._session.write(_command(":TRIGger:HOLDoff", value))

    # 查询触发释抑时间；只执行一次 TRIGger:HOLDoff? Query，不改变触发条件或扫描模式。
    def holdoff_get(self) -> float:
        return _parse_float(self._session.query_text(":TRIGger:HOLDoff?"))

    # 打开或关闭触发噪声抑制；只发送一次 TRIGger:NREJect 命令。
    def noise_reject_set(self, enabled: bool) -> None:
        self._session.write(_command(":TRIGger:NREJect", enabled))

    # 查询触发噪声抑制开关；只执行一次 TRIGger:NREJect? Query。
    def noise_reject_get(self) -> bool:
        return _parse_bool(self._session.query_text(":TRIGger:NREJect?"))

    # 设置 EDGE 触发源；只接受 D0..D15、CHANnel1..4 或 ACLine 手册源。
    def edge_source_set(self, source: str) -> None:
        self._session.write(_command(":TRIGger:EDGE:SOURce", _validate_edge_source(source)))

    # 查询 EDGE 触发源；保留仪器返回的 CHAN1、D0 或 ACL 等原生字符串。
    def edge_source_get(self) -> str:
        return self._session.query_text(":TRIGger:EDGE:SOURce?")

    # 设置 EDGE 触发斜率；只接受 POSitive、NEGative 或 RFALl。
    def edge_slope_set(self, slope: Mso5204TriggerSlope | str) -> None:
        normalized = _validate_scpi_token(
            slope,
            tuple(item.value for item in Mso5204TriggerSlope),
            "edge trigger slope",
        )
        self._session.write(_command(":TRIGger:EDGE:SLOPe", normalized))

    # 查询 EDGE 触发斜率；保留仪器返回的 POS、NEG 或 RFAL 字符串。
    def edge_slope_get(self) -> str:
        return self._session.query_text(":TRIGger:EDGE:SLOPe?")

    # 设置 EDGE 触发电平；动态范围依赖当前通道刻度/偏置，本层只拒绝非有限值。
    def edge_level_set(self, level: float) -> None:
        self._session.write(
            _command(":TRIGger:EDGE:LEVel", _validate_finite(level, "trigger level"))
        )

    # 查询 EDGE 触发电平；返回当前源幅值单位下的浮点值。
    def edge_level_get(self) -> float:
        return _parse_float(self._session.query_text(":TRIGger:EDGE:LEVel?"))
