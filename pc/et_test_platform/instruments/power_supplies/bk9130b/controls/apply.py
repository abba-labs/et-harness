# B&K Precision 9130B APPLy 批量设定命令。
#
# 职责：映射手册明确提供的单条 APPLy、三通道电压、电流和输出状态批量命令。
# 边界：虽然一条命令可同时作用多个通道，但每个 API 仍只发送一条仪器原子命令。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Bk9130bApplyState, Bk9130bChannel
from ..validation import (
    BK9130B_CH3_VOLTAGE_MAX_V,
    BK9130B_CURRENT_MAX_A,
    BK9130B_VOLTAGE_MAX_V,
    parse_apply_state,
    parse_bool,
    parse_float_tuple,
    require_channel_voltage,
    require_range,
)


# 提供 9130B APPLy 单命令控制；批量作用范围完全由该条 SCPI 命令自身定义。
class Bk9130bApplyControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 用一条 APPLy 命令选择通道并同时设置该通道电压和电流；不会打开总输出。
    def channel_set(self, channel: Bk9130bChannel, voltage_v: float, current_a: float) -> None:
        if not isinstance(channel, Bk9130bChannel):
            raise ValueError("channel must be Bk9130bChannel")
        voltage = require_channel_voltage(channel, voltage_v)
        current = require_range(current_a, 0.0, BK9130B_CURRENT_MAX_A, "current_a")
        self._session.write(f"APPLy {channel.value},{voltage:g},{current:g}")

    # 查询指定通道 APPLy 的电压和电流设定；查询过程不会改变当前通道。
    def channel_get(self, channel: Bk9130bChannel) -> Bk9130bApplyState:
        if not isinstance(channel, Bk9130bChannel):
            raise ValueError("channel must be Bk9130bChannel")
        return parse_apply_state(self._session.query_text(f"APPLy? {channel.value}"))

    # 用一条命令设置 CH1、CH2、CH3 电压；不会改变当前通道选择或输出开关。
    def voltages_set(self, ch1_v: float, ch2_v: float, ch3_v: float) -> None:
        ch1 = require_range(ch1_v, 0.0, BK9130B_VOLTAGE_MAX_V, "ch1_v")
        ch2 = require_range(ch2_v, 0.0, BK9130B_VOLTAGE_MAX_V, "ch2_v")
        ch3 = require_range(ch3_v, 0.0, BK9130B_CH3_VOLTAGE_MAX_V, "ch3_v")
        self._session.write(f"APPLy:VOLTage {ch1:g},{ch2:g},{ch3:g}")

    # 查询 CH1、CH2、CH3 电压设定值；查询过程不会修改通道输出。
    def voltages_get(self) -> tuple[float, float, float]:
        values = parse_float_tuple(self._session.query_text("APPLy:VOLTage?"), 3, "APPLY VOLT")
        return values[0], values[1], values[2]

    # 用一条命令设置 CH1、CH2、CH3 电流；不会改变当前通道选择或输出开关。
    def currents_set(self, ch1_a: float, ch2_a: float, ch3_a: float) -> None:
        ch1 = require_range(ch1_a, 0.0, BK9130B_CURRENT_MAX_A, "ch1_a")
        ch2 = require_range(ch2_a, 0.0, BK9130B_CURRENT_MAX_A, "ch2_a")
        ch3 = require_range(ch3_a, 0.0, BK9130B_CURRENT_MAX_A, "ch3_a")
        self._session.write(f"APPLy:CURRent {ch1:g},{ch2:g},{ch3:g}")

    # 查询 CH1、CH2、CH3 电流设定值；查询过程不会修改通道输出。
    def currents_get(self) -> tuple[float, float, float]:
        values = parse_float_tuple(self._session.query_text("APPLy:CURRent?"), 3, "APPLY CURR")
        return values[0], values[1], values[2]

    # 用一条命令设置 CH1、CH2、CH3 输出开关；不会改变对应电压和电流设定。
    def outputs_set(self, ch1: bool, ch2: bool, ch3: bool) -> None:
        if not all(isinstance(value, bool) for value in (ch1, ch2, ch3)):
            raise ValueError("ch1, ch2 and ch3 must be bool")
        values = ",".join("1" if value else "0" for value in (ch1, ch2, ch3))
        self._session.write(f"APPLy:OUTput {values}")

    # 查询 CH1、CH2、CH3 输出开关；查询过程不会修改任何输出状态。
    def outputs_get(self) -> tuple[bool, bool, bool]:
        parts = [part.strip() for part in self._session.query_text("APPLy:OUTput?").split(",")]
        if len(parts) != 3:
            raise ValueError(f"unexpected APPLy:OUTput? response: {parts!r}")
        return parse_bool(parts[0]), parse_bool(parts[1]), parse_bool(parts[2])
