# SYSCNT纯编解码。
# 职责：校验固定长度、保留位和稳定枚举，不接受截断响应。
# 边界：不访问硬件，不执行等待或测试判定。
# 依赖：本IP合同/类型和ProtocolError。

from struct import Struct

from ...core.errors import ProtocolError
from . import contract
from .models import (
    SyscntCapabilities,
    SyscntControl,
    SyscntFeature,
    SyscntHaltPolicy,
    SyscntReferenceSample,
)


# 无符号输入拒绝bool和越界值，避免struct错误泄漏成不明确的参数提示。
def encode_uint(value: int, layout: Struct) -> bytes:
    if type(value) is not int or not 0 <= value < (1 << (layout.size * 8)):
        raise ValueError(f"SYSCNT value must be uint{layout.size * 8}: {value!r}")
    return layout.pack(value)


# 固定响应必须精确等长，不能忽略尾部或补齐缺失字节。
def decode_words(body: bytes, layout: Struct) -> tuple[int, ...]:
    if len(body) != layout.size:
        raise ProtocolError(f"SYSCNT response length {len(body)} != {layout.size}")
    return layout.unpack(body)


# 解码固件发布的原子动作能力、计数位宽和访问窗口；未知位或非法宽度立即拒绝。
def decode_capabilities(body: bytes) -> SyscntCapabilities:
    flags, bits, views, reference, word = decode_words(body, contract.CAPABILITIES)
    if flags & ~int(SyscntFeature.ALL) or not 1 <= bits <= 64 or views not in (1, 2, 3):
        raise ProtocolError("SYSCNT capabilities contain invalid flags/width/views")
    if not 1 <= reference <= 64 or not 1 <= word <= bits:
        raise ProtocolError("SYSCNT reference/word width is invalid")
    return SyscntCapabilities(SyscntFeature(flags), bits, views, reference, word)


# 保留字节必须为零；配置HDBG与实际DBGH不互相替代。
def decode_control(body: bytes) -> SyscntControl:
    enabled, policy, halted, reserved, frequency = decode_words(body, contract.CONTROL)
    if enabled not in (0, 1) or policy not in (0, 1) or halted not in (0, 1) or reserved:
        raise ProtocolError("SYSCNT control contains invalid Boolean, policy or reserved byte")
    return SyscntControl(bool(enabled), SyscntHaltPolicy(policy), bool(halted), frequency)


# 三个值均为原始计数，换算和误差判定由Case负责。
def decode_reference(body: bytes) -> SyscntReferenceSample:
    return SyscntReferenceSample(*decode_words(body, contract.REFERENCE))
