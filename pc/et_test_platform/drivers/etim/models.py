# ETIM稳定公共类型。
# 职责：表达时基、独立使能、计数和中断源快照。
# 边界：不包含芯片寄存器或测试期望。
# 依赖：仅标准库。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# 五种独立使能的公共选择；设置其中一项不隐式改变其他控制位。
class EtimEnable(IntEnum):
    MODULE = 0
    TIMER = 1
    PWM = 2
    CAPTURE = 3
    CAPTURE_LOAD = 4


# 公共中断源语义位集合；位号由本IP契约定义，不暴露底层寄存器布局。
class EtimIrq(IntFlag):
    NONE = 0
    FAULT_ONE_SHOT = 1 << 0
    FAULT_CBC = 1 << 1
    FAULT_OVERFLOW = 1 << 2
    COMPARE_ERROR = 1 << 3
    COMPARE_A = 1 << 4
    COMPARE_B = 1 << 5
    PERIOD = 1 << 6
    COUNTER_OVERFLOW = 1 << 7
    CAPTURE_1 = 1 << 8
    CAPTURE_2 = 1 << 9
    CAPTURE_3 = 1 << 10
    CAPTURE_4 = 1 << 11
    ALL = (1 << 12) - 1


# 实际分频数和完整周期Tick数，不是寄存器编码。
@dataclass(frozen=True, slots=True)
class EtimTimebase:
    divider: int
    period_ticks: int


# 当前逻辑通道发布的运行时上限与IRQ源集合，不表示所有规划Feature均可用。
@dataclass(frozen=True, slots=True)
class EtimCapabilities:
    maximum_divider: int
    maximum_period_ticks: int
    maximum_count_polls: int
    irq_sources: EtimIrq


# 实时计数与既有锁存值的两次独立采样，不承诺原子同一时刻。
@dataclass(frozen=True, slots=True)
class EtimCount:
    live: int
    latched: int


# 一次有界锁存或清零动作的前后真实观测，polls为软件采样次数而非物理时间。
@dataclass(frozen=True, slots=True)
class EtimCountObservation:
    before: int
    previous_latched: int
    latched: int
    live: int
    polls: int


# 源使能、屏蔽、原始与有效状态各自独立读取，不由其他字段推算或伪造投递数。
@dataclass(frozen=True, slots=True)
class EtimIrqSnapshot:
    enabled: EtimIrq
    masked: EtimIrq
    raw: EtimIrq
    status: EtimIrq


# 保留目标详细错误与可用观测，调用者不需要解析Wire。
class EtimOperationError(RuntimeError):
    def __init__(
        self,
        operation: str,
        instance_id: int,
        protocol_status: int,
        detail: int | None,
        observation: EtimCountObservation | None,
    ) -> None:
        self.operation = operation
        self.instance_id = instance_id
        self.protocol_status = protocol_status
        self.detail = detail
        self.observation = observation
        super().__init__(
            f"ETIM {operation} instance={instance_id} status={protocol_status} detail={detail}"
        )
