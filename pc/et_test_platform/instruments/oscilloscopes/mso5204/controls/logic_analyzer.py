# RIGOL MSO5204 Logic Analyzer 与数字通道原子控制。
#
# 职责：完整映射 LA 命令组的总开关、数字通道、POD、阈值、显示布局和用户分组操作。
# 边界：每个公开 API 只发送一条 SCPI；不探测 PLA2216 探头，也不自动启用数字通道或触发。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 参数格式化/响应解析辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int


# 提供 LA 命令组全部稳定设置/查询/动作的一条命令对应一个 API 的控制接口。
class Mso5204LogicAnalyzerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _pod(self, pod: int) -> int:
        number = int(pod)
        if number not in {1, 2}:
            raise ValueError("LA pod must be 1 or 2")
        return number

    def _digital(self, digital: int | str) -> str:
        if isinstance(digital, int):
            if not 0 <= digital <= 15:
                raise ValueError("digital channel must be 0..15")
            return f"D{digital}"
        value = digital.strip().upper()
        if value.startswith("D") and value[1:].isdigit() and 0 <= int(value[1:]) <= 15:
            return value
        raise ValueError("digital channel must be D0..D15")

    # 打开或关闭 Logic Analyzer 功能；只修改 LA 总开关，不改变各数字通道状态。
    def state_set(self, enabled: bool) -> None:
        self._session.write(_command(":LA:STATe", enabled))

    # 查询 Logic Analyzer 总开关；只读取当前状态，不检查探头是否存在。
    def state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":LA:STATe?"))

    # 设置当前活动数字通道；接受 D0..D15 或 NONE，不自动启用该通道。
    def active_set(self, digital: str) -> None:
        value = digital.strip()
        if value.upper() != "NONE":
            value = self._digital(value)
        self._session.write(_command(":LA:ACTive", value))

    # 查询当前活动数字通道；保留仪器返回的 D0..D15 或 NONE。
    def active_get(self) -> str:
        return self._session.query_text(":LA:ACTive?")

    # 设置数字波形自动排序方向；手册参数只允许 0 或 1。
    def auto_sort_set(self, mode: int) -> None:
        number = int(mode)
        if number not in {0, 1}:
            raise ValueError("LA auto sort mode must be 0 or 1")
        self._session.write(_command(":LA:AUTOsort", number))

    # 删除指定用户分组 GROUP1..GROUP4；只取消该分组设置，不关闭其他通道。
    def group_delete(self, group: str) -> None:
        self._session.write(_command(":LA:DELete", group))

    # 打开或关闭指定数字通道；digital 可用 0..15 或 D0..D15 表示。
    def digital_display_set(self, digital: int | str, enabled: bool) -> None:
        self._session.write(_command(":LA:DIGital:DISPlay", self._digital(digital), enabled))

    # 查询指定数字通道显示状态；只读取 D0..D15 当前开关。
    def digital_display_get(self, digital: int | str) -> bool:
        return _parse_bool(
            self._session.query_text(_command(":LA:DIGital:DISPlay?", self._digital(digital)))
        )

    # 设置指定数字通道在屏幕中的显示位置；实际最大值依赖当前 LA:SIZE。
    def digital_position_set(self, digital: int | str, position: int) -> None:
        number = int(position)
        if not 0 <= number <= 31:
            raise ValueError("digital position must be 0..31")
        self._session.write(_command(":LA:DIGital:POSition", self._digital(digital), number))

    # 查询指定数字通道的显示位置；返回当前布局下的整数位置。
    def digital_position_get(self, digital: int | str) -> int:
        return _parse_int(
            self._session.query_text(_command(":LA:DIGital:POSition?", self._digital(digital)))
        )

    # 设置指定数字通道标签；只修改该通道标签文本，不改变通道显示状态。
    def digital_label_set(self, digital: int | str, label: str) -> None:
        self._session.write(_command(":LA:DIGital:LABel", self._digital(digital), label))

    # 查询指定数字通道标签；返回仪器原生 ASCII 标签文本。
    def digital_label_get(self, digital: int | str) -> str:
        return self._session.query_text(_command(":LA:DIGital:LABel?", self._digital(digital)))

    # 打开或关闭默认 POD1/POD2 通道组；只修改指定 POD 显示状态。
    def pod_display_set(self, pod: int, enabled: bool) -> None:
        self._session.write(_command(f":LA:POD{self._pod(pod)}:DISPlay", enabled))

    # 查询默认 POD1/POD2 通道组显示状态；只读取对应 POD 开关。
    def pod_display_get(self, pod: int) -> bool:
        return _parse_bool(self._session.query_text(f":LA:POD{self._pod(pod)}:DISPlay?"))

    # 打开或关闭数字通道、用户组或 POD；channel 接受手册 LA:DISPlay 参数。
    def display_set(self, channel: str, enabled: bool) -> None:
        self._session.write(_command(":LA:DISPlay", channel, enabled))

    # 查询数字通道、用户组或 POD 显示状态；返回单一布尔状态。
    def display_get(self, channel: str) -> bool:
        return _parse_bool(self._session.query_text(_command(":LA:DISPlay?", channel)))

    # 设置 POD1/POD2 数字阈值，单位 V；手册有效范围为 -15 V 到 +15 V。
    def pod_threshold_set(self, pod: int, threshold_v: float) -> None:
        value = float(threshold_v)
        if not -15.0 <= value <= 15.0:
            raise ValueError("LA pod threshold must be -15..15 V")
        self._session.write(_command(f":LA:POD{self._pod(pod)}:THReshold", value))

    # 查询 POD1/POD2 数字阈值，返回以 V 为单位的浮点值。
    def pod_threshold_get(self, pod: int) -> float:
        return _parse_float(self._session.query_text(f":LA:POD{self._pod(pod)}:THReshold?"))

    # 设置数字波形显示尺寸；接受 SMALl、MEDium 或 LARGe。
    def size_set(self, size: str) -> None:
        self._session.write(_command(":LA:SIZE", size))

    # 查询数字波形显示尺寸；保留仪器返回的 SMAL、MED 或 LARG 字符串。
    def size_get(self) -> str:
        return self._session.query_text(":LA:SIZE?")

    # 设置数字通道延迟校准时间，单位 s；手册范围为 -1000 ns 到 +100 ns。
    def time_calibration_set(self, seconds: float) -> None:
        value = float(seconds)
        if not -1e-6 <= value <= 1e-7:
            raise ValueError("LA time calibration must be -1e-6..1e-7 s")
        self._session.write(_command(":LA:TCALibrate", value))

    # 查询数字通道延迟校准时间；返回以 s 为单位的浮点值。
    def time_calibration_get(self) -> float:
        return _parse_float(self._session.query_text(":LA:TCALibrate?"))

    # 向 GROUP1..GROUP4 追加一个或多个 D0..D15 通道；一次调用只发送一条 APPend 命令。
    def group_append(self, group: str, digitals: tuple[int | str, ...]) -> None:
        if not digitals:
            raise ValueError("digitals must not be empty")
        if len(digitals) > 16:
            raise ValueError("digitals must contain at most 16 channels")
        self._session.write(
            _command(":LA:GROup:APPend", group, *(self._digital(item) for item in digitals))
        )
