# B&K Precision 9130B 稳定业务数据、配置和结果模型。
#
# 职责：定义 9130B 通道、通信接口、Typed Operations 配置、设备标识和测量结果等稳定语义。
# 边界：不拼接 SCPI、不访问 Transport，也不执行仪器 I/O 或测试判定。
# 依赖：仅依赖 Python 标准库 dataclass/Enum。

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# 表示 9130B 三个独立输出通道的稳定名称；该枚举不执行任何设备 I/O。
class Bk9130bChannel(str, Enum):
    CH1 = "CH1"
    CH2 = "CH2"
    CH3 = "CH3"


# 表示编程手册允许由 SYSTem:INTerface 选择的通信接口。
class Bk9130bInterface(str, Enum):
    RS232 = "RS232"
    USB = "USB"
    GPIB = "GPIB"


# 表示 *IDN? 返回的四段设备标识信息；只保存一次查询结果。
@dataclass(frozen=True, slots=True)
class Bk9130bIdentification:
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str


# 表示 SYSTem:ERRor? 返回的一条错误队列记录。
@dataclass(frozen=True, slots=True)
class Bk9130bSystemError:
    code: int
    message: str


# 表示指定通道 APPLy? 返回的电压和电流设定值。
@dataclass(frozen=True, slots=True)
class Bk9130bApplyState:
    voltage_v: float
    current_a: float


# 表示显式通道输出配置；CH3 的 5 V 上限会在任何 SCPI 写入之前被校验。
@dataclass(frozen=True, slots=True)
class Bk9130bChannelConfig:
    channel: Bk9130bChannel
    voltage_v: float
    current_a: float
    output_enabled: bool = True
    ovp_limit_v: float | None = None
    ovp_enabled: bool | None = None
    disable_before_configure: bool = True


# 表示一次三通道测量快照；电压、电流元组顺序固定为 CH1、CH2、CH3。
@dataclass(frozen=True, slots=True)
class Bk9130bOutputMeasurements:
    voltages_v: tuple[float, float, float]
    currents_a: tuple[float, float, float]


# 表示一次指定通道的电压、电流、功率测量结果；读取前会显式选择对应通道。
@dataclass(frozen=True, slots=True)
class Bk9130bChannelMeasurement:
    channel: Bk9130bChannel
    voltage_v: float
    current_a: float
    power_w: float
