# AES PC Driver 参数校验层。
#
# 职责：在发送 Wire 请求前拒绝非法 AES Model 和范围参数。
# 边界：不访问 TargetClient/Profile/Resource，不做跨 IP 检查或 pytest 断言。
# 依赖：仅依赖 AES Model 和稳定 Wire 字段边界。

from __future__ import annotations

from .models import (
    AesConfig,
    AesDirection,
    AesDmaTransferMode,
    AesEndian,
    AesIrqEvent,
    AesKeySize,
    AesMode,
    AesPadding,
)

UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1


# 校验无符号 32-bit 参数，供 AES Wire 字段共享边界语义。
def require_uint32(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= UINT32_MAX:
        raise ValueError(f"{name} must be an unsigned 32-bit integer")
    return value


# 校验 AES Service instance ID 的无符号范围。
def validate_instance_id(instance_id: int) -> int:
    return require_uint32(instance_id, "instance_id")


# 校验全部 AES 配置枚举、32-bit counter 和仅 CTR 可使用 counter 的组合约束。
def validate_config(config: AesConfig) -> AesConfig:
    if not isinstance(config, AesConfig):
        raise TypeError("config must be AesConfig")
    for name, enum_type, value in (
        ("direction", AesDirection, config.direction),
        ("key_size", AesKeySize, config.key_size),
        ("mode", AesMode, config.mode),
        ("padding", AesPadding, config.padding),
        ("endian", AesEndian, config.endian),
        ("dma_transfer_mode", AesDmaTransferMode, config.dma_transfer_mode),
    ):
        if not isinstance(value, enum_type):
            raise ValueError(f"config.{name} must be {enum_type.__name__}")
    if isinstance(config.ctr_counter, bool) or not isinstance(config.ctr_counter, int):
        raise ValueError("config.ctr_counter must be an unsigned 32-bit integer")
    require_uint32(config.ctr_counter, "config.ctr_counter")
    if config.mode is AesMode.CTR and config.padding is not AesPadding.NONE:
        raise ValueError("CTR mode only supports NONE padding")
    return config


# 校验 AES-128/256 密钥长度并返回规范化值。
def validate_key(key: bytes, key_size: AesKeySize) -> tuple[bytes, AesKeySize]:
    if not isinstance(key_size, AesKeySize):
        raise ValueError("key_size must be AesKeySize")
    value = bytes(key)
    expected = 16 if key_size is AesKeySize.AES128 else 32
    if len(value) != expected:
        raise ValueError(f"key must contain exactly {expected} bytes for {key_size.name}")
    return value, key_size


# 校验 AES IV 必须为固定 16 字节序列。
def validate_iv(iv: bytes) -> bytes:
    value = bytes(iv)
    if len(value) != 16:
        raise ValueError("iv must contain exactly 16 bytes")
    return value


# 校验 AES Wire 可表达的无符号 64-bit 数据长度；硬件位宽由运行时能力约束。
def validate_data_length(length_bytes: int, maximum: int = UINT64_MAX) -> int:
    if isinstance(length_bytes, bool) or not isinstance(length_bytes, int):
        raise ValueError("length_bytes must be an unsigned integer")
    if not 0 <= length_bytes <= maximum:
        raise ValueError(f"length_bytes must be in range 0..{maximum}")
    return length_bytes


# 校验单次 AES PROCESS 的非零长度和运行时上限。
def validate_process_length(length_bytes: int, maximum: int = UINT32_MAX) -> int:
    value = validate_data_length(length_bytes, maximum)
    if not 1 <= value <= maximum:
        raise ValueError(f"length_bytes must be in range 1..{maximum}")
    return value


# 计算 AES 模式、padding 和方向对应的目标输出容量。
def expected_output_length(
    length_bytes: int,
    mode: AesMode,
    padding: AesPadding,
    direction: AesDirection = AesDirection.ENCRYPT,
) -> int:
    validate_process_length(length_bytes)
    if not isinstance(mode, AesMode) or not isinstance(padding, AesPadding):
        raise ValueError("mode and padding must be AES enums")
    if mode is AesMode.CTR:
        if padding is not AesPadding.NONE:
            raise ValueError("CTR mode only supports NONE padding")
        return length_bytes
    if padding is AesPadding.NONE:
        if length_bytes % 16:
            raise ValueError("NONE padding requires a block-aligned length")
        return length_bytes
    if direction is AesDirection.DECRYPT:
        if length_bytes % 16:
            raise ValueError("padded ciphertext length must be block aligned")
        return length_bytes
    if padding is AesPadding.PKCS7:
        return ((length_bytes // 16) + 1) * 16
    return ((length_bytes + 15) // 16) * 16


# 校验 destination Resource 足以容纳 AES 预期输出。
def validate_process_output_capacity(
    capacity: int,
    length_bytes: int,
    config: AesConfig,
    maximum: int = UINT32_MAX,
) -> int:
    value = require_uint32(capacity, "destination_capacity")
    expected = expected_output_length(length_bytes, config.mode, config.padding, config.direction)
    if value < expected or value > maximum:
        raise ValueError(f"destination_capacity must cover {expected}..{maximum} bytes")
    return value


# 校验 Resource handle、offset 和长度不会溢出 32-bit 地址空间。
def validate_resource_range(
    handle: int, offset: int, size: int, name: str = "resource"
) -> tuple[int, int, int]:
    handle_value = require_uint32(handle, f"{name}_handle")
    offset_value = require_uint32(offset, f"{name}_offset")
    size_value = require_uint32(size, f"{name}_size")
    if offset_value + size_value > UINT32_MAX:
        raise ValueError(f"{name} range exceeds uint32 offset space")
    return handle_value, offset_value, size_value


# 校验 AES IRQ 事件集合只包含已发布非零 bit。
def validate_irq_events(events: AesIrqEvent) -> AesIrqEvent:
    if not isinstance(events, AesIrqEvent):
        raise ValueError("events must be AesIrqEvent")
    if events == AesIrqEvent(0) or events & ~AesIrqEvent.ALL:
        raise ValueError("events must contain only published non-zero AES IRQ bits")
    return events


# 校验 AES status W1C 掩码只包含已发布状态位。
def validate_status_mask(mask: int) -> int:
    value = require_uint32(mask, "status_mask")
    if value & ~0x07:
        raise ValueError("status_mask contains unknown AES status bits")
    return value


# 校验 AES DMA input/output request gate 位。
def validate_dma_request_flags(flags: int) -> int:
    value = require_uint32(flags, "dma_request_flags")
    if value & ~0x03:
        raise ValueError("dma_request_flags contains unknown AES request bits")
    return value


# 校验 Wire reserved 字段必须保持零值。
def validate_reserved_zero(value: int, name: str = "reserved") -> None:
    if value != 0:
        raise ValueError(f"{name} must be zero")
