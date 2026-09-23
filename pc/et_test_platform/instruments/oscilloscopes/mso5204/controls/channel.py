# RIGOL MSO5204 模拟通道原子控制。
#
# 职责：映射 CHANnel<n> 命令组中的带宽、耦合、显示、反相、偏置、时延、量程和探头等控制。
# 边界：每个公开 API 只操作一个模拟通道的一项参数，不自动联动其他通道或时基。
# 依赖：仅依赖公共 ScpiSession、通道枚举和参数校验辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..models import (
    Mso5204AnalogChannel,
    Mso5204BandwidthLimit,
    Mso5204ChannelCoupling,
    Mso5204ChannelUnit,
)
from ..validation import (
    _command,
    _parse_bool,
    _parse_float,
    _query_command,
    _validate_channel,
    _validate_float_range,
    _validate_positive_finite,
    _validate_probe_ratio,
    _validate_scpi_token,
)


# 提供四个模拟通道的稳定 SCPI 原子访问接口。
class Mso5204ChannelControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _header(self, channel: int | Mso5204AnalogChannel, suffix: str) -> str:
        number = _validate_channel(int(channel))
        return f":CHANnel{number}:{suffix}"

    # 设置指定通道带宽限制；MSO5204 允许 20M、100M 或 OFF。
    def bandwidth_limit_set(
        self,
        channel: int | Mso5204AnalogChannel,
        value: Mso5204BandwidthLimit | str,
    ) -> None:
        normalized = _validate_scpi_token(
            value,
            tuple(item.value for item in Mso5204BandwidthLimit),
            "channel bandwidth limit",
        )
        self._session.write(_command(self._header(channel, "BWLimit"), normalized))

    # 查询指定通道带宽限制；只执行一次 CHANnel<n>:BWLimit? Query。
    def bandwidth_limit_get(self, channel: int | Mso5204AnalogChannel) -> str:
        return self._session.query_text(_query_command(self._header(channel, "BWLimit")))

    # 设置指定通道输入耦合方式；只接受 AC、DC 或 GND 手册离散值。
    def coupling_set(
        self,
        channel: int | Mso5204AnalogChannel,
        value: Mso5204ChannelCoupling | str,
    ) -> None:
        normalized = _validate_scpi_token(
            value,
            tuple(item.value for item in Mso5204ChannelCoupling),
            "channel coupling",
        )
        self._session.write(_command(self._header(channel, "COUPling"), normalized))

    # 查询指定通道输入耦合方式；保留仪器返回的 AC、DC 或 GND 字符串。
    def coupling_get(self, channel: int | Mso5204AnalogChannel) -> str:
        return self._session.query_text(_query_command(self._header(channel, "COUPling")))

    # 打开或关闭指定模拟通道显示；只发送一次 CHANnel<n>:DISPlay 命令。
    def display_set(self, channel: int | Mso5204AnalogChannel, enabled: bool) -> None:
        self._session.write(_command(self._header(channel, "DISPlay"), enabled))

    # 查询指定模拟通道显示状态；只执行一次 CHANnel<n>:DISPlay? Query。
    def display_get(self, channel: int | Mso5204AnalogChannel) -> bool:
        return _parse_bool(
            self._session.query_text(_query_command(self._header(channel, "DISPlay")))
        )

    # 打开或关闭指定通道波形反相；只发送一次 CHANnel<n>:INVert 命令。
    def invert_set(self, channel: int | Mso5204AnalogChannel, enabled: bool) -> None:
        self._session.write(_command(self._header(channel, "INVert"), enabled))

    # 查询指定通道波形反相状态；只执行一次 CHANnel<n>:INVert? Query。
    def invert_get(self, channel: int | Mso5204AnalogChannel) -> bool:
        return _parse_bool(
            self._session.query_text(_query_command(self._header(channel, "INVert")))
        )

    # 设置指定通道垂直偏置，单位为 V；动态量程依赖当前刻度，本层先拒绝手册绝对上限外参数。
    def offset_set(self, channel: int | Mso5204AnalogChannel, offset_v: float) -> None:
        value = _validate_float_range(offset_v, "channel vertical offset", -100.0, 100.0)
        self._session.write(_command(self._header(channel, "OFFSet"), value))

    # 查询指定通道垂直偏置，返回以 V 为单位的浮点值。
    def offset_get(self, channel: int | Mso5204AnalogChannel) -> float:
        return _parse_float(
            self._session.query_text(_query_command(self._header(channel, "OFFSet")))
        )

    # 设置指定通道时延校准值，单位为 s；Programming Guide 范围为 -100 ns..100 ns。
    def time_calibration_set(self, channel: int | Mso5204AnalogChannel, delay_s: float) -> None:
        value = _validate_float_range(delay_s, "channel delay calibration", -100e-9, 100e-9)
        self._session.write(_command(self._header(channel, "TCALibrate"), value))

    # 查询指定通道时延校准值，返回以 s 为单位的浮点值。
    def time_calibration_get(self, channel: int | Mso5204AnalogChannel) -> float:
        return _parse_float(
            self._session.query_text(_query_command(self._header(channel, "TCALibrate")))
        )

    # 设置指定通道垂直刻度，单位为 V/div；探头倍率会改变上限，因此原子层只拒绝非正或非有限值。
    def scale_set(self, channel: int | Mso5204AnalogChannel, scale_v: float) -> None:
        value = _validate_positive_finite(scale_v, "channel vertical scale")
        self._session.write(_command(self._header(channel, "SCALe"), value))

    # 查询指定通道垂直刻度，返回以 V/div 为单位的浮点值。
    def scale_get(self, channel: int | Mso5204AnalogChannel) -> float:
        return _parse_float(
            self._session.query_text(_query_command(self._header(channel, "SCALe")))
        )

    # 设置指定通道探头衰减倍率；只接受 Programming Guide 列出的 27 个离散倍率。
    def probe_ratio_set(self, channel: int | Mso5204AnalogChannel, ratio: float) -> None:
        self._session.write(_command(self._header(channel, "PROBe"), _validate_probe_ratio(ratio)))

    # 查询指定通道探头衰减倍率；返回仪器当前倍率数值。
    def probe_ratio_get(self, channel: int | Mso5204AnalogChannel) -> float:
        return _parse_float(
            self._session.query_text(_query_command(self._header(channel, "PROBe")))
        )

    # 设置指定通道幅值显示单位；只接受 VOLTage、WATT、AMPere 或 UNKNown。
    def units_set(
        self,
        channel: int | Mso5204AnalogChannel,
        units: Mso5204ChannelUnit | str,
    ) -> None:
        normalized = _validate_scpi_token(
            units,
            tuple(item.value for item in Mso5204ChannelUnit),
            "channel display unit",
        )
        self._session.write(_command(self._header(channel, "UNITs"), normalized))

    # 查询指定通道幅值显示单位；保留仪器返回的原生单位字符串。
    def units_get(self, channel: int | Mso5204AnalogChannel) -> str:
        return self._session.query_text(_query_command(self._header(channel, "UNITs")))

    # 打开或关闭指定通道垂直刻度细调；只发送一次 CHANnel<n>:VERNier 命令。
    def vernier_set(self, channel: int | Mso5204AnalogChannel, enabled: bool) -> None:
        self._session.write(_command(self._header(channel, "VERNier"), enabled))

    # 查询指定通道垂直刻度细调状态；只执行一次 CHANnel<n>:VERNier? Query。
    def vernier_get(self, channel: int | Mso5204AnalogChannel) -> bool:
        return _parse_bool(
            self._session.query_text(_query_command(self._header(channel, "VERNier")))
        )

    # 设置指定通道零点校准电压；Programming Guide 范围为 -100 V..100 V。
    def position_set(self, channel: int | Mso5204AnalogChannel, offset_v: float) -> None:
        value = _validate_float_range(offset_v, "channel zero calibration", -100.0, 100.0)
        self._session.write(_command(self._header(channel, "POSition"), value))

    # 查询指定通道零点校准电压；返回以 V 为单位的浮点值。
    def position_get(self, channel: int | Mso5204AnalogChannel) -> float:
        return _parse_float(
            self._session.query_text(_query_command(self._header(channel, "POSition")))
        )
