# RIGOL DM3068 System 与系统显示设置原子控制。
#
# 职责：映射 Common SYSTem 以及 RIGOL 原生 SYSTem 子系统中的单条控制和查询命令。
# 边界：不操作 LAN/GPIB/RS232 参数，不组合复位、测量或测试流程。
# 依赖：仅依赖公共 ScpiSession、本型号 models 与 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import (
    Dm3068DecimalMark,
    Dm3068DigitSeparator,
    Dm3068Language,
    Dm3068PowerOnMode,
    Dm3068SystemError,
)
from ..validation import _bool_token, _parse_bool, _parse_error, _parse_int


# 提供 DM3068 系统错误、显示、格式、语言和设备信息的原子访问接口。
class Dm3068SystemControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 弹出并返回一条系统错误；只执行 SYSTem:ERRor?，不循环清空错误队列。
    def error_get(self) -> Dm3068SystemError:
        return _parse_error(self._session.query_text(":SYSTem:ERRor?"))

    # 查询 SCPI 版本字符串；只执行一次 SYSTem:VERSion? Query。
    def version_get(self) -> str:
        return self._session.query_text(":SYSTem:VERSion?").strip()

    # 触发一次蜂鸣动作；只发送 SYSTem:BEEPer，不改变蜂鸣器全局使能状态。
    def beeper(self) -> None:
        self._session.write(":SYSTem:BEEPer")

    # 设置蜂鸣器使能状态；只写入 SYSTem:BEEPer:STATe，不触发蜂鸣动作。
    def beeper_state_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:BEEPer:STATe {_bool_token(enabled)}")

    # 查询蜂鸣器使能状态；只读取 SYSTem:BEEPer:STATe? 当前值。
    def beeper_state_get(self) -> bool:
        return _parse_bool(self._session.query_text(":SYSTem:BEEPer:STATe?"))

    # 查询仪器时钟文本；只执行一次 SYSTem:CLOCk? Query，不修改系统时间。
    def clock_get(self) -> str:
        return self._session.query_text(":SYSTem:CLOCk?").strip()

    # 恢复系统默认配置；只发送 SYSTem:CONFigure:DEFault，不追加 *RST。
    def configure_default(self) -> None:
        self._session.write(":SYSTem:CONFigure:DEFault")

    # 设置上电恢复模式；只写入 SYSTem:CONFigure:POWEron，不立即恢复配置。
    def power_on_mode_set(self, mode: Dm3068PowerOnMode) -> None:
        self._session.write(f":SYSTem:CONFigure:POWEron {mode.value}")

    # 设置显示亮度等级；只写入 SYSTem:DISPlay:BRIGht，不改变对比度。
    def display_brightness_set(self, value: int) -> None:
        self._session.write(f":SYSTem:DISPlay:BRIGht {value}")

    # 查询显示亮度等级；只读取 SYSTem:DISPlay:BRIGht? 当前值。
    def display_brightness_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:DISPlay:BRIGht?"))

    # 设置显示对比度等级；只写入 SYSTem:DISPlay:CONTrast，不改变亮度。
    def display_contrast_set(self, value: int) -> None:
        self._session.write(f":SYSTem:DISPlay:CONTrast {value}")

    # 查询显示对比度等级；只读取 SYSTem:DISPlay:CONTrast? 当前值。
    def display_contrast_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:DISPlay:CONTrast?"))

    # 反转一次显示配色；只发送 SYSTem:DISPlay:INVErt，不组合其他显示设置。
    def display_invert(self) -> None:
        self._session.write(":SYSTem:DISPlay:INVErt")

    # 查询硬件或软件版本标识文本；只执行 SYSTem:EDITion? Query。
    def edition_get(self) -> str:
        return self._session.query_text(":SYSTem:EDITion?").strip()

    # 设置小数点显示格式；只写入 SYSTem:FORMat:DECImal，不改变分组符。
    def decimal_mark_set(self, mark: Dm3068DecimalMark) -> None:
        self._session.write(f":SYSTem:FORMat:DECImal {mark.value}")

    # 查询小数点显示格式；只读取 SYSTem:FORMat:DECImal? 当前值。
    def decimal_mark_get(self) -> str:
        return self._session.query_text(":SYSTem:FORMat:DECImal?").strip()

    # 设置数字分组符格式；只写入 SYSTem:FORMat:SEPArate，不改变小数点。
    def digit_separator_set(self, separator: Dm3068DigitSeparator) -> None:
        self._session.write(f":SYSTem:FORMat:SEPArate {separator.value}")

    # 查询数字分组符格式；只读取 SYSTem:FORMat:SEPArate? 当前值。
    def digit_separator_get(self) -> str:
        return self._session.query_text(":SYSTem:FORMat:SEPArate?").strip()

    # 设置前面板显示语言；只写入 SYSTem:LANGuage，不改变命令集。
    def language_set(self, language: Dm3068Language) -> None:
        self._session.write(f":SYSTem:LANGuage {language.value}")

    # 查询前面板显示语言；只读取 SYSTem:LANGuage? 当前值。
    def language_get(self) -> str:
        return self._session.query_text(":SYSTem:LANGuage?").strip()

    # 查询 LAN MAC 地址文本；只执行 SYSTem:MACAddr? Query，不改网络参数。
    def mac_address_get(self) -> str:
        return self._session.query_text(":SYSTem:MACAddr?").strip()

    # 查询仪器累计开机次数；只执行 SYSTem:OPENtimes? Query。
    def open_times_get(self) -> int:
        return _parse_int(self._session.query_text(":SYSTem:OPENtimes?"))

    # 查询仪器序列号文本；只执行 SYSTem:SERIal? Query，不修改设备信息。
    def serial_number_get(self) -> str:
        return self._session.query_text(":SYSTem:SERIal?").strip()

    # 查询仪器类型文本；只执行 SYSTem:TYPE? Query，不执行型号兼容推断。
    def type_get(self) -> str:
        return self._session.query_text(":SYSTem:TYPE?").strip()
