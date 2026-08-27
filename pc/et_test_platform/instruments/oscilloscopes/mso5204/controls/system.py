# RIGOL MSO5204 系统设置原子控制。
#
# 职责：完整映射 SYSTem 命令组，包括面板设置、日期时间、选件、错误、系统配置数据块和硬件模块查询。
# 边界：不替调用方重启仪器、不解释选件业务资格，也不自动修改测试流程或 PASS/FAIL。
# 依赖：仅依赖 Python datetime、公共 ScpiSession、系统错误模型和基础解析辅助函数。

from __future__ import annotations

from datetime import date

from ....common.scpi import ScpiSession
from ..models import Mso5204SystemError
from ..validation import (
    _command,
    _parse_bool,
    _parse_csv_ints,
    _parse_int,
    _parse_system_error,
    _query_command,
)


# 提供 MSO5000 Programming Guide 全部 SYSTem 原子命令的稳定访问接口。
class Mso5204SystemControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置后面板 TRIG OUT 输出类型；参数接受 TOUT 或 PFAil。
    def auxiliary_output_set(self, output_type: str) -> None:
        self._session.write(_command(":SYSTem:AOUTput", output_type))

    # 查询 TRIG OUT 输出类型；保留仪器返回的 TOUT 或 PFA 字符串。
    def auxiliary_output_get(self) -> str:
        return self._session.query_text(":SYSTem:AOUTput?")

    # 启用或禁用前面板 AUTO 键功能；只发送一次 SYSTem:AUToscale 命令。
    def autoscale_key_enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":SYSTem:AUToscale", enabled))

    # 查询前面板 AUTO 键功能开关；只执行一次 SYSTem:AUToscale? Query。
    def autoscale_key_enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":SYSTem:AUToscale?"))

    # 打开或关闭蜂鸣器；只发送一次 SYSTem:BEEPer 命令。
    def beeper_set(self, enabled: bool) -> None:
        self._session.write(_command(":SYSTem:BEEPer", enabled))

    # 查询蜂鸣器开关；只执行一次 SYSTem:BEEPer? Query。
    def beeper_get(self) -> bool:
        return _parse_bool(self._session.query_text(":SYSTem:BEEPer?"))

    # 设置系统日期；先用 Python 日期规则拒绝不存在的年月日，再发送一次 SYSTem:DATE。
    def date_set(self, year: int, month: int, day: int) -> None:
        parsed = date(int(year), int(month), int(day))
        if not 2017 <= parsed.year <= 2099:
            raise ValueError("MSO5204 system year must be 2017..2099")
        self._session.write(_command(":SYSTem:DATE", parsed.year, parsed.month, parsed.day))

    # 查询系统日期；返回 year、month、day 三个整数。
    def date_get(self) -> tuple[int, int, int]:
        values = _parse_csv_ints(self._session.query_text(":SYSTem:DATE?"))
        if len(values) != 3:
            raise ValueError(f"invalid system date response: {values!r}")
        return values[0], values[1], values[2]

    # 查询并弹出最新系统错误；只执行一次 SYSTem:ERRor:NEXT? Query。
    def error_get(self) -> Mso5204SystemError:
        return _parse_system_error(self._session.query_text(":SYSTem:ERRor:NEXT?"))

    # 查询屏幕水平方向网格数量；MSO5000 手册定义当前固定返回 10。
    def horizontal_grid_count_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:GAMount?"))

    # 设置 GPIB 地址；手册范围为 1..30，超出范围在写入前拒绝。
    def gpib_address_set(self, address: int) -> None:
        number = int(address)
        if not 1 <= number <= 30:
            raise ValueError("GPIB address must be 1..30")
        self._session.write(_command(":SYSTem:GPIB", number))

    # 查询 GPIB 地址；返回 1..30 的整数地址。
    def gpib_address_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:GPIB?"))

    # 模拟按下指定前面板按键；只发送一次 SYSTem:KEY:PRESs 命令。
    def key_press(self, key: str) -> None:
        self._session.write(_command(":SYSTem:KEY:PRESs", key))

    # 模拟指定旋钮顺时针增加；可选 val 表示旋转次数，不附加其他操作。
    def key_increase(self, key: str, value: int | None = None) -> None:
        if value is None:
            self._session.write(_command(":SYSTem:KEY:INCRease", key))
            return
        self._session.write(_command(":SYSTem:KEY:INCRease", key, int(value)))

    # 模拟指定旋钮逆时针减少；可选 val 表示旋转次数，不附加其他操作。
    def key_decrease(self, key: str, value: int | None = None) -> None:
        if value is None:
            self._session.write(_command(":SYSTem:KEY:DECRease", key))
            return
        self._session.write(_command(":SYSTem:KEY:DECRease", key, int(value)))

    # 设置系统界面语言；只发送一次 SYSTem:LANGuage 命令。
    def language_set(self, language: str) -> None:
        self._session.write(_command(":SYSTem:LANGuage", language))

    # 查询系统界面语言；保留仪器返回的 ENGL、SCH、JAP 等缩写。
    def language_get(self) -> str:
        return self._session.query_text(":SYSTem:LANGuage?")

    # 设置下次上电恢复方式；参数接受 LATest 或 DEFault。
    def power_on_mode_set(self, mode: str) -> None:
        self._session.write(_command(":SYSTem:PON", mode))

    # 查询下次上电恢复方式；保留仪器返回的 LAT 或 DEF 字符串。
    def power_on_mode_get(self) -> str:
        return self._session.query_text(":SYSTem:PON?")

    # 安装一条仪器选件许可证；只发送一次 SYSTem:OPTion:INSTall 命令。
    def option_install(self, license_text: str) -> None:
        self._session.write(_command(":SYSTem:OPTion:INSTall", license_text))

    # 卸载全部官方选件；只发送一次 SYSTem:OPTion:UNINstall，是否重启由调用方决定。
    def options_uninstall_all(self) -> None:
        self._session.write(":SYSTem:OPTion:UNINstall")

    # 查询指定选件是否安装；参数接受 AWG、PWR、AUTO、EMBD 等手册选件类型。
    def option_status_get(self, option_type: str) -> bool:
        return _parse_bool(
            self._session.query_text(_query_command(":SYSTem:OPTion:STATus", option_type))
        )

    # 查询当前模拟通道数量；MSO5204 正常返回 4，但 API 保留仪器实际结果。
    def analog_channel_count_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:RAMount?"))

    # 一次写入完整系统设置数据块；ScpiSession 自动生成 IEEE488.2 definite-length block 头。
    def setup_set(self, setup_data: bytes, *, timeout_s: float | None = None) -> None:
        self._session.write_definite_block(
            ":SYSTem:SETup",
            setup_data,
            timeout_s=timeout_s,
        )

    # 读取系统设置数据块；ScpiSession 返回已经去除 TMC 数据块头的有效设置载荷。
    def setup_get(self, *, timeout_s: float | None = None) -> bytes:
        return self._session.query_bytes(":SYSTem:SETup?", timeout_s=timeout_s)

    # 设置屏幕保护等待时间，单位为 minute；手册范围为 1..999。
    def screen_saver_time_set(self, minutes: int) -> None:
        value = int(minutes)
        if not 1 <= value <= 999:
            raise ValueError("screen saver time must be 1..999 minutes")
        self._session.write(_command(":SYSTem:SSAVer:TIME", value))

    # 查询屏幕保护等待时间；返回以 minute 为单位的整数。
    def screen_saver_time_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:SSAVer:TIME?"))

    # 设置系统时间；小时、分钟、秒在写入前按手册范围检查。
    def time_set(self, hours: int, minutes: int, seconds: int) -> None:
        h = int(hours)
        m = int(minutes)
        s = int(seconds)
        if not 0 <= h <= 23 or not 0 <= m <= 59 or not 0 <= s <= 59:
            raise ValueError("invalid MSO5204 system time")
        self._session.write(_command(":SYSTem:TIME", h, m, s))

    # 查询系统时间；返回 hours、minutes、seconds 三个整数。
    def time_get(self) -> tuple[int, int, int]:
        values = _parse_csv_ints(self._session.query_text(":SYSTem:TIME?"))
        if len(values) != 3:
            raise ValueError(f"invalid system time response: {values!r}")
        return values[0], values[1], values[2]

    # 打开或关闭前面板键盘锁；只发送一次 SYSTem:LOCKed 命令。
    def locked_set(self, enabled: bool) -> None:
        self._session.write(_command(":SYSTem:LOCKed", enabled))

    # 查询前面板键盘锁状态；只执行一次 SYSTem:LOCKed? Query。
    def locked_get(self) -> bool:
        return _parse_bool(self._session.query_text(":SYSTem:LOCKed?"))

    # 查询硬件模块存在状态；返回手册定义的逗号分隔整数序列。
    def modules_get(self) -> tuple[int, ...]:
        return _parse_csv_ints(self._session.query_text(":SYSTem:MODules?"))
