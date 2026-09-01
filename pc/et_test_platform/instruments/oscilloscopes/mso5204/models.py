# RIGOL MSO5204 稳定业务枚举、配置和结果模型。
#
# 职责：表达核心示波器控制参数、常用 Operations 配置、设备标识和测量/波形结果。
# 边界：不生成 SCPI 文本、不访问 Transport，也不执行测试 PASS/FAIL 判定。
# 依赖：仅依赖 Python 标准库 dataclass、Enum 和 IntEnum。

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


# 表示 MSO5204 四个模拟输入通道的稳定编号；枚举值直接对应 CHANnel1..CHANnel4 的通道号。
class Mso5204AnalogChannel(IntEnum):
    CH1 = 1
    CH2 = 2
    CH3 = 3
    CH4 = 4


# 表示 ACQuire:TYPE 支持的采集模式；枚举只表达手册参数，不改变当前采集状态或平均次数。
class Mso5204AcquireType(str, Enum):
    NORMAL = "NORMal"
    AVERAGE = "AVERages"
    PEAK_DETECT = "PEAK"
    HIGH_RESOLUTION = "HRESolution"


# 表示 ACQuire:MDEPth 支持的离散存储深度；AUTO 让仪器根据采样率自动选择。
class Mso5204MemoryDepth(str, Enum):
    AUTO = "AUTO"
    PTS_1K = "1k"
    PTS_10K = "10k"
    PTS_100K = "100k"
    PTS_1M = "1M"
    PTS_10M = "10M"
    PTS_25M = "25M"
    PTS_50M = "50M"
    PTS_100M = "100M"
    PTS_200M = "200M"


# 表示模拟通道 AC/DC/GND 输入耦合方式；枚举只表达手册参数，不执行任何通道配置动作。
class Mso5204ChannelCoupling(str, Enum):
    DC = "DC"
    AC = "AC"
    GROUND = "GND"


# 表示 MSO5204 模拟通道实际支持的带宽限制选项；枚举只保存 OFF、20M、100M 三种参数值。
class Mso5204BandwidthLimit(str, Enum):
    OFF = "OFF"
    MHZ_20 = "20M"
    MHZ_100 = "100M"


# 表示模拟通道幅值显示单位；枚举只表达 CHANnel<n>:UNITs 的手册离散参数。
class Mso5204ChannelUnit(str, Enum):
    VOLTAGE = "VOLTage"
    WATT = "WATT"
    AMPERE = "AMPere"
    UNKNOWN = "UNKNown"


# 表示水平时基工作模式；YT 使用手册 MAIN 参数，枚举本身不改变时基刻度或水平偏移。
class Mso5204TimebaseMode(str, Enum):
    YT = "MAIN"
    XY = "XY"
    ROLL = "ROLL"


# 表示 TRIGger:MODE 允许的触发类型；枚举只保存 SCPI 参数，不自动配置各触发子系统的条件。
class Mso5204TriggerMode(str, Enum):
    EDGE = "EDGE"
    PULSE = "PULSe"
    SLOPE = "SLOPe"
    VIDEO = "VIDeo"
    PATTERN = "PATTern"
    DURATION = "DURation"
    TIMEOUT = "TIMeout"
    RUNT = "RUNT"
    WINDOW = "WINDow"
    DELAY = "DELay"
    SETUP_HOLD = "SETup"
    NTH_EDGE = "NEDGe"
    RS232 = "RS232"
    I2C = "IIC"
    CAN = "CAN"
    SPI = "SPI"
    FLEXRAY = "FLEXray"
    I2S = "IIS"
    LIN = "LIN"
    MIL1553 = "M1553"


# 表示 TRIGger:SWEep 的 AUTO/NORMAL/SINGLE 扫描方式；枚举只表达设置值，不主动开始采集。
class Mso5204TriggerSweep(str, Enum):
    AUTO = "AUTO"
    NORMAL = "NORMal"
    SINGLE = "SINGle"


# 表示模拟边沿触发的 AC/DC/HF/LF 抑制耦合选项；枚举只表达手册 SCPI 参数，不修改触发源。
class Mso5204TriggerCoupling(str, Enum):
    DC = "DC"
    AC = "AC"
    HF_REJECT = "HFReject"
    LF_REJECT = "LFReject"


# 表示 EDGE 触发的上升沿、下降沿或任一沿斜率；枚举只表达 SLOPe 参数，不改变触发电平。
class Mso5204TriggerSlope(str, Enum):
    RISING = "POSitive"
    FALLING = "NEGative"
    EITHER = "RFALl"


# 表示 WAVeform:MODE 的 NORMal/MAXimum/RAW 读取模式；枚举不改变示波器 RUN/STOP 状态。
class Mso5204WaveformMode(str, Enum):
    NORMAL = "NORMal"
    MAXIMUM = "MAXimum"
    RAW = "RAW"


# 表示 WAVeform:FORMat 的 BYTE/WORD/ASCII 编码方式；枚举只选择传输格式，不进行数据解析。
class Mso5204WaveformFormat(str, Enum):
    BYTE = "BYTE"
    WORD = "WORD"
    ASCII = "ASCii"


# 表示常用波形数据源；数字通道和数学通道也可以直接用字符串传入控制 API，不执行来源切换。
class Mso5204WaveformSource(str, Enum):
    CH1 = "CHANnel1"
    CH2 = "CHANnel2"
    CH3 = "CHANnel3"
    CH4 = "CHANnel4"
    MATH1 = "MATH1"
    MATH2 = "MATH2"
    MATH3 = "MATH3"
    MATH4 = "MATH4"


# 表示 MEASure:ITEM 支持的 41 个稳定测量参数；枚举不启用屏幕测量项。
class Mso5204MeasurementItem(str, Enum):
    VMAX = "VMAX"
    VMIN = "VMIN"
    VPP = "VPP"
    VTOP = "VTOP"
    VBASE = "VBASe"
    VAMPLITUDE = "VAMP"
    VAVERAGE = "VAVG"
    VRMS = "VRMS"
    OVERSHOOT = "OVERshoot"
    PRESHOOT = "PREShoot"
    AREA = "MARea"
    PERIOD_AREA = "MPARea"
    PERIOD = "PERiod"
    FREQUENCY = "FREQuency"
    RISE_TIME = "RTIMe"
    FALL_TIME = "FTIMe"
    POSITIVE_WIDTH = "PWIDth"
    NEGATIVE_WIDTH = "NWIDth"
    POSITIVE_DUTY = "PDUTy"
    NEGATIVE_DUTY = "NDUTy"
    TIME_VMAX = "TVMAX"
    TIME_VMIN = "TVMIN"
    POSITIVE_SLEW_RATE = "PSLewrate"
    NEGATIVE_SLEW_RATE = "NSLewrate"
    VUPPER = "VUPPer"
    VMID = "VMID"
    VLOWER = "VLOWer"
    VARIANCE = "VARiance"
    PERIOD_VRMS = "PVRMs"
    POSITIVE_PULSES = "PPULses"
    NEGATIVE_PULSES = "NPULses"
    POSITIVE_EDGES = "PEDGes"
    NEGATIVE_EDGES = "NEDGes"
    RR_DELAY = "RRDelay"
    RF_DELAY = "RFDelay"
    FR_DELAY = "FRDelay"
    FF_DELAY = "FFDelay"
    RR_PHASE = "RRPHase"
    RF_PHASE = "RFPHase"
    FR_PHASE = "FRPHase"
    FF_PHASE = "FFPHase"


# 表示 MEASure:STATistic:ITEM? 支持的统计结果类型；枚举本身不打开统计显示。
class Mso5204MeasurementStatistic(str, Enum):
    MAXIMUM = "MAXimum"
    MINIMUM = "MINimum"
    CURRENT = "CURRent"
    AVERAGE = "AVERages"
    DEVIATION = "DEViation"
    COUNT = "CNT"


# 表示一次 *IDN? 响应解析后的厂商、型号、序列号和软件版本；该结果模型不执行任何仪器 I/O。
@dataclass(frozen=True, slots=True)
class Mso5204Identification:
    manufacturer: str
    model: str
    serial_number: str
    software_version: str


# 表示 SYSTem:ERRor? 弹出的错误码和错误文本；该结果模型只保存已解析数据，不访问仪器。
@dataclass(frozen=True, slots=True)
class Mso5204SystemError:
    code: int
    message: str


# 表示 WAVeform:PREamble? 返回的十个波形缩放参数；模型仅保存换算所需元数据，不读取波形数据。
@dataclass(frozen=True, slots=True)
class Mso5204WaveformPreamble:
    format_code: int
    type_code: int
    points: int
    count: int
    x_increment_s: float
    x_origin_s: float
    x_reference: float
    y_increment_v: float
    y_origin: float
    y_reference: float


# 表示一次已经换算到物理时间/电压单位的模拟波形读取结果；模型不执行采集、触发或测试判定。
@dataclass(frozen=True, slots=True)
class Mso5204Waveform:
    preamble: Mso5204WaveformPreamble
    samples: tuple[float, ...]
    times_s: tuple[float, ...]


# 表示常用 EDGE 捕获的显式配置；None 字段表示该项保持仪器当前状态，不发生隐式修改。
@dataclass(frozen=True, slots=True)
class Mso5204EdgeCaptureConfig:
    channel: int | Mso5204AnalogChannel
    vertical_scale_v: float
    time_scale_s: float
    trigger_level_v: float
    trigger_slope: Mso5204TriggerSlope = Mso5204TriggerSlope.RISING
    coupling: Mso5204ChannelCoupling = Mso5204ChannelCoupling.DC
    probe_ratio: float | None = None
    bandwidth_limit: Mso5204BandwidthLimit | None = None
    vertical_offset_v: float | None = None
    time_offset_s: float | None = None
    acquire_type: Mso5204AcquireType | None = None
    average_count: int | None = None
    trigger_sweep: Mso5204TriggerSweep | None = None


# 表示 NORMal/BYTE 屏幕波形读取区间；Operation 固定按屏幕 1..1000 点语义执行。
@dataclass(frozen=True, slots=True)
class Mso5204WaveformReadConfig:
    channel: int | Mso5204AnalogChannel
    start: int = 1
    stop: int = 1000
    timeout_s: float | None = None


# 表示一次常用单通道自动测量快照；字段保持仪器原生物理量单位，不执行阈值判定。
@dataclass(frozen=True, slots=True)
class Mso5204SignalMeasurements:
    frequency_hz: float
    period_s: float
    duty_cycle_percent: float
    vpp_v: float
    vrms_v: float
    rise_time_s: float
    fall_time_s: float
