# CPU Owner PC Driver 模型。
# 职责：表达跨芯片 NMI 能力和硬件快照。
# 边界：不暴露 CMSIS 类型、地址、IRQn 或选定芯片的位定义。
# 依赖：仅依赖 Python 标准库的不可变数据类。

from dataclasses import dataclass


# 表达 CPU Owner 发布的 NMI 源能力掩码，不包含芯片寄存器定义。
@dataclass(frozen=True, slots=True)
class CpuNmiCapabilities:
    source_mask: int


# 表达一次 NMI 硬件状态与 ISR 事件计数的同一时刻快照。
@dataclass(frozen=True, slots=True)
class CpuNmiSnapshot:
    source_raw: int
    source_masked: int
    nmi_mask: int
    nmi_status: int
    event_count: int
