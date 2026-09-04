# CAN芯片中立的配置和硬件读回。
# 职责：不可变参数、实际时序计数及控制状态。
# 边界：不编码协议、不选择实例、时钟或引脚，不保存测试结果。
# 依赖：标准库dataclass。

from dataclasses import dataclass


# 值直接来自控制器身份查询，不从Profile制造读回。
@dataclass(frozen=True, slots=True)
class CanIdentity:
    revision: int
    endian: int


# 正整数物理计数，减一寄存器编码只在固件适配内部处理。
@dataclass(frozen=True, slots=True)
class CanPhaseTiming:
    prescaler: int
    segment1: int
    segment2: int
    sjw: int


# 仲裁和数据阶段分别配置；同类型也用于表达各字段的可表示上限。
@dataclass(frozen=True, slots=True)
class CanTiming:
    nominal: CanPhaseTiming
    data: CanPhaseTiming


# 全部选项由调用者提供；不隐式补充测试模式或数据路径配置。
@dataclass(frozen=True, slots=True)
class CanOptions:
    fd_enabled: bool
    brs_enabled: bool
    automatic_retry: bool
    tx_pause: bool
    edge_filter: bool
    protocol_exception: bool
    tdc_enabled: bool
    tdc_offset_cycles: int
    tdc_filter_cycles: int
    ram_watchdog_cycles: int


# 三项硬件周期上限，不代表Observer精度或PC等待时间。
@dataclass(frozen=True, slots=True)
class CanOptionLimits:
    tdc_offset_cycles: int
    tdc_filter_cycles: int
    ram_watchdog_cycles: int
