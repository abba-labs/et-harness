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


# 完整RAM布局；offset为CAN RAM内字节偏移，不是CPU地址。
# dedicated RX没有硬件数量字段，按ram_limits.rx_buffer_count预留，避免缓存虚构读回。
@dataclass(frozen=True, slots=True)
class CanRamLayout:
    std_offset: int
    std_count: int
    ext_offset: int
    ext_count: int
    tx_offset: int
    tx_buffer_count: int
    tx_fifo_count: int
    tx_queue: bool
    tx_payload_bytes: int
    event_offset: int
    event_count: int
    event_watermark: int
    rx0_offset: int
    rx0_count: int
    rx0_watermark: int
    rx0_overwrite: bool
    rx1_offset: int
    rx1_count: int
    rx1_watermark: int
    rx1_overwrite: bool
    rx_buffer_offset: int
    rx_buffer_payload_bytes: int
    rx0_payload_bytes: int
    rx1_payload_bytes: int


# 由目标实例发布的区域最大数量，不使用寄存器字段位宽猜测上限。
@dataclass(frozen=True, slots=True)
class CanRamLimits:
    ram_bytes: int
    std_count: int
    ext_count: int
    tx_count: int
    rx_fifo_count: int
    event_count: int
    rx_buffer_count: int
