# SPINLOCK PC Driver 的稳定原子 API。
# 职责：发送单 IP 命令、约束 Runtime Capability 并返回硬件事实。
# 边界：不调用其他 IP Driver、不读取芯片映射、不实现 Case 或最终判断。
# 依赖：仅依赖 SPINLOCK Model/Contract/Codec、TargetClient 和平台异常。

from __future__ import annotations

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage, Status
from ...core.errors import TargetRejected
from .codec import (
    decode_capabilities,
    decode_config_snapshot,
    decode_flag_snapshot,
    decode_local_stress_result,
    decode_master_id,
    decode_peer_job_snapshot,
    decode_peer_status,
    decode_resource_snapshot,
    decode_shared_snapshot,
    encode_clear_probe,
    encode_config,
    encode_local_stress,
    encode_peer_control,
    encode_peer_job,
    encode_resource_id,
    encode_resource_request,
)
from .contract import SPINLOCK_SERVICE_ID, SpinlockCommand
from .models import (
    SpinlockCapabilities,
    SpinlockClearScope,
    SpinlockConfigSnapshot,
    SpinlockFeature,
    SpinlockFlagSnapshot,
    SpinlockMode,
    SpinlockPeerControl,
    SpinlockPeerJobSnapshot,
    SpinlockPeerJobType,
    SpinlockPeerStatus,
    SpinlockResourceSnapshot,
    SpinlockSharedSnapshot,
)


# Firmware SPINLOCK Service 的稳定单 IP 客户端。
class SpinlockDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            SpinlockCommand.CAPABILITIES_GET,
            SpinlockCommand.CONFIG_SNAPSHOT_GET,
            SpinlockCommand.LOCAL_MASTER_ID_GET,
            SpinlockCommand.FLAG_SNAPSHOT_GET,
            SpinlockCommand.RESOURCE_SNAPSHOT_GET,
            SpinlockCommand.PEER_STATUS_GET,
            SpinlockCommand.PEER_JOB_SNAPSHOT_GET,
            SpinlockCommand.SHARED_SNAPSHOT_GET,
        }
    )

    def __init__(self, target: TargetClient, instance_id: int) -> None:

        if (
            isinstance(instance_id, bool)
            or not isinstance(instance_id, int)
            or not 0 <= instance_id <= 0xFFFF
        ):
            raise ValueError("instance_id must be an unsigned 16-bit integer")
        self._target = target
        self.instance_id = instance_id
        self._capabilities: SpinlockCapabilities | None = None

    # 读取并缓存当前SPINLOCK运行时能力；只等待本次Target响应，拒绝、协议错误或超时按平台异常上抛。
    def capabilities_get(self) -> SpinlockCapabilities:

        message, _ = self._request(SpinlockCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 配置SPINLOCK Enable与模式且不隐式释放Resource；只等待命令响应，拒绝、协议错误或超时按平台异常上抛。
    def configure(self, *, enabled: bool, mode: SpinlockMode) -> None:

        normalized_mode = SpinlockMode(mode)
        capabilities = self._runtime_capabilities()
        if (
            normalized_mode is SpinlockMode.ONE_STEP
            and not capabilities.features & SpinlockFeature.ONE_STEP
        ):
            raise ValueError("ONE_STEP is not supported by runtime capability")
        if (
            normalized_mode is SpinlockMode.TWO_STEP
            and not capabilities.features & SpinlockFeature.TWO_STEP
        ):
            raise ValueError("TWO_STEP is not supported by runtime capability")
        self._request(SpinlockCommand.CONFIGURE, encode_config(enabled, normalized_mode))

    # 读取SPINLOCK Enable与模式硬件值；只等待本次Target响应，拒绝、协议错误或超时按平台异常上抛。
    def config_snapshot_get(self) -> SpinlockConfigSnapshot:

        message, _ = self._request(SpinlockCommand.CONFIG_SNAPSHOT_GET)
        return decode_config_snapshot(message.body)

    # 读取当前执行实体对应的硬件Master ID；只等待本次Target响应，拒绝、协议错误或超时按平台异常上抛。
    def local_master_id_get(self) -> int:

        message, _ = self._request(SpinlockCommand.LOCAL_MASTER_ID_GET)
        return decode_master_id(message.body)

    # 有界尝试获取一个 Resource；竞争导致的 BUSY 返回 False，其他错误上抛。
    def resource_acquire_try(self, resource_id: int, *, process_id: int = 0) -> bool:

        self._validate_resource_process(resource_id, process_id)
        try:
            self._request(
                SpinlockCommand.RESOURCE_ACQUIRE_TRY,
                encode_resource_request(resource_id, process_id),
            )
        except TargetRejected as error:
            if error.status == int(Status.BUSY):
                return False
            raise
        return True

    # 由当前实体释放指定Resource且不执行批量清除；只等待命令响应，拒绝、协议错误或超时按平台异常上抛。
    def resource_release(self, resource_id: int, *, process_id: int = 0) -> None:

        self._validate_resource_process(resource_id, process_id)
        self._request(
            SpinlockCommand.RESOURCE_RELEASE,
            encode_resource_request(resource_id, process_id),
        )

    # 读取两组无副作用Resource Flag原始值；只等待本次Target响应，拒绝、协议错误或超时按平台异常上抛。
    def flag_snapshot_get(self) -> SpinlockFlagSnapshot:

        message, _ = self._request(SpinlockCommand.FLAG_SNAPSHOT_GET)
        return decode_flag_snapshot(message.body)

    # 先读Flag并仅在Locked时读取Owner；只等待本次Target响应，拒绝、协议错误或超时按平台异常上抛。
    def resource_snapshot_get(self, resource_id: int) -> SpinlockResourceSnapshot:

        self._validate_resource(resource_id)
        message, _ = self._request(
            SpinlockCommand.RESOURCE_SNAPSHOT_GET,
            encode_resource_id(resource_id),
        )
        return decode_resource_snapshot(message.body)

    # 释放当前Master占用的全部Resource；只等待命令响应，拒绝、协议错误或超时按平台异常上抛。
    def batch_release(self) -> None:

        self._request(SpinlockCommand.BATCH_RELEASE)

    # 释放全部Master的Resource以恢复硬件基线；只等待命令响应，拒绝、协议错误或超时按平台异常上抛。
    def global_release(self) -> None:

        self._request(SpinlockCommand.GLOBAL_RELEASE)

    # 以正确或故意错误授权探测 Clear Key 保护，不暴露芯片 Key 数值。
    def clear_key_probe(self, scope: SpinlockClearScope, *, authorized: bool) -> None:

        self._request(
            SpinlockCommand.CLEAR_KEY_PROBE,
            encode_clear_probe(scope, authorized),
        )

    # 读取Peer就绪状态和已验证硬件Master ID；只等待一次响应，协议错误或超时按平台异常上抛。
    def peer_status_get(self) -> SpinlockPeerStatus:

        self._require_feature(SpinlockFeature.PEER_JOB)
        message, _ = self._request(SpinlockCommand.PEER_STATUS_GET)
        return decode_peer_status(message.body)

    # 启动一个异步Peer Job且不等待Job完成；参数拒绝、协议错误或超时按平台异常上抛。
    def peer_job_start(
        self,
        job_type: SpinlockPeerJobType,
        *,
        mode: SpinlockMode,
        resource_id: int,
        process_id: int = 0,
        loop_count: int = 0,
    ) -> None:

        self._require_feature(SpinlockFeature.PEER_JOB)
        self._validate_resource_process(resource_id, process_id)
        self._request(
            SpinlockCommand.PEER_JOB_START,
            encode_peer_job(job_type, mode, resource_id, process_id, loop_count),
        )

    # 读取异步Peer Job的状态、结果和进度；只等待一次快照响应，协议错误或超时按平台异常上抛。
    def peer_job_snapshot_get(self) -> SpinlockPeerJobSnapshot:

        self._require_feature(SpinlockFeature.PEER_JOB)
        message, _ = self._request(SpinlockCommand.PEER_JOB_SNAPSHOT_GET)
        return decode_peer_job_snapshot(message.body)

    # 请求持锁 Peer 释放，或请求等待/压力 Job 中止。
    def peer_job_control(self, control: SpinlockPeerControl) -> None:

        self._require_feature(SpinlockFeature.PEER_JOB)
        self._request(SpinlockCommand.PEER_JOB_CONTROL, encode_peer_control(control))

    # 为双执行实体压力Case清零共享计数和违规计数；只等待命令响应，拒绝或超时按平台异常上抛。
    def shared_stress_reset(self) -> None:

        self._require_feature(SpinlockFeature.SHARED_STRESS)
        self._request(SpinlockCommand.SHARED_STRESS_RESET)

    # 在本地执行实体运行有界压力循环并等待完成；执行失败、协议错误或超时按平台异常上抛。
    def local_stress_run(self, resource_id: int, loop_count: int) -> int:

        self._require_feature(SpinlockFeature.SHARED_STRESS)
        self._validate_resource(resource_id)
        message, _ = self._request(
            SpinlockCommand.LOCAL_STRESS_RUN,
            encode_local_stress(resource_id, loop_count),
        )
        return decode_local_stress_result(message.body)

    # 读取双执行实体压力操作后的共享计数和互斥违规次数；只等待一次响应，协议错误或超时按平台异常上抛。
    def shared_snapshot_get(self) -> SpinlockSharedSnapshot:

        self._require_feature(SpinlockFeature.SHARED_STRESS)
        message, _ = self._request(SpinlockCommand.SHARED_SNAPSHOT_GET)
        return decode_shared_snapshot(message.body)

    # 拒绝在 Runtime 未发布所需能力时发送命令。
    def _require_feature(self, feature: SpinlockFeature) -> None:

        if not self._runtime_capabilities().features & feature:
            raise ValueError(f"runtime capability does not support {feature.name}")

    # 校验 Resource ID 不超过当前 Runtime Capability。
    def _validate_resource(self, resource_id: int) -> None:

        if isinstance(resource_id, bool) or not isinstance(resource_id, int):
            raise TypeError("resource_id must be int")
        if not 0 <= resource_id < self._runtime_capabilities().resource_count:
            raise ValueError("resource_id exceeds runtime capability")

    # 同时校验 Resource ID 和两步模式 Process ID 范围。
    def _validate_resource_process(self, resource_id: int, process_id: int) -> None:

        self._validate_resource(resource_id)
        if isinstance(process_id, bool) or not isinstance(process_id, int):
            raise TypeError("process_id must be int")
        if not 0 <= process_id < self._runtime_capabilities().process_id_count:
            raise ValueError("process_id exceeds runtime capability")

    # 延迟读取 Runtime Capability 并复用同一连接事实。
    def _runtime_capabilities(self) -> SpinlockCapabilities:

        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 向当前 SPINLOCK Service Instance 发送一次请求；仅只读命令允许安全重试。
    def _request(
        self,
        command: SpinlockCommand,
        body: bytes = b"",
    ) -> tuple[ServiceMessage, Frame]:

        return self._target.request(
            SPINLOCK_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
