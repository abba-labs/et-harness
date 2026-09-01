# CRC Formal Case 本地 Support 模块。
#
# 职责：保存已核对的只读事实、Driver 构造结果和纯软件 CRC Golden 算法。
# 边界：不执行硬件 Mutation、不隐藏完整 Case、不拥有最终断言。
# 依赖：仅依赖 CRC/Resource Driver、Capability 和标准库。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.crc import CrcCapabilities, CrcConfig, CrcDriver, CrcMode, CrcXorOut
from ...drivers.dma import DmaCapabilities, DmaDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers.dma_routes import CrcDmaInputRoute


# 保存一个已经通过静态与运行时 Gate 的 CRC 实例，不执行设备操作。
@dataclass(frozen=True, slots=True)
class CrcCaseSupport:
    instance_id: int
    instance_name: str
    resource: ResourceDriver
    crc: CrcDriver
    runtime: CrcCapabilities


# 保存 CRC DMA Case 已核对的跨 IP Driver 和 Route 事实，不执行 Feature 动作。
@dataclass(frozen=True, slots=True)
class CrcDmaSupport:
    crc_support: CrcCaseSupport
    dma: DmaDriver
    dma_capabilities: DmaCapabilities
    sysctrl: SysctrlDriver
    route: CrcDmaInputRoute


CrcSupportFactory = Callable[[int], CrcCaseSupport]


# 返回 CRC 宽度内的全一掩码。
def crc_width_mask(mode: CrcMode) -> int:

    return (1 << int(mode)) - 1


# 对一个自然宽度数值执行 bit reflection。
def reflect_bits(value: int, width: int) -> int:

    reflected = 0

    # 逐位反转：使用明确宽度，避免 Python 无限精度影响结果。
    for bit in range(width):
        reflected = (reflected << 1) | ((value >> bit) & 1)
    return reflected


# 按稳定 CRC 输入访问契约计算独立软件 Golden。
def calculate_crc_reference(config: CrcConfig, payload: bytes) -> int:

    if not payload:
        raise ValueError("CRC reference payload must not be empty")
    width = int(config.mode)
    unit_bytes = width // 8
    mask = crc_width_mask(config.mode)
    top_bit = 1 << (width - 1)
    ordered = bytearray()

    # 按实际 IR Access Unit 分组；CPU/DMA 从小端内存取自然数时先形成 unit 内反序。
    for offset in range(0, len(payload), unit_bytes):
        unit = payload[offset : offset + unit_bytes]
        if len(unit) == unit_bytes and not config.byte_swap:
            unit = unit[::-1]
        ordered.extend(unit)

    remainder = config.initial_value & mask

    # 逐 Byte 执行 RefIn 和 MSB-first normal-polynomial Kernel。
    for source_byte in ordered:
        input_byte = reflect_bits(source_byte, 8) if config.ref_in else source_byte
        remainder ^= input_byte << (width - 8)

        # 每个输入 Byte 固定推进八个 CRC bit。
        for _ in range(8):
            if remainder & top_bit:
                remainder = ((remainder << 1) ^ config.polynomial) & mask
            else:
                remainder = (remainder << 1) & mask

    if config.ref_out:
        remainder = reflect_bits(remainder, width)
    if config.xor_out is CrcXorOut.ALL_ONE:
        remainder ^= mask
    return remainder & mask


# 生成跨平台可复现的确定性 Byte Payload。
def make_crc_pattern(length: int, seed: int) -> bytes:

    if length <= 0:
        raise ValueError("CRC pattern length must be positive")
    state = seed & 0xFFFFFFFF
    payload = bytearray()

    # 使用固定 LCG 生成器，不依赖 Python random 的版本实现。
    for index in range(length):
        state = (1664525 * state + 1013904223 + index) & 0xFFFFFFFF
        payload.append((state >> 24) & 0xFF)
    return bytes(payload)


# 核对一个 CRC 实例的静态 Feature/Mode/Limit，并返回稳定实例名。
def require_crc_static_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    feature: str | None = None,
    mode: CrcMode | None = None,
) -> str:

    instance = f"crc{instance_id}"
    try:
        if instance not in capabilities.instances("crc"):
            raise UnsupportedCapability(f"CRC instance {instance!r} is unavailable")
        if feature is not None and not capabilities.has_feature(
            "crc",
            feature,
            instance=instance,
        ):
            raise UnsupportedCapability(f"{instance} does not support feature {feature!r}")
        if mode is not None and mode.name.lower() not in capabilities.options(
            "crc",
            "modes",
            instance=instance,
        ):
            raise UnsupportedCapability(f"{instance} does not support mode {mode.name}")
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as exc:
        raise UnsupportedCapability(f"CRC static capability is unavailable: {exc}") from exc


# 核对运行中 CRC Service 的模式和 Feature 位。
def require_crc_runtime_capability(
    runtime: CrcCapabilities,
    *,
    mode: CrcMode | None = None,
    feature_bits: int = 0,
) -> None:

    if mode is not None and mode not in runtime.modes:
        raise UnsupportedCapability(f"running CRC firmware does not support {mode.name}")
    if feature_bits and int(runtime.features) & feature_bits != feature_bits:
        raise UnsupportedCapability(
            f"running CRC firmware is missing feature bits 0x{feature_bits:08x}"
        )
