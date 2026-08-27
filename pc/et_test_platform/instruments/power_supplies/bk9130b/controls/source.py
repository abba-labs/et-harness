# B&K Precision 9130B 单通道 Source 控制。
#
# 职责：映射当前选中通道的输出开关、电压、电流、步进、触发值和 OVP 原子命令。
# 边界：不隐式切换/查询当前通道；通道相关上限应由显式 channel 的 Operations 在组合前校验。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import (
    BK9130B_CURRENT_MAX_A,
    BK9130B_VOLTAGE_MAX_V,
    format_bool,
    format_numeric_or_keyword,
    parse_bool,
    require_range,
)


# 提供当前选中通道的 9130B Source 单命令控制；每个方法最多发送一条命令。
class Bk9130bSourceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭当前选中通道输出；不改变总输出状态或通道设定值。
    def channel_output_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"CHANnel:OUTPut:STATe {format_bool(enabled)}")

    # 查询当前选中通道输出状态；查询过程不会修改输出。
    def channel_output_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("CHANnel:OUTPut:STATe?"))

    # 设置当前通道电流或 MIN/MAX/UP/DOWN/DEF；不隐式选择通道。
    def current_set(self, value_a: float | str) -> None:
        value = format_numeric_or_keyword(value_a, 0.0, BK9130B_CURRENT_MAX_A, "value_a")
        self._session.write(f"CURRent:LEVel {value}")

    # 查询当前通道电流设定值；查询过程不会读取实际测量电流。
    def current_get(self) -> float:
        return float(self._session.query_text("CURRent:LEVel?"))

    # 按已配置步进值增加当前通道电流；只发送一次 CURRent:UP。
    def current_up(self) -> None:
        self._session.write("CURRent:LEVel:UP")

    # 按已配置步进值减小当前通道电流；只发送一次 CURRent:DOWN。
    def current_down(self) -> None:
        self._session.write("CURRent:LEVel:DOWN")

    # 设置当前通道电流步进值；不会立即改变当前电流设定。
    def current_step_set(self, step_a: float) -> None:
        value = require_range(step_a, 0.0, BK9130B_CURRENT_MAX_A, "step_a")
        self._session.write(f"CURRent:LEVel:STEP {value:g}")

    # 查询当前通道电流步进值；查询过程不会改变当前电流。
    def current_step_get(self) -> float:
        return float(self._session.query_text("CURRent:LEVel:STEP?"))

    # 设置当前通道触发电流值或 SCPI 关键字；不产生触发动作。
    def current_triggered_set(self, value_a: float | str) -> None:
        value = format_numeric_or_keyword(value_a, 0.0, BK9130B_CURRENT_MAX_A, "value_a")
        self._session.write(f"CURRent:LEVel:TRIGgered {value}")

    # 查询当前通道触发电流设定；查询过程不会产生触发。
    def current_triggered_get(self) -> float:
        return float(self._session.query_text("CURRent:LEVel:TRIGgered?"))

    # 设置当前选中通道电压；原子层仅能证明系列 30 V 上限，CH3 的 5 V 上限由 Operations 校验。
    def voltage_set(self, value_v: float | str) -> None:
        value = format_numeric_or_keyword(value_v, 0.0, BK9130B_VOLTAGE_MAX_V, "value_v")
        self._session.write(f"VOLTage:LEVel {value}")

    # 查询当前通道电压设定值；查询过程不会读取实际测量电压。
    def voltage_get(self) -> float:
        return float(self._session.query_text("VOLTage:LEVel?"))

    # 按已配置步进值增加当前通道电压；只发送一次 VOLTage:UP。
    def voltage_up(self) -> None:
        self._session.write("VOLTage:LEVel:UP")

    # 按已配置步进值减小当前通道电压；只发送一次 VOLTage:DOWN。
    def voltage_down(self) -> None:
        self._session.write("VOLTage:LEVel:DOWN")

    # 设置当前通道电压步进值；不会立即改变当前电压设定。
    def voltage_step_set(self, step_v: float) -> None:
        value = require_range(step_v, 0.0, BK9130B_VOLTAGE_MAX_V, "step_v")
        self._session.write(f"VOLTage:LEVel:STEP {value:g}")

    # 查询当前通道电压步进值；查询过程不会改变当前电压。
    def voltage_step_get(self) -> float:
        return float(self._session.query_text("VOLTage:LEVel:STEP?"))

    # 设置当前通道触发电压值；CH3 的 5 V 上限无法由无通道参数的原子命令可靠推断。
    def voltage_triggered_set(self, value_v: float | str) -> None:
        value = format_numeric_or_keyword(value_v, 0.0, BK9130B_VOLTAGE_MAX_V, "value_v")
        self._session.write(f"VOLTage:LEVel:TRIGgered {value}")

    # 查询当前通道触发电压设定；查询过程不会产生触发。
    def voltage_triggered_get(self) -> float:
        return float(self._session.query_text("VOLTage:LEVel:TRIGgered?"))

    # 打开或关闭当前通道软件过压保护；不改变保护阈值。
    def voltage_protection_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"VOLTage:PROTection:STATe {format_bool(enabled)}")

    # 查询当前通道软件过压保护是否启用；查询过程不会清除保护。
    def voltage_protection_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("VOLTage:PROTection:STATe?"))

    # 设置当前通道过压保护阈值；通道相关上限由显式 channel 的 Operations 在组合前校验。
    def voltage_protection_level_set(self, value_v: float | str) -> None:
        value = format_numeric_or_keyword(value_v, 0.0, BK9130B_VOLTAGE_MAX_V, "value_v")
        self._session.write(f"VOLTage:PROTection:LEVel {value}")

    # 查询当前通道过压保护阈值；查询过程不会改变保护状态。
    def voltage_protection_level_get(self) -> float:
        return float(self._session.query_text("VOLTage:PROTection:LEVel?"))

    # 查询当前通道 OVP 是否已经触发；只读取 TRIPed 状态。
    def voltage_protection_tripped_get(self) -> bool:
        return parse_bool(self._session.query_text("VOLTage:PROTection:TRIPed?"))

    # 清除当前通道 OVP 保护状态；不修改 OVP 阈值或使能配置。
    def voltage_protection_clear(self) -> None:
        self._session.write("VOLTage:PROTection:CLEar")

    # 设置当前通道输出电压上限；CH3 的 5 V 上限无法由无通道参数的原子命令可靠推断。
    def voltage_limit_set(self, value_v: float | str) -> None:
        value = format_numeric_or_keyword(value_v, 0.0, BK9130B_VOLTAGE_MAX_V, "value_v")
        self._session.write(f"VOLTage:LIMIT:LEVel {value}")

    # 查询当前通道输出电压上限；查询过程不会修改输出设定。
    def voltage_limit_get(self) -> float:
        return float(self._session.query_text("VOLTage:LIMIT:LEVel?"))
