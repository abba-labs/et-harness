# STIMER PC Driver稳定原子API。
# 职责：发送单IP命令、约束Runtime Capability并提供有界状态轮询。
# 边界：不调用其他IP Driver、不读取板级事实、不实现Case判定。
# 依赖：仅依赖 STIMER Model/Contract/Codec/Validation 和 TargetClient。

from __future__ import annotations

from collections.abc import Callable

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.deadline import OperationDeadline
from .codec import (
    decode_capabilities,
    decode_count,
    decode_irq_snapshot,
    decode_status,
    encode_compare,
    encode_config,
    encode_debug_halt_policy,
    encode_emergency_route,
    encode_event_pulse_width,
    encode_irq,
)
from .contract import STIMER_SERVICE_ID, StimerCommand
from .models import (
    StimerCapabilities,
    StimerConfig,
    StimerDebugHaltPolicy,
    StimerFeature,
    StimerIrqEvent,
    StimerIrqSnapshot,
    StimerRuntimeStatus,
)
from .validation import (
    validate_compare_channel,
    validate_config,
    validate_event_pulse_width,
    validate_irq_events,
    validate_single_event,
)


# Firmware STIMER Service 的稳定单 IP 客户端，统一拥有请求和轮询 Deadline。
class StimerDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            StimerCommand.CAPABILITIES_GET,
            StimerCommand.LIVE_COUNT_GET,
            StimerCommand.LATCHED_COUNT_GET,
            StimerCommand.STATUS_GET,
            StimerCommand.IRQ_SNAPSHOT_GET,
            StimerCommand.EMERGENCY_CAPTURE_GET,
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
        self._capabilities: StimerCapabilities | None = None

    # 读取并缓存当前STIMER Service的真实运行时能力。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def capabilities_get(self) -> StimerCapabilities:

        message, _ = self._request(StimerCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 校验Runtime边界后，原子下发一份完整STIMER公共配置。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def configure(self, config: StimerConfig) -> None:

        normalized = validate_config(config)
        capabilities = self._runtime_capabilities()
        if normalized.period_ticks > capabilities.maximum_period_ticks:
            raise ValueError("period_ticks exceeds runtime capability")
        if normalized.prescaler_divider > capabilities.maximum_prescaler_divider:
            raise ValueError("prescaler_divider exceeds runtime capability")
        self._request(StimerCommand.CONFIGURE, encode_config(normalized))

    # 配置CPU被Debugger Halt时的STIMER运行策略，不启动或停止计数。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def debug_halt_policy_set(self, policy: StimerDebugHaltPolicy) -> None:

        if not isinstance(policy, StimerDebugHaltPolicy):
            raise ValueError("policy must be a StimerDebugHaltPolicy")
        if not self._runtime_capabilities().features & StimerFeature.DEBUG_HALT:
            raise ValueError("STIMER debug halt policy is not supported by runtime capability")
        self._request(
            StimerCommand.DEBUG_HALT_POLICY_SET,
            encode_debug_halt_policy(policy),
        )

    # 启动当前STIMER计数，不隐式清零或改变配置。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def start(self) -> None:

        self._request(StimerCommand.START)

    # 停止当前STIMER计数，并保留最后计数供后续观测。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def stop(self) -> None:

        self._request(StimerCommand.STOP)

    # 暂停当前STIMER计数并保留当前值，不代替Stop。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def pause(self) -> None:

        self._request(StimerCommand.PAUSE)

    # 从暂停值继续计数，不隐式Reload或Clear。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def resume(self) -> None:

        self._request(StimerCommand.RESUME)

    # 发出一次不可自动重试的Clear动作，不隐式改变生命周期。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def clear(self) -> None:

        self._request(StimerCommand.CLEAR)

    # 发出一次不可自动重试的Period Reload动作。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def reload(self) -> None:

        self._request(StimerCommand.RELOAD)

    # 读取当前32-bit实时计数，不触发Latch或状态清理。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def live_count_get(self) -> int:

        message, _ = self._request(StimerCommand.LIVE_COUNT_GET)
        return decode_count(message.body)

    # 执行一次不可重试的Latch动作并读取32-bit稳定快照。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def latched_count_get(self) -> int:

        message, _ = self._request(StimerCommand.LATCHED_COUNT_GET)
        return decode_count(message.body)

    # 读取全部运行时诊断状态，并由Codec拒绝未知状态位。
    def status_get(self) -> StimerRuntimeStatus:

        message, _ = self._request(StimerCommand.STATUS_GET)
        return decode_status(message.body)

    # 校验Runtime通道边界后，原子配置一个32-bit Compare门限。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def compare_set(self, channel: int, threshold: int) -> None:

        capabilities = self._runtime_capabilities()
        normalized_channel = validate_compare_channel(channel, capabilities.compare_channel_count)
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, int)
            or not 0 <= threshold <= 0xFFFFFFFF
        ):
            raise ValueError("threshold must be an unsigned 32-bit integer")
        self._request(StimerCommand.COMPARE_SET, encode_compare(normalized_channel, threshold))

    # 配置一个Compare或Overflow事件输出的脉宽，不启动计数或改变IRQ状态。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def event_pulse_width_set(self, event: StimerIrqEvent, width_cycles: int) -> None:

        if not self._runtime_capabilities().features & StimerFeature.EVENT_PULSE_WIDTH:
            raise ValueError(
                "event pulse-width configuration is not supported by runtime capability"
            )
        normalized_event, normalized_width = validate_event_pulse_width(event, width_cycles)
        self._request(
            StimerCommand.EVENT_PULSE_WIDTH_SET,
            encode_event_pulse_width(normalized_event, normalized_width),
        )

    # 选择一个Compare或Overflow事件作为DMA Request，不配置DMA Controller或DMAMUX。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def dma_request_select(self, event: StimerIrqEvent) -> None:

        if not self._runtime_capabilities().features & StimerFeature.DMA_REQUEST:
            raise ValueError("DMA request selection is not supported by runtime capability")
        normalized = validate_single_event(event)
        self._request(StimerCommand.DMA_REQUEST_SELECT, encode_irq(normalized))

    # 配置一个由Capability映射的逻辑紧急源，不向Wire暴露芯片XBAR掩码。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def emergency_capture_configure(self, source_id: int, trigger_group: int = 0) -> None:

        self._validate_emergency_route(source_id, trigger_group)
        self._request(
            StimerCommand.EMERGENCY_CAPTURE_CONFIGURE,
            encode_emergency_route(source_id, trigger_group),
        )

    # 读取DUT系统级紧急捕获的STIMER计数；读取不清除只读捕获端点。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def emergency_capture_get(self) -> int:

        if not self._runtime_capabilities().features & StimerFeature.EMERGENCY_CAPTURE:
            raise ValueError("STIMER emergency capture is not supported by runtime capability")
        message, _ = self._request(StimerCommand.EMERGENCY_CAPTURE_GET)
        return decode_count(message.body)

    # 禁用一个由Capability映射的逻辑紧急源；目标芯片只读捕获值由下一次触发覆盖。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def emergency_capture_clear(self, source_id: int, trigger_group: int = 0) -> None:

        self._validate_emergency_route(source_id, trigger_group)
        self._request(
            StimerCommand.EMERGENCY_CAPTURE_CLEAR,
            encode_emergency_route(source_id, trigger_group),
        )

    # 使能指定IRQ Source并建立CPU投递路由。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_enable(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_ENABLE, events)

    # 禁用指定IRQ Source，不隐式清除现有Raw或Status。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_disable(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_DISABLE, events)

    # Mask指定IRQ Source但保留Raw事实。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_mask(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_MASK, events)

    # 解除指定IRQ Source的Mask，不隐式改变Source Enable。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_unmask(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_UNMASK, events)

    # 软件强制指定IRQ Source，仅验证控制路径。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_force(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_FORCE, events)

    # 精确清除指定IRQ Source和对应Service latch。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_clear(self, events: StimerIrqEvent) -> None:

        self._irq_request(StimerCommand.IRQ_CLEAR, events)

    # 读取Raw、Status、ISR latch/count和最后Source。
    # 等待语义：仅等待本次响应，失败按平台异常上抛。
    def irq_snapshot_get(self) -> StimerIrqSnapshot:

        message, _ = self._request(StimerCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 在统一Deadline内等待计数满足调用方给出的简单谓词。
    def wait_count(
        self,
        predicate: Callable[[int], bool],
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> int:

        deadline = OperationDeadline.start(timeout_s, label="STIMER count wait")
        last = self.live_count_get()
        while not predicate(last):
            if deadline.expired:
                raise TimeoutError(f"STIMER count condition was not reached; last={last}")
            deadline.sleep(poll_interval_s)
            last = self.live_count_get()
        return last

    # 在统一Deadline内等待IRQ Event Count达到目标值。
    def wait_irq_count(
        self,
        minimum_event_count: int,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> StimerIrqSnapshot:

        if minimum_event_count < 0:
            raise ValueError("minimum_event_count must be non-negative")
        deadline = OperationDeadline.start(timeout_s, label="STIMER IRQ wait")
        last = self.irq_snapshot_get()
        while last.event_count < minimum_event_count:
            if deadline.expired:
                raise TimeoutError(f"STIMER IRQ count was not reached; last={last!r}")
            deadline.sleep(poll_interval_s)
            last = self.irq_snapshot_get()
        return last

    # 在统一Deadline内等待指定Raw Source出现；不要求CPU IRQ实际Delivery。
    def wait_irq_raw(
        self,
        events: StimerIrqEvent,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> StimerIrqSnapshot:

        normalized = validate_irq_events(events)
        deadline = OperationDeadline.start(timeout_s, label="STIMER raw IRQ wait")
        last = self.irq_snapshot_get()
        while last.raw & normalized != normalized:
            if deadline.expired:
                raise TimeoutError(f"STIMER raw IRQ source was not reached; last={last!r}")
            deadline.sleep(poll_interval_s)
            last = self.irq_snapshot_get()
        return last

    # 校验并发送一个STIMER IRQ掩码命令。
    def _irq_request(self, command: StimerCommand, events: StimerIrqEvent) -> None:

        normalized = validate_irq_events(events)
        if normalized & ~self._runtime_capabilities().irq_events:
            raise ValueError("IRQ event is not supported by runtime capability")
        self._request(command, encode_irq(normalized))

    # 校验逻辑紧急源的公共无符号范围，并确认目标Runtime声明了该Feature。
    def _validate_emergency_route(self, source_id: int, trigger_group: int) -> None:

        if (
            isinstance(source_id, bool)
            or not isinstance(source_id, int)
            or not 0 <= source_id <= 0xFF
        ):
            raise ValueError("source_id must be an unsigned 8-bit integer")
        if (
            isinstance(trigger_group, bool)
            or not isinstance(trigger_group, int)
            or not 0 <= trigger_group <= 0xFF
        ):
            raise ValueError("trigger_group must be an unsigned 8-bit integer")
        if not self._runtime_capabilities().features & StimerFeature.EMERGENCY_CAPTURE:
            raise ValueError("STIMER emergency capture is not supported by runtime capability")

    # 延迟读取Runtime Capability。
    def _runtime_capabilities(self) -> StimerCapabilities:

        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 向当前STIMER Service实例发送一次请求；仅只读命令允许安全重试。
    def _request(self, command: StimerCommand, body: bytes = b"") -> tuple[ServiceMessage, Frame]:

        return self._target.request(
            STIMER_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
