# SPI纯Wire编解码。
# 职责：精确校验长度、枚举、Boolean和保留位。
# 边界：不发送请求，不轮询，不读取芯片配置。
# 依赖：本IP Model/Contract及公共ProtocolError。

from ...core.errors import ProtocolError
from . import contract
from .models import (
    SpiClockMode,
    SpiConfig,
    SpiCsPolicy,
    SpiErrorStatus,
    SpiFifoLimits,
    SpiFormat,
    SpiIrq,
    SpiIrqEvent,
    SpiLimits,
    SpiRole,
    SpiSnapshot,
    SpiStatusFlag,
    SpiTransferMode,
)


# 拒绝bool和不可表示值；IntEnum需在调用点明确转换。
def uint32(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"SPI value must be uint32: {value!r}")
    return value


# Boolean不会把任意非零整数静默转换成True。
def boolean(value: bool) -> int:
    if type(value) is not bool:
        raise ValueError("SPI flag must be bool")
    return int(value)


# 编码实例前缀和固定数量的u32参数；无效数据在任何设备I/O之前拒绝。
def encode_request(command: contract.SpiCommand, instance_id: int, words: tuple[int, ...]) -> bytes:
    uint32(instance_id)
    if instance_id > 0xFF or len(words) != contract.REQUEST_WORDS[command]:
        raise ValueError(f"SPI {command.name}: invalid instance or request fields")
    return contract.INSTANCE.pack(instance_id) + b"".join(
        contract.WORD.pack(uint32(word)) for word in words
    )


# 响应必须精确等长；空响应也不能悄悄接受多余字节。
def decode_response(command: contract.SpiCommand, body: bytes) -> tuple[int, ...]:
    expected = contract.RESPONSE_WORDS[command] * contract.WORD.size
    if len(body) != expected:
        raise ProtocolError(f"SPI {command.name}: response bytes {len(body)} != {expected}")
    return tuple(item[0] for item in contract.WORD.iter_unpack(body))


# 全配置保持固定顺序；保留字由Codec填零，不暴露给Case。
def config_words(config: SpiConfig) -> tuple[int, ...]:
    if not isinstance(config, SpiConfig):
        raise ValueError("SPI configure requires SpiConfig")
    if not isinstance(config.role, SpiRole):
        raise ValueError("SPI role requires SpiRole")
    if not isinstance(config.frame_format, SpiFormat):
        raise ValueError("SPI frame_format requires SpiFormat")
    if not isinstance(config.clock_mode, SpiClockMode):
        raise ValueError("SPI clock_mode requires SpiClockMode")
    if not isinstance(config.transfer_mode, SpiTransferMode):
        raise ValueError("SPI transfer_mode requires SpiTransferMode")
    if not isinstance(config.cs_policy, SpiCsPolicy):
        raise ValueError("SPI cs_policy requires SpiCsPolicy")
    return (
        int(config.role),
        int(config.frame_format),
        int(config.clock_mode),
        int(config.transfer_mode),
        int(config.cs_policy),
        uint32(config.frame_bits),
        uint32(config.frame_count),
        uint32(config.divider),
        boolean(config.target_output_enabled),
        boolean(config.loopback),
        uint32(config.rx_sample_delay),
        uint32(config.control_bits),
        boolean(config.sequential),
        boolean(config.transmit),
        boolean(config.handshake),
        0,
    )


# 真实复位值允许小于可配置范围，但未知枚举、非法Boolean和保留位必须拒绝。
def decode_config(words: tuple[int, ...]) -> SpiConfig:
    if words[-1] or any(words[index] not in (0, 1) for index in (8, 9, 12, 13, 14)):
        raise ProtocolError("SPI config readback contains invalid flags/reserved word")
    try:
        return SpiConfig(
            SpiRole(words[0]),
            SpiFormat(words[1]),
            SpiClockMode(words[2]),
            SpiTransferMode(words[3]),
            SpiCsPolicy(words[4]),
            words[5],
            words[6],
            words[7],
            bool(words[8]),
            bool(words[9]),
            words[10],
            words[11],
            bool(words[12]),
            bool(words[13]),
            bool(words[14]),
        )
    except ValueError as error:
        raise ProtocolError("SPI configuration has unknown enum") from error


# 范围自洽性检查不固化任何芯片的FIFO容量或分频上限。
def decode_limits(words: tuple[int, ...]) -> SpiLimits:
    result = SpiLimits(*words)
    if not 1 <= result.frame_bits_min <= result.frame_bits_max <= 32 or result.fifo_depth == 0:
        raise ProtocolError("SPI invalid frame width/FIFO limits")
    if not 1 <= result.divider_min <= result.divider_max or result.frame_count_max == 0:
        raise ProtocolError("SPI invalid divider/frame count limits")
    return result


# 阈值协议使用u8设置值；零上限表示只有阈值0合法，不等于不支持。
def decode_fifo_limits(words: tuple[int, ...]) -> SpiFifoLimits:
    if any(not 0 <= word <= 0xFF for word in words):
        raise ProtocolError("SPI threshold maximum exceeds command range")
    return SpiFifoLimits(*words)


# 快照包含硬件事实；位集合和Boolean非法时不能继续参与断言。
def decode_snapshot(words: tuple[int, ...]) -> SpiSnapshot:
    if any(words[index] not in (0, 1) for index in (0, 1, 10, 11)):
        raise ProtocolError("SPI snapshot contains invalid Boolean")
    if any(words[index] & ~int(SpiIrq.ALL) for index in (7, 8, 9)):
        raise ProtocolError("SPI snapshot contains unknown IRQ source")
    return SpiSnapshot(
        bool(words[0]),
        bool(words[1]),
        words[2],
        words[3],
        words[4],
        words[5],
        words[6],
        SpiIrq(words[7]),
        SpiIrq(words[8]),
        SpiIrq(words[9]),
        bool(words[10]),
        bool(words[11]),
        words[12],
        words[13],
    )


# 解码完整ISR软件证据及故障计数，未知来源或故障位必须拒绝，不能当成没有事件。
def decode_event(words: tuple[int, ...]) -> SpiIrqEvent:
    if any(value & ~int(SpiIrq.ALL) for value in words[:3]) or words[7] & ~7:
        raise ProtocolError("SPI capture contains unknown source/fault bits")
    return SpiIrqEvent(SpiIrq(words[0]), SpiIrq(words[1]), SpiIrq(words[2]), *words[3:])


# 显式错误状态读取的第二个字只能使用已定义语义位。
def decode_error(words: tuple[int, ...]) -> SpiErrorStatus:
    if words[1] & ~int(sum(SpiStatusFlag)):
        raise ProtocolError("SPI error status contains unknown flags")
    return SpiErrorStatus(words[0], SpiStatusFlag(words[1]))
