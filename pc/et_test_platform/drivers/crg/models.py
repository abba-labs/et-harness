# CRG PC Driver Package 的models层。
#
# 职责：提供 CRG 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from dataclasses import dataclass
from enum import IntEnum


# 表示 CrgPeripheral 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
class CrgPeripheral(IntEnum):
    UART = 0
    DMA = 1
    AES = 2
    CORDIC = 3
    FMAC = 4
    CRC = 5
    STIMER = 6
    WDG = 7
    # 核间 Mailbox 控制器类别；实例号不是执行核编号。
    IPCM = 8
    # SPI控制器类别；Controller/Target角色共用同一逻辑实例。
    SPI = 9


# 表示 CRG 对 WDG 时基提供的稳定时钟源语义，不暴露芯片寄存器编码。
class CrgWdgClockSource(IntEnum):
    HSOSC = 0
    APB1 = 1


# 表示一个逻辑 WDG 的 CRG 时钟配置读回。
@dataclass(frozen=True, slots=True)
class CrgWdgClockConfig:
    source: CrgWdgClockSource
    divider: int
