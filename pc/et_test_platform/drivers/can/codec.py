# CAN纯Wire编解码。
# 职责：明确字段顺序、精确长度与Boolean约束。
# 边界：不执行I/O，不读取Profile，不缓存期望硬件结果。
# 依赖：本IP合同/Model及统一ProtocolError。

from ...core.errors import ProtocolError
from . import contract
from .models import (
    CanActivity,
    CanBusConfig,
    CanDmuCounters,
    CanDmuRequest,
    CanEccEvent,
    CanEccSnapshot,
    CanEccSource,
    CanError,
    CanEventFormat,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanHighPriorityStatus,
    CanHighPriorityStorage,
    CanIrqEvent,
    CanIrqSnapshot,
    CanIrqSource,
    CanOptions,
    CanPhaseTiming,
    CanProtocolStatus,
    CanRamLayout,
    CanRxFrame,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTsuConfig,
    CanTsuLimits,
    CanTxEvent,
    CanTxEventDetails,
    CanTxEventType,
    CanTxFrame,
    CanUnmatchedPolicy,
)


# ECC请求只接受专用非空源枚举，禁止控制器中断位图混用。
def ecc_sources(value: CanEccSource) -> int:
    if not isinstance(value, CanEccSource) or not 1 <= int(value) <= 3:
        raise ValueError("CAN ECC requires a nonempty public ECC source mask")
    return int(value)


# 四项均保留实际位图，不强加跨寄存器采样的同时性假设。
def decode_ecc_snapshot(words: tuple[int, ...]) -> CanEccSnapshot:
    if len(words) != 4 or any(value & ~3 for value in words):
        raise ProtocolError("CAN ECC snapshot contains reserved sources")
    return CanEccSnapshot(*(CanEccSource(value) for value in words))


# 只解析显式ISR实例字段；禁止用本Driver实例补造回调归属。
def decode_ecc_event(words: tuple[int, ...]) -> CanEccEvent:
    if len(words) != 9 or any(value & ~3 for value in words[:3]):
        raise ProtocolError("CAN ECC event contains reserved sources or wrong length")
    instance = words[8]
    if instance > 255 and instance != 0xFFFFFFFF:
        raise ProtocolError("CAN ECC callback instance is invalid")
    return CanEccEvent(
        *(CanEccSource(value) for value in words[:3]),
        *words[3:8],
        None if instance == 0xFFFFFFFF else instance,
    )


# 编码TSU配置；不允许非法分频或隐式Boolean转换。
def tsu_config_words(config: CanTsuConfig) -> tuple[int, ...]:
    if isinstance(config.divisor, bool) or not isinstance(config.divisor, int):
        raise ValueError("CAN TSU divisor must be an integer")
    if not 1 <= config.divisor <= 256:
        raise ValueError("CAN TSU divisor must be in 1..256")
    return boolean(config.enabled), boolean(config.external), boolean(config.sof), config.divisor


# 独立解码硬件配置并拒绝保留值，不用输入配置补值。
def decode_tsu_config(words: tuple[int, ...]) -> CanTsuConfig:
    if len(words) != 4 or not 1 <= words[3] <= 256:
        raise ProtocolError("CAN TSU configuration is invalid")
    return CanTsuConfig(*(status_boolean(word) for word in words[:3]), words[3])


# 从三个实际Wire字段解码槽数和内部源/SOF支持；槽数仅接受4/8/16，保留值失败关闭。
def decode_tsu_limits(words: tuple[int, ...]) -> CanTsuLimits:
    if len(words) != 3 or words[0] not in (4, 8, 16):
        raise ProtocolError("CAN TSU limits are invalid")
    return CanTsuLimits(words[0], status_boolean(words[1]), status_boolean(words[2]))


BUS_SELECTORS = {
    "timestamp_source": CanTimestampSource,
    "timeout_source": CanTimeoutSource,
    "unmatched_ext": CanUnmatchedPolicy,
    "unmatched_std": CanUnmatchedPolicy,
}
RX_FLAGS = (
    CanFrameFlags.EXTENDED
    | CanFrameFlags.REMOTE
    | CanFrameFlags.FD
    | CanFrameFlags.BRS
    | CanFrameFlags.ESI
)
TX_FLAGS = RX_FLAGS | CanFrameFlags.STORE_EVENT | CanFrameFlags.CAPTURE_TIME
IRQ_ALL = (1 << 30) - 1


# 中断位图必须只包含公共CAN事件，禁止未知位穿过Wire进入芯片适配。
def irq_sources(value: CanIrqSource) -> int:
    if not isinstance(value, CanIrqSource) or int(value) & ~IRQ_ALL:
        raise ValueError(f"CAN interrupt sources are invalid: {value!r}")
    return int(value)


# 解码非破坏IRQ硬件快照；控制器只有两条输出线，因此使能位只允许bit0/1。
def decode_irq_snapshot(words: tuple[int, ...]) -> CanIrqSnapshot:
    if len(words) != 4 or any(value & ~IRQ_ALL for value in words[:3]) or words[3] & ~0x3:
        raise ProtocolError(f"CAN invalid interrupt snapshot: {words}")
    return CanIrqSnapshot(
        CanIrqSource(words[0]), CanIrqSource(words[1]), CanIrqSource(words[2]), words[3]
    )


# 解码固定ISR证据；前三项是公共事件位图，其余项保留原始计数和诊断值。
def decode_irq_event(words: tuple[int, ...]) -> CanIrqEvent:
    if len(words) != 8 or any(value & ~IRQ_ALL for value in words[:3]):
        raise ProtocolError(f"CAN invalid interrupt event evidence: {words}")
    return CanIrqEvent(
        CanIrqSource(words[0]),
        CanIrqSource(words[1]),
        CanIrqSource(words[2]),
        *words[3:],
    )


# 过滤器只校验协议语义；配置列表长度和具体RAM容量仍由固件读取硬件确认。
# 专用Buffer精确匹配不接受隐藏的ID2编码，防止Case把芯片位域写进公共参数。
def filter_words(extended: bool, config: CanFilter) -> tuple[int, ...]:
    boolean(extended)
    if not isinstance(config, CanFilter):
        raise ValueError("CAN filter requires CanFilter")
    if not isinstance(config.type, CanFilterType) or not isinstance(config.action, CanFilterAction):
        raise ValueError("CAN filter selectors require public enums")
    maximum = contract.EXTENDED_ID_MAX if extended else contract.STANDARD_ID_MAX
    if uint32(config.id1) > maximum or uint32(config.id2) > maximum:
        raise ValueError("CAN filter identifier exceeds the selected frame format")
    uint32(config.buffer_index)
    if (extended and config.type is CanFilterType.DISABLED) or (
        not extended and config.type is CanFilterType.RANGE_NO_MASK
    ):
        raise ValueError("CAN filter type is not defined for this frame format")
    if config.action is CanFilterAction.BUFFER:
        if config.type is not CanFilterType.RANGE or config.id2 != 0:
            raise ValueError("CAN Buffer filter uses exact ID1, RANGE and ID2 zero")
    elif config.buffer_index != 0:
        raise ValueError("CAN non-Buffer filter cannot select a Buffer index")
    elif (
        config.type in {CanFilterType.RANGE, CanFilterType.RANGE_NO_MASK}
        and config.id2 < config.id1
    ):
        raise ValueError("CAN filter range has reversed bounds")
    return (int(config.type), int(config.action), config.id1, config.id2, config.buffer_index)


# 解码独立RAM读回，不调用SET校验去否认硬件确实保存的字段组合。
# 未知枚举作为协议错误，不能以默认配置替代原始结果。
def decode_filter(words: tuple[int, ...]) -> CanFilter:
    try:
        return CanFilter(CanFilterType(words[0]), CanFilterAction(words[1]), *words[2:])
    except ValueError as error:
        raise ProtocolError(f"CAN filter selectors are invalid: {words}") from error


# 解码一次High Priority Message状态；保留Filter列表与索引，不解释为接收成功。
def decode_high_priority_status(words: tuple[int, ...]) -> CanHighPriorityStatus:
    if len(words) != 4 or words[3] not in (0, 1):
        raise ProtocolError(f"CAN High Priority status is invalid: {words}")
    try:
        storage = CanHighPriorityStorage(words[1])
    except ValueError as error:
        raise ProtocolError(f"CAN High Priority storage is invalid: {words[1]}") from error
    return CanHighPriorityStatus(words[0], storage, words[2], bool(words[3]))


# 编码显式事件格式；TSU不支持八位Marker组合，非法值不得下发。
def event_format_words(config: CanEventFormat) -> tuple[int, ...]:
    if not isinstance(config, CanEventFormat):
        raise ValueError("CAN event format requires CanEventFormat")
    uint32(config.marker_bits)
    enabled = boolean(config.tsu_enabled)
    if config.marker_bits not in (8, 16) or (enabled and config.marker_bits != 16):
        raise ValueError("CAN event marker width must be 8/16, with 16 required for TSU")
    return (config.marker_bits, enabled)


# 实际配置必须是严格宽度/Boolean组合，不把未知硬件状态换成默认值。
def decode_event_format(words: tuple[int, ...]) -> CanEventFormat:
    if len(words) != 2:
        raise ProtocolError("CAN event format response length is invalid")
    config = CanEventFormat(words[0], status_boolean(words[1]))
    try:
        event_format_words(config)
    except ValueError as error:
        raise ProtocolError("CAN event format response is invalid") from error
    return config


# 解码有效性独立的事件，拒绝无效字段携带伪时间戳或伪TSU指针。
def decode_tx_event_details(words: tuple[int, ...]) -> CanTxEventDetails:
    if len(words) != 10:
        raise ProtocolError("CAN extended event response length is invalid")
    event = decode_tx_event(words[:7])
    valid, captured = status_boolean(words[7]), status_boolean(words[8])
    pointer = words[9]
    if (
        event.marker > (0xFF if valid else 0xFFFF)
        or event.timestamp > 0xFFFF
        or (not valid and event.timestamp != 0)
        or (valid and captured)
        or pointer > 15
        or (not captured and pointer != 0)
    ):
        raise ProtocolError("CAN extended event validity fields are inconsistent")
    return CanTxEventDetails(
        event.identifier,
        event.flags,
        event.dlc,
        event.timestamp if valid else None,
        event.event_type,
        event.marker,
        event.index,
        pointer if captured else None,
    )


# 解码TX Event FIFO头；只接受基本帧标志、合法DLC和已定义事件类型。
def decode_tx_event(words: tuple[int, ...]) -> CanTxEvent:
    if len(words) != 7:
        raise ProtocolError(f"CAN TX Event field count is invalid: {words}")
    identifier, raw_flags, dlc, timestamp, raw_type, marker, index = words
    flags = CanFrameFlags(raw_flags)
    maximum_id = (
        contract.EXTENDED_ID_MAX if flags & CanFrameFlags.EXTENDED else contract.STANDARD_ID_MAX
    )
    if (
        raw_flags & ~int(RX_FLAGS)
        or identifier > maximum_id
        or dlc >= len(contract.FD_DATA_LENGTHS)
    ):
        raise ProtocolError(f"CAN TX Event header is invalid: {words}")
    if (flags & CanFrameFlags.FD and flags & CanFrameFlags.REMOTE) or (
        not flags & CanFrameFlags.FD and flags & (CanFrameFlags.BRS | CanFrameFlags.ESI)
    ):
        raise ProtocolError(f"CAN TX Event frame format is inconsistent: {words}")
    try:
        event_type = CanTxEventType(raw_type)
    except ValueError as error:
        raise ProtocolError(f"CAN TX Event type is invalid: {raw_type}") from error
    return CanTxEvent(identifier, flags, dlc, timestamp, event_type, marker, index)


# 严格解码已消费的单次状态；使用命名字段，不让Driver包含Wire索引。
def decode_protocol_status(words: tuple[int, ...]) -> CanProtocolStatus:
    if len(words) != len(contract.PROTOCOL_FIELDS):
        raise ProtocolError("CAN protocol status has invalid field count")
    values = dict(zip(contract.PROTOCOL_FIELDS, words, strict=True))
    try:
        for name in contract.PROTOCOL_FLAGS:
            if values[name] not in (0, 1):
                raise ValueError(f"{name} is not Boolean")
            values[name] = bool(values[name])
        values["last_error"] = CanError(values["last_error"])
        values["data_last_error"] = CanError(values["data_last_error"])
        values["activity"] = CanActivity(values["activity"])
    except ValueError as error:
        raise ProtocolError(f"CAN invalid consumed protocol status: {words}") from error
    return CanProtocolStatus(**values)


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


# 标准协议DLC长度转换；Remote无payload，Classic的DLC9～15仍只有8字节。
def frame_payload_length(dlc: int, flags: CanFrameFlags) -> int:
    uint32(dlc)
    if dlc >= len(contract.FD_DATA_LENGTHS):
        raise ValueError("CAN DLC exceeds four bits")
    if flags & CanFrameFlags.REMOTE:
        return 0
    return (
        contract.FD_DATA_LENGTHS[dlc]
        if flags & CanFrameFlags.FD
        else min(dlc, contract.CLASSIC_DATA_BYTES)
    )


# TX必须提供完整有效payload，不替调用者补测试数据；Wire尾部保留区固定补零。
def tx_frame_words(index: int, frame: CanTxFrame) -> tuple[int, ...]:
    uint32(index)
    if not isinstance(frame, CanTxFrame) or not isinstance(frame.flags, CanFrameFlags):
        raise ValueError("CAN TX requires CanTxFrame and CanFrameFlags")
    uint32(frame.identifier)
    uint32(frame.marker)
    flags = frame.flags
    maximum_id = (
        contract.EXTENDED_ID_MAX if flags & CanFrameFlags.EXTENDED else contract.STANDARD_ID_MAX
    )
    if int(flags) & ~int(TX_FLAGS) or frame.identifier > maximum_id:
        raise ValueError("CAN TX flags or identifier are invalid")
    if (flags & CanFrameFlags.REMOTE and flags & CanFrameFlags.FD) or (
        not flags & CanFrameFlags.FD and flags & (CanFrameFlags.BRS | CanFrameFlags.ESI)
    ):
        raise ValueError("CAN TX frame format is inconsistent")
    length = frame_payload_length(frame.dlc, flags)
    if not isinstance(frame.data, bytes) or len(frame.data) != length:
        raise ValueError(f"CAN TX requires exactly {length} payload bytes")
    padded = frame.data.ljust(contract.FRAME_DATA_BYTES, b"\x00")
    return (index, frame.identifier, int(flags), frame.dlc, frame.marker) + tuple(
        word[0] for word in contract.WORD.iter_unpack(padded)
    )


# 校验完整TX读回头、槽索引及零填充；非法硬件响应不能变成合法预期帧。
def decode_tx_frame(index: int, words: tuple[int, ...]) -> CanTxFrame:
    if len(words) != contract.RESPONSE_WORDS[contract.CanCommand.TX_READ] or words[0] != index:
        raise ProtocolError("CAN TX readback has an invalid envelope or slot")
    _, identifier, raw_flags, dlc, marker = words[: contract.TX_HEADER_WORDS]
    try:
        flags = CanFrameFlags(raw_flags)
        length = frame_payload_length(dlc, flags)
        padded = b"".join(contract.WORD.pack(word) for word in words[contract.TX_HEADER_WORDS :])
        frame = CanTxFrame(identifier, flags, dlc, marker, padded[:length])
        if tx_frame_words(index, frame) != words:
            raise ValueError("CAN TX unused payload bytes are not zero")
    except ValueError as error:
        raise ProtocolError(f"CAN TX readback is malformed: {error}") from error
    return frame


# 只返回固件实际存储的payload；短槽保留原DLC，不能把缺失字节补成完整帧。
def decode_rx_frame(words: tuple[int, ...]) -> CanRxFrame:
    expected = contract.RESPONSE_WORDS[contract.CanCommand.RX_READ]
    if len(words) != expected:
        raise ProtocolError("CAN RX envelope has invalid field count")
    identifier, raw_flags, dlc, timestamp, filter_index, nonmatching, length, index = words[
        : contract.RX_HEADER_WORDS
    ]
    flags = CanFrameFlags(raw_flags)
    maximum_id = (
        contract.EXTENDED_ID_MAX if flags & CanFrameFlags.EXTENDED else contract.STANDARD_ID_MAX
    )
    if raw_flags & ~int(RX_FLAGS) or identifier > maximum_id or nonmatching not in (0, 1):
        raise ProtocolError("CAN RX header contains invalid fields")
    if (flags & CanFrameFlags.FD and flags & CanFrameFlags.REMOTE) or (
        not flags & CanFrameFlags.FD and flags & (CanFrameFlags.BRS | CanFrameFlags.ESI)
    ):
        raise ProtocolError("CAN RX frame format is inconsistent")
    try:
        if length > frame_payload_length(dlc, flags):
            raise ValueError("CAN stored payload exceeds protocol DLC length")
    except ValueError as error:
        raise ProtocolError(str(error)) from error
    data = b"".join(contract.WORD.pack(word) for word in words[contract.RX_HEADER_WORDS :])[:length]
    return CanRxFrame(
        identifier, flags, dlc, timestamp, filter_index, bool(nonmatching), index, data
    )


# 选择值必须属于公共枚举，不能把保留编码当成默认RX0。
def decode_dmu_request(words: tuple[int, ...]) -> CanDmuRequest:
    if len(words) != contract.RESPONSE_WORDS[contract.CanCommand.DMU_REQUEST_GET]:
        raise ProtocolError("CAN DMU request response has invalid field count")
    try:
        return CanDmuRequest(words[0])
    except ValueError as error:
        raise ProtocolError("CAN DMU request response has reserved selection") from error


# 模数必须可表示且大于1；每个计数严格小于模数，不进行差值或最终判定。
def decode_dmu_counters(words: tuple[int, ...]) -> CanDmuCounters:
    if len(words) != contract.RESPONSE_WORDS[contract.CanCommand.DMU_COUNTERS_GET]:
        raise ProtocolError("CAN DMU counter response has invalid field count")
    *counts, modulus = words
    if modulus < 2 or modulus & (modulus - 1) or any(count >= modulus for count in counts):
        raise ProtocolError("CAN DMU counters violate the reported binary modulus")
    return CanDmuCounters(*counts, modulus)


# 状态Boolean必须为0/1；不能将未知数值当作True隐藏固件编码错误。
def status_boolean(value: int) -> bool:
    if value not in (0, 1):
        raise ProtocolError(f"CAN status is not Boolean: {value}")
    return bool(value)
