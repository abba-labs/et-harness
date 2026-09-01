# RIGOL DM3068 CALCulate 数学功能原子控制。
#
# 职责：映射统计、REL、dB、dBm、P/F 以及数学功能选择的单条 SCPI 命令。
# 边界：不选择基础测量功能、不启动触发，也不把数学配置组合成测试流程。
# 依赖：仅依赖公共 ScpiSession 和本型号 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import (
    _bool_token,
    _format_number,
    _nonempty_token,
    _parse_bool,
    _parse_float,
    _parse_int,
)


# 提供 DM3068 原生 CALCulate 子系统的逐项设置和查询接口。
class Dm3068CalculateControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置数学功能关键字；参数域按 DM3068 编程手册传入且不组合其他配置。
    def function_set(self, function: str) -> None:
        self._session.write(f":CALCulate:FUNCtion {_nonempty_token(function, 'function')}")

    # 查询当前数学功能关键字；只执行一次 CALCulate:FUNCtion? Query。
    def function_get(self) -> str:
        return self._session.query_text(":CALCulate:FUNCtion?").strip()

    # 查询当前统计最小值；只读取 STATistic:MIN，不重置统计累积状态。
    def statistic_minimum_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:STATistic:MIN?"))

    # 查询当前统计最大值；只读取 STATistic:MAX，不重置统计累积状态。
    def statistic_maximum_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:STATistic:MAX?"))

    # 查询当前统计平均值；只读取 STATistic:AVERage，不重置统计累积状态。
    def statistic_average_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:STATistic:AVERage?"))

    # 查询当前统计样本计数；只读取 STATistic:COUNt，不改变统计使能状态。
    def statistic_count_get(self) -> int:
        return _parse_int(self._session.query_text(":CALCulate:STATistic:COUNt?"))

    # 设置统计计算状态；只写入 STATistic:STATe，不选择其他数学功能。
    def statistic_state_set(self, enabled: bool) -> None:
        self._session.write(f":CALCulate:STATistic:STATe {_bool_token(enabled)}")

    # 查询统计计算状态；只读取 STATistic:STATe? 当前值。
    def statistic_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CALCulate:STATistic:STATe?"))

    # 设置 REL 偏移值；只写入 REL:OFFSet，不自动打开 REL 状态。
    def relative_offset_set(self, value: float) -> None:
        self._session.write(f":CALCulate:REL:OFFSet {_format_number(value)}")

    # 查询 REL 偏移值；只读取 REL:OFFSet? 当前值。
    def relative_offset_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:REL:OFFSet?"))

    # 设置 REL 功能状态；只写入 REL:STATe，不修改偏移值。
    def relative_state_set(self, enabled: bool) -> None:
        self._session.write(f":CALCulate:REL:STATe {_bool_token(enabled)}")

    # 查询 REL 功能状态；只读取 REL:STATe? 当前值。
    def relative_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CALCulate:REL:STATe?"))

    # 查询当前 dB 计算结果；只读取 CALCulate:DB?，不改变参考值。
    def db_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:DB?"))

    # 设置 dB 参考值；只写入 DB:REFErence，不自动启用 dB 功能。
    def db_reference_set(self, value: float) -> None:
        self._session.write(f":CALCulate:DB:REFErence {_format_number(value)}")

    # 查询 dB 参考值；只读取 DB:REFErence? 当前设置。
    def db_reference_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:DB:REFErence?"))

    # 设置 dB 功能状态；只写入 DB:STATe，不修改参考值。
    def db_state_set(self, enabled: bool) -> None:
        self._session.write(f":CALCulate:DB:STATe {_bool_token(enabled)}")

    # 查询 dB 功能状态；只读取 DB:STATe? 当前值。
    def db_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CALCulate:DB:STATe?"))

    # 查询当前 dBm 计算结果；只读取 CALCulate:DBM?，不改变参考阻抗。
    def dbm_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:DBM?"))

    # 设置 dBm 参考阻抗；只写入 DBM:REFErence，不自动启用 dBm 功能。
    def dbm_reference_set(self, value: float) -> None:
        self._session.write(f":CALCulate:DBM:REFErence {_format_number(value)}")

    # 查询 dBm 参考阻抗；只读取 DBM:REFErence? 当前设置。
    def dbm_reference_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:DBM:REFErence?"))

    # 设置 dBm 功能状态；只写入 DBM:STATe，不修改参考阻抗。
    def dbm_state_set(self, enabled: bool) -> None:
        self._session.write(f":CALCulate:DBM:STATe {_bool_token(enabled)}")

    # 查询 dBm 功能状态；只读取 DBM:STATe? 当前值。
    def dbm_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CALCulate:DBM:STATe?"))

    # 查询当前 P/F 判定结果；只读取 CALCulate:PF?，不改变上下限。
    def pass_fail_get(self) -> str:
        return self._session.query_text(":CALCulate:PF?").strip()

    # 设置 P/F 下限；只写入 PF:LOWEr，不自动启用 P/F 功能。
    def pass_fail_lower_set(self, value: float) -> None:
        self._session.write(f":CALCulate:PF:LOWEr {_format_number(value)}")

    # 查询 P/F 下限；只读取 PF:LOWEr? 当前设置。
    def pass_fail_lower_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:PF:LOWEr?"))

    # 设置 P/F 上限；只写入 PF:UPPEr，不自动启用 P/F 功能。
    def pass_fail_upper_set(self, value: float) -> None:
        self._session.write(f":CALCulate:PF:UPPEr {_format_number(value)}")

    # 查询 P/F 上限；只读取 PF:UPPEr? 当前设置。
    def pass_fail_upper_get(self) -> float:
        return _parse_float(self._session.query_text(":CALCulate:PF:UPPEr?"))

    # 设置 P/F 功能状态；只写入 PF:STATe，不修改上下限。
    def pass_fail_state_set(self, enabled: bool) -> None:
        self._session.write(f":CALCulate:PF:STATe {_bool_token(enabled)}")

    # 查询 P/F 功能状态；只读取 PF:STATe? 当前值。
    def pass_fail_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":CALCulate:PF:STATe?"))
