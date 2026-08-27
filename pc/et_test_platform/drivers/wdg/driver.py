# WDG PC Driver 的稳定原子 API。
# 职责：发送单 IP 命令、约束 Runtime Capability 并提供有界状态轮询。
# 边界：不调用其他 IP Driver、不读取板卡事实、不实现 Case 或最终判断。
# 依赖：仅依赖 WDG Model/Contract/Codec/Validation 和 TargetClient。

from __future__ import annotations

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.deadline import OperationDeadline
from .codec import (
    decode_capabilities,
    decode_config,
    decode_irq_snapshot,
    decode_records,
    decode_status,
    encode_config,
    encode_mask,
)
from .contract import WDG_SERVICE_ID, WdgCommand
from .models import (
    WdgCapabilities,
    WdgConfig,
    WdgIrqEvent,
    WdgIrqSnapshot,
    WdgRecord,
    WdgRecordSnapshot,
    WdgStatus,
)
from .validation import validate_config, validate_irq_events, validate_records


# Firmware WDG Service 的稳定单 IP 客户端，统一拥有请求和轮询 Deadline。
class WdgDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            WdgCommand.CAPABILITIES_GET,
            WdgCommand.CONFIG_GET,
            WdgCommand.STATUS_GET,
            WdgCommand.IRQ_SNAPSHOT_GET,
            WdgCommand.RECORD_GET,
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
        self._capabilities: WdgCapabilities | None = None

    # 读取并缓存当前 WDG Service 的真实运行时能力。
    # 仅等待本次响应并返回真实运行时能力，失败按平台异常上抛。
    def capabilities_get(self) -> WdgCapabilities:

        message, _ = self._request(WdgCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 解锁受保护的 WDG 配置寄存器；不隐式执行其他配置动作。
    # 仅等待本次响应并解锁当前实例，失败按平台异常上抛。
    def unlock(self) -> None:

        self._request(WdgCommand.UNLOCK)

    # 锁定受保护的 WDG 配置寄存器；不改变当前配置值。
    # 仅等待本次响应并锁定当前实例，失败按平台异常上抛。
    def lock(self) -> None:

        self._request(WdgCommand.LOCK)

    # 应用一份完整的公共 WDG 配置，并按 Runtime Capability 拒绝不支持项。
    def configure(self, config: WdgConfig) -> None:

        normalized = validate_config(config)
        capabilities = self._runtime_capabilities()
        if normalized.reload_count > capabilities.maximum_reload_count:
            raise ValueError("reload_count exceeds runtime capability")
        if normalized.window_high_count > capabilities.maximum_window_count:
            raise ValueError("window_high_count exceeds runtime capability")
        if (
            normalized.mode not in capabilities.modes
            or normalized.work_mode not in capabilities.work_modes
        ):
            raise ValueError("WDG mode is not supported by runtime capability")
        self._request(WdgCommand.CONFIGURE, encode_config(normalized))

    # 读取硬件实际接受的完整配置；不使用本地缓存替代硬件读回。
    # 仅等待本次响应并返回硬件配置读回，失败按平台异常上抛。
    def config_get(self) -> WdgConfig:

        message, _ = self._request(WdgCommand.CONFIG_GET)
        return decode_config(message.body)

    # 通过原子命令使能 WDG 计数过程，不在 PC 端伪造运行状态。
    # 仅等待本次响应并使能当前实例，失败按平台异常上抛。
    def enable(self) -> None:

        self._request(WdgCommand.ENABLE)

    # 通过原子命令禁用 WDG 计数过程，防止新的自然超时事件。
    def disable(self) -> None:

        self._request(WdgCommand.DISABLE)

    # 发出一次原子喂狗请求，不自动重试也不缓存计数结果。
    # 仅等待本次响应且喂狗动作不自动重试，失败按平台异常上抛。
    def feed(self) -> None:

        self._request(WdgCommand.FEED)

    # 读取目标实际使能状态与当前硬件计数，不使用本地缓存代替。
    # 仅等待本次响应并返回硬件状态读回，失败按平台异常上抛。
    def status_get(self) -> WdgStatus:

        message, _ = self._request(WdgCommand.STATUS_GET)
        return decode_status(message.body)

    # 复位选中的 WDG 模块；系统复位语义不由该动作代替。
    # 仅等待本次响应并复位选中模块，失败按平台异常上抛。
    def module_reset(self) -> None:

        self._request(WdgCommand.MODULE_RESET)

    # 绑定并使能 WDG timeout IRQ Source。
    # 仅等待本次响应并使能指定 IRQ Source，失败按平台异常上抛。
    def irq_enable(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_ENABLE, events)

    # 禁用 WDG timeout IRQ Source，并按需释放路由。
    # 仅等待本次响应并禁用指定 IRQ Source，失败按平台异常上抛。
    def irq_disable(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_DISABLE, events)

    # Mask 有效 IRQ 状态，同时保留 Raw 状态。
    # 仅等待本次响应并 Mask 指定 IRQ Source，失败按平台异常上抛。
    def irq_mask(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_MASK, events)

    # 解除 IRQ Mask，不隐式改变 Source Enable。
    # 仅等待本次响应并 Unmask 指定 IRQ Source，失败按平台异常上抛。
    def irq_unmask(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_UNMASK, events)

    # 强制 timeout Source，仅验证 IRQ 控制路径。
    # 仅等待本次响应并 Force 指定 IRQ Source，失败按平台异常上抛。
    def irq_force(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_FORCE, events)

    # 清除 timeout Raw/Status 和对应 Service latch。
    # 仅等待本次响应并清除指定 IRQ Source，失败按平台异常上抛。
    def irq_clear(self, events: WdgIrqEvent = WdgIrqEvent.TIMEOUT) -> None:

        self._irq_request(WdgCommand.IRQ_CLEAR, events)

    # 读取 Raw、Status、Service latch/count 与最后 Raw 的同一快照。
    # 仅等待本次响应并返回分层 IRQ 快照，失败按平台异常上抛。
    def irq_snapshot_get(self) -> WdgIrqSnapshot:

        message, _ = self._request(WdgCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 读取彼此独立的 WDG reset 与 interrupt 持久记录。
    # 仅等待本次响应并返回持久记录读回，失败按平台异常上抛。
    def record_get(self) -> WdgRecordSnapshot:

        message, _ = self._request(WdgCommand.RECORD_GET)
        return decode_records(message.body)

    # 精确清除选中的 WDG 持久记录，不允许空掩码或未知位。
    # 仅等待本次响应并精确清除持久记录，失败按平台异常上抛。
    def record_clear(self, records: WdgRecord) -> None:

        self._request(WdgCommand.RECORD_CLEAR, encode_mask(validate_records(records)))

    # 在统一 Deadline 内等待 counter 进入目标闭区间，并保留最后状态用于错误诊断。
    def wait_counter_between(
        self,
        minimum: int,
        maximum: int,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> WdgStatus:

        if not 0 <= minimum <= maximum <= 0xFFFFFFFF:
            raise ValueError("counter interval must satisfy 0 <= minimum <= maximum <= UINT32_MAX")
        deadline = OperationDeadline.start(timeout_s, label="WDG counter wait")
        last = self.status_get()
        while not minimum <= last.counter <= maximum:
            if deadline.expired:
                raise TimeoutError(
                    f"WDG counter did not enter [{minimum}, {maximum}]; last={last.counter}"
                )
            deadline.sleep(poll_interval_s)
            last = self.status_get()
        return last

    # 在统一 Deadline 内等待目标 IRQ 快照条件。
    def wait_irq(
        self,
        *,
        raw: WdgIrqEvent | None = None,
        minimum_event_count: int | None = None,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> WdgIrqSnapshot:

        if raw is None and minimum_event_count is None:
            raise ValueError("raw or minimum_event_count must be provided")
        expected_raw = validate_irq_events(raw) if raw is not None else None
        if minimum_event_count is not None and minimum_event_count < 0:
            raise ValueError("minimum_event_count must be non-negative")
        deadline = OperationDeadline.start(timeout_s, label="WDG IRQ wait")
        last = self.irq_snapshot_get()
        while (expected_raw is not None and last.raw & expected_raw != expected_raw) or (
            minimum_event_count is not None and last.event_count < minimum_event_count
        ):
            if deadline.expired:
                raise TimeoutError(f"WDG IRQ condition was not reached; last={last!r}")
            deadline.sleep(poll_interval_s)
            last = self.irq_snapshot_get()
        return last

    # 校验并发送一个 WDG IRQ 位掩码命令。
    def _irq_request(self, command: WdgCommand, events: WdgIrqEvent) -> None:

        normalized = validate_irq_events(events)
        if normalized & ~self._runtime_capabilities().irq_events:
            raise ValueError("IRQ event is not supported by runtime capability")
        self._request(command, encode_mask(normalized))

    # 延迟读取 Runtime Capability 并复用同一连接事实。
    def _runtime_capabilities(self) -> WdgCapabilities:

        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 向当前 WDG Service Instance 发送一次请求；仅只读命令允许安全重试。
    def _request(self, command: WdgCommand, body: bytes = b"") -> tuple[ServiceMessage, Frame]:

        return self._target.request(
            WDG_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
