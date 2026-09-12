# ETIM本地参数校验。
# 职责：拒绝不可表示或超出公共枚举的输入。
# 边界：不查询设备、不填默认配置。
# 依赖：仅本IP模型。

from .models import EtimEnable, EtimIrq, EtimTimebase


# 校验调用方指定的整数闭区间，明确排除Python bool且不做隐式类型转换。
def integer(value: int, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


# 实际单位保持完整64位，运行时芯片上限由Driver另行检查。
def timebase(config: EtimTimebase) -> EtimTimebase:
    if not isinstance(config, EtimTimebase):
        raise ValueError("config must be EtimTimebase")
    integer(config.divider, "divider", 1, 0xFFFFFFFF)
    integer(config.period_ticks, "period_ticks", 1, 0xFFFFFFFFFFFFFFFF)
    return config


# 控制选择必须使用公共枚举，禁止把任意整数解释为SDK选择。
def control(value: EtimEnable) -> EtimEnable:
    if not isinstance(value, EtimEnable):
        raise ValueError("control must be EtimEnable")
    return value


# IRQ位集合只允许当前公共语义，force/clear必须至少选择一位。
def irq(value: EtimIrq, *, nonempty: bool = False) -> EtimIrq:
    if not isinstance(value, EtimIrq) or int(value) & ~int(EtimIrq.ALL):
        raise ValueError("sources must contain only known EtimIrq bits")
    if nonempty and not value:
        raise ValueError("sources must not be empty")
    return value
