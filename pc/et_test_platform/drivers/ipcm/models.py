# IPCM 稳定配置与观测模型。
# 职责：区分硬件数量、软件采样预算、即时状态和锁存事件。
# 边界：不保存寄存器地址、物理 Core 或 IRQ 编号。
# 依赖：标准库。

from dataclasses import dataclass
from enum import IntEnum


# ACK 模式；显式 ACK 和释放 Destination 是两个独立动作。
class IpcmAckMode(IntEnum):
    MANUAL = 0
    AUTO = 1


# 链模式；链长按总成员数量计数，包括首 Mailbox。
class IpcmLinkMode(IntEnum):
    SINGLE = 0
    LINKED = 1


# PC 指定的采样阶段标识，不声称来自某个硬件状态位。
class IpcmEventStage(IntEnum):
    MESSAGE = 0
    ACK = 1


# Service 的单次异步采样状态，与硬件 Pending 分开。
class IpcmCaptureState(IntEnum):
    IDLE = 0
    WAITING = 1
    READY = 2
    FAULT = 3


# 原子Peer控制事务状态，不代表消息/ACK硬件状态。
class IpcmPeerState(IntEnum):
    IDLE = 0
    QUEUED = 1
    DONE = 2
    CANCELLED = 3


# 内部转发响应；Body只交回同一IP Codec，不向Case暴露Wire。
@dataclass(frozen=True, slots=True)
class IpcmPeerResult:
    ticket: int
    state: IpcmPeerState
    status: int
    executor_identity: int
    heartbeat: int
    body: bytes


# 实际硬件容量以及独立的 Service 观测存储上限。
@dataclass(frozen=True, slots=True)
class IpcmCapabilities:
    mailbox_count: int
    channel_count: int
    data_word_count: int
    mailbox_payload_bytes: int
    capture_slots: int
    capture_bytes: int


# 完整路由配置；Endpoint 是公共逻辑编号，不是芯片通道或 IRQn。
@dataclass(frozen=True, slots=True)
class IpcmConfig:
    first_mailbox: int
    mailbox_count: int
    source_endpoint: int
    destination_endpoints: frozenset[int]
    irq_enabled_endpoints: frozenset[int]
    ack_mode: IpcmAckMode
    link_mode: IpcmLinkMode


# Mailbox 当前配置的真实读回，不从请求参数推导。
@dataclass(frozen=True, slots=True)
class IpcmMailboxSnapshot:
    source_endpoints: frozenset[int]
    destination_endpoints: frozenset[int]
    irq_enabled_endpoints: frozenset[int]
    ack_mode: IpcmAckMode
    link_mode: IpcmLinkMode


# Endpoint 的实时 Raw/Masked Mailbox 位集合，可同时包含多个 Mailbox。
@dataclass(frozen=True, slots=True)
class IpcmPendingSnapshot:
    raw_pending: int
    masked_pending: int


# 清除前锁存的完整事件；计数、代次、阶段和状态均为软件 Measurement。
@dataclass(frozen=True, slots=True)
class IpcmCaptureEvent:
    generation: int
    raw_status: int
    masked_status: int
    latched_events: int
    callback_count: int
    unexpected_count: int
    overflow_count: int
    fault_flags: int
    endpoint: int
    mailbox: int
    length: int
    state: IpcmCaptureState
    stage: IpcmEventStage
    payload: bytes
