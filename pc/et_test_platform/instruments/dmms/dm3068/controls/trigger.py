# RIGOL DM3068 TRIGger 原子控制。
#
# 职责：映射自动/单次/外部触发、Reading Hold 和 VMC 触发输出的单条命令。
# 边界：不读取测量结果、不组合采样流程，也不实现 PC 侧轮询等待。
# 依赖：仅依赖公共 ScpiSession、本型号触发枚举与 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dm3068TriggerSource, Dm3068VmcPolarity
from ..validation import _bool_token, _nonempty_token, _parse_bool, _parse_int


# 提供 DM3068 原生 TRIGger 子系统的单命令设置、动作和查询接口。
class Dm3068TriggerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置触发源为自动、单次或外部；只写入 TRIGger:SOURce，不改变其他触发参数。
    def source_set(self, source: Dm3068TriggerSource) -> None:
        self._session.write(f":TRIGger:SOURce {source.value}")

    # 查询当前触发源；只读取 TRIGger:SOURce? 当前关键字。
    def source_get(self) -> str:
        return self._session.query_text(":TRIGger:SOURce?").strip()

    # 设置自动触发时间间隔；只写入 TRIGger:AUTO:INTErval，不改变触发源。
    def auto_interval_set(self, value: int) -> None:
        self._session.write(f":TRIGger:AUTO:INTErval {value}")

    # 查询自动触发时间间隔；只读取 TRIGger:AUTO:INTErval? 当前值。
    def auto_interval_get(self) -> int:
        return _parse_int(self._session.query_text(":TRIGger:AUTO:INTErval?"))

    # 设置 Reading Hold 自动保持状态；只写入 TRIGger:AUTO:HOLD，不改变灵敏度。
    def auto_hold_set(self, enabled: bool) -> None:
        self._session.write(f":TRIGger:AUTO:HOLD {_bool_token(enabled)}")

    # 查询 Reading Hold 自动保持状态；只读取 TRIGger:AUTO:HOLD? 当前值。
    def auto_hold_get(self) -> bool:
        return _parse_bool(self._session.query_text(":TRIGger:AUTO:HOLD?"))

    # 设置 Reading Hold 灵敏度参数；只写入 HOLD:SENSitivity，不改变保持开关。
    def auto_hold_sensitivity_set(self, value: int) -> None:
        self._session.write(f":TRIGger:AUTO:HOLD:SENSitivity {value}")

    # 查询 Reading Hold 灵敏度参数；只读取 HOLD:SENSitivity? 当前值。
    def auto_hold_sensitivity_get(self) -> int:
        return _parse_int(self._session.query_text(":TRIGger:AUTO:HOLD:SENSitivity?"))

    # 设置单次触发采样数；只写入 TRIGger:SINGle，不主动执行单次触发。
    def single_count_set(self, value: int) -> None:
        self._session.write(f":TRIGger:SINGle {value}")

    # 查询单次触发采样数；只读取 TRIGger:SINGle? 当前值。
    def single_count_get(self) -> int:
        return _parse_int(self._session.query_text(":TRIGger:SINGle?"))

    # 执行一次单次触发动作；只发送 TRIGger:SINGle:TRIGgered，不等待测量完成。
    def single_trigger(self) -> None:
        self._session.write(":TRIGger:SINGle:TRIGgered")

    # 设置外部触发边沿或电平关键字；只写入 TRIGger:EXT，不改变触发源。
    def external_mode_set(self, mode: str) -> None:
        self._session.write(f":TRIGger:EXT {_nonempty_token(mode, 'mode')}")

    # 查询外部触发边沿或电平关键字；只读取 TRIGger:EXT? 当前值。
    def external_mode_get(self) -> str:
        return self._session.query_text(":TRIGger:EXT?").strip()

    # 设置 VMC 触发输出极性；只写入 VMComplete:POLAr，不改变脉宽。
    def vmc_polarity_set(self, polarity: Dm3068VmcPolarity) -> None:
        self._session.write(f":TRIGger:VMComplete:POLAr {polarity.value}")

    # 查询 VMC 触发输出极性；只读取 VMComplete:POLAr? 当前值。
    def vmc_polarity_get(self) -> str:
        return self._session.query_text(":TRIGger:VMComplete:POLAr?").strip()

    # 设置 VMC 触发输出脉宽；只写入 VMComplete:PULSewidth，不改变极性。
    def vmc_pulse_width_set(self, value_ms: int) -> None:
        self._session.write(f":TRIGger:VMComplete:PULSewidth {value_ms}")

    # 查询 VMC 触发输出脉宽；只读取 VMComplete:PULSewidth? 当前值。
    def vmc_pulse_width_get(self) -> int:
        return _parse_int(self._session.query_text(":TRIGger:VMComplete:PULSewidth?"))
