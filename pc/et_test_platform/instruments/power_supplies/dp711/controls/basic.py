# RIGOL DP711 基础、IEEE488.2、显示、通道和许可控制。
#
# 职责：把手册中的 APPLy、DISPlay、IEEE488.2、INSTrument 和 LIC 原子命令映射为 API。
# 边界：不组合电源测试流程、不管理跨能力状态，也不执行测量判定。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dp711ApplyState, Dp711Identification, Dp711Options
from ..validation import (
    DP711_APPLY_VOLTAGE_MAX_V,
    DP711_CURRENT_MAX_A,
    DP711_CURRENT_MIN_A,
    DP711_VOLTAGE_MIN_V,
    parse_apply_state,
    parse_bool,
    parse_identification,
    parse_options,
    require_integer,
    require_range,
)


# 提供 DP711 基础单命令控制；每个方法最多发送一条 SCPI 命令。
class Dp711BasicControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 一次设置 APPLy 命令中的电压和电流；不自动打开输出。
    def apply_set(self, voltage_v: float, current_a: float) -> None:
        voltage = require_range(
            voltage_v,
            DP711_VOLTAGE_MIN_V,
            DP711_APPLY_VOLTAGE_MAX_V,
            "voltage_v",
        )
        current = require_range(
            current_a,
            DP711_CURRENT_MIN_A,
            DP711_CURRENT_MAX_A,
            "current_a",
        )
        self._session.write(f":APPLy CH1,{voltage:g},{current:g}")

    # 查询 APPLy 当前电压和电流设定值；不读取实际输出测量值。
    def apply_get(self) -> Dp711ApplyState:
        return parse_apply_state(self._session.query_text(":APPLy? CH1"))

    # 打开或关闭前面板显示；只修改显示状态；只修改该配置项，不执行额外仪器动作。
    def display_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":DISPlay {'ON' if enabled else 'OFF'}")

    # 查询前面板显示是否打开；查询或解析过程不会修改仪器配置。
    def display_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":DISPlay?"))

    # 查询 IEEE488.2 设备标识并解析厂商、型号、序列号和软件版本。
    def identity_get(self) -> Dp711Identification:
        return parse_identification(self._session.query_text("*IDN?"))

    # 查询 Trigger、Timer 和 High Resolution 选件安装状态。
    def options_get(self) -> Dp711Options:
        return parse_options(self._session.query_text("*OPT?"))

    # 从内部非易失存储器召回指定状态或定时文件位置；该 API 不隐式执行额外仪器操作。
    def state_recall(self, position: int) -> None:
        normalized = require_integer(position, 1, 12, "position")
        self._session.write(f"*RCL {normalized}")

    # 恢复手册定义的仪器默认设置；不等待后续稳定过程。
    def reset(self) -> None:
        self._session.write("*RST")

    # 把当前状态或定时参数保存到指定内部位置；该 API 不隐式执行额外仪器操作。
    def state_save(self, position: int) -> None:
        normalized = require_integer(position, 1, 12, "position")
        self._session.write(f"*SAV {normalized}")

    # 查询仪器自检结果；返回设备原始自检文本；查询或解析过程不会修改仪器配置。
    def self_test_get(self) -> str:
        return self._session.query_text("*TST?")

    # 选择唯一的 DP711 通道；参数只允许 1；只修改该配置项，不执行额外仪器动作。
    def channel_number_set(self, channel: int) -> None:
        normalized = require_integer(channel, 1, 1, "channel")
        self._session.write(f":INSTrument:NSELect {normalized}")

    # 查询当前数字通道选择；DP711 正常应返回 1。
    def channel_number_get(self) -> int:
        return int(self._session.query_text(":INSTrument:NSELect?"))

    # 使用名称形式选择唯一的 DP711 通道 CH1。
    def channel_select(self) -> None:
        self._session.write(":INSTrument:SELect CH1")

    # 查询当前通道名称；DP711 正常应返回 CH1。
    def channel_selected_get(self) -> str:
        return self._session.query_text(":INSTrument:SELect?")

    # 安装设备许可字符串；许可有效性由仪器固件判断；只修改该配置项，不执行额外仪器动作。
    def license_set(self, license_code: str) -> None:
        normalized = license_code.strip()
        if not normalized or any(character.isspace() for character in normalized):
            raise ValueError("license_code must be a non-empty token")
        self._session.write(f":LIC:SET {normalized}")
