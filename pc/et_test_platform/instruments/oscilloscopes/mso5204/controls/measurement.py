# RIGOL MSO5204 自动测量系统原子控制。
#
# 职责：完整映射 MSO5000 Programming Guide 的 MEASure 命令组，包括来源、阈值、统计和测量项查询。
# 边界：不替测试用例决定测量参数、阈值或 PASS/FAIL，也不自动启用输入通道。
# 依赖：仅依赖公共 ScpiSession、测量枚举和基础 SCPI 格式化/解析/校验辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..models import Mso5204MeasurementItem, Mso5204MeasurementStatistic
from ..validation import (
    _command,
    _parse_bool,
    _parse_float,
    _parse_int,
    _query_command,
    _validate_int_range,
    _validate_measurement_item,
    _validate_measurement_source,
    _validate_measurement_statistic,
    _validate_measurement_threshold_source,
    _validate_scpi_token,
)


# 提供 MEASure 命令组全部公开 Set/Query 语义的一条命令对应一个 API 的访问方式。
class Mso5204MeasurementControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _item_args(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: str | None,
        source_b: str | None,
    ) -> tuple[str, ...]:
        values = [_validate_measurement_item(item)]
        if source_a is not None:
            values.append(_validate_measurement_source(source_a))
        if source_b is not None:
            if source_a is None:
                raise ValueError("source_b requires source_a")
            values.append(_validate_measurement_source(source_b))
        return tuple(values)

    # 设置当前自动测量来源；只接受 D0..D15、CHANnel1..4 或 MATH1..4 手册源。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":MEASure:SOURce", _validate_measurement_source(source)))

    # 查询当前自动测量来源；保留仪器返回的 CHAN1、D0、MATH1 等字符串。
    def source_get(self) -> str:
        return self._session.query_text(":MEASure:SOURce?")

    # 清除指定的屏幕测量项；参数接受 ITEM1..ITEM10 或 ALL。
    def item_clear(self, item: str) -> None:
        normalized = _validate_scpi_token(
            item,
            (*tuple(f"ITEM{index}" for index in range(1, 11)), "ALL"),
            "measurement display item",
        )
        self._session.write(_command(":MEASure:CLEar", normalized))

    # 设置自动测量阈值来源；手册只允许 CHANnel1..4 或 MATH1..4。
    def threshold_source_set(self, source: str) -> None:
        self._session.write(
            _command(
                ":MEASure:THReshold:SOURce",
                _validate_measurement_threshold_source(source),
            )
        )

    # 将模拟通道自动测量阈值恢复为默认值；只发送一次 THReshold:DEFault 命令。
    def threshold_default(self) -> None:
        self._session.write(":MEASure:THReshold:DEFault")

    # 设置测量模式；只接受 NORMal 或 PRECision，不附加其他测量配置。
    def mode_set(self, mode: str) -> None:
        normalized = _validate_scpi_token(mode, ("NORMal", "PRECision"), "measurement mode")
        self._session.write(_command(":MEASure:MODE", normalized))

    # 查询当前测量模式；保留仪器返回的 NORM 或 PREC 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":MEASure:MODE?")

    # 设置“全部测量”功能来源；参数接受 CHANnel1..4 或 OFF。
    def all_measure_source_set(self, source: str) -> None:
        normalized = _validate_scpi_token(
            source,
            ("CHANnel1", "CHANnel2", "CHANnel3", "CHANnel4", "OFF"),
            "all-measure source",
        )
        self._session.write(_command(":MEASure:AMSource", normalized))

    # 查询“全部测量”功能来源；保留仪器返回的 CHAN1..CHAN4 或 OFF。
    def all_measure_source_get(self) -> str:
        return self._session.query_text(":MEASure:AMSource?")

    # 设置自动测量阈值上限；百分比/绝对值两种模式的手册静态并集范围均不超过 -100..100。
    def threshold_max_set(self, value: int) -> None:
        number = _validate_int_range(value, "measurement threshold maximum", -100, 100)
        self._session.write(_command(":MEASure:SETup:MAX", number))

    # 查询自动测量阈值上限；只执行一次 MEASure:SETup:MAX? Query，不修改测量阈值配置。
    def threshold_max_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:SETup:MAX?"))

    # 设置自动测量阈值中值；百分比/绝对值两种模式的手册静态并集范围均不超过 -100..100。
    def threshold_mid_set(self, value: int) -> None:
        number = _validate_int_range(value, "measurement threshold middle", -100, 100)
        self._session.write(_command(":MEASure:SETup:MID", number))

    # 查询自动测量阈值中值；只执行一次 MEASure:SETup:MID? Query，不修改测量阈值配置。
    def threshold_mid_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:SETup:MID?"))

    # 设置自动测量阈值下限；百分比/绝对值两种模式的手册静态并集范围均不超过 -100..100。
    def threshold_min_set(self, value: int) -> None:
        number = _validate_int_range(value, "measurement threshold minimum", -100, 100)
        self._session.write(_command(":MEASure:SETup:MIN", number))

    # 查询自动测量阈值下限；只执行一次 MEASure:SETup:MIN? Query，不修改测量阈值配置。
    def threshold_min_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:SETup:MIN?"))

    # 设置相位/延迟测量 Source A；只发送一次 MEASure:SETup:PSA 命令。
    def phase_source_a_set(self, source: str) -> None:
        self._session.write(_command(":MEASure:SETup:PSA", _validate_measurement_source(source)))

    # 查询相位测量 Source A；保留仪器返回的原生源字符串。
    def phase_source_a_get(self) -> str:
        return self._session.query_text(":MEASure:SETup:PSA?")

    # 设置相位测量 Source B；只发送一次 MEASure:SETup:PSB 命令。
    def phase_source_b_set(self, source: str) -> None:
        self._session.write(_command(":MEASure:SETup:PSB", _validate_measurement_source(source)))

    # 查询相位测量 Source B；保留仪器返回的原生源字符串。
    def phase_source_b_get(self) -> str:
        return self._session.query_text(":MEASure:SETup:PSB?")

    # 设置延迟测量 Source A；只发送一次 MEASure:SETup:DSA 命令。
    def delay_source_a_set(self, source: str) -> None:
        self._session.write(_command(":MEASure:SETup:DSA", _validate_measurement_source(source)))

    # 查询延迟测量 Source A；保留仪器返回的原生源字符串。
    def delay_source_a_get(self) -> str:
        return self._session.query_text(":MEASure:SETup:DSA?")

    # 设置延迟测量 Source B；只发送一次 MEASure:SETup:DSB 命令。
    def delay_source_b_set(self, source: str) -> None:
        self._session.write(_command(":MEASure:SETup:DSB", _validate_measurement_source(source)))

    # 查询延迟测量 Source B；保留仪器返回的原生源字符串。
    def delay_source_b_get(self) -> str:
        return self._session.query_text(":MEASure:SETup:DSB?")

    # 打开或关闭测量统计显示；只发送一次 MEASure:STATistic:DISPlay 命令。
    def statistics_display_set(self, enabled: bool) -> None:
        self._session.write(_command(":MEASure:STATistic:DISPlay", enabled))

    # 查询测量统计显示开关；只执行一次 MEASure:STATistic:DISPlay? Query。
    def statistics_display_get(self) -> bool:
        return _parse_bool(self._session.query_text(":MEASure:STATistic:DISPlay?"))

    # 清除历史统计并重新开始统计；只发送一次 MEASure:STATistic:RESet。
    def statistics_reset(self) -> None:
        self._session.write(":MEASure:STATistic:RESet")

    # 启用指定测量参数的统计；可选指定一个或两个来源，不追加查询。
    def statistics_item_enable(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: str | None = None,
        source_b: str | None = None,
    ) -> None:
        args = self._item_args(item, source_a, source_b)
        self._session.write(_command(":MEASure:STATistic:ITEM", *args))

    # 查询指定参数的统计值；statistic_type 只接受 Programming Guide 的六个统计类型。
    def statistics_item_get(
        self,
        statistic_type: Mso5204MeasurementStatistic | str,
        item: Mso5204MeasurementItem | str,
        source_a: str | None = None,
        source_b: str | None = None,
    ) -> float:
        statistic = _validate_measurement_statistic(statistic_type)
        args = (statistic, *self._item_args(item, source_a, source_b))
        return _parse_float(
            self._session.query_text(_query_command(":MEASure:STATistic:ITEM", *args))
        )

    # 启用指定波形参数的屏幕测量项；可选指定一个或两个来源。
    def item_enable(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: str | None = None,
        source_b: str | None = None,
    ) -> None:
        args = self._item_args(item, source_a, source_b)
        self._session.write(_command(":MEASure:ITEM", *args))

    # 立即查询指定波形参数的当前测量值；可选指定一个或两个来源。
    def item_get(
        self,
        item: Mso5204MeasurementItem | str,
        source_a: str | None = None,
        source_b: str | None = None,
    ) -> float:
        args = self._item_args(item, source_a, source_b)
        return _parse_float(self._session.query_text(_query_command(":MEASure:ITEM", *args)))

    # 设置测量区域类型；参数接受 MAIN、ZOOM 或 CURSor。
    def area_set(self, area: str) -> None:
        normalized = _validate_scpi_token(area, ("MAIN", "ZOOM", "CURSor"), "measurement area")
        self._session.write(_command(":MEASure:AREA", normalized))

    # 查询测量区域类型；保留仪器返回的 MAIN、ZOOM 或 CURS 字符串。
    def area_get(self) -> str:
        return self._session.query_text(":MEASure:AREA?")

    # 设置 Cursor A 的测量区域像素位置；手册范围为 0..1000。
    def cursor_a_position_set(self, position: int) -> None:
        number = int(position)
        if not 0 <= number <= 1000:
            raise ValueError("measurement cursor A position must be 0..1000")
        self._session.write(_command(":MEASure:CREGion:CAX", number))

    # 查询 Cursor A 的测量区域像素位置；返回 0..1000 的整数。
    def cursor_a_position_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CREGion:CAX?"))

    # 设置 Cursor B 的测量区域像素位置；手册范围为 0..1000。
    def cursor_b_position_set(self, position: int) -> None:
        number = int(position)
        if not 0 <= number <= 1000:
            raise ValueError("measurement cursor B position must be 0..1000")
        self._session.write(_command(":MEASure:CREGion:CBX", number))

    # 查询 Cursor B 的测量区域像素位置；返回 0..1000 的整数。
    def cursor_b_position_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CREGion:CBX?"))

    # 设置测量类别；0 为水平、1 为垂直、2 为其他，其他值在写入前拒绝。
    def category_set(self, category: int) -> None:
        number = int(category)
        if number not in {0, 1, 2}:
            raise ValueError("measurement category must be 0, 1, or 2")
        self._session.write(_command(":MEASure:CATegory", number))

    # 查询当前测量类别；返回 0、1 或 2 的整数值。
    def category_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CATegory?"))
