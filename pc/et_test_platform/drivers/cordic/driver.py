# CORDIC PC Driver Package 的 driver 层。
#
# 职责：提供 CORDIC 单 IP 稳定原子 API、运行时能力约束和请求边界。
# 边界：不调用其他 IP Driver、不读取 Profile/Bench、不实现数学 Golden 或 Case 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 和 TargetClient。

from __future__ import annotations

from enum import IntFlag

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.deadline import OperationDeadline
from .codec import (
    decode_capabilities,
    decode_irq_snapshot,
    decode_result,
    decode_timed_result,
    decode_uint32,
    encode_argument,
    encode_config,
    encode_timed,
    encode_uint32,
    encode_zero_overhead,
)
from .contract import CORDIC_SERVICE_ID, CordicCommand
from .models import (
    CordicCapabilities,
    CordicConfig,
    CordicConversionStatus,
    CordicFunction,
    CordicIrqEvent,
    CordicIrqSnapshot,
    CordicResult,
    CordicStatus,
    CordicTimedResult,
)
from .validation import (
    validate_config,
    validate_function,
    validate_irq_events,
    validate_raw_word,
    validate_zero_overhead_arguments,
)


# Firmware 固定 CORDIC Service 的稳定单 IP 客户端。
class CordicDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            CordicCommand.CAPABILITIES_GET,
            CordicCommand.RESULT_GET,
            CordicCommand.STATUS_GET,
            CordicCommand.ARGUMENT_COUNT_GET,
            CordicCommand.CONVERSION_STATUS_GET,
            CordicCommand.IRQ_SNAPSHOT_GET,
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
        self._capabilities: CordicCapabilities | None = None
        self._configured = False

    # 读取并缓存当前 CORDIC Service 的真实运行时能力；仅等待本次响应，失败按平台异常上抛。
    def capabilities_get(self) -> CordicCapabilities:

        message, _ = self._request(CordicCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 应用经过 Runtime Capability 校验的完整配置；仅等待本次响应，失败按平台异常上抛。
    def configure(self, config: CordicConfig) -> None:

        normalized = validate_config(config, self._runtime_capabilities())
        self._request(CordicCommand.CONFIGURE, encode_config(normalized))
        self._configured = True

    # 向指定数学函数提交一个不解释 Codec 的 Raw 输入字；仅等待本次响应，失败按平台异常上抛。
    def argument_submit(self, function: CordicFunction, raw_value: int) -> None:

        self._require_configured()
        normalized_function = validate_function(function)
        if normalized_function not in self._runtime_capabilities().functions:
            raise ValueError("function is not supported by runtime capability")
        self._request(
            CordicCommand.ARGUMENT_SUBMIT,
            encode_argument(normalized_function, validate_raw_word(raw_value, "raw_value")),
        )

    # 读取两个 Raw 结果字；仅等待本次响应，失败按平台异常上抛，数值判定仍由 Case 负责。
    def result_get(self) -> CordicResult:

        self._require_configured()
        message, _ = self._request(CordicCommand.RESULT_GET)
        return decode_result(message.body)

    # 读取计算完成、参数溢出和 PM 第二参数错误状态；仅等待本次响应，失败按平台异常上抛。
    def status_get(self) -> CordicStatus:

        self._require_configured()
        message, _ = self._request(CordicCommand.STATUS_GET)
        value = decode_uint32(message.body, "STATUS_GET")
        if value & ~int(CordicStatus.ALL):
            raise ValueError("CORDIC status contains unknown bits")
        return CordicStatus(value)

    # 在统一Deadline内等待指定硬件状态，并返回最后状态与实际查询次数。
    def wait_status(
        self,
        expected: CordicStatus,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> tuple[CordicStatus, int]:

        normalized = CordicStatus(
            self._validate_flag(expected, CordicStatus.ALL, "expected status")
        )
        deadline = OperationDeadline.start(timeout_s, label="CORDIC status wait")
        poll_count = 1
        last = self.status_get()

        while last & normalized != normalized:
            if deadline.expired:
                raise TimeoutError(f"CORDIC status {normalized!r} was not reached; last={last!r}")
            deadline.sleep(poll_interval_s)
            poll_count += 1
            last = self.status_get()

        return last, poll_count

    # 清除指定 CORDIC W1C 状态；仅等待本次响应，非法位或目标失败立即上抛。
    def status_clear(self, status: CordicStatus) -> None:

        self._require_configured()
        self._request(
            CordicCommand.STATUS_CLEAR,
            encode_uint32(self._validate_flag(status, CordicStatus.ALL, "status")),
        )

    # 读取硬件已接收参数个数；仅等待本次响应，失败或超时按平台异常上抛。
    def argument_count_get(self) -> int:

        self._require_configured()
        message, _ = self._request(CordicCommand.ARGUMENT_COUNT_GET)
        return decode_uint32(message.body, "ARGUMENT_COUNT_GET")

    # 读取 Float-to-Fixed Overflow/Underflow 状态；仅等待本次响应，失败按平台异常上抛。
    def conversion_status_get(self) -> CordicConversionStatus:

        self._require_configured()
        message, _ = self._request(CordicCommand.CONVERSION_STATUS_GET)
        value = decode_uint32(message.body, "CONVERSION_STATUS_GET")
        if value & ~int(CordicConversionStatus.ALL):
            raise ValueError("CORDIC conversion status contains unknown bits")
        return CordicConversionStatus(value)

    # 在统一Deadline内等待指定Float-to-Fixed转换状态，并保留最后硬件状态用于诊断。
    def wait_conversion_status(
        self,
        expected: CordicConversionStatus,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> CordicConversionStatus:

        normalized = CordicConversionStatus(
            self._validate_flag(
                expected,
                CordicConversionStatus.ALL,
                "expected conversion status",
            )
        )
        deadline = OperationDeadline.start(timeout_s, label="CORDIC conversion status wait")
        last = self.conversion_status_get()

        while last & normalized != normalized:
            if deadline.expired:
                raise TimeoutError(
                    f"CORDIC conversion status {normalized!r} was not reached; last={last!r}"
                )
            deadline.sleep(poll_interval_s)
            last = self.conversion_status_get()

        return last

    # 清除指定转换状态并拒绝未知位；仅等待本次响应，失败按平台异常上抛。
    def conversion_status_clear(self, status: CordicConversionStatus) -> None:

        self._require_configured()
        value = self._validate_flag(status, CordicConversionStatus.ALL, "conversion status")
        self._request(CordicCommand.CONVERSION_STATUS_CLEAR, encode_uint32(value))

    # 绑定并使能指定 CORDIC IRQ Source；仅等待本次响应，失败按平台异常上抛。
    def irq_enable(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_ENABLE, events)

    # 禁用指定 CORDIC IRQ Source 并按需释放绑定；仅等待本次响应，失败按平台异常上抛。
    def irq_disable(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_DISABLE, events)

    # Mask 指定 IRQ Source 并保留 Raw；仅等待本次响应，失败按平台异常上抛。
    def irq_mask(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_MASK, events)

    # 解除指定 IRQ Source 的硬件 Mask；仅等待本次响应，失败按平台异常上抛。
    def irq_unmask(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_UNMASK, events)

    # 软件 Force 指定 CORDIC IRQ Source；仅等待本次响应，失败按平台异常上抛。
    def irq_force(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_FORCE, events)

    # 清除指定 IRQ Source 的硬件 Raw/Status；仅等待本次响应，失败按平台异常上抛。
    def irq_clear(self, events: CordicIrqEvent) -> None:

        self._irq_request(CordicCommand.IRQ_CLEAR, events)

    # 读取 Raw、Status 与 ISR 回调计数的同一快照；仅等待本次响应，失败按平台异常上抛。
    def irq_snapshot_get(self) -> CordicIrqSnapshot:

        self._require_configured()
        message, _ = self._request(CordicCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 在统一Deadline内等待指定IRQ Source完成一次新的真实投递。
    def wait_irq(
        self,
        events: CordicIrqEvent,
        *,
        minimum_event_count: int,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> CordicIrqSnapshot:

        normalized = validate_irq_events(events)
        if normalized & ~self._runtime_capabilities().irq_events:
            raise ValueError("IRQ event is not supported by runtime capability")
        if (
            isinstance(minimum_event_count, bool)
            or not isinstance(minimum_event_count, int)
            or not 0 <= minimum_event_count <= 0xFFFFFFFF
        ):
            raise ValueError("minimum_event_count must be an unsigned 32-bit integer")

        deadline = OperationDeadline.start(timeout_s, label="CORDIC IRQ wait")
        last = self.irq_snapshot_get()

        while last.event_count < minimum_event_count or last.last_event & normalized != normalized:
            if deadline.expired:
                raise TimeoutError(f"CORDIC IRQ {normalized!r} was not delivered; last={last!r}")
            deadline.sleep(poll_interval_s)
            last = self.irq_snapshot_get()

        return last

    # 在目标原子窗口提交完整 Raw 参数并读取结果；仅等待本次响应，失败或超时立即上抛。
    def zero_overhead_execute(
        self,
        function: CordicFunction,
        arguments: tuple[int, ...],
    ) -> CordicResult:

        self._require_configured()
        normalized_function, normalized_arguments = validate_zero_overhead_arguments(
            function, arguments
        )
        if normalized_function not in self._runtime_capabilities().functions:
            raise ValueError("function is not supported by runtime capability")
        message, _ = self._request(
            CordicCommand.ZERO_OVERHEAD_EXECUTE,
            encode_zero_overhead(normalized_function, normalized_arguments),
        )
        return decode_result(message.body)

    # 在目标侧独立周期计数器中测量一次完成事务；等待本次有界响应，超时或目标失败按平台异常上抛。
    def execute_timed(
        self,
        function: CordicFunction,
        arguments: tuple[int, ...],
        timeout_polls: int,
    ) -> CordicTimedResult:

        self._require_configured()
        normalized_function, normalized_arguments = validate_zero_overhead_arguments(
            function, arguments
        )
        if normalized_function not in self._runtime_capabilities().functions:
            raise ValueError("function is not supported by runtime capability")
        if isinstance(timeout_polls, bool) or not isinstance(timeout_polls, int):
            raise TypeError("timeout_polls must be an integer")
        if timeout_polls <= 0 or timeout_polls > 0xFFFFFFFF:
            raise ValueError("timeout_polls must be an unsigned nonzero 32-bit integer")
        message, _ = self._request(
            CordicCommand.TEST_EXECUTE_TIMED,
            encode_timed(normalized_function, normalized_arguments, timeout_polls),
        )
        return decode_timed_result(message.body)

    # 校验并发送一个CORDIC IRQ命令。
    def _irq_request(self, command: CordicCommand, events: CordicIrqEvent) -> None:

        self._require_configured()
        normalized = validate_irq_events(events)
        if normalized & ~self._runtime_capabilities().irq_events:
            raise ValueError("IRQ event is not supported by runtime capability")
        self._request(command, encode_uint32(int(normalized)))

    # 延迟读取Runtime Capability并复用同一连接事实。
    def _runtime_capabilities(self) -> CordicCapabilities:

        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 在发送依赖硬件配置的命令前检查本地生命周期。
    def _require_configured(self) -> None:

        if not self._configured:
            raise RuntimeError("CORDIC must be configured before this operation")

    # 校验一个稳定IntFlag的类型、非空性和已知位。
    @staticmethod
    def _validate_flag(value: IntFlag, allowed: IntFlag, label: str) -> int:

        if type(value) is not type(allowed) or value == 0 or int(value) & ~int(allowed):
            raise ValueError(f"{label} must contain only published nonzero bits")
        return int(value)

    # 向当前CORDIC Service Instance发送一次请求；仅只读命令允许安全重试。
    def _request(self, command: CordicCommand, body: bytes = b"") -> tuple[ServiceMessage, Frame]:

        return self._target.request(
            CORDIC_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
