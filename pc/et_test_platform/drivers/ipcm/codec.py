# IPCM 纯二进制编解码。
# 职责：检查公共数值范围、精确长度、版本和保留字段。
# 边界：不执行 I/O，不读取能力文件，不比较 Case 的 Expected。
# 依赖：本 IP Contract/Model 与公共 ProtocolError。

from struct import Struct

from ...core.errors import ProtocolError
from . import contract
from .models import (
    IpcmAckMode,
    IpcmCapabilities,
    IpcmCaptureEvent,
    IpcmCaptureState,
    IpcmConfig,
    IpcmEventStage,
    IpcmLinkMode,
    IpcmMailboxSnapshot,
    IpcmPeerResult,
    IpcmPeerState,
    IpcmPendingSnapshot,
)


# 解析非零Peer事务票据；禁止把未发布的零序号当作有效操作。
def decode_peer_ticket(body: bytes) -> int:

    (ticket,) = _unpack(contract.PEER_TICKET, body, "PEER_TICKET")
    if ticket == 0:
        raise ProtocolError("IPCM Peer returned a zero ticket")
    return ticket


# 严格解析Peer响应；长度、保留字和非终态响应均验证，防止继承旧响应。
def decode_peer_result(body: bytes) -> IpcmPeerResult:

    if len(body) < contract.PEER_RESULT.size:
        raise ProtocolError("IPCM Peer response header is truncated")
    ticket, raw_state, status, length, reserved, identity, heartbeat = (
        contract.PEER_RESULT.unpack_from(body)
    )
    try:
        state = IpcmPeerState(raw_state)
    except ValueError as error:
        raise ProtocolError("IPCM Peer returned unknown state") from error
    if reserved or len(body) != contract.PEER_RESULT.size + length:
        raise ProtocolError("IPCM Peer response length/reserved mismatch")
    if state is not IpcmPeerState.DONE and length:
        raise ProtocolError("IPCM Peer non-DONE response contains stale payload")
    return IpcmPeerResult(
        ticket, state, status, identity, heartbeat, body[contract.PEER_RESULT.size :]
    )


# 校验公开整数参数，拒绝 bool、负数和越界，避免 pack 错误掩盖参数含义。
def checked_u16(value: int, name: str) -> int:

    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        raise ValueError(f"IPCM {name} must be an unsigned 16-bit integer")
    return value


# 逻辑 Endpoint 集合按公共位宽编码；不在这里猜物理 Channel 映射。
def _encode_endpoints(endpoints: frozenset[int]) -> int:

    mask = 0
    for endpoint in endpoints:
        if checked_u16(endpoint, "endpoint") >= contract.LOGICAL_SET_BITS:
            raise ValueError("IPCM endpoint exceeds logical-set width")
        mask |= 1 << endpoint
    return mask


# 恢复逻辑 Endpoint 集合，保留所有返回位。
def _decode_endpoints(mask: int) -> frozenset[int]:

    return frozenset(index for index in range(contract.LOGICAL_SET_BITS) if mask & (1 << index))


# 固定响应必须精确匹配布局，禁止忽略尾部字节。
def _unpack(layout: Struct, body: bytes, operation: str) -> tuple[int, ...]:

    if len(body) != layout.size:
        raise ProtocolError(f"IPCM {operation}: expected {layout.size} bytes, got {len(body)}")
    return layout.unpack(body)


# 从响应字节读取硬件容量及Service预算；版本、长度或容量不一致时抛出ProtocolError。
def decode_capabilities(body: bytes) -> IpcmCapabilities:

    api, size, mailboxes, channels, words, capacity, slots, capture_bytes = _unpack(
        contract.CAPABILITIES, body, "CAPABILITIES_GET"
    )
    if api != contract.IPCM_SERVICE_API_VERSION or size != contract.CAPABILITIES.size:
        raise ProtocolError("IPCM CAPABILITIES_GET incompatible version/size")
    if not (
        0 < mailboxes <= contract.LOGICAL_SET_BITS
        and 0 < channels <= contract.LOGICAL_SET_BITS
        and words > 0
        and capacity == words * contract.DATA_WORD_BYTES
        and slots > 0
        and capture_bytes > 0
    ):
        raise ProtocolError("IPCM CAPABILITIES_GET invalid capacities")
    return IpcmCapabilities(mailboxes, channels, words, capacity, slots, capture_bytes)


# 编码完整配置；Source 必须唯一，Destination 非空且不含 Source。
def encode_config(config: IpcmConfig) -> bytes:

    first = checked_u16(config.first_mailbox, "first_mailbox")
    count = checked_u16(config.mailbox_count, "mailbox_count")
    source = _encode_endpoints(frozenset((config.source_endpoint,)))
    destinations = _encode_endpoints(config.destination_endpoints)
    irq = _encode_endpoints(config.irq_enabled_endpoints)
    if isinstance(config.ack_mode, bool) or isinstance(config.link_mode, bool):
        raise ValueError("IPCM modes must be stable enums, not bool")
    ack = IpcmAckMode(config.ack_mode)
    link = IpcmLinkMode(config.link_mode)
    if count == 0 or first + count > contract.LOGICAL_SET_BITS:
        raise ValueError("IPCM mailbox range exceeds logical pending-set width")
    if not destinations or source & destinations or irq & ~(source | destinations):
        raise ValueError("IPCM source/destination/IRQ endpoint sets are inconsistent")
    if link is IpcmLinkMode.SINGLE and count != 1:
        raise ValueError("IPCM SINGLE requires exactly one mailbox")
    return contract.CONFIG.pack(first, count, source, destinations, irq, ack, link, 0)


# 返回真实 Mailbox 读回；SOURCE=0 的释放态允许为空集合。
def decode_mailbox(body: bytes) -> IpcmMailboxSnapshot:

    source, destination, irq, ack, link, reserved = _unpack(
        contract.MAILBOX, body, "MAILBOX_SNAPSHOT"
    )
    if reserved != 0:
        raise ProtocolError("IPCM MAILBOX_SNAPSHOT nonzero reserved field")
    try:
        return IpcmMailboxSnapshot(
            _decode_endpoints(source),
            _decode_endpoints(destination),
            _decode_endpoints(irq),
            IpcmAckMode(ack),
            IpcmLinkMode(link),
        )
    except ValueError as error:
        raise ProtocolError("IPCM MAILBOX_SNAPSHOT unknown mode") from error


# 不以单一 Mailbox 布尔值替代完整 Raw/Masked 位集合。
def decode_pending(body: bytes) -> IpcmPendingSnapshot:

    return IpcmPendingSnapshot(*_unpack(contract.PENDING, body, "PENDING_SNAPSHOT"))


# 将逻辑标识编码为Little Endian u16；bool、负数或超过16位范围时抛出ValueError。
def encode_id(value: int) -> bytes:

    return contract.IDENTIFIER.pack(checked_u16(value, "identifier"))


# 编码 Mailbox 范围、读长度或 Endpoint 配对；具体语义由调用 API 明确。
def encode_pair(first: int, second: int) -> bytes:

    return contract.PAIR.pack(checked_u16(first, "first"), checked_u16(second, "second"))


# 写入仅准备 Payload；不隐式 SEND，不补全为满容量消息。
def encode_payload(first: int, count: int, payload: bytes) -> bytes:

    if not isinstance(payload, bytes) or not payload:
        raise ValueError("IPCM payload must be nonempty bytes")
    return (
        contract.WRITE_HEADER.pack(
            checked_u16(first, "first_mailbox"),
            checked_u16(count, "mailbox_count"),
            checked_u16(len(payload), "payload length"),
        )
        + payload
    )


# 编码一次事件捕获；有效长度和消息/ACK阶段均由调用方明确提供。
def encode_capture_arm(
    slot: int, endpoint: int, mailbox: int, length: int, *, irq: bool, stage: IpcmEventStage
) -> bytes:

    if not isinstance(irq, bool):
        raise TypeError("IPCM irq must be bool")
    if isinstance(stage, bool):
        raise ValueError("IPCM stage must be MESSAGE or ACK, not bool")
    if checked_u16(length, "length") == 0:
        raise ValueError("IPCM capture length must be nonzero")
    return contract.CAPTURE_ARM.pack(
        checked_u16(slot, "slot"),
        checked_u16(endpoint, "endpoint"),
        checked_u16(mailbox, "mailbox"),
        length,
        int(irq),
        int(IpcmEventStage(stage)),
    )


# 事件长度、状态、代次和真实 Payload 一起解码；不从实时硬件重新补数据。
def decode_event(body: bytes) -> IpcmCaptureEvent:

    if len(body) < contract.EVENT_HEADER.size:
        raise ProtocolError("IPCM CAPTURE_GET truncated event header")
    fields = contract.EVENT_HEADER.unpack_from(body)
    generation, raw, masked, latched, count, unexpected, overflow, fault = fields[:8]
    endpoint, mailbox, length, state, stage = fields[8:]
    try:
        capture_state = IpcmCaptureState(state)
        event_stage = IpcmEventStage(stage)
    except ValueError as error:
        raise ProtocolError("IPCM CAPTURE_GET unknown state/stage") from error
    if len(body) != contract.EVENT_HEADER.size + length:
        raise ProtocolError("IPCM CAPTURE_GET payload length mismatch")
    if capture_state is IpcmCaptureState.READY:
        if length == 0 or fault or overflow or unexpected:
            raise ProtocolError("IPCM CAPTURE_GET READY contains missing payload or faults")
    elif length != 0:
        raise ProtocolError("IPCM CAPTURE_GET unfinished event contains payload")
    return IpcmCaptureEvent(
        generation,
        raw,
        masked,
        latched,
        count,
        unexpected,
        overflow,
        fault,
        endpoint,
        mailbox,
        length,
        capture_state,
        event_stage,
        body[contract.EVENT_HEADER.size :],
    )


# 成功的原子控制命令应返回空体，拒绝不匹配的固件布局。
def require_empty(body: bytes) -> None:

    if body:
        raise ProtocolError("IPCM action returned an unexpected response body")
