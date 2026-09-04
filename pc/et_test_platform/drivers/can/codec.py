# CAN纯Wire编解码。
# 职责：明确字段顺序、精确长度与Boolean约束。
# 边界：不执行I/O，不读取Profile，不缓存期望硬件结果。
# 依赖：本IP合同/Model及统一ProtocolError。

from ...core.errors import ProtocolError
from . import contract
from .models import (
    CanBusConfig,
    CanOptions,
    CanPhaseTiming,
    CanRamLayout,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanUnmatchedPolicy,
)

BUS_SELECTORS = {
    "timestamp_source": CanTimestampSource,
    "timeout_source": CanTimeoutSource,
    "unmatched_ext": CanUnmatchedPolicy,
    "unmatched_std": CanUnmatchedPolicy,
}


# 不接受bool冒充计数，负值和超宽值必须在发命令前被拒绝。
def uint32(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"CAN value must be uint32: {value!r}")
    return value


# 只有真正的Boolean可作为使能参数，避免非零值被静默归一化。
def boolean(value: bool) -> int:
    if type(value) is not bool:
        raise ValueError("CAN flag must be bool")
    return int(value)


# 实例前缀与路由实例必须一致；命令严格由枚举指定。
def encode_request(command: contract.CanCommand, instance_id: int, words: tuple[int, ...]) -> bytes:
    if not isinstance(command, contract.CanCommand):
        raise ValueError("CAN command must be CanCommand")
    uint32(instance_id)
    if instance_id > 0xFF or len(words) != contract.REQUEST_WORDS[command]:
        raise ValueError(f"CAN {command.name}: invalid instance or field count")
    return contract.INSTANCE.pack(instance_id) + b"".join(
        contract.WORD.pack(uint32(value)) for value in words
    )


# 固件返回的空响应也必须确实为空，不接受截断或附加字节。
def decode_response(command: contract.CanCommand, body: bytes) -> tuple[int, ...]:
    expected = contract.RESPONSE_WORDS[command] * contract.WORD.size
    if len(body) != expected:
        raise ProtocolError(f"CAN {command.name}: response bytes {len(body)} != {expected}")
    return tuple(value[0] for value in contract.WORD.iter_unpack(body))


# 编码两阶段实际计数；硬件上限由选中实例的Wrap验证，不在PC固化。
def timing_words(timing: CanTiming) -> tuple[int, ...]:
    if not isinstance(timing, CanTiming):
        raise ValueError("CAN timing requires CanTiming")
    result = []
    for phase in (timing.nominal, timing.data):
        if not isinstance(phase, CanPhaseTiming):
            raise ValueError("CAN phase requires CanPhaseTiming")
        values = tuple(uint32(getattr(phase, name)) for name in contract.PHASE_FIELDS)
        if not all(values) or phase.sjw > min(phase.segment1, phase.segment2):
            raise ValueError("CAN timing counts must be positive and SJW must fit both segments")
        result.extend(values)
    return tuple(result)


# 解码后的零计数不是有效实际时序；不把无效返回当成设备默认配置。
def decode_timing(words: tuple[int, ...]) -> CanTiming:
    if len(words) != 2 * len(contract.PHASE_FIELDS) or not all(words):
        raise ProtocolError("CAN timing readback has invalid field count or zero count")
    split = len(contract.PHASE_FIELDS)
    return CanTiming(CanPhaseTiming(*words[:split]), CanPhaseTiming(*words[split:]))


# 公开自动重传与异常处理使用正语义；固件内部处理对应Disable位。
def option_words(options: CanOptions) -> tuple[int, ...]:
    if not isinstance(options, CanOptions):
        raise ValueError("CAN options require CanOptions")
    return tuple(boolean(getattr(options, name)) for name in contract.OPTION_FLAGS) + tuple(
        uint32(getattr(options, name)) for name in contract.OPTION_COUNTS
    )


# 不接受非法Boolean，也不使用请求缓存补齐缺失字段。
def decode_options(words: tuple[int, ...]) -> CanOptions:
    count = len(contract.OPTION_FLAGS)
    if len(words) != count + len(contract.OPTION_COUNTS) or any(
        value not in (0, 1) for value in words[:count]
    ):
        raise ProtocolError("CAN options readback has invalid flags or field count")
    return CanOptions(*(bool(value) for value in words[:count]), *words[count:])


# RAM参数不包含芯片地址；范围和区域重叠由选中实例的Wrap在写入前统一验证。
def ram_layout_words(layout: CanRamLayout) -> tuple[int, ...]:
    if not isinstance(layout, CanRamLayout):
        raise ValueError("CAN RAM layout requires CanRamLayout")
    return tuple(
        boolean(getattr(layout, name))
        if name in contract.RAM_FLAGS
        else uint32(getattr(layout, name))
        for name in contract.RAM_FIELDS
    )


# GET只能解码独立硬件读回；严格检查长度和Boolean，不能补请求缓存。
def decode_ram_layout(words: tuple[int, ...]) -> CanRamLayout:
    if len(words) != len(contract.RAM_FIELDS):
        raise ProtocolError("CAN RAM layout has invalid field count")
    values = []
    for name, value in zip(contract.RAM_FIELDS, words, strict=True):
        if name in contract.RAM_FLAGS:
            if value not in (0, 1):
                raise ProtocolError(f"CAN RAM flag {name} is not Boolean: {value}")
            values.append(bool(value))
        else:
            values.append(value)
    return CanRamLayout(*values)


# 按公开顺序编码；选择器必须使用对应Enum，不接受任意数值或隐式默认值。
def bus_config_words(config: CanBusConfig) -> tuple[int, ...]:
    if not isinstance(config, CanBusConfig):
        raise ValueError("CAN bus configuration requires CanBusConfig")
    values = []
    for name in contract.BUS_FIELDS:
        value = getattr(config, name)
        if name in contract.BUS_FLAGS:
            values.append(boolean(value))
        elif name in BUS_SELECTORS:
            if not isinstance(value, BUS_SELECTORS[name]):
                raise ValueError(f"CAN bus selector {name} has wrong enum type")
            values.append(int(value))
        else:
            values.append(uint32(value))
    if config.timestamp_divisor == 0:
        raise ValueError("CAN timestamp divisor must be positive")
    return tuple(values)


# 独立GET解码，未知选择器、非法Boolean或零分频均报告协议错误。
def decode_bus_config(words: tuple[int, ...]) -> CanBusConfig:
    if len(words) != len(contract.BUS_FIELDS):
        raise ProtocolError("CAN bus configuration has invalid field count")
    values = []
    try:
        for name, value in zip(contract.BUS_FIELDS, words, strict=True):
            if name in contract.BUS_FLAGS:
                if value not in (0, 1):
                    raise ValueError(f"CAN bus flag {name} is not Boolean")
                values.append(bool(value))
            elif name in BUS_SELECTORS:
                values.append(BUS_SELECTORS[name](value))
            else:
                values.append(value)
        config = CanBusConfig(*values)
        if config.timestamp_divisor == 0:
            raise ValueError("CAN timestamp divisor is zero")
        return config
    except ValueError as error:
        raise ProtocolError(str(error)) from error
