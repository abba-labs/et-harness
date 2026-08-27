# B&K Precision 9130B 输出模式和定时控制。
#
# 职责：映射总输出、定时、跟踪、串联和并联状态的原子 SCPI 控制与查询。
# 边界：不选择通道、不设置电压电流，也不自动处理模式冲突或接线安全。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import format_bool, parse_bool, require_range


# 提供 9130B 输出级单命令控制；模式冲突由仪器固件按手册规则拒绝。
class Bk9130bOutputControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 打开或关闭总输出状态；只修改 OUTPut:STATe，不改变设定值。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(f"OUTPut:STATe {format_bool(enabled)}")

    # 查询总输出状态；查询过程不会修改任何通道输出或其他输出配置。
    def enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("OUTPut:STATe?"))

    # 打开或关闭输出定时器；只修改定时器状态，不改变延时值。
    def timer_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"OUTPut:TIMer:STATe {format_bool(enabled)}")

    # 查询输出定时器是否启用；查询过程不会修改定时参数。
    def timer_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("OUTPut:TIMer:STATe?"))

    # 设置输出定时延时 0.1~99999.9 秒；不自动启用定时器。
    def timer_delay_set(self, delay_s: float) -> None:
        normalized = require_range(delay_s, 0.1, 99999.9, "delay_s")
        self._session.write(f"OUTPut:TIMer:DELay {normalized:g}")

    # 查询编程手册定义的定时数据响应；只读取 OUTPut:TIMer:DATA?。
    def timer_data_get(self) -> str:
        return self._session.query_text("OUTPut:TIMer:DATA?")

    # 打开或关闭 CH1/CH2 跟踪输出模式；模式冲突由仪器固件判断。
    def tracking_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"OUTPut:TRACk:STATe {format_bool(enabled)}")

    # 查询 CH1/CH2 跟踪输出模式；查询过程不会修改组合状态。
    def tracking_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("OUTPut:TRACk:STATe?"))

    # 打开或关闭 CH1/CH2 串联输出模式；不自动修改物理接线。
    def series_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"OUTPut:SERies:STATe {format_bool(enabled)}")

    # 查询 CH1/CH2 串联输出模式；查询过程不会修改组合状态。
    def series_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("OUTPut:SERies:STATe?"))

    # 打开或关闭 CH1/CH2 并联输出模式；不自动修改物理接线。
    def parallel_enabled_set(self, enabled: bool) -> None:
        self._session.write(f"OUTPut:PARallel:STATe {format_bool(enabled)}")

    # 查询 CH1/CH2 并联输出模式；查询过程不会修改组合状态。
    def parallel_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text("OUTPut:PARallel:STATe?"))
