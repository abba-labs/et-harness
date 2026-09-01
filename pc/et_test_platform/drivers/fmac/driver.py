# FMAC PC Driver Package 的 driver 层。
#
# 职责：提供 FMAC 单 IP 稳定原子 API、Runtime Capability 校验和请求边界。
# 边界：不调用其他 IP Driver、不读取 Profile、不实现 Golden 或 Case 结论。
# 依赖：仅依赖TargetClient及本FMAC Contract、Codec、Model和Validation。

from __future__ import annotations

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from .codec import (
    decode_capabilities,
    decode_config_snapshot,
    decode_count,
    decode_irq_snapshot,
    decode_process_result,
    decode_status,
    decode_timed_process_result,
    decode_uint32,
    encode_coefficients,
    encode_config,
    encode_process,
    encode_resource,
    encode_start,
    encode_uint32,
)
from .contract import FMAC_SERVICE_ID, FmacCommand
from .models import (
    FmacCapabilities,
    FmacConfig,
    FmacDataFormat,
    FmacDmaRequest,
    FmacFeature,
    FmacFunction,
    FmacIrqEvent,
    FmacIrqSnapshot,
    FmacProcessResult,
    FmacStatus,
    FmacTimedProcessResult,
)
from .validation import (
    require_uint,
    validate_config,
    validate_data_action,
    validate_dma_requests,
    validate_function,
    validate_irq_events,
)


# 提供芯片中立的FMAC原子操作；统一校验参数并通过TargetClient完成事务。
class FmacDriver:
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            FmacCommand.CAPABILITIES_GET,
            FmacCommand.CONFIG_SNAPSHOT_GET,
            FmacCommand.STATUS_GET,
            FmacCommand.IRQ_SNAPSHOT_GET,
        }
    )

    def __init__(self, target: TargetClient, instance_id: int = 0) -> None:

        self.instance_id = require_uint(instance_id, "instance_id", 0xFFFF)
        self._target = target
        self._capabilities: FmacCapabilities | None = None
        self._configured = False

    # 读取并缓存当前FMAC Service的真实运行时能力；等待一次响应，超时或目标失败时抛出异常。
    def capabilities_get(self) -> FmacCapabilities:

        message, _ = self._request(FmacCommand.CAPABILITIES_GET)
        self._capabilities = decode_capabilities(message.body)
        return self._capabilities

    # 清除FMAC Service保存的配置和IRQ状态；等待一次响应，超时或目标失败时抛出异常。
    # 本操作不复位硬件或Resource Pool，三步隔离顺序由Case显式编排。
    def state_reset(self) -> None:

        self._request(FmacCommand.STATE_RESET)
        self._configured = False

    # 应用一份完整FMAC准静态配置；等待一次响应，非法参数、超时或目标失败时抛出异常。
    def configure(self, config: FmacConfig) -> None:

        normalized = validate_config(config, self._runtime_capabilities())
        self._request(FmacCommand.CONFIGURE, encode_config(normalized))
        self._configured = True

    # 读取当前FMAC完整公共配置快照；等待一次响应，超时或目标失败时抛出异常。
    def config_snapshot_get(self) -> FmacConfig:

        message, _ = self._request(FmacCommand.CONFIG_SNAPSHOT_GET)
        return decode_config_snapshot(message.body)

    # 启动一个已发布FMAC功能并显式提供P/Q抽头数量；等待一次响应，参数或目标失败时抛出异常。
    def start(
        self,
        function: FmacFunction,
        feedforward_taps: int,
        feedback_taps: int = 0,
    ) -> None:

        self._require_configured()
        normalized = validate_function(
            function,
            feedforward_taps,
            feedback_taps,
            self._runtime_capabilities(),
        )
        self._request(FmacCommand.START, encode_start(*normalized))

    # 启动一笔保留原始P/Q值的测试事务，用于自然参数错误刺激。
    def start_unchecked(
        self,
        function: FmacFunction,
        feedforward_taps: int,
        feedback_taps: int = 0,
    ) -> None:

        self._require_configured()
        capabilities = self._runtime_capabilities()
        if not capabilities.features & FmacFeature.TEST_EXTENSIONS:
            raise RuntimeError("FMAC unchecked start is unavailable")
        if not isinstance(function, FmacFunction):
            raise TypeError("function must be FmacFunction")
        feedforward = require_uint(feedforward_taps, "feedforward_taps", 0xFF)
        feedback = require_uint(feedback_taps, "feedback_taps", 0xFF)
        self._request(
            FmacCommand.START_UNCHECKED,
            encode_start(function, feedforward, feedback),
        )

    # 显式停止当前运行功能；等待一次响应，超时或目标失败时抛出异常，不隐式执行Clear。
    def stop(self) -> None:

        self._request(FmacCommand.STOP)

    # 清除FMAC动态指针、状态和活动控制；等待一次响应，超时或目标失败时抛出异常。
    def clear(self) -> None:

        self._request(FmacCommand.CLEAR)

    # 从一个Resource范围向X1装载确定数量的数据；等待一次响应，范围或目标失败时抛出异常。
    def x1_preload(
        self,
        handle: int,
        offset: int,
        count: int,
        format_: FmacDataFormat = FmacDataFormat.Q15,
    ) -> int:

        return self._resource_action(FmacCommand.X1_PRELOAD, handle, offset, count, format_)

    # 从两个独立Resource范围装载前馈和可选反馈系数段；等待一次响应，范围或目标失败时抛出异常。
    def coefficients_load(
        self,
        feedforward_handle: int,
        feedforward_offset: int,
        feedforward_count: int,
        *,
        feedback_handle: int = 0,
        feedback_offset: int = 0,
        feedback_count: int = 0,
    ) -> None:

        self._require_configured()
        capabilities = self._runtime_capabilities()
        require_uint(feedforward_handle, "feedforward_handle", 0xFFFFFFFF, nonzero=True)
        require_uint(feedforward_offset, "feedforward_offset", 0xFFFFFFFF)
        require_uint(
            feedforward_count,
            "feedforward_count",
            capabilities.max_feedforward_taps,
            nonzero=True,
        )
        require_uint(feedback_handle, "feedback_handle", 0xFFFFFFFF)
        require_uint(feedback_offset, "feedback_offset", 0xFFFFFFFF)
        require_uint(feedback_count, "feedback_count", capabilities.max_feedback_taps)
        if feedback_count != 0 and feedback_handle == 0:
            raise ValueError("feedback_handle is required when feedback_count is nonzero")
        self._request(
            FmacCommand.COEFFICIENTS_LOAD,
            encode_coefficients(
                feedforward_handle,
                feedforward_offset,
                feedforward_count,
                feedback_handle,
                feedback_offset,
                feedback_count,
            ),
        )

    # 从一个Resource范围向Y装载确定数量的数据或反馈初态；等待一次响应，范围或目标失败时抛出异常。
    def y_preload(
        self,
        handle: int,
        offset: int,
        count: int,
        format_: FmacDataFormat = FmacDataFormat.Q15,
    ) -> int:

        return self._resource_action(FmacCommand.Y_PRELOAD, handle, offset, count, format_)

    # 将Resource中的有界Chunk写入活动FMAC流；等待一次响应，范围或目标失败时抛出异常。
    def stream_write(
        self,
        handle: int,
        offset: int,
        count: int,
        format_: FmacDataFormat = FmacDataFormat.Q15,
    ) -> int:

        return self._resource_action(FmacCommand.STREAM_WRITE, handle, offset, count, format_)

    # 将活动FMAC输出读入Resource范围；等待一次响应，范围或目标失败时抛出异常。
    def stream_read(
        self,
        handle: int,
        offset: int,
        count: int,
        format_: FmacDataFormat = FmacDataFormat.Q15,
    ) -> int:

        return self._resource_action(FmacCommand.STREAM_READ, handle, offset, count, format_)

    # 执行一次不经Full保护的原始数据写；等待一次响应，配置或目标失败时抛出异常。
    def data_write_one_unchecked(self, raw_value: int) -> None:

        self._require_configured()
        self._request(
            FmacCommand.DATA_WRITE_ONE_UNCHECKED,
            encode_uint32(require_uint(raw_value, "raw_value", 0xFFFFFFFF)),
        )

    # 执行一次不经Empty保护的原始数据读；等待一次响应，配置或目标失败时抛出异常。
    def data_read_one_unchecked(self) -> int:

        self._require_configured()
        message, _ = self._request(FmacCommand.DATA_READ_ONE_UNCHECKED)
        return decode_uint32(message.body, "DATA_READ_ONE_UNCHECKED")

    # 在目标端执行一笔有界one-shot事务；等待硬件处理完成，超时或目标失败时抛出异常。
    def process(
        self,
        function: FmacFunction,
        feedforward_taps: int,
        feedback_taps: int,
        format_: FmacDataFormat,
        source_handle: int,
        source_offset: int,
        destination_handle: int,
        destination_offset: int,
        count: int,
    ) -> FmacProcessResult:

        self._require_configured()
        normalized_function, feedforward, feedback = validate_function(
            function,
            feedforward_taps,
            feedback_taps,
            self._runtime_capabilities(),
        )
        source = validate_data_action(
            source_handle,
            source_offset,
            count,
            format_,
            self._runtime_capabilities(),
        )
        destination = validate_data_action(
            destination_handle,
            destination_offset,
            count,
            format_,
            self._runtime_capabilities(),
        )
        message, _ = self._request(
            FmacCommand.PROCESS,
            encode_process(
                normalized_function,
                feedforward,
                feedback,
                format_,
                source[0],
                source[1],
                destination[0],
                destination[1],
                source[2],
            ),
        )
        return decode_process_result(message.body)

    # 在目标侧执行一笔有界one-shot事务；等待硬件完成，超时或目标失败时抛出异常并保留周期事实。
    def process_timed(
        self,
        function: FmacFunction,
        feedforward_taps: int,
        feedback_taps: int,
        format_: FmacDataFormat,
        source_handle: int,
        source_offset: int,
        destination_handle: int,
        destination_offset: int,
        count: int,
    ) -> FmacTimedProcessResult:

        self._require_configured()
        capabilities = self._runtime_capabilities()
        if not capabilities.features & FmacFeature.TIMED_PROCESS:
            raise RuntimeError("FMAC timed process is unavailable")
        normalized_function, feedforward, feedback = validate_function(
            function,
            feedforward_taps,
            feedback_taps,
            capabilities,
        )
        source = validate_data_action(
            source_handle,
            source_offset,
            count,
            format_,
            capabilities,
        )
        destination = validate_data_action(
            destination_handle,
            destination_offset,
            count,
            format_,
            capabilities,
        )
        message, _ = self._request(
            FmacCommand.PROCESS_TIMED,
            encode_process(
                normalized_function,
                feedforward,
                feedback,
                format_,
                source[0],
                source[1],
                destination[0],
                destination[1],
                source[2],
            ),
        )
        return decode_timed_process_result(message.body)

    # 读取FMAC状态快照并保留各独立硬件事实；等待一次响应，超时或目标失败时抛出异常。
    def status_get(self) -> FmacStatus:

        message, _ = self._request(FmacCommand.STATUS_GET)
        return decode_status(message.body)

    # 启用指定FMAC IRQ Source；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_enable(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_ENABLE, events)

    # 禁用指定FMAC IRQ Source；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_disable(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_DISABLE, events)

    # 屏蔽指定FMAC IRQ Source；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_mask(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_MASK, events)

    # 解除指定FMAC IRQ Source屏蔽；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_unmask(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_UNMASK, events)

    # 强制指定FMAC IRQ Source；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_force(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_FORCE, events)

    # 清除指定FMAC IRQ Source及Service latch；等待一次响应，非法事件或目标失败时抛出异常。
    def irq_clear(self, events: FmacIrqEvent) -> None:
        self._irq_request(FmacCommand.IRQ_CLEAR, events)

    # 读取FMAC Raw、Status、ISR latch和投递计数快照；等待一次响应，超时或目标失败时抛出异常。
    def irq_snapshot_get(self) -> FmacIrqSnapshot:

        message, _ = self._request(FmacCommand.IRQ_SNAPSHOT_GET)
        return decode_irq_snapshot(message.body)

    # 控制FMAC输入/输出DMA request gate；等待一次响应，非法位或目标失败时抛出异常。
    def dma_request_set(self, requests: FmacDmaRequest) -> None:

        normalized = validate_dma_requests(requests)
        self._request(FmacCommand.DMA_REQUEST_SET, encode_uint32(int(normalized)))

    def _resource_action(
        self,
        command: FmacCommand,
        handle: int,
        offset: int,
        count: int,
        format_: FmacDataFormat,
    ) -> int:

        self._require_configured()
        normalized = validate_data_action(
            handle,
            offset,
            count,
            format_,
            self._runtime_capabilities(),
        )
        message, _ = self._request(command, encode_resource(*normalized))
        return decode_count(message.body, command.name)

    def _irq_request(self, command: FmacCommand, events: FmacIrqEvent) -> None:

        normalized = validate_irq_events(events, self._runtime_capabilities())
        self._request(command, encode_uint32(int(normalized)))

    def _runtime_capabilities(self) -> FmacCapabilities:

        if self._capabilities is None:
            self._capabilities = self.capabilities_get()
        return self._capabilities

    def _require_configured(self) -> None:

        if not self._configured:
            raise RuntimeError("FMAC must be configured before this operation")

    def _request(self, command: FmacCommand, body: bytes = b"") -> tuple[ServiceMessage, Frame]:

        return self._target.request(
            FMAC_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            retry_safe=command in self._RETRY_SAFE_COMMANDS,
        )
