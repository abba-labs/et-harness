# RIGOL DM3068 仪器适配包公共入口。
#
# 职责：导出 DM3068 Driver、LAN/串口构造、Typed Operations 配置、稳定枚举和结果模型。
# 边界：不在导入时创建连接、不执行设备 I/O，也不暴露兼容命令集的重复语法层。
# 依赖：仅依赖本型号 connection、driver、models 和 operations。

from .connection import create_dm3068_lan_driver, create_dm3068_serial_driver
from .driver import Dm3068Driver
from .models import (
    Dm3068BasicMeasurementFunction,
    Dm3068CommandSet,
    Dm3068DecimalMark,
    Dm3068DigitSeparator,
    Dm3068Identification,
    Dm3068Language,
    Dm3068MeasurementConfig,
    Dm3068MeasurementMode,
    Dm3068Parity,
    Dm3068PowerOnMode,
    Dm3068RangeKeyword,
    Dm3068Rate,
    Dm3068Reading,
    Dm3068SystemError,
    Dm3068TriggerSource,
    Dm3068VmcPolarity,
)
from .operations import (
    Dm3068Operations,
    configure_dc_current,
    configure_dc_voltage,
    configure_external_trigger,
    configure_resistance_4wire,
)

__all__ = [
    "Dm3068BasicMeasurementFunction",
    "Dm3068CommandSet",
    "Dm3068DecimalMark",
    "Dm3068DigitSeparator",
    "Dm3068Driver",
    "Dm3068Identification",
    "Dm3068Language",
    "Dm3068MeasurementConfig",
    "Dm3068MeasurementMode",
    "Dm3068Operations",
    "Dm3068Parity",
    "Dm3068PowerOnMode",
    "Dm3068RangeKeyword",
    "Dm3068Rate",
    "Dm3068Reading",
    "Dm3068SystemError",
    "Dm3068TriggerSource",
    "Dm3068VmcPolarity",
    "configure_dc_current",
    "configure_dc_voltage",
    "configure_external_trigger",
    "configure_resistance_4wire",
    "create_dm3068_lan_driver",
    "create_dm3068_serial_driver",
]
