# CAN纯Wire编解码。
# 职责：明确字段顺序、精确长度与Boolean约束。
# 边界：不执行I/O，不读取Profile，不缓存期望硬件结果。
# 依赖：本IP合同/Model及统一ProtocolError。

from ...core.errors import ProtocolError
from . import contract
from .models import CanOptions, CanPhaseTiming, CanTiming


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
