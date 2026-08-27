# CRC PC Driver Package 的 driver 层。
#
# 职责：提供 CRC 单 IP 稳定业务 API、Deadline/Retry 所有权和单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取 Profile/Bench、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation、Core Cleanup 和 TargetClient。

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.cleanup import OperationCleanupError, raise_with_cleanup, run_cleanup
from .codec import (
    decode_calculate_result,
    decode_capabilities,
    decode_fifo_status,
    decode_irq_snapshot,
    decode_test_input_burst_result,
    decode_timed_result,
    decode_uint32,
    encode_calculate,
    encode_config,
    encode_irq_events,
    encode_test_input,
    encode_test_input_burst,
    encode_timed_calculate,
    encode_uint32,
)
from .contract import CRC_SERVICE_ID, CrcCommand
from .models import (
    CrcCalculateResult,
    CrcCapabilities,
    CrcConfig,
    CrcFifoStatus,
    CrcInputAccessWidth,
    CrcInputBurstResult,
    CrcIrqEvent,
    CrcIrqSnapshot,
    CrcMode,
    CrcTimedResult,
)
from .validation import (
    validate_calculate,
    validate_config,
    validate_data_length,
    validate_irq_events,
    validate_mode_value,
    validate_test_input,
    validate_test_input_burst,
)


# Firmware 固定 CRC Service 的稳定单 IP 客户端。
class CrcDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            CrcCommand.CAPABILITIES_GET,
            CrcCommand.DATA_LENGTH_GET,
            CrcCommand.RESULT_GET,
            CrcCommand.FIFO_STATUS_GET,
            CrcCommand.IRQ_SNAPSHOT_GET,
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
        self._mode: CrcMode | None = None
        self._max_calculate_bytes: int | None = None

    # 读取当前 CRC Service 的真实运行时能力；仅等待本次响应，失败按平台异常上抛。
    def capabilities_get(self) -> CrcCapabilities:

        message, _ = self._request(CrcCommand.CAPABILITIES_GET)
        capabilities = decode_capabilities(message.body)
        self._max_calculate_bytes = capabilities.max_calculate_bytes
        return capabilities

    # 使能当前 CRC 实例并清除旧模式缓存；仅等待本次响应，失败按平台异常上抛。
    def enable(self) -> None:

        self._request(CrcCommand.ENABLE)
        self._mode = None

    # 关闭当前 CRC 实例和它拥有的 IRQ 会话；仅等待本次响应，失败按平台异常上抛。
    def disable(self) -> None:

        self._request(CrcCommand.DISABLE)
        self._mode = None

    # 应用完整 CRC 配置并缓存当前模式；仅等待本次响应，失败按平台异常上抛。
    def configure(self, config: CrcConfig) -> None:

        normalized = validate_config(config)
        self._request(CrcCommand.CONFIGURE, encode_config(normalized))
        self._mode = normalized.mode

    # 在 Resource 地址范围上执行有界同步 CRC 计算；共享 Target 超时，失败按平台异常上抛。
    def calculate(
        self,
        source_address: int,
        length_bytes: int,
        *,
        timeout_s: float | None = None,
    ) -> CrcCalculateResult:

        mode = self._require_mode()
        maximum = self._runtime_maximum()
        address, length = validate_calculate(mode, source_address, length_bytes, maximum)
        message, _ = self._request(
            CrcCommand.CALCULATE,
            encode_calculate(address, length),
            timeout_s=timeout_s,
        )
        result = decode_calculate_result(message.body)
        validate_mode_value(mode, result.result, "result")
        return result

    # 设置诊断型 LENGTH 字节数；仅等待本次 Target 响应，失败按平台异常上抛。
    def data_length_set(self, length_bytes: int) -> None:

        self._require_mode()
        self._request(
            CrcCommand.DATA_LENGTH_SET,
            encode_uint32(validate_data_length(length_bytes)),
        )

    # 读取硬件剩余输入事务数；仅等待本次 Target 响应，失败按平台异常上抛。
    def remaining_input_count_get(self) -> int:

        self._require_mode()
        message, _ = self._request(CrcCommand.DATA_LENGTH_GET)
        return decode_uint32(message.body, "DATA_LENGTH_GET")

    # 读取并校验当前模式结果；仅等待本次 Target 响应，失败按平台异常上抛。
    def result_get(self) -> int:

        mode = self._require_mode()
        message, _ = self._request(CrcCommand.RESULT_GET)
        result = decode_uint32(message.body, "RESULT_GET")
        return validate_mode_value(mode, result, "result")

    # 校验并设置当前模式 CHECK 值；仅等待本次 Target 响应，失败按平台异常上抛。
    def check_value_set(self, value: int) -> None:

        mode = self._require_mode()
        self._request(
            CrcCommand.CHECK_VALUE_SET,
            encode_uint32(validate_mode_value(mode, value, "check_value")),
        )

    # 读取 CRC FIFO Overflow 状态；仅等待本次 Target 响应，失败按平台异常上抛。
    def fifo_status_get(self) -> CrcFifoStatus:

        self._require_mode()
        message, _ = self._request(CrcCommand.FIFO_STATUS_GET)
        return decode_fifo_status(message.body)

    # 使能指定 CRC IRQ 源并绑定回调；仅等待本次 Target 响应，失败按平台异常上抛。
    def irq_enable(self, events: CrcIrqEvent) -> None:

        self._irq_request(CrcCommand.IRQ_ENABLE, events)

    # 禁用指定 CRC IRQ 源并按需释放回调；仅等待本次响应，失败按平台异常上抛。
    def irq_disable(self, events: CrcIrqEvent) -> None:

        self._irq_request(CrcCommand.IRQ_DISABLE, events)

    # 屏蔽指定 CRC IRQ 源但保留 Raw 状态；仅等待本次响应，失败按平台异常上抛。
    def irq_mask(self, events: CrcIrqEvent) -> None:

        self._irq_request(CrcCommand.IRQ_MASK, events)

    # 解除指定 CRC IRQ 源的硬件屏蔽；仅等待本次响应，失败按平台异常上抛。
    def irq_unmask(self, events: CrcIrqEvent) -> None:

        self._irq_request(CrcCommand.IRQ_UNMASK, events)

    # 强制产生指定 CRC IRQ 源以验证链路；仅等待本次响应，失败按平台异常上抛。
    def irq_force(self, events: CrcIrqEvent) -> None:

        self._irq_request(CrcCommand.IRQ_FORCE, events)

    # 清除指定 CRC IRQ Pending；该命令允许在失败 Cleanup 中调用。
    def irq_clear(self, events: CrcIrqEvent) -> None:

        normalized = validate_irq_events(events)
        self._request(CrcCommand.IRQ_CLEAR, encode_irq_events(normalized))

    # 读取 CRC IRQ 状态和回调证据快照；仅等待本次响应，失败按平台异常上抛。
    def irq_snapshot_get(self) -> CrcIrqSnapshot:

        message, _ = self._request(CrcCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 执行一次宽度明确的测试输入写入，用于错误和 FIFO Feature。
    def test_input_write(self, width: CrcInputAccessWidth, value: int) -> None:

        self._require_mode()
        normalized_width, normalized_value = validate_test_input(width, value)
        self._request(
            CrcCommand.TEST_INPUT_WRITE,
            encode_test_input(normalized_width, normalized_value),
        )

    # 连续执行一组目标端 32-Bit 写入，并返回检查点、最终结果和 Overflow 事实。
    # 只等待本次批量响应；非法参数、目标拒绝、协议错误或超时立即失败。
    def test_input_burst_32(
        self,
        values: tuple[int, ...],
        checkpoint_count: int,
    ) -> CrcInputBurstResult:

        mode = self._require_mode()
        if mode is not CrcMode.CRC32:
            raise ValueError("test_input_burst_32 requires CRC32 mode")
        normalized_values, normalized_checkpoint = validate_test_input_burst(
            values,
            checkpoint_count,
        )
        message, _ = self._request(
            CrcCommand.TEST_INPUT_BURST_32,
            encode_test_input_burst(normalized_values, normalized_checkpoint),
        )
        result = decode_test_input_burst_result(message.body)
        if result.count != len(normalized_values) or (
            result.checkpoint_count != normalized_checkpoint
        ):
            raise ValueError("CRC burst response changed the requested counts")
        return result

    # 使用目标 DWT 测量 CRC32 CPU 路径；共享 Target 超时，失败按平台异常上抛。
    def calculate_timed(
        self,
        source_address: int,
        length_bytes: int,
        *,
        timeout_s: float | None = None,
    ) -> CrcTimedResult:

        mode = self._require_mode()
        if mode is not CrcMode.CRC32:
            raise ValueError("calculate_timed requires CRC32 mode")
        address, length = validate_calculate(
            mode,
            source_address,
            length_bytes,
            self._runtime_maximum(),
        )
        message, _ = self._request(
            CrcCommand.TEST_CALCULATE_TIMED,
            encode_timed_calculate(address, length),
            timeout_s=timeout_s,
        )
        result = decode_timed_result(message.body)
        validate_mode_value(mode, result.result, "result")
        if result.measured_bytes != length:
            raise ValueError("CRC timed response changed the requested byte count")
        return result

    # 进入 CRC Module 生命周期；不额外等待，退出或异常时均执行本 IP 清理。
    @contextmanager
    def module_mode(self) -> Iterator[CrcDriver]:

        self.enable()
        with self._cleanup_mode(
            "CRC module mode",
            (
                ("CRC IRQ clear", lambda: self.irq_clear(CrcIrqEvent.ALL)),
                ("CRC disable", self.disable),
            ),
        ):
            yield self

    # 执行一个 CRC IRQ 命令并保持本 IP 边界。
    def _irq_request(self, command: CrcCommand, events: CrcIrqEvent) -> None:

        self._require_mode()
        normalized = validate_irq_events(events)
        self._request(command, encode_irq_events(normalized))

    # 返回当前已配置模式；本地生命周期缺失时在发命令前失败。
    def _require_mode(self) -> CrcMode:

        if self._mode is None:
            raise RuntimeError("CRC must be enabled and configured before this operation")
        return self._mode

    # 延迟读取 Runtime Capability，并缓存本次连接的同步上限。
    def _runtime_maximum(self) -> int:

        if self._max_calculate_bytes is None:
            self._max_calculate_bytes = self.capabilities_get().max_calculate_bytes
        return self._max_calculate_bytes

    # 保留主错误并聚合 CRC 单 IP Cleanup 错误。
    @contextmanager
    def _cleanup_mode(
        self,
        label: str,
        actions: tuple[tuple[str, Callable[[], object]], ...],
    ) -> Iterator[None]:

        try:
            yield
        except BaseException as primary_error:
            cleanup_failures = run_cleanup(actions)
            if isinstance(primary_error, OperationCleanupError) and cleanup_failures:
                raise OperationCleanupError(
                    primary_error.primary_error,
                    (*primary_error.cleanup_failures, *cleanup_failures),
                ) from primary_error
            raise_with_cleanup(primary_error, cleanup_failures)
        cleanup_failures = run_cleanup(actions)
        if cleanup_failures:
            raise_with_cleanup(
                RuntimeError(f"{label} completed but cleanup did not"),
                cleanup_failures,
            )

    # 向当前 CRC Service Instance 发送一次请求；仅只读命令允许安全重试。
    def _request(
        self,
        command: CrcCommand,
        body: bytes = b"",
        *,
        timeout_s: float | None = None,
    ) -> tuple[ServiceMessage, Frame]:

        arguments: dict[str, object] = {
            "instance_id": self.instance_id,
            "body": body,
            "retry_safe": command in self._RETRY_SAFE_COMMANDS,
        }
        if timeout_s is not None:
            arguments["timeout_s"] = timeout_s
        return self._target.request(
            CRC_SERVICE_ID,
            int(command),
            **arguments,
        )
