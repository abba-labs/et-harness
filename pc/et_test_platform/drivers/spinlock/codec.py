# SPINLOCK Wire 编解码。
# 职责：提供固定布局的纯 Request/Response 转换和严格解码。
# 边界：不执行 I/O、Capability 查询或测试判断。
# 依赖：仅依赖本 IP Contract/Model 和公共 ProtocolError。

from ...core.errors import ProtocolError
from .contract import (
    CAPABILITIES_STRUCT,
    CLEAR_PROBE_STRUCT,
    CONFIG_STRUCT,
    FLAG_SNAPSHOT_STRUCT,
    LOCAL_STRESS_REQUEST_STRUCT,
    LOCAL_STRESS_RESPONSE_STRUCT,
    MASTER_ID_STRUCT,
    PEER_CONTROL_STRUCT,
    PEER_JOB_CONFIG_STRUCT,
    PEER_JOB_SNAPSHOT_STRUCT,
    PEER_STATUS_STRUCT,
    RESOURCE_ID_STRUCT,
    RESOURCE_REQUEST_STRUCT,
    RESOURCE_SNAPSHOT_STRUCT,
    SHARED_SNAPSHOT_STRUCT,
    SPINLOCK_SERVICE_API_VERSION,
)
from .models import (
    SpinlockCapabilities,
    SpinlockClearScope,
    SpinlockConfigSnapshot,
    SpinlockFeature,
    SpinlockFlagSnapshot,
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobSnapshot,
    SpinlockPeerJobState,
    SpinlockPeerJobType,
    SpinlockPeerResult,
    SpinlockPeerStatus,
    SpinlockResourceSnapshot,
    SpinlockSharedSnapshot,
)

_KNOWN_FEATURES = SpinlockFeature((1 << 8) - 1)


# 严格解码 Runtime Capability 并拒绝未知位和非法数量。
def decode_capabilities(body: bytes) -> SpinlockCapabilities:

    if len(body) != CAPABILITIES_STRUCT.size:
        raise ProtocolError("SPINLOCK CAPABILITIES_GET response length is invalid")
    api, size, features, resource_count, process_id_count = CAPABILITIES_STRUCT.unpack(body)
    if api != SPINLOCK_SERVICE_API_VERSION or size != CAPABILITIES_STRUCT.size:
        raise ProtocolError("SPINLOCK CAPABILITIES_GET version or size is incompatible")
    if features & ~int(_KNOWN_FEATURES):
        raise ProtocolError("SPINLOCK CAPABILITIES_GET contains unknown feature bits")
    if not 0 < resource_count <= 64 or not 0 < process_id_count <= 0x10000:
        raise ProtocolError("SPINLOCK CAPABILITIES_GET contains invalid limits")
    return SpinlockCapabilities(
        features=SpinlockFeature(features),
        resource_count=resource_count,
        process_id_count=process_id_count,
    )


# 编码一份稳定 SPINLOCK Enable/Mode 配置。
def encode_config(enabled: bool, mode: SpinlockMode) -> bytes:

    if not isinstance(enabled, bool):
        raise TypeError("enabled must be bool")
    try:
        normalized_mode = SpinlockMode(mode)
    except ValueError as error:
        raise ValueError("mode is not a stable SPINLOCK mode") from error
    return CONFIG_STRUCT.pack(int(enabled), int(normalized_mode))


# 严格解码 SPINLOCK Enable/Mode 真实读回。
def decode_config_snapshot(body: bytes) -> SpinlockConfigSnapshot:

    if len(body) != CONFIG_STRUCT.size:
        raise ProtocolError("SPINLOCK CONFIG_SNAPSHOT_GET response length is invalid")
    enabled, mode = CONFIG_STRUCT.unpack(body)
    if enabled not in (0, 1):
        raise ProtocolError("SPINLOCK config contains a noncanonical enabled value")
    try:
        return SpinlockConfigSnapshot(enabled=bool(enabled), mode=SpinlockMode(mode))
    except ValueError as error:
        raise ProtocolError("SPINLOCK config contains an unknown mode") from error


# 解码当前执行实体使用的硬件 Master ID。
def decode_master_id(body: bytes) -> int:

    if len(body) != MASTER_ID_STRUCT.size:
        raise ProtocolError("SPINLOCK LOCAL_MASTER_ID_GET response length is invalid")
    return MASTER_ID_STRUCT.unpack(body)[0]


# 编码一个 Resource/Process 原子操作请求。
def encode_resource_request(resource_id: int, process_id: int) -> bytes:

    if not 0 <= resource_id <= 0xFFFF or not 0 <= process_id <= 0xFFFF:
        raise ValueError("resource_id and process_id must fit uint16")
    return RESOURCE_REQUEST_STRUCT.pack(resource_id, process_id)


# 校验Resource ID的uint16边界，并编码为只读快照命令使用的小端请求体。
def encode_resource_id(resource_id: int) -> bytes:

    if not 0 <= resource_id <= 0xFFFF:
        raise ValueError("resource_id must fit uint16")
    return RESOURCE_ID_STRUCT.pack(resource_id)


# 解码两组无副作用 Resource Flag 原始值。
def decode_flag_snapshot(body: bytes) -> SpinlockFlagSnapshot:

    if len(body) != FLAG_SNAPSHOT_STRUCT.size:
        raise ProtocolError("SPINLOCK FLAG_SNAPSHOT_GET response length is invalid")
    low, high = FLAG_SNAPSHOT_STRUCT.unpack(body)
    return SpinlockFlagSnapshot(low=low, high=high)


# 解码单 Resource 安全快照并校验空闲/Owner 字段关系。
def decode_resource_snapshot(body: bytes) -> SpinlockResourceSnapshot:

    if len(body) != RESOURCE_SNAPSHOT_STRUCT.size:
        raise ProtocolError("SPINLOCK RESOURCE_SNAPSHOT_GET response length is invalid")
    locked, owner_valid, process_valid, reserved, master_id, process_id = (
        RESOURCE_SNAPSHOT_STRUCT.unpack(body)
    )
    if any(value not in (0, 1) for value in (locked, owner_valid, process_valid)) or reserved != 0:
        raise ProtocolError("SPINLOCK resource snapshot contains invalid flags")
    if (locked == 0 and (owner_valid != 0 or process_valid != 0)) or (
        owner_valid == 0 and (master_id != 0 or process_valid != 0 or process_id != 0)
    ):
        raise ProtocolError("SPINLOCK resource snapshot contains invalid owner semantics")
    return SpinlockResourceSnapshot(
        locked=bool(locked),
        owner_valid=bool(owner_valid),
        process_id_valid=bool(process_valid),
        master_id=master_id,
        process_id=process_id,
    )


# 编码 Clear Key 探测的稳定作用域和授权选择，不暴露芯片 Key。
def encode_clear_probe(scope: SpinlockClearScope, authorized: bool) -> bytes:

    try:
        normalized_scope = SpinlockClearScope(scope)
    except ValueError as error:
        raise ValueError("scope is not a stable SPINLOCK clear scope") from error
    if not isinstance(authorized, bool):
        raise TypeError("authorized must be bool")
    return CLEAR_PROBE_STRUCT.pack(int(normalized_scope), int(authorized))


# 严格解码 Peer 就绪状态和已验证硬件 Master ID。
def decode_peer_status(body: bytes) -> SpinlockPeerStatus:

    if len(body) != PEER_STATUS_STRUCT.size:
        raise ProtocolError("SPINLOCK PEER_STATUS_GET response length is invalid")
    ready, reserved, master_id = PEER_STATUS_STRUCT.unpack(body)
    if ready not in (0, 1) or reserved != 0 or (ready == 0 and master_id != 0):
        raise ProtocolError("SPINLOCK peer status contains invalid semantics")
    return SpinlockPeerStatus(ready=bool(ready), master_id=master_id)


# 编码异步Peer Job的类型、锁模式、资源、进程和有界循环参数。
def encode_peer_job(
    job_type: SpinlockPeerJobType,
    mode: SpinlockMode,
    resource_id: int,
    process_id: int,
    loop_count: int,
) -> bytes:

    normalized_job = SpinlockPeerJobType(job_type)
    normalized_mode = SpinlockMode(mode)
    if not 0 <= resource_id <= 0xFFFF or not 0 <= process_id <= 0xFFFF:
        raise ValueError("resource_id and process_id must fit uint16")
    if not 0 <= loop_count <= 0xFFFFFFFF:
        raise ValueError("loop_count must fit uint32")
    return PEER_JOB_CONFIG_STRUCT.pack(
        int(normalized_job),
        int(normalized_mode),
        resource_id,
        process_id,
        loop_count,
    )


# 严格解码异步 Peer Job 的状态、结果和进度。
def decode_peer_job_snapshot(body: bytes) -> SpinlockPeerJobSnapshot:

    if len(body) != PEER_JOB_SNAPSHOT_STRUCT.size:
        raise ProtocolError("SPINLOCK PEER_JOB_SNAPSHOT_GET response length is invalid")
    state, result, master_id, enter_count, completed_count = PEER_JOB_SNAPSHOT_STRUCT.unpack(body)
    try:
        return SpinlockPeerJobSnapshot(
            state=SpinlockPeerJobState(state),
            result=SpinlockPeerResult(result),
            master_id=master_id,
            enter_count=enter_count,
            completed_count=completed_count,
        )
    except ValueError as error:
        raise ProtocolError("SPINLOCK peer job snapshot contains unknown values") from error


# 编码Peer Job的释放或中止控制，并拒绝未定义的控制语义。
def encode_peer_control(control: SpinlockPeerControl) -> bytes:

    return PEER_CONTROL_STRUCT.pack(int(SpinlockPeerControl(control)))


# 编码本地执行实体的资源和有界循环次数，并校验Wire字段范围。
def encode_local_stress(resource_id: int, loop_count: int) -> bytes:

    if not 0 <= resource_id <= 0xFFFF:
        raise ValueError("resource_id must fit uint16")
    if not 0 < loop_count <= 0xFFFFFFFF:
        raise ValueError("loop_count must be in [1, 0xFFFFFFFF]")
    return LOCAL_STRESS_REQUEST_STRUCT.pack(resource_id, loop_count)


# 严格校验响应长度并解码本地执行实体实际完成的压力循环次数。
def decode_local_stress_result(body: bytes) -> int:

    if len(body) != LOCAL_STRESS_RESPONSE_STRUCT.size:
        raise ProtocolError("SPINLOCK LOCAL_STRESS_RUN response length is invalid")
    return LOCAL_STRESS_RESPONSE_STRUCT.unpack(body)[0]


# 严格校验响应长度并解码共享计数值和临界区互斥违规次数。
def decode_shared_snapshot(body: bytes) -> SpinlockSharedSnapshot:

    if len(body) != SHARED_SNAPSHOT_STRUCT.size:
        raise ProtocolError("SPINLOCK SHARED_SNAPSHOT_GET response length is invalid")
    shared_counter, violation_count = SHARED_SNAPSHOT_STRUCT.unpack(body)
    return SpinlockSharedSnapshot(
        shared_counter=shared_counter,
        violation_count=violation_count,
    )
