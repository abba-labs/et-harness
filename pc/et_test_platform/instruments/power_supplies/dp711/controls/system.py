# RIGOL DP711 系统、前面板、串口和外部触发控制。
#
# 职责：把 SYSTem 子系统各叶子命令逐项映射为原子 API。
# 边界：不重建串口连接、不组合上电/锁定流程，也不解释屏幕图像内容。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.errors import InstrumentProtocolError
from ....common.scpi import ScpiSession
from ..models import Dp711Language, Dp711Limit, Dp711Parity, Dp711PowerOnMode, Dp711SystemError
from ..validation import (
    DP711_RS232_BAUDRATES,
    parse_bool,
    parse_system_error,
    require_integer,
    require_key,
)


# 提供 DP711 SYSTem 子系统原子控制。
class Dp711SystemControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 立即触发一次蜂鸣；不改变蜂鸣器使能状态；命令发送完成即返回，不等待蜂鸣结束。
    def beep(self) -> None:
        self._session.write(":SYSTem:BEEPer:IMMediate")

    # 打开或关闭蜂鸣器功能；只修改该配置项，不执行额外仪器动作。
    def beeper_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:BEEPer {'ON' if enabled else 'OFF'}")

    # 查询蜂鸣器功能是否打开；查询或解析过程不会修改仪器配置。
    def beeper_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:BEEPer?"))

    # 设置屏幕亮度百分比，手册范围 1 到 100；只修改该配置项，不执行额外仪器动作。
    def brightness_set(self, brightness: int) -> None:
        value = require_integer(brightness, 1, 100, "brightness")
        self._session.write(f":SYSTem:BRIGhtness {value}")

    # 查询当前、最小或最大屏幕亮度；查询或解析过程不会修改仪器配置。
    def brightness_get(self, limit: Dp711Limit | None = None) -> int:
        suffix = "" if limit is None else f" {limit.value}"
        return int(self._session.query_text(f":SYSTem:BRIGhtness?{suffix}"))

    # 设置仪器 RS232 波特率；命令生效后调用方必须按新参数重建串口连接。
    def rs232_baudrate_set(self, baudrate: int) -> None:
        if baudrate not in DP711_RS232_BAUDRATES:
            raise ValueError(f"unsupported DP711 baudrate: {baudrate}")
        self._session.write(f":SYSTem:COMMunicate:RS232:BAUD {baudrate}")

    # 查询仪器当前 RS232 波特率；查询或解析过程不会修改仪器配置。
    def rs232_baudrate_get(self) -> int:
        return int(self._session.query_text(":SYSTem:COMMunicate:RS232:BAUD?"))

    # 设置 RS232 数据位；DP711 手册固定只支持 8 位。
    def rs232_data_bits_set(self, data_bits: int) -> None:
        value = require_integer(data_bits, 8, 8, "data_bits")
        self._session.write(f":SYSTem:COMMunicate:RS232:DATABit {value}")

    # 查询 RS232 数据位；查询或解析过程不会修改仪器配置。
    def rs232_data_bits_get(self) -> int:
        return int(self._session.query_text(":SYSTem:COMMunicate:RS232:DATABit?"))

    # 设置 RS232 校验方式；当前连接参数不会被自动重建。
    def rs232_parity_set(self, parity: Dp711Parity) -> None:
        self._session.write(f":SYSTem:COMMunicate:RS232:PARItybit {parity.value}")

    # 查询 RS232 校验方式；查询或解析过程不会修改仪器配置。
    def rs232_parity_get(self) -> Dp711Parity:
        response = self._session.query_text(":SYSTem:COMMunicate:RS232:PARItybit?")
        try:
            return Dp711Parity(response.strip().upper())
        except ValueError as exc:
            raise InstrumentProtocolError(f"invalid DP711 parity response: {response!r}") from exc

    # 设置 RS232 停止位；DP711 手册固定只支持 1 位。
    def rs232_stop_bits_set(self, stop_bits: int) -> None:
        value = require_integer(stop_bits, 1, 1, "stop_bits")
        self._session.write(f":SYSTem:COMMunicate:RS232:STOPBit {value}")

    # 查询 RS232 停止位；查询或解析过程不会修改仪器配置。
    def rs232_stop_bits_get(self) -> int:
        return int(self._session.query_text(":SYSTem:COMMunicate:RS232:STOPBit?"))

    # 读取并弹出错误队列中的最后一条错误；查询或解析过程不会修改仪器配置。
    def error_get(self) -> Dp711SystemError:
        return parse_system_error(self._session.query_text(":SYSTem:ERRor?"))

    # 查询风扇上电自检结果原始文本；查询或解析过程不会修改仪器配置。
    def fan_test_get(self) -> str:
        return self._session.query_text(":SYSTem:FAN?")

    # 锁定或解锁指定前面板按键/旋钮；只修改该配置项，不执行额外仪器动作。
    def key_locked_set(self, key: str, locked: bool) -> None:
        normalized = require_key(key)
        self._session.write(f":SYSTem:KLOCk {normalized},{'ON' if locked else 'OFF'}")

    # 查询指定前面板按键/旋钮是否锁定；查询或解析过程不会修改仪器配置。
    def key_locked_get(self, key: str) -> bool:
        normalized = require_key(key)
        return parse_bool(self._session.query_text(f":SYSTem:KLOCk? {normalized}"))

    # 打开或关闭远程锁定；打开后前面板无法直接返回本地模式。
    def remote_lock_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:KLOCk:STATe {'ON' if enabled else 'OFF'}")

    # 查询远程锁定是否打开；查询或解析过程不会修改仪器配置。
    def remote_lock_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:KLOCk:STATe?"))

    # 设置界面语言为英文或中文；只修改该配置项，不执行额外仪器动作。
    def language_set(self, language: Dp711Language) -> None:
        self._session.write(f":SYSTem:LANGuage:TYPE {language.value}")

    # 查询当前界面语言并归一化为稳定枚举；查询或解析过程不会修改仪器配置。
    def language_get(self) -> Dp711Language:
        response = self._session.query_text(":SYSTem:LANGuage:TYPE?").strip().upper()
        if response in {"EN", "ENGLISH"}:
            return Dp711Language.ENGLISH
        if response in {"CH", "CHINESE"}:
            return Dp711Language.CHINESE
        raise InstrumentProtocolError(f"invalid DP711 language response: {response!r}")

    # 让仪器返回本地模式；该命令还会解除远程锁定；只修改该配置项，不执行额外仪器动作。
    def local_mode_set(self) -> None:
        self._session.write(":SYSTem:LOCal")

    # 打开或关闭普通前面板锁定；只修改该配置项，不执行额外仪器动作。
    def panel_lock_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:LOCK {'ON' if enabled else 'OFF'}")

    # 查询普通前面板锁定是否打开；查询或解析过程不会修改仪器配置。
    def panel_lock_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:LOCK?"))

    # 设置上电恢复默认状态或最后状态；只修改该配置项，不执行额外仪器动作。
    def power_on_mode_set(self, mode: Dp711PowerOnMode) -> None:
        self._session.write(f":SYSTem:POWEron {mode.value}")

    # 查询当前上电恢复模式；查询或解析过程不会修改仪器配置。
    def power_on_mode_get(self) -> Dp711PowerOnMode:
        response = self._session.query_text(":SYSTem:POWEron?").strip().upper()
        try:
            return Dp711PowerOnMode(response)
        except ValueError as exc:
            raise InstrumentProtocolError(f"invalid DP711 power-on mode: {response!r}") from exc

    # 读取当前屏幕图像数据；SCPI block 返回时去除 block header。
    def screen_image_get(self) -> bytes:
        return self._session.query_bytes(":SYSTem:PRINT?")

    # 让仪器进入远程模式；不自动锁定远程会话；只修改该配置项，不执行额外仪器动作。
    def remote_mode_set(self) -> None:
        self._session.write(":SYSTem:REMote")

    # 使用 RWLock 命令打开或关闭远程锁定；该命令没有对应查询形式。
    def rwlock_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:RWLock {'ON' if enabled else 'OFF'}")

    # 打开或关闭屏幕保护功能；只修改该配置项，不执行额外仪器动作。
    def screen_saver_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:SAVer {'ON' if enabled else 'OFF'}")

    # 查询屏幕保护功能是否打开；查询或解析过程不会修改仪器配置。
    def screen_saver_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:SAVer?"))

    # 查询仪器系统自检结果原始文本；查询或解析过程不会修改仪器配置。
    def self_test_get(self) -> str:
        return self._session.query_text(":SYSTem:SELF:TEST?")

    # 打开或关闭外部触发输入；该能力要求 Trigger 选件。
    def trigger_input_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:TRIGger:IN:STATe {'ON' if enabled else 'OFF'}")

    # 查询外部触发输入是否打开；查询或解析过程不会修改仪器配置。
    def trigger_input_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:TRIGger:IN:STATe?"))

    # 打开或关闭外部触发输出；该能力要求 Trigger 选件。
    def trigger_output_enabled_set(self, enabled: bool) -> None:
        self._session.write(f":SYSTem:TRIGger:OUT:STATe {'ON' if enabled else 'OFF'}")

    # 查询外部触发输出是否打开；查询或解析过程不会修改仪器配置。
    def trigger_output_enabled_get(self) -> bool:
        return parse_bool(self._session.query_text(":SYSTem:TRIGger:OUT:STATe?"))

    # 查询设备实现的 SCPI 版本文本；查询或解析过程不会修改仪器配置。
    def scpi_version_get(self) -> str:
        return self._session.query_text(":SYSTem:VERSion?")
