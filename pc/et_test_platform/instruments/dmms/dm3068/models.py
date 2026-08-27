# RIGOL DM3068 稳定业务枚举、配置和响应模型。
#
# 职责：表达 DM3068 原生命令集中的有限选项、Typed Operations 配置、设备标识和系统错误结果。
# 边界：不生成 SCPI 文本、不访问 Transport，也不执行测量流程或测试判定。
# 依赖：仅依赖 Python 标准库 dataclass/Enum。

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# 表示 DM3068 可切换的三套厂家命令集；公共 Driver 默认使用 RIGOL 原生命令语义。
class Dm3068CommandSet(str, Enum):
    RIGOL = "RIGOL"
    AGILENT = "AGILENT"
    FLUKE = "FLUKE"


# 表示测量量程命令支持的标准 SCPI 边界关键字；具体量程索引由测量功能决定。
class Dm3068RangeKeyword(str, Enum):
    MINIMUM = "MIN"
    MAXIMUM = "MAX"
    DEFAULT = "DEF"


# 表示 RIGOL 原生命令中的快、中、慢三档测量速率关键字。
class Dm3068Rate(str, Enum):
    FAST = "F"
    MEDIUM = "M"
    SLOW = "S"


# 表示 MEASure 命令支持的自动或手动测量模式；只表达单条原子参数。
class Dm3068MeasurementMode(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANU"


# 表示具有 Function + Range + Rate 完整配置链的六类基础测量功能。
class Dm3068BasicMeasurementFunction(str, Enum):
    VOLTAGE_DC = "VOLTAGE_DC"
    VOLTAGE_AC = "VOLTAGE_AC"
    CURRENT_DC = "CURRENT_DC"
    CURRENT_AC = "CURRENT_AC"
    RESISTANCE_2WIRE = "RESISTANCE_2WIRE"
    RESISTANCE_4WIRE = "RESISTANCE_4WIRE"


# 表示 RS232 配置页支持的无校验、奇校验和偶校验三种模式。
class Dm3068Parity(str, Enum):
    NONE = "NONE"
    ODD = "ODD"
    EVEN = "EVEN"


# 表示触发源使用自动、单次或外部触发；该枚举不组合任何触发配置流程。
class Dm3068TriggerSource(str, Enum):
    AUTO = "AUTO"
    SINGLE = "SINGLE"
    EXTERNAL = "EXT"


# 表示触发输出 VMC 脉冲的正极性或负极性；只用于单条极性配置命令。
class Dm3068VmcPolarity(str, Enum):
    POSITIVE = "POS"
    NEGATIVE = "NEG"


# 表示上电配置恢复最后状态或默认状态；只映射 SYSTem:CONFigure:POWEron 参数。
class Dm3068PowerOnMode(str, Enum):
    LAST = "LAST"
    DEFAULT = "DEF"


# 表示数值小数点使用逗号或点号；只映射 SYSTem:FORMat:DECImal 参数。
class Dm3068DecimalMark(str, Enum):
    COMMA = "COMMA"
    DOT = "DOT"


# 表示数字分组符开启、关闭或使用空格；只映射 SYSTem:FORMat:SEPArate 参数。
class Dm3068DigitSeparator(str, Enum):
    ON = "ON"
    NONE = "NONE"
    SPACE = "SPACE"


# 表示前面板中文或英文显示语言；只映射 SYSTem:LANGuage 参数。
class Dm3068Language(str, Enum):
    CHINESE = "CHINESE"
    ENGLISH = "ENGLISH"


# 表示 *IDN? 返回的四段稳定设备标识；保留原始字段而不执行型号兼容推断。
@dataclass(frozen=True, slots=True)
class Dm3068Identification:
    manufacturer: str
    model: str
    serial_number: str
    software_version: str


# 表示 SYSTem:ERRor? 弹出的单条错误码和消息；读取动作本身由 System Control 负责。
@dataclass(frozen=True, slots=True)
class Dm3068SystemError:
    code: int
    message: str


# 表示一次基础测量 Function + Range + Rate 配置；写入前会先完成整个 Config 的本地校验。
@dataclass(frozen=True, slots=True)
class Dm3068MeasurementConfig:
    function: Dm3068BasicMeasurementFunction
    range_value: int | Dm3068RangeKeyword = Dm3068RangeKeyword.DEFAULT
    rate: Dm3068Rate = Dm3068Rate.MEDIUM


# 表示一次基础测量读取结果；value 保留对应 Function 的厂家原生物理单位。
@dataclass(frozen=True, slots=True)
class Dm3068Reading:
    function: Dm3068BasicMeasurementFunction
    value: float
