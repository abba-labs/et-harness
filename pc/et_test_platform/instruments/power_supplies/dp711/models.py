# RIGOL DP711 稳定业务枚举、配置和结果模型。
#
# 职责：表达 DP711 SCPI API 的有限选项、常用 Operations 配置、测量结果、错误和定时参数。
# 边界：不生成 SCPI 文本、不访问 Transport、不执行设备 I/O 或测试断言。
# 依赖：仅依赖 Python 标准库 dataclass/Enum。

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# 表示 SCPI MINimum/MAXimum 边界查询。
class Dp711Limit(str, Enum):
    MINIMUM = "MIN"
    MAXIMUM = "MAX"


# 区分内部状态文件 RSF 与 Timer 文件 RTF。
class Dp711FileType(str, Enum):
    STATE = "RSF"
    TIMER = "RTF"


# 表示输出端 CV、CC 或未稳压 UR 模式；该类型不隐藏多步仪器操作流程。
class Dp711OutputMode(str, Enum):
    CONSTANT_VOLTAGE = "CV"
    CONSTANT_CURRENT = "CC"
    UNREGULATED = "UR"


# 表示 DP711 RS232 支持的校验方式；该类型不隐藏多步仪器操作流程。
class Dp711Parity(str, Enum):
    NONE = "NONE"
    ODD = "ODD"
    EVEN = "EVEN"


# 表示前面板英文或中文显示语言；该类型不隐藏多步仪器操作流程。
class Dp711Language(str, Enum):
    ENGLISH = "EN"
    CHINESE = "CH"


# 表示上电恢复默认状态或最后状态；该类型不隐藏多步仪器操作流程。
class Dp711PowerOnMode(str, Enum):
    DEFAULT = "DEFAULT"
    LAST = "LAST"


# 表示 Timer 结束后关闭输出或保持最后一组。
class Dp711TimerEndState(str, Enum):
    OFF = "OFF"
    LAST = "LAST"


# 表示 Timer 自动或单步触发模式；该类型不隐藏多步仪器操作流程。
class Dp711TimerTriggerMode(str, Enum):
    DEFAULT = "DEFAULT"
    SINGLE = "SINGLE"


# 表示 *IDN? 返回的四段稳定设备标识；该类型不隐藏多步仪器操作流程。
@dataclass(frozen=True, slots=True)
class Dp711Identification:
    manufacturer: str
    model: str
    serial_number: str
    software_version: str


# 表示 *OPT? 返回的三个 DP700 选件安装状态。
@dataclass(frozen=True, slots=True)
class Dp711Options:
    trigger: bool
    timer: bool
    high_resolution: bool


# 表示 APPLy? 返回的电压和电流设定值；该类型不隐藏多步仪器操作流程。
@dataclass(frozen=True, slots=True)
class Dp711ApplyState:
    voltage_v: float
    current_a: float


# 表示 MEASure:ALL? 返回的输出端电压、电流和功率。
@dataclass(frozen=True, slots=True)
class Dp711Measurement:
    voltage_v: float
    current_a: float
    power_w: float


# 表示 SYSTem:ERRor? 弹出的错误码和消息。
@dataclass(frozen=True, slots=True)
class Dp711SystemError:
    code: int
    message: str


# 表示一组 Timer 的组号、电压、电流和持续时间。
@dataclass(frozen=True, slots=True)
class Dp711TimerStep:
    group: int
    voltage_v: float
    current_a: float
    duration_s: float


# 表示一次安全输出配置；所有字段会在第一条 SCPI 写入前完成静态参数校验。
@dataclass(frozen=True, slots=True)
class Dp711OutputConfig:
    voltage_v: float
    current_a: float
    enabled: bool = True
    ocp_limit_a: float | None = None
    ovp_limit_v: float | None = None
    disable_before_configure: bool = True
