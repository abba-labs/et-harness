# SPINLOCK PC Driver 的稳定模型。
# 职责：表达跨芯片模式、能力、Flag 和 Resource Owner 事实。
# 边界：不包含芯片寄存器编码、地址、Clear Key 或 Core 拓扑。
# 依赖：仅依赖标准库。

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# SPINLOCK 公共工作模式，与 Firmware Wrap 公共值逐值对应。
class SpinlockMode(IntEnum):
    ONE_STEP = 0
    TWO_STEP = 1


# 区分当前Master批量释放与全部Master全局释放的稳定作用域，不暴露芯片Clear Key编码。
class SpinlockClearScope(IntEnum):
    CURRENT_MASTER_ALL = 0
    GLOBAL_ALL = 1


# SPINLOCK Runtime Service 发布的稳定 Feature 位。
class SpinlockFeature(IntFlag):
    ONE_STEP = 1 << 0
    TWO_STEP = 1 << 1
    BATCH_RELEASE = 1 << 2
    GLOBAL_RELEASE = 1 << 3
    CLEAR_KEY_PROTECTION = 1 << 4
    PEER_JOB = 1 << 5
    PEER_MASTER_MAPPING = 1 << 6
    SHARED_STRESS = 1 << 7


# SPINLOCK Peer 可执行的稳定异步动作，不暴露芯片 Core 编号或 Mailbox。
class SpinlockPeerJobType(IntEnum):
    TRY_HOLD = 0
    BLOCKING_HOLD = 1
    RELEASE_ONCE = 2
    HOLD = 3
    STRESS = 4


# SPINLOCK Peer Job 的稳定生命周期状态。
class SpinlockPeerJobState(IntEnum):
    IDLE = 0
    STARTED = 1
    WAITING = 2
    HOLDING = 3
    DONE = 4
    ABORTED = 5
    ERROR = 6


# SPINLOCK Peer Job 的稳定执行结果。
class SpinlockPeerResult(IntEnum):
    NONE = 0
    ACQUIRED = 1
    BUSY = 2
    RELEASED = 3
    COMPLETED = 4
    ABORTED = 5
    ERROR = 6


# 控制正在等待或持锁的Peer Job，并限定为释放或中止两种稳定语义。
class SpinlockPeerControl(IntEnum):
    RELEASE = 1
    ABORT = 2


# SPINLOCK 实例的运行时模式、数量与释放能力。
@dataclass(frozen=True, slots=True)
class SpinlockCapabilities:
    features: SpinlockFeature
    resource_count: int
    process_id_count: int


# SPINLOCK 当前 Enable 与模式的真实硬件读回。
@dataclass(frozen=True, slots=True)
class SpinlockConfigSnapshot:
    enabled: bool
    mode: SpinlockMode


# SPINLOCK 两组无副作用 Resource Flag 原始值。
@dataclass(frozen=True, slots=True)
class SpinlockFlagSnapshot:
    low: int
    high: int

    # 返回指定 Resource 的无副作用 Locked 状态。
    def is_locked(self, resource_id: int) -> bool:

        if not 0 <= resource_id < 64:
            raise ValueError("resource_id must be in [0, 63]")
        bank = self.low if resource_id < 32 else self.high
        bit = resource_id if resource_id < 32 else resource_id - 32
        return bool(bank & (1 << bit))


# SPINLOCK 单 Resource 的安全快照；空闲时 Owner/Process 字段无效。
@dataclass(frozen=True, slots=True)
class SpinlockResourceSnapshot:
    locked: bool
    owner_valid: bool
    process_id_valid: bool
    master_id: int
    process_id: int


# 已验证 Peer 的就绪状态和硬件 Master 身份。
@dataclass(frozen=True, slots=True)
class SpinlockPeerStatus:
    ready: bool
    master_id: int


# 异步 Peer Job 的状态、结果和进度快照。
@dataclass(frozen=True, slots=True)
class SpinlockPeerJobSnapshot:
    state: SpinlockPeerJobState
    result: SpinlockPeerResult
    master_id: int
    enter_count: int
    completed_count: int


# 保存双执行实体压力测试产生的共享计数值和临界区互斥违规次数。
@dataclass(frozen=True, slots=True)
class SpinlockSharedSnapshot:
    shared_counter: int
    violation_count: int
