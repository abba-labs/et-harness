# DMA PC Driver Package 的driver层。
#
# 职责：提供 DMA 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.cleanup import OperationCleanupError, raise_with_cleanup, run_cleanup
from ...core.deadline import OperationDeadline
from ...core.errors import ProtocolError, RequestTimeout
from .codec import (
    decode_capabilities,
    decode_channel_snapshot,
    decode_channel_status,
    decode_component_snapshot,
    decode_free_channel,
    decode_interrupt_snapshot,
    decode_irq_enable_response,
    decode_irq_result,
    decode_timing_snapshot,
    encode_channel,
    encode_channel_mask,
    encode_config,
    encode_interrupt_control,
    encode_irq_enable,
    encode_irq_events,
    encode_lli_descriptor_location,
    encode_lli_descriptor_location_v2,
    encode_software_handshake_request,
)
from .contract import DMA_SERVICE_ID, DmaCommand
from .models import (
    DmaAccessView,
    DmaCapabilities,
    DmaChannelSnapshot,
    DmaChannelStatus,
    DmaComponentSnapshot,
    DmaConfig,
    DmaHandshakeTarget,
    DmaInterruptSnapshot,
    DmaIrqEvent,
    DmaIrqResult,
    DmaSoftwareRequestKind,
    DmaTimingSnapshot,
)
from .validation import (
    normalize_descriptor_handle,
    validate_channel_mask,
    validate_descriptor_offset,
    validate_start_wait,
)


# 一个 DMA Controller Service Instance 的 PC 侧稳定客户端。
class DmaDriver:
    _READ_ONLY_COMMANDS = {
        DmaCommand.CAPABILITIES_GET,
        DmaCommand.CHANNEL_STATUS_GET,
        DmaCommand.FREE_CHANNEL_FIND,
        DmaCommand.COMPONENT_SNAPSHOT_GET,
        DmaCommand.INTERRUPT_SNAPSHOT_GET,
        DmaCommand.CHANNEL_SNAPSHOT_GET,
        DmaCommand.IRQ_RESULT_GET,
        DmaCommand.TIMING_SNAPSHOT_GET,
    }
    _IDEMPOTENT_COMMANDS = {
        DmaCommand.CONTROLLER_ENABLE,
        DmaCommand.CONTROLLER_DISABLE,
        DmaCommand.CHANNEL_DECONFIGURE,
        DmaCommand.CHANNEL_STOP,
        DmaCommand.CHANNEL_SUSPEND,
        DmaCommand.CHANNEL_RESUME,
        DmaCommand.LLI_DESCRIPTOR_INIT,
        DmaCommand.LLI_DESCRIPTOR_INIT_V2,
        DmaCommand.INTERRUPT_MASK_ENABLE,
        DmaCommand.INTERRUPT_MASK_DISABLE,
        DmaCommand.IRQ_ENABLE,
        DmaCommand.IRQ_COMBINED_ENABLE,
        DmaCommand.IRQ_DISABLE,
    }
    _RETRY_SAFE_COMMANDS = _READ_ONLY_COMMANDS | _IDEMPOTENT_COMMANDS

    # 绑定一个DMA Service实例；clock和sleep仅用于可测试的有界轮询。
    def __init__(
        self,
        target: TargetClient,
        instance_id: int = 0,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._target = target
        self.instance_id = instance_id
        self._clock = clock
        self._sleep = sleep
        self._capabilities_cache: DmaCapabilities | None = None

    # 读取当前DMA实例能力并缓存Channel数量，供后续位图边界校验使用。
    # 等待一次能力响应；目标拒绝、协议错误或超时立即失败。
    def capabilities_get(self) -> DmaCapabilities:

        message, _ = self._request(DmaCommand.CAPABILITIES_GET)
        capabilities = decode_capabilities(message.body)
        self._capabilities_cache = capabilities
        return capabilities

    # 启用当前DMA Controller；只提交单条原子命令。
    # 等待本次响应；目标拒绝、协议错误或超时立即失败。
    def controller_enable(self) -> None:

        self._request(DmaCommand.CONTROLLER_ENABLE)

    # 关闭当前DMA Controller；不隐式停止或释放Channel。
    # 等待本次响应；目标拒绝、协议错误或超时立即失败。
    def controller_disable(self) -> None:

        self._request(DmaCommand.CONTROLLER_DISABLE)

    # 兼容存量调用：进入时启用Controller，退出时关闭并保留Cleanup错误。
    @contextmanager
    def controller_mode(self) -> Iterator[None]:

        self.controller_enable()
        with self._cleanup_mode(
            "DMA controller mode",
            (("DMA controller disable", self.controller_disable),),
        ):
            yield

    # 配置一个DMA Channel；请求超时时尝试Deconfigure，避免留下未知配置状态。
    def configure(self, config: DmaConfig) -> None:

        try:
            self._request(DmaCommand.CHANNEL_CONFIGURE, encode_config(config))
        except RequestTimeout as primary_error:
            cleanup_failures = run_cleanup(
                (("DMA channel deconfigure", lambda: self.deconfigure(config.channel)),)
            )
            raise_with_cleanup(primary_error, cleanup_failures)

    # 解除指定Channel配置；调用方负责先停止仍在运行的Channel。
    # 等待本次响应；目标拒绝、协议错误或超时立即失败。
    def deconfigure(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_DECONFIGURE, encode_channel(channel))

    # 兼容存量调用：配置Channel，退出时依次Stop、Deconfigure并保留Cleanup错误。
    @contextmanager
    def configured_channel(self, config: DmaConfig) -> Iterator[None]:

        self.configure(config)
        with self._cleanup_mode(
            "DMA configured channel",
            (
                ("DMA channel stop", lambda: self.stop(config.channel)),
                ("DMA channel deconfigure", lambda: self.deconfigure(config.channel)),
            ),
        ):
            yield

    # 启动一个已配置Channel；不在本接口内轮询完成状态。
    # 只等待启动命令响应；目标拒绝、协议错误或超时立即失败。
    def start(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_START, encode_channel(channel))

    # 在一个总 Deadline 内启动并等待通道完成。
    #
    # START 与每次 STATUS_GET 都使用同一个 ``OperationDeadline`` 的剩余
    # 时间。ERROR 或 Deadline Exhaustion 是 Primary Error；随后始终依次
    # 尝试 STOP 和 DECONFIGURE，清理失败通过 ``OperationCleanupError``
    # 与 Primary Error 同时保留。
    def wait_complete(
        self,
        channel: int,
        *,
        timeout_s: float,
        poll_interval_s: float = 0.001,
    ) -> None:

        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label=f"DMA channel {channel} completion",
        )
        channel_body = encode_channel(channel)
        try:
            self._request(
                DmaCommand.CHANNEL_START,
                channel_body,
                timeout_s=deadline.remaining_s(),
            )
            while True:
                message, _ = self._request(
                    DmaCommand.CHANNEL_STATUS_GET,
                    channel_body,
                    timeout_s=deadline.remaining_s(),
                )
                status = decode_channel_status(message.body)
                if status.interrupt_events & DmaIrqEvent.ERROR:
                    raise RuntimeError(f"DMA channel {channel} completed with ERROR")
                if status.is_free:
                    return
                deadline.sleep(poll_interval_s)
        except BaseException as primary_error:
            cleanup_failures = run_cleanup(
                (
                    ("DMA channel stop", lambda: self.stop(channel)),
                    ("DMA channel deconfigure", lambda: self.deconfigure(channel)),
                )
            )
            raise_with_cleanup(primary_error, cleanup_failures)

    # 兼容旧 Poll-Count API，并委托给严格总 Deadline 实现。
    def start_wait(
        self,
        channel: int,
        max_polls: int = 2_000,
        *,
        poll_interval_s: float = 0.001,
    ) -> None:

        validate_start_wait(max_polls, poll_interval_s)
        self.wait_complete(
            channel,
            timeout_s=max_polls * poll_interval_s,
            poll_interval_s=poll_interval_s,
        )

    # 停止指定Channel；不隐式Deconfigure或关闭Controller。
    # 等待本次响应；目标拒绝、协议错误或超时立即失败。
    def stop(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_STOP, encode_channel(channel))

    # 请求指定Channel暂停；完成时机由后续状态观测判定。
    # 只等待暂停命令响应；目标拒绝、协议错误或超时立即失败。
    def suspend(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_SUSPEND, encode_channel(channel))

    # 请求指定Channel恢复；不在本接口内等待传输完成。
    def resume(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_RESUME, encode_channel(channel))

    # 返回Firmware选出的首个空闲Channel，并用已缓存能力校验返回范围。
    # 等待一次查询响应；无空闲资源、非法响应或超时立即失败。
    def find_free_channel(self) -> int:

        message, _ = self._request(DmaCommand.FREE_CHANNEL_FIND)
        channel = decode_free_channel(message.body)
        if (
            self._capabilities_cache is not None
            and channel >= self._capabilities_cache.channel_count
        ):
            raise ProtocolError("DMA free-channel response is out of range")
        return channel

    # 以一个Channel位图原子启动多路Channel；不轮询各路完成状态。
    # 只等待启动命令响应；目标拒绝、协议错误或超时立即失败。
    def start_channels(self, channel_mask: int) -> None:

        channel_count = (
            self._capabilities_cache.channel_count if self._capabilities_cache is not None else 32
        )
        validate_channel_mask(channel_mask, channel_count)
        self._request(DmaCommand.CHANNELS_START, encode_channel_mask(channel_mask))

    # 读取指定访问视图的DMA组件身份和静态参数快照。
    # 等待一次快照响应；目标拒绝、协议错误或超时立即失败。
    def component_snapshot_get(
        self,
        access_view: DmaAccessView = DmaAccessView.NORMAL,
    ) -> DmaComponentSnapshot:

        message, _ = self._request(
            DmaCommand.COMPONENT_SNAPSHOT_GET,
            encode_channel(int(access_view)),
        )
        return decode_component_snapshot(message.body)

    # 读取全部DMA分类中断的Raw、Mask和Status快照。
    # 等待一次快照响应；目标拒绝、协议错误或超时立即失败。
    def interrupt_snapshot_get(self) -> DmaInterruptSnapshot:

        message, _ = self._request(DmaCommand.INTERRUPT_SNAPSHOT_GET)
        return decode_interrupt_snapshot(message.body)

    # 读取指定Channel的地址、Control和Config寄存器语义快照。
    # 等待一次快照响应；目标拒绝、协议错误或超时立即失败。
    def channel_snapshot_get(self, channel: int) -> DmaChannelSnapshot:

        message, _ = self._request(
            DmaCommand.CHANNEL_SNAPSHOT_GET,
            encode_channel(channel),
        )
        return decode_channel_snapshot(message.body)

    # 按Resource Handle和Offset初始化一个LLI Descriptor；不启动Channel。
    # 等待一次初始化响应；非法参数、目标拒绝或超时立即失败。
    def lli_descriptor_init(
        self,
        descriptor_handle: int,
        config: DmaConfig,
        *,
        is_last: bool,
        descriptor_offset: int = 0,
    ) -> None:

        normalized_handle = normalize_descriptor_handle(descriptor_handle)
        validate_descriptor_offset(descriptor_offset)
        body = encode_config(config) + encode_lli_descriptor_location(
            normalized_handle,
            descriptor_offset,
            is_last,
        )
        self._request(DmaCommand.LLI_DESCRIPTOR_INIT, body)

    # 按稳定Descriptor地址初始化一个LLI节点；不绑定具体内存区域。
    # 等待一次初始化响应；非法参数、目标拒绝或超时立即失败。
    def lli_descriptor_init_v2(
        self,
        descriptor_address: int,
        config: DmaConfig,
        *,
        is_last: bool,
    ) -> None:

        body = encode_config(config) + encode_lli_descriptor_location_v2(
            descriptor_address,
            is_last,
        )
        self._request(DmaCommand.LLI_DESCRIPTOR_INIT_V2, body)

    # 使能指定Channel和事件集合的分类中断Mask。
    # 等待本次响应；非法事件、目标拒绝或超时立即失败。
    def interrupt_mask_enable(self, channel: int, events: DmaIrqEvent) -> None:

        self._request(
            DmaCommand.INTERRUPT_MASK_ENABLE,
            encode_interrupt_control(channel, events),
        )

    # 关闭指定Channel和事件集合的分类中断Mask。
    # 等待本次响应；非法事件、目标拒绝或超时立即失败。
    def interrupt_mask_disable(self, channel: int, events: DmaIrqEvent) -> None:

        self._request(
            DmaCommand.INTERRUPT_MASK_DISABLE,
            encode_interrupt_control(channel, events),
        )

    # 清除指定Channel和事件集合的Pending位；不改变Mask配置。
    # 等待本次响应；非法事件、目标拒绝或超时立即失败。
    def interrupt_pending_clear(self, channel: int, events: DmaIrqEvent) -> None:

        self._request(
            DmaCommand.INTERRUPT_PENDING_CLEAR,
            encode_interrupt_control(channel, events),
        )

    # 读取指定Channel当前Free、FIFO和中断事件状态。
    # 等待一次状态响应；目标拒绝、协议错误或超时立即失败。
    def channel_status(
        self,
        channel: int,
        *,
        timeout_s: float | None = None,
    ) -> DmaChannelStatus:

        message, _ = self._request(
            DmaCommand.CHANNEL_STATUS_GET,
            encode_channel(channel),
            timeout_s=timeout_s,
        )
        return decode_channel_status(message.body)

    # 原子采样 DWT 并启动已配置 Channel；仅等待本次响应，失败按平台异常上抛。
    def start_timed(self, channel: int) -> None:

        self._request(DmaCommand.CHANNEL_START_TIMED, encode_channel(channel))

    # 读取 DMA Start-to-IRQ 计时快照；仅等待本次响应，失败按平台异常上抛。
    def timing_snapshot_get(
        self,
        *,
        timeout_s: float | None = None,
    ) -> DmaTimingSnapshot:

        message, _ = self._request(
            DmaCommand.TIMING_SNAPSHOT_GET,
            timeout_s=timeout_s,
        )
        return decode_timing_snapshot(message.body)

    # 等待目标侧 DMA IRQ 计时完成，全部查询共享一个 OperationDeadline。
    def wait_timing_complete(
        self,
        channel: int,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> DmaTimingSnapshot:

        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label=f"DMA channel {channel} timing wait",
        )
        while True:
            snapshot = self.timing_snapshot_get(timeout_s=deadline.remaining_s())
            if snapshot.complete:
                if snapshot.channel != channel:
                    raise RuntimeError(
                        f"DMA timing completed for channel {snapshot.channel}, expected {channel}"
                    )
                return snapshot
            deadline.sleep(poll_interval_s)

    # 等待单个 DMA Channel 进入 Free；ERROR 或 Deadline 超时作为操作失败上抛。
    #
    # 查询顺序与历史 Case Helper 保持一致：每轮先读取 CHANNEL_STATUS，再判断
    # ERROR/Free，未完成时等待固定轮询间隔；本方法不执行 Stop/Deconfigure。
    def wait_channel_free(
        self,
        channel: int,
        *,
        timeout_s: float = 1.0,
        poll_interval_s: float = 0.001,
    ) -> DmaChannelStatus:

        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label=f"DMA channel {channel} free wait",
        )
        while True:
            status = self.channel_status(channel, timeout_s=deadline.remaining_s())
            if status.interrupt_events & DmaIrqEvent.ERROR:
                raise RuntimeError(f"DMA channel {channel} terminated with ERROR")
            if status.is_free:
                return status
            deadline.sleep(poll_interval_s)

    # 等待一组 DMA Channel 变为 Free，并保留 Full-Duplex Case 的既有 Deadline 语义。
    #
    # 首次立即读取全部 Channel；任一 Channel 报 ERROR 时失败。全部查询共享同一个
    # OperationDeadline，耗尽时抛出 RequestTimeout；本方法不执行 Cleanup。
    def wait_channels_free(
        self,
        channels: tuple[int, ...],
        *,
        timeout_s: float = 5.0,
        poll_interval_s: float = 0.001,
    ) -> dict[int, DmaChannelStatus]:

        if not channels:
            raise ValueError("DMA channel wait set must not be empty")
        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label="DMA channels free wait",
        )
        latest = {
            channel: self.channel_status(channel, timeout_s=deadline.remaining_s())
            for channel in channels
        }
        while True:
            failed = {
                channel: status
                for channel, status in latest.items()
                if status.interrupt_events & DmaIrqEvent.ERROR
            }
            if failed:
                raise RuntimeError(
                    "DMA channel error: "
                    + repr(
                        {
                            channel: int(status.interrupt_events)
                            for channel, status in failed.items()
                        }
                    )
                )
            if all(status.is_free for status in latest.values()):
                return latest
            deadline.sleep(poll_interval_s)
            latest = {
                channel: self.channel_status(channel, timeout_s=deadline.remaining_s())
                for channel in channels
            }

    # 为一个Channel启用独立IRQ路由，返回Firmware实际建立的路由数量。
    # 等待一次配置响应；非法参数、目标拒绝或超时立即失败。
    def irq_enable(self, channel: int, events: DmaIrqEvent, priority: int) -> int:

        message, _ = self._request(
            DmaCommand.IRQ_ENABLE,
            encode_irq_enable(channel, events, priority),
        )
        return decode_irq_enable_response(message.body, events, combined=False)

    # 为一个Channel启用Combined IRQ路由，返回Firmware实际建立的路由数量。
    # 等待一次配置响应；非法参数、目标拒绝或超时立即失败。
    def irq_enable_combined(
        self,
        channel: int,
        events: DmaIrqEvent,
        priority: int,
    ) -> int:

        message, _ = self._request(
            DmaCommand.IRQ_COMBINED_ENABLE,
            encode_irq_enable(channel, events, priority),
        )
        return decode_irq_enable_response(message.body, events, combined=True)

    # 关闭当前DMA实例中指定事件集合的IRQ路由；不清除已锁存结果或其他事件配置。
    # 等待本次响应；非法事件、目标拒绝或超时立即失败。
    def irq_disable(self, events: DmaIrqEvent) -> None:

        self._request(DmaCommand.IRQ_DISABLE, encode_irq_events(events))

    # 读取Firmware锁存的DMA IRQ事件、计数和异常统计。
    def irq_result_get(self, *, timeout_s: float | None = None) -> DmaIrqResult:

        message, _ = self._request(DmaCommand.IRQ_RESULT_GET, timeout_s=timeout_s)
        return decode_irq_result(message.body)

    # 等待并轮询本 DMA IRQ 结果，达到最小计数或 Deadline 超时时返回最后事实。
    #
    # 为保持已验证 Case 的运行语义，首次立即读取，随后按固定间隔继续查询；
    # 超时本身不在 Driver 生成最终失败结论，Event 与最小计数断言仍由 Case 负责。
    def wait_irq(
        self,
        *,
        timeout_s: float = 2.0,
        minimum_count: int = 1,
        poll_interval_s: float = 0.001,
    ) -> DmaIrqResult:

        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label="DMA IRQ wait",
        )
        latest = self.irq_result_get(timeout_s=deadline.remaining_s())
        while latest.irq_count < minimum_count:
            if deadline.expired:
                return latest
            deadline.sleep(poll_interval_s)
            if deadline.expired:
                return latest
            latest = self.irq_result_get(timeout_s=deadline.remaining_s())
        return latest

    # 等待 DMA IRQ Count 达到最小值；全部查询共享同一个 OperationDeadline。
    #
    # 该严格入口保持历史 ``wait_for_irq_count`` Helper 的失败语义；只查询本 DMA
    # IRQ_RESULT，不判断具体 Event 是否满足整个 Test Case 的通过条件。
    def wait_irq_count(
        self,
        *,
        minimum_count: int,
        timeout_s: float = 1.0,
        poll_interval_s: float = 0.001,
    ) -> DmaIrqResult:

        if minimum_count <= 0:
            raise ValueError("DMA minimum IRQ count must be positive")
        deadline = OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label="DMA IRQ count wait",
        )
        while True:
            result = self.irq_result_get(timeout_s=deadline.remaining_s())
            if result.irq_count >= minimum_count:
                return result
            deadline.sleep(poll_interval_s)

    # 清空Firmware维护的DMA IRQ结果；不改变硬件IRQ路由配置。
    # 等待本次响应；目标拒绝、协议错误或超时立即失败。
    def irq_result_clear(self) -> None:

        self._request(DmaCommand.IRQ_RESULT_CLEAR)

    # 设置或撤销指定Channel端点的一类Software Handshake Request。
    # 等待本次响应；非法参数、目标拒绝或超时立即失败。
    def software_handshake_request_set(
        self,
        channel: int,
        target: DmaHandshakeTarget,
        request_kind: DmaSoftwareRequestKind,
        active: bool,
    ) -> None:

        self._request(
            DmaCommand.SOFTWARE_HANDSHAKE_REQUEST_SET,
            encode_software_handshake_request(
                channel,
                target,
                request_kind,
                active,
            ),
        )

    # 在单 IP Scope 退出时执行全部 Cleanup；主体与清理同时失败时保留第一错误并合并全部 Cleanup 错误。
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

    # 向当前 DMA Service Instance 发送一次请求；仅只读或明确幂等命令允许安全重试，显式 timeout 原样传给 TargetClient。
    def _request(
        self,
        command: int,
        body: bytes = b"",
        *,
        timeout_s: float | None = None,
    ) -> tuple[ServiceMessage, Frame]:
        arguments: dict[str, object] = {
            "instance_id": self.instance_id,
            "body": body,
            "retry_safe": DmaCommand(command) in self._RETRY_SAFE_COMMANDS,
        }
        if timeout_s is not None:
            arguments["timeout_s"] = timeout_s
        return self._target.request(
            DMA_SERVICE_ID,
            command,
            **arguments,
        )
