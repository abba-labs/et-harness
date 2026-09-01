# AES PC Driver 单 IP 操作层。
#
# 职责：封装 AES Service 命令、请求超时、重试属性和 AES 本地清理。
# 边界：不调用其他 IP Driver，不读取 Profile，不包含 pytest 断言或跨 IP 编排。
# 依赖：仅依赖 TargetClient 和 AES 包内的协议、模型、编解码与校验模块。

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.cleanup import OperationCleanupError, raise_with_cleanup, run_cleanup
from .codec import (
    decode_block,
    decode_capabilities,
    decode_data_length,
    decode_irq_snapshot,
    decode_irq_transfer_status,
    decode_iv,
    decode_process_result,
    decode_status,
    decode_timed_result,
    encode_block,
    encode_config,
    encode_data_length,
    encode_irq_events,
    encode_irq_transfer,
    encode_iv,
    encode_key,
    encode_process,
    encode_status_mask,
    encode_timed_process,
)
from .contract import AES_SERVICE_ID, AesCommand
from .models import (
    AesCapabilities,
    AesConfig,
    AesFeature,
    AesIrqEvent,
    AesIrqSnapshot,
    AesIrqTransferStatus,
    AesKeySize,
    AesProcessResult,
    AesStatus,
    AesTimedResult,
)
from .validation import (
    validate_config,
    validate_data_length,
    validate_dma_request_flags,
    validate_instance_id,
    validate_irq_events,
    validate_key,
    validate_process_length,
    validate_process_output_capacity,
)


# AES Driver 只表达单个逻辑实例的原子操作，实例及能力均由运行时配置提供。
class AesDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            AesCommand.CAPABILITIES_GET,
            AesCommand.IV_GET,
            AesCommand.DATA_LENGTH_GET,
            AesCommand.STATUS_GET,
            AesCommand.IRQ_SNAPSHOT_GET,
            AesCommand.IRQ_TRANSFER_STATUS_GET,
        }
    )

    # 绑定一个逻辑 AES Service 实例；实例范围在发出任何请求前完成校验。
    def __init__(self, target: TargetClient, instance_id: int) -> None:
        self._target = target
        self.instance_id = validate_instance_id(instance_id)
        self._capabilities: AesCapabilities | None = None
        self._configured = False
        self._key_size: AesKeySize | None = None
        self._config: AesConfig | None = None

    # 获取 AES Service 能力快照并缓存运行时上限。
    # 等待能力响应；目标拒绝、协议错误或超时均由统一请求层抛出异常。
    def capabilities_get(self) -> AesCapabilities:
        message, _ = self._request(AesCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 发送 AES module enable 命令，建立本地运行前置状态。
    # 等待使能响应；目标拒绝或超时立即失败，不在 Driver 内吞掉错误。
    def enable(self) -> None:
        self._request(AesCommand.ENABLE)

    # 发送 AES module disable 命令并清除本地配置缓存。
    # 等待禁用响应；成功后才清理本地状态，失败或超时保留现场。
    def disable(self) -> None:
        self._request(AesCommand.DISABLE)
        self._configured = False
        self._key_size = None
        self._config = None

    # 配置 AES 方向、密钥尺寸、模式、padding、endian 和 counter。
    # 先校验能力范围再等待配置响应；非法配置、目标拒绝或超时立即失败。
    def configure(self, config: AesConfig) -> None:
        normalized = validate_config(config)
        self._request(AesCommand.CONFIGURE, encode_config(normalized))
        self._configured = True
        self._key_size = normalized.key_size
        self._config = normalized

    # 写入当前 AES 配置对应的 128-bit 或 256-bit 密钥。
    # 先校验密钥长度再等待写入响应；未配置、目标拒绝或超时立即失败。
    def key_set(self, key: bytes, key_size: AesKeySize | None = None) -> None:
        selected = self._key_size if key_size is None else key_size
        if selected is None:
            raise RuntimeError("AES key size must be configured before key_set")
        value, normalized = validate_key(key, selected)
        self._request(AesCommand.KEY_SET, encode_key(value, normalized))

    # 写入 CBC/CTR 使用的 16 字节 AES IV。
    # 先校验 IV 长度再等待写入响应；目标拒绝或超时立即失败。
    def iv_set(self, iv: bytes) -> None:
        self._request(AesCommand.IV_SET, encode_iv(iv))

    # 读取并解码 AES 当前 canonical 16-byte IV，保留 Service 的精确字节顺序。
    # 等待 IV 读取响应并严格解码；长度错误、目标拒绝或超时立即失败。
    def iv_get(self) -> bytes:
        message, _ = self._request(AesCommand.IV_GET)
        return decode_iv(message.body)

    # 按固件自报的数据长度位宽校验后写入 AES 数据长度字段。
    # 按运行时能力校验长度并等待响应；越界、目标拒绝或超时立即失败。
    def data_length_set(self, length_bytes: int) -> None:
        maximum = (1 << self._runtime_capabilities().hardware_data_length_bits) - 1
        self._request(
            AesCommand.DATA_LENGTH_SET,
            encode_data_length(validate_data_length(length_bytes, maximum)),
        )

    # 读取 AES 当前数据长度字段，并按运行时能力验证目标没有返回越界值。
    # 等待长度读取响应并按运行时位宽复核；越界或协议错误立即失败。
    def data_length_get(self) -> int:
        message, _ = self._request(AesCommand.DATA_LENGTH_GET)
        value = decode_data_length(message.body)
        maximum = (1 << self._runtime_capabilities().hardware_data_length_bits) - 1
        return validate_data_length(value, maximum)

    # 执行 Resource-backed AES PROCESS，并可校验 destination 容量。
    # 等待一次有界处理完成；容量不足、目标拒绝、协议错误或超时立即失败。
    def process(
        self,
        source_handle: int,
        source_offset: int,
        destination_handle: int,
        destination_offset: int,
        logical_length: int,
        *,
        destination_capacity: int | None = None,
        timeout_s: float | None = None,
    ) -> AesProcessResult:
        self._require_configured()
        length = validate_process_length(logical_length, self._runtime_process_maximum())
        if destination_capacity is not None:
            if self._config is None:
                raise RuntimeError(
                    "AES configuration is unavailable for output capacity validation"
                )
            validate_process_output_capacity(
                destination_capacity,
                length,
                self._config,
                self._runtime_capabilities().max_process_output_bytes,
            )
        body = encode_process(
            source_handle,
            source_offset,
            destination_handle,
            destination_offset,
            length,
        )
        message, _ = self._request(AesCommand.PROCESS, body, timeout_s=timeout_s)
        result = decode_process_result(message.body)
        if destination_capacity is not None and result.produced_bytes > destination_capacity:
            raise ValueError("AES PROCESS produced bytes exceed destination capacity")
        return result

    # 读取 AES BUSY、request 和 FINISH 状态快照。
    # 等待状态快照响应；目标拒绝、协议错误或超时立即失败。
    def status_get(self) -> AesStatus:
        message, _ = self._request(AesCommand.STATUS_GET)
        return decode_status(message.body)

    # 校验 W1C 状态掩码并精确清除所选 AES 状态位，不影响其他位。
    # 等待状态清除响应；非法掩码、目标拒绝或超时立即失败。
    def status_clear(self, status_mask: int) -> None:
        self._request(AesCommand.STATUS_CLEAR, encode_status_mask(status_mask))

    # 校验 IRQ source 掩码，并请求固件使能和绑定所选 AES 中断源。
    # 等待中断使能响应；非法事件、目标拒绝或超时立即失败。
    def irq_enable(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_ENABLE, events)

    # 校验 IRQ source 掩码，并请求固件禁用和按需解绑所选 AES 中断源。
    # 等待中断禁用响应；非法事件、目标拒绝或超时立即失败。
    def irq_disable(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_DISABLE, events)

    # 屏蔽指定 AES IRQ source 的 delivery status。
    # 等待中断屏蔽响应；非法事件、目标拒绝或超时立即失败。
    def irq_mask(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_MASK, events)

    # 解除指定 AES IRQ source 的 delivery mask。
    # 等待解除屏蔽响应；非法事件、目标拒绝或超时立即失败。
    def irq_unmask(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_UNMASK, events)

    # 软件 force 指定 AES IRQ source 生成事件。
    # 等待软件触发响应；非法事件、目标拒绝或超时立即失败。
    def irq_force(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_FORCE, events)

    # 清除指定 AES IRQ source 的 pending/latched 状态。
    # 等待中断清除响应；非法事件、目标拒绝或超时立即失败。
    def irq_clear(self, events: AesIrqEvent) -> None:
        self._irq_request(AesCommand.IRQ_CLEAR, events)

    # 读取 AES IRQ raw/status/latched 和事件计数快照。
    # 等待中断快照响应并严格解码；目标拒绝、协议错误或超时立即失败。
    def irq_snapshot_get(self) -> AesIrqSnapshot:
        message, _ = self._request(AesCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 设置 AES input/output DMA request gate。
    # 等待 DMA 请求门控响应；参数非法、目标拒绝或超时立即失败。
    def dma_request_set(self, input_enable: bool, output_enable: bool) -> None:
        if not isinstance(input_enable, bool) or not isinstance(output_enable, bool):
            raise ValueError("AES DMA request enables must be bool")
        flags = int(input_enable) | (int(output_enable) << 1)
        self._request(
            AesCommand.DMA_REQUEST_SET, validate_dma_request_flags(flags).to_bytes(4, "little")
        )

    # 启动 AES IRQ-driven Resource transfer。
    # 等待中断传输启动响应；未配置、长度越界、目标拒绝或超时立即失败。
    def irq_transfer_start(
        self,
        source_handle: int,
        source_offset: int,
        destination_handle: int,
        destination_offset: int,
        logical_length: int,
        *,
        timeout_s: float | None = None,
    ) -> None:
        self._require_configured()
        body = encode_irq_transfer(
            source_handle,
            source_offset,
            destination_handle,
            destination_offset,
            validate_process_length(logical_length, self._runtime_process_maximum()),
        )
        self._request(AesCommand.IRQ_TRANSFER_START, body, timeout_s=timeout_s)

    # 读取 AES IRQ transfer state、offset 和产出计数。
    # 等待中断传输状态响应；目标拒绝、协议错误或超时立即失败。
    def irq_transfer_status_get(self) -> AesIrqTransferStatus:
        message, _ = self._request(AesCommand.IRQ_TRANSFER_STATUS_GET)
        return decode_irq_transfer_status(message.body)

    # 中止当前 AES IRQ transfer 会话。
    # 等待中断传输终止响应；目标拒绝或超时立即失败。
    def irq_transfer_abort(self) -> None:
        self._request(AesCommand.IRQ_TRANSFER_ABORT)

    # 执行 AES target-local timed process 并返回目标周期。
    # 等待目标端计时处理完成；未配置、目标拒绝、协议错误或超时立即失败。
    def timed_process(
        self,
        source_handle: int,
        source_offset: int,
        destination_handle: int,
        destination_offset: int,
        logical_length: int,
        *,
        timeout_s: float | None = None,
    ) -> AesTimedResult:
        self._require_configured()
        body = encode_timed_process(
            source_handle,
            source_offset,
            destination_handle,
            destination_offset,
            validate_process_length(logical_length, self._runtime_process_maximum()),
        )
        message, _ = self._request(AesCommand.TIMED_PROCESS, body, timeout_s=timeout_s)
        return decode_timed_result(message.body)

    # 写入一个 16 字节 AES CPU input block。
    # 等待单块写入响应；块长度错误、目标拒绝或超时立即失败。
    def block_write(self, block: bytes) -> None:
        self._request(AesCommand.BLOCK_WRITE, encode_block(block))

    # 绕过 DATA_IN_REQ 握手写入一个测试块，仅用于触发硬件错误 Feature。
    # 目标必须声明 TEST_EXTENSIONS；长度错误、目标拒绝或超时立即失败。
    def block_write_direct(self, block: bytes) -> None:
        capabilities = self.capabilities_get()
        if not (capabilities.features & AesFeature.TEST_EXTENSIONS):
            raise RuntimeError("AES direct block stimulus is not supported")
        self._request(AesCommand.BLOCK_WRITE_DIRECT, encode_block(block))

    # 在同一个目标执行窗口内连续写入两个测试块，用于刺激输入冲突。
    # 目标必须声明 TEST_EXTENSIONS；两个块均严格限制为 16 字节。
    # 等待一次原子响应；编码失败、目标拒绝或超时立即失败，不自动重试激励。
    def block_write_pair_direct(self, first: bytes, second: bytes) -> None:
        capabilities = self.capabilities_get()
        if not (capabilities.features & AesFeature.TEST_EXTENSIONS):
            raise RuntimeError("AES direct block stimulus is not supported")
        body = encode_block(first) + encode_block(second)
        self._request(AesCommand.BLOCK_WRITE_PAIR_DIRECT, body)

    # 在同一个目标执行窗口内写入测试块并立即关闭模块。
    # 目标必须声明 TEST_EXTENSIONS；用于观测未完成关闭硬件事件。
    # 等待一次原子响应；编码失败、目标拒绝或超时立即失败，不自动重试激励。
    def block_write_disable_direct(self, block: bytes) -> None:
        capabilities = self.capabilities_get()
        if not (capabilities.features & AesFeature.TEST_EXTENSIONS):
            raise RuntimeError("AES direct block stimulus is not supported")
        self._request(AesCommand.BLOCK_WRITE_DISABLE_DIRECT, encode_block(block))
        self._configured = False
        self._key_size = None
        self._config = None

    # 读取一个 16 字节 AES CPU output block。
    # 等待单块读取响应并严格解码；目标拒绝、长度错误或超时立即失败。
    def block_read(self) -> bytes:
        message, _ = self._request(AesCommand.BLOCK_READ)
        return decode_block(message.body)

    # 进入 AES 单 IP module scope，退出时按固定顺序清理 IRQ、DMA、状态和模块。
    # 进入模块作用域并等待原子操作；退出时按固定顺序清理，清理失败统一上抛。
    @contextmanager
    def module_mode(self) -> Iterator[AesDriver]:
        self.enable()
        with self._cleanup_mode(
            "AES module mode",
            (
                ("AES IRQ transfer abort", self.irq_transfer_abort),
                ("AES DMA request disable", lambda: self.dma_request_set(False, False)),
                ("AES IRQ disable", lambda: self.irq_disable(AesIrqEvent.ALL)),
                ("AES IRQ clear", lambda: self.irq_clear(AesIrqEvent.ALL)),
                ("AES status clear", lambda: self.status_clear(0x07)),
                ("AES disable", self.disable),
            ),
        ):
            yield self

    # 校验 IRQ 事件掩码，并发送一条 AES IRQ 原子命令。
    def _irq_request(self, command: AesCommand, events: AesIrqEvent) -> None:
        self._request(command, encode_irq_events(validate_irq_events(events)))

    # 要求当前实例已成功配置，避免在本地前置状态缺失时发送运算命令。
    def _require_configured(self) -> None:
        if not self._configured:
            raise RuntimeError("AES must be enabled and configured before this operation")

    # 返回运行时声明的单次 PROCESS 最大输入长度。
    def _runtime_process_maximum(self) -> int:
        return self._runtime_capabilities().max_process_bytes

    # 延迟读取并缓存当前连接的 AES Runtime Capability。
    def _runtime_capabilities(self) -> AesCapabilities:
        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    # 聚合本 IP 生命周期清理失败，并保留原始业务异常。
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

    # 发送一次 AES Service 请求；只有白名单中的只读命令允许安全重试。
    def _request(
        self,
        command: AesCommand,
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
        return self._target.request(AES_SERVICE_ID, int(command), **arguments)
