# RIGOL MSO5204 显示系统原子控制。
#
# 职责：完整映射 DISPlay 命令组，包含显示类型、余辉、亮度、网格、截图、标尺和色温显示。
# 边界：不保存截图文件、不解释图像内容，也不联动采集或触发状态。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_int


# 提供 MSO5000 Programming Guide 全部 DISPlay 原子命令的稳定访问接口。
class Mso5204DisplayControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 清除当前屏幕波形显示；只发送一次 DISPlay:CLEar，不改变 RUN/STOP 状态。
    def clear(self) -> None:
        self._session.write(":DISPlay:CLEar")

    # 设置波形显示类型；参数接受 VECTors 或 DOTS。
    def type_set(self, display_type: str) -> None:
        self._session.write(_command(":DISPlay:TYPE", display_type))

    # 查询波形显示类型；保留仪器返回的 VECT 或 DOTS 字符串。
    def type_get(self) -> str:
        return self._session.query_text(":DISPlay:TYPE?")

    # 设置余辉时间；参数接受 MIN、0.1/0.2/0.5/1/2/5/10 或 INFinite。
    def persistence_set(self, seconds: str | float) -> None:
        self._session.write(_command(":DISPlay:GRADing:TIME", seconds))

    # 查询余辉时间；保留仪器返回的 MIN、数值或 INF 字符串。
    def persistence_get(self) -> str:
        return self._session.query_text(":DISPlay:GRADing:TIME?")

    # 设置波形亮度百分比；手册范围为 1..100，超出范围在写入前拒绝。
    def waveform_brightness_set(self, percent: int) -> None:
        value = int(percent)
        if not 1 <= value <= 100:
            raise ValueError("waveform brightness must be 1..100")
        self._session.write(_command(":DISPlay:WBRightness", value))

    # 查询波形亮度百分比；返回 1..100 的整数。
    def waveform_brightness_get(self) -> int:
        return _parse_int(self._session.query_text(":DISPlay:WBRightness?"))

    # 设置屏幕网格类型；参数接受 FULL、HALF、NONE 或 IRE。
    def grid_set(self, grid: str) -> None:
        self._session.write(_command(":DISPlay:GRID", grid))

    # 查询屏幕网格类型；保留仪器返回的 FULL、HALF、NONE 或 IRE 字符串。
    def grid_get(self) -> str:
        return self._session.query_text(":DISPlay:GRID?")

    # 设置网格亮度百分比；手册范围为 1..100，超出范围在写入前拒绝。
    def grid_brightness_set(self, percent: int) -> None:
        value = int(percent)
        if not 1 <= value <= 100:
            raise ValueError("grid brightness must be 1..100")
        self._session.write(_command(":DISPlay:GBRightness", value))

    # 查询网格亮度百分比；返回 1..100 的整数。
    def grid_brightness_get(self) -> int:
        return _parse_int(self._session.query_text(":DISPlay:GBRightness?"))

    # 读取当前屏幕 BMP 数据流；ScpiSession 会去除 IEEE488.2 definite-length block 头。
    def screenshot_get(self, *, timeout_s: float | None = None) -> bytes:
        return self._session.query_bytes(":DISPlay:DATA?", timeout_s=timeout_s)

    # 打开或关闭标尺显示；只发送一次 DISPlay:RULers 命令。
    def rulers_set(self, enabled: bool) -> None:
        self._session.write(_command(":DISPlay:RULers", enabled))

    # 查询标尺显示开关；只执行一次 DISPlay:RULers? Query。
    def rulers_get(self) -> bool:
        return _parse_bool(self._session.query_text(":DISPlay:RULers?"))

    # 打开或关闭色温等级显示；只发送一次 DISPlay:COLor 命令。
    def color_grade_set(self, enabled: bool) -> None:
        self._session.write(_command(":DISPlay:COLor", enabled))

    # 查询色温等级显示开关；只执行一次 DISPlay:COLor? Query。
    def color_grade_get(self) -> bool:
        return _parse_bool(self._session.query_text(":DISPlay:COLor?"))
