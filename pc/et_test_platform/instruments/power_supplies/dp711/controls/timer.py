# RIGOL DP711 定时输出控制。
#
# 职责：把 TIMEr 周期、结束状态、组数、组参数、使能和触发模式映射为原子 API。
# 边界：不自动保存 Timer 文件，不组合输出使能流程，也不判断 Timer 测试结果。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.errors import InstrumentProtocolError
from ....common.scpi import ScpiSession
from ..models import Dp711TimerEndState, Dp711TimerStep, Dp711TimerTriggerMode
from ..validation import (
    DP711_CURRENT_MAX_A,
    DP711_CURRENT_MIN_A,
    DP711_TIMER_CYCLE_MAX,
    DP711_TIMER_GROUP_MAX,
    DP711_TIMER_GROUP_MIN,
    DP711_TIMER_STEP_DURATION_MAX_S,
    DP711_TIMER_STEP_DURATION_MIN_S,
    DP711_TIMER_STEP_VOLTAGE_MAX_V,
    DP711_VOLTAGE_MIN_V,
    parse_bool,
    parse_timer_steps,
    require_integer,
    require_range,
)


# 提供 DP711 TIMEr 子系统原子控制；该类型不隐藏多步仪器操作流程。
class Dp711TimerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置 Timer 循环次数；None 表示手册中的无限循环 I。
    def cycles_set(self, cycles: int | None) -> None:
        if cycles is None:
            self._session.write(":TIMEr:CYCLEs I")
            return
        value = require_integer(cycles, 1, DP711_TIMER_CYCLE_MAX, "cycles")
        self._session.write(f":TIMEr:CYCLEs N,{value}")

    # 查询 Timer 循环次数；无限循环返回 None。
    def cycles_get(self) -> int | None:
        response = self._session.query_text(":TIMEr:CYCLEs?").strip().upper()
        if response == "I":
            return None
        if response.startswith("N,"):
            try:
                return int(response.split(",", 1)[1])
            except ValueError as exc:
                raise InstrumentProtocolError(f"invalid DP711 timer cycles: {response!r}") from exc
        raise InstrumentProtocolError(f"invalid DP711 timer cycles: {response!r}")

    # 设置 Timer 完成后的 OFF 或 LAST 状态。
    def end_state_set(self, state: Dp711TimerEndState) -> None:
        self._session.write(f":TIMEr:ENDState {state.value}")

    # 查询 Timer 完成后的状态；查询或解析过程不会修改仪器配置。
    def end_state_get(self) -> Dp711TimerEndState:
        response = self._session.query_text(":TIMEr:ENDState?").strip().upper()
        try:
            return Dp711TimerEndState(response)
        except ValueError as exc:
            raise InstrumentProtocolError(f"invalid DP711 timer end state: {response!r}") from exc

    # 设置每个 Timer 循环实际输出的组数；只修改该配置项，不执行额外仪器动作。
    def groups_set(self, groups: int) -> None:
        value = require_integer(groups, DP711_TIMER_GROUP_MIN, DP711_TIMER_GROUP_MAX, "groups")
        self._session.write(f":TIMEr:GROUPs {value}")

    # 查询每个 Timer 循环的输出组数；查询或解析过程不会修改仪器配置。
    def groups_get(self) -> int:
        return int(self._session.query_text(":TIMEr:GROUPs?"))

    # 设置一组 Timer 的电压、电流和持续时间；不修改总组数或循环次数。
    def parameter_set(
        self,
        group: int,
        voltage_v: float,
        current_a: float,
        duration_s: float,
    ) -> None:
        group_value = require_integer(
            group,
            DP711_TIMER_GROUP_MIN,
            DP711_TIMER_GROUP_MAX,
            "group",
        )
        voltage = require_range(
            voltage_v,
            DP711_VOLTAGE_MIN_V,
            DP711_TIMER_STEP_VOLTAGE_MAX_V,
            "voltage_v",
        )
        current = require_range(
            current_a,
            DP711_CURRENT_MIN_A,
            DP711_CURRENT_MAX_A,
            "current_a",
        )
        duration = require_range(
            duration_s,
            DP711_TIMER_STEP_DURATION_MIN_S,
            DP711_TIMER_STEP_DURATION_MAX_S,
            "duration_s",
        )
        self._session.write(f":TIMEr:PARAmeter {group_value},{voltage:g},{current:g},{duration:g}")

    # 从指定组开始查询一个或多个 Timer 组；返回去除 SCPI block header 后的结构化结果。
    def parameter_get(self, first_group: int, count: int = 1) -> tuple[Dp711TimerStep, ...]:
        first = require_integer(
            first_group,
            DP711_TIMER_GROUP_MIN,
            DP711_TIMER_GROUP_MAX,
            "first_group",
        )
        normalized_count = require_integer(count, 1, DP711_TIMER_GROUP_MAX, "count")
        if first + normalized_count - 1 > DP711_TIMER_GROUP_MAX:
            raise ValueError("requested timer parameter range exceeds group 2048")
        payload = self._session.query_bytes(f":TIMEr:PARAmeter? {first},{normalized_count}")
        return parse_timer_steps(payload)

    # 打开或关闭 Timer 输出；打开会改变 CH1 输出状态。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(f":TIMEr:STATe {'ON' if enabled else 'OFF'}")

    # 查询 Timer 输出是否打开；查询或解析过程不会修改仪器配置。
    def enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":TIMEr:STATe?"))

    # 设置 Timer 默认自动或单步触发模式；只修改该配置项，不执行额外仪器动作。
    def trigger_mode_set(self, mode: Dp711TimerTriggerMode) -> None:
        self._session.write(f":TIMEr:TRIGger {mode.value}")

    # 查询 Timer 触发模式；查询或解析过程不会修改仪器配置。
    def trigger_mode_get(self) -> Dp711TimerTriggerMode:
        response = self._session.query_text(":TIMEr:TRIGger?").strip().upper()
        try:
            return Dp711TimerTriggerMode(response)
        except ValueError as exc:
            raise InstrumentProtocolError(
                f"invalid DP711 timer trigger mode: {response!r}"
            ) from exc
