# CPU Owner PC Driver 的稳定原子 API。
# 职责：发送 CPU/NMI Owner 命令并提供有界事件计数轮询。
# 边界：不调用 WDG 或其他 IP Driver；WDG 与 CPU 的时序组合由 Case 负责。
# 依赖：仅依赖 CPU Contract/Codec/Model、TargetClient 和公共 Deadline。

from __future__ import annotations

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.deadline import OperationDeadline
from .codec import decode_capabilities, decode_snapshot, encode_nmi_configure
from .contract import CPU_SERVICE_ID, CpuCommand
from .models import CpuNmiCapabilities, CpuNmiSnapshot


# 提供 CPU/NMI Owner 的稳定原子操作；不承担其他 IP 的触发与测试结论。
class CpuDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            CpuCommand.CAPABILITIES_GET,
            CpuCommand.NMI_SNAPSHOT_GET,
        }
    )

    def __init__(self, target: TargetClient, instance_id: int = 0) -> None:
        if (
            isinstance(instance_id, bool)
            or not isinstance(instance_id, int)
            or not 0 <= instance_id <= 0xFFFF
        ):
            raise ValueError("instance_id must be an unsigned 16-bit integer")
        self._target = target
        self.instance_id = instance_id
        self._capabilities: CpuNmiCapabilities | None = None

    # 读取 CPU Owner 的真实 NMI 源能力；只等待本次响应，失败或超时按平台异常上抛。
    def capabilities_get(self) -> CpuNmiCapabilities:
        message, _ = self._request(CpuCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 配置 NMI 源屏蔽值；只等待本次响应，失败或超时按平台异常上抛。
    def nmi_configure(self, nmi_mask: int) -> None:
        capabilities = self._runtime_capabilities()
        if isinstance(nmi_mask, bool) or not isinstance(nmi_mask, int) or nmi_mask < 0:
            raise ValueError("nmi_mask must be a non-negative integer")
        if nmi_mask & ~capabilities.source_mask:
            raise ValueError("nmi_mask contains unsupported source bits")
        self._request(CpuCommand.NMI_CONFIGURE, encode_nmi_configure(nmi_mask))

    # 清零 Service 自己的 NMI ISR 事件计数；只等待本次响应，失败或超时按平台异常上抛。
    def nmi_event_clear(self) -> None:
        self._request(CpuCommand.NMI_EVENT_CLEAR)

    # 读取 CPU NMI 源、屏蔽、状态和真实 ISR 事件计数；只等待本次响应，失败或超时按平台异常上抛。
    def nmi_snapshot_get(self) -> CpuNmiSnapshot:
        message, _ = self._request(CpuCommand.NMI_SNAPSHOT_GET)
        return decode_snapshot(message.body)

    # 在统一 Deadline 内等待真实 NMI ISR 事件计数达到目标。
    def wait_nmi(
        self,
        minimum_event_count: int,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> CpuNmiSnapshot:
        if minimum_event_count < 0:
            raise ValueError("minimum_event_count must be non-negative")
        deadline = OperationDeadline.start(timeout_s, label="CPU NMI wait")
        last = self.nmi_snapshot_get()
        while last.event_count < minimum_event_count:
            if deadline.expired:
                raise TimeoutError(f"CPU NMI event condition was not reached; last={last!r}")
            deadline.sleep(poll_interval_s)
            last = self.nmi_snapshot_get()
        return last

    # 延迟查询并缓存 Runtime Capability。
    def _runtime_capabilities(self) -> CpuNmiCapabilities:
        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 向 CPU Owner Service 发送一次请求；只有只读命令允许安全重试。
    def _request(self, command: CpuCommand, body: bytes = b"") -> tuple[ServiceMessage, Frame]:
        return self._target.request(
            CPU_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
