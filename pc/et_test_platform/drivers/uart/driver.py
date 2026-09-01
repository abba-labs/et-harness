# UART PC Driver Package 的driver层。
#
# 职责：提供 UART 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager

from ...clients.target import TargetClient
from ...communication.protocols.et_message import Status
from ...core.cleanup import OperationCleanupError, raise_with_cleanup, run_cleanup
from ...core.deadline import OperationDeadline
from ...core.errors import OperationBusy, ProtocolError, RequestTimeout, TargetRejected
from .codec import (
    ADDRESS,
    BUSY_DETECT_RESULT,
    CAPABILITIES,
    FIFO_ACCESS_CONFIG,
    FIFO_TX_VALUE,
    SHADOW_FIFO_CONFIG,
    TRANSFERRED,
    UART_IRQ_STATE,
    UART_MODEM_STATUS,
    UART_SNAPSHOT,
    UART_STATUS,
    decode_address,
    decode_busy_detect,
    decode_capabilities,
    decode_capture,
    decode_fifo_access,
    decode_fifo_tx,
    decode_irq_state,
    decode_modem_status,
    decode_nine_bit_read,
    decode_shadow_fifo,
    decode_snapshot,
    decode_status,
    decode_transferred,
    encode_bool,
    encode_count,
    encode_endpoint,
    encode_fifo_access,
    encode_fifo_config,
    encode_fifo_rx,
    encode_flow_control,
    encode_irq_config,
    encode_line_config,
    encode_modem_control,
    encode_nine_bit_config,
    encode_nine_bit_write,
    encode_poll_budget,
    encode_read_request,
    encode_shadow_fifo,
    require_response_size,
)
from .contract import (
    DEFAULT_IO_POLL_INTERVAL_S,
    DEFAULT_IO_TIMEOUT_S,
    MAX_CAPTURE_BYTES,
    MAX_NINE_BIT_WORDS,
    MAX_PARTIAL_WRITE_BYTES,
    MAX_READ_CHUNK_BYTES,
    MAX_WRITE_CHUNK_BYTES,
    UART_SERVICE_ID,
    UartCommand,
)
from .models import (
    UartBusyDetectResult,
    UartCapabilities,
    UartCapture,
    UartDmaEndpoint,
    UartDmaMode,
    UartIrqSource,
    UartIrqState,
    UartModemStatus,
    UartParity,
    UartShadowFifoState,
    UartSnapshot,
    UartStatus,
    UartStopBits,
)
from .validation import (
    bool_byte,
    enum_value,
    uint,
    validate_dma_mode,
    validate_fifo_thresholds,
    validate_polling,
)


# 一个 UART Service Instance 的稳定 PC 客户端。
class UartDriver:
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

    # 读取 capabilities get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def capabilities_get(self) -> UartCapabilities:

        body = self._request(
            UartCommand.CAPABILITIES_GET,
            response_size=CAPABILITIES.size,
        )
        return decode_capabilities(body)

    # 读取 dma endpoint get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def dma_endpoint_get(self, endpoint: UartDmaEndpoint) -> int:

        value = enum_value(endpoint, UartDmaEndpoint, "DMA endpoint")
        body = self._request(
            UartCommand.DMA_ENDPOINT_GET,
            encode_endpoint(value),
            response_size=ADDRESS.size,
        )
        return decode_address(body)

    # 发送 dma enable set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def dma_enable_set(self, enabled: bool) -> None:

        self._request(
            UartCommand.DMA_ENABLE_SET,
            encode_endpoint(bool_byte(enabled, "DMA enabled")),
        )

    # 发送 initialize 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def initialize(
        self,
        *,
        baudrate: int,
        data_bits: int = 8,
        stop_bits: int | float | UartStopBits = UartStopBits.ONE,
        parity: int | UartParity = UartParity.NONE,
    ) -> None:

        self._request(
            UartCommand.INITIALIZE,
            encode_line_config(
                baudrate=baudrate,
                data_bits=data_bits,
                stop_bits=stop_bits,
                parity=parity,
            ),
        )

    # 发送 configure extended 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def configure_extended(
        self,
        *,
        baudrate: int,
        data_bits: int = 8,
        stop_bits: UartStopBits = UartStopBits.ONE,
        parity: UartParity = UartParity.NONE,
    ) -> None:

        self.initialize(
            baudrate=baudrate,
            data_bits=data_bits,
            stop_bits=stop_bits,
            parity=parity,
        )

    # 发送 deinitialize 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def deinitialize(self) -> None:

        self._request(UartCommand.DEINITIALIZE)

    # 在作用域进入时初始化本 UART，退出时反初始化；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def initialized_mode(
        self,
        *,
        baudrate: int,
        data_bits: int = 8,
        stop_bits: int | float | UartStopBits = UartStopBits.ONE,
        parity: int | UartParity = UartParity.NONE,
    ) -> Iterator[None]:

        self.initialize(
            baudrate=baudrate,
            data_bits=data_bits,
            stop_bits=stop_bits,
            parity=parity,
        )
        with self._cleanup_mode(
            "UART initialized mode",
            (("UART deinitialize", self.deinitialize),),
        ):
            yield

    # 保持进入时状态不变并在退出时反初始化本 UART；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def deinitialize_on_exit(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART deinitialize-on-exit mode",
            (("UART deinitialize", self.deinitialize),),
        ):
            yield

    # 执行 write 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def write(
        self,
        data: bytes,
        *,
        max_polls: int = 1_000_000,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> int:

        payload = bytes(data)
        if not payload:
            raise ValueError("UART write data must not be empty")
        poll_cap, timeout, interval = validate_polling(
            max_polls=max_polls,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART write")
        return self._write_with_deadline(payload, poll_cap, interval, deadline)

    # 执行 write partial 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def write_partial(self, data: bytes) -> int:

        payload = bytes(data)
        if not payload:
            raise ValueError("UART partial write data must not be empty")
        if len(payload) > MAX_PARTIAL_WRITE_BYTES:
            raise ValueError("UART partial write exceeds ET service body capacity")
        body = self._request(
            UartCommand.WRITE_PARTIAL,
            payload,
            response_size=TRANSFERRED.size,
        )
        return decode_transferred(body, len(payload), "partial write")

    # 执行 read exact 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def read_exact(
        self,
        length: int,
        *,
        max_polls: int = 1_000_000,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> bytes:

        uint(length, 16, "read length", nonzero=True)
        poll_cap, timeout, interval = validate_polling(
            max_polls=max_polls,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART read")
        return self._read_with_deadline(length, poll_cap, interval, deadline)

    # 发送 capture start 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def capture_start(self, length: int) -> None:

        self._validate_capture_length(length)
        self._request(UartCommand.CAPTURE_START, encode_count(length))

    # 读取 capture get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def capture_get(self, *, timeout_s: float | None = None) -> UartCapture:

        return decode_capture(
            self._request(
                UartCommand.CAPTURE_GET,
                response_size=None,
                timeout_s=timeout_s,
            )
        )

    # 轮询本 UART Capture，完成时返回数据事实，异常/超时保持既有 Helper 语义。
    #
    # 该方法只执行 UART 的 CAPTURE_GET/IRQ_STATE_GET 查询，不启动 Capture、
    # 不执行跨 IP 动作，也不替 Case 判断业务 Payload 是否符合预期。
    def capture_wait(
        self,
        expected: int,
        *,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.001,
    ) -> UartCapture:

        deadline = self._deadline(timeout_s, "UART capture wait")
        latest = None
        while True:
            latest = self.capture_get(timeout_s=deadline.remaining_s())
            if not latest.active and latest.received != expected:
                raise ProtocolError(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "reason": "capture_aborted",
                            "expected": expected,
                            "received": latest.received,
                        },
                        sort_keys=True,
                    )
                )
            if latest.complete:
                if latest.received != expected or len(latest.data) != expected:
                    raise ProtocolError(
                        json.dumps(
                            {
                                "status": "FAIL",
                                "reason": "capture_length_or_data_inconsistent",
                                "expected": expected,
                                "received": latest.received,
                            },
                            sort_keys=True,
                        )
                    )
                irq_state = self.irq_state_get(timeout_s=deadline.remaining_s())
                if irq_state.fault_count != 0:
                    raise ProtocolError(
                        json.dumps(
                            {
                                "status": "FAIL",
                                "reason": "capture_irq_cleanup_fault",
                                "fault_count": irq_state.fault_count,
                            },
                            sort_keys=True,
                        )
                    )
                return latest
            try:
                deadline.sleep(poll_interval_s)
            except RequestTimeout as error:
                raise ProtocolError(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "reason": "capture_timeout",
                            "expected": expected,
                            "received": getattr(latest, "received", 0),
                        },
                        sort_keys=True,
                    )
                ) from error

    # 发送 capture cancel 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def capture_cancel(self) -> None:

        self._request(UartCommand.CAPTURE_CANCEL)

    # 管理本 UART 的 Capture 退出清理但不负责启动；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def capture_mode(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART capture mode",
            (("UART capture cancel", self.capture_cancel),),
        ):
            yield

    # 使用一个总 Deadline 完成 Capture、Write、Observe 和 Cleanup。
    def exchange(
        self,
        data: bytes,
        *,
        max_polls: int = 1_000_000,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> bytes:

        payload = bytes(data)
        if not payload:
            raise ValueError("UART exchange data must not be empty")
        self._validate_capture_length(len(payload))
        poll_cap, timeout, interval = validate_polling(
            max_polls=max_polls,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART exchange")
        try:
            baseline_irq = decode_irq_state(
                self._request(
                    UartCommand.IRQ_STATE_GET,
                    response_size=UART_IRQ_STATE.size,
                    timeout_s=deadline.remaining_s(),
                )
            )
            self._request(
                UartCommand.CAPTURE_START,
                encode_count(len(payload)),
                timeout_s=deadline.remaining_s(),
            )
            self._write_with_deadline(payload, poll_cap, interval, deadline)
            attempts = 0
            while attempts < poll_cap:
                capture = decode_capture(
                    self._request(
                        UartCommand.CAPTURE_GET,
                        response_size=None,
                        timeout_s=deadline.remaining_s(),
                    )
                )
                if capture.complete:
                    final_irq = decode_irq_state(
                        self._request(
                            UartCommand.IRQ_STATE_GET,
                            response_size=UART_IRQ_STATE.size,
                            timeout_s=deadline.remaining_s(),
                        )
                    )
                    if final_irq.fault_count > baseline_irq.fault_count:
                        raise ProtocolError(
                            "UART capture_irq_cleanup_fault: "
                            f"{baseline_irq.fault_count}->{final_irq.fault_count}"
                        )
                    return capture.data
                if not capture.active:
                    raise ProtocolError("UART exchange capture aborted")
                attempts += 1
                deadline.sleep(interval)
            raise TimeoutError("UART exchange reached the compatibility poll cap")
        except BaseException as primary_error:
            cleanup_failures = run_cleanup((("UART capture cancel", self.capture_cancel),))
            raise_with_cleanup(primary_error, cleanup_failures)

    # 开启本 UART 内部回环，并在退出时可靠取消 Capture 和关闭回环。
    #
    # 该作用域只管理本 UART 的回环相关状态，不初始化外设、不形成 Case 断言，
    # 主体错误与全部清理错误会同时保留。
    @contextmanager
    def internal_loopback_mode(self) -> Iterator[None]:

        self.loopback_set(True)
        actions = (
            ("UART capture cancel", self.capture_cancel),
            ("UART loopback disable", lambda: self.loopback_set(False)),
        )
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
                RuntimeError("UART internal loopback completed but cleanup did not"),
                cleanup_failures,
            )

    # 读取 snapshot get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def snapshot_get(self) -> UartSnapshot:

        body = self._request(
            UartCommand.SNAPSHOT_GET,
            response_size=UART_SNAPSHOT.size,
        )
        return decode_snapshot(body)

    # 发送 software reset 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def software_reset(self) -> None:

        self._request(UartCommand.SOFTWARE_RESET)

    # 发送 loopback set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def loopback_set(self, enabled: bool) -> None:

        self._request(
            UartCommand.LOOPBACK_SET,
            encode_bool(enabled, "loopback enabled"),
        )

    # 在作用域进入时开启本 UART 内部回环，退出时关闭；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def loopback_mode(self) -> Iterator[None]:

        self.loopback_set(True)
        with self._cleanup_mode(
            "UART loopback mode",
            (("UART loopback disable", lambda: self.loopback_set(False)),),
        ):
            yield

    # 保持进入时状态不变并在退出时关闭内部回环；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def loopback_disable_on_exit(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART loopback-disable-on-exit mode",
            (("UART loopback disable", lambda: self.loopback_set(False)),),
        ):
            yield

    # 发送 fifo config 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def fifo_config(
        self,
        tx_threshold: int = 0,
        rx_threshold: int = 1,
        *,
        enabled: bool = True,
        dma_mode: UartDmaMode = UartDmaMode.DISABLED,
    ) -> None:

        validate_fifo_thresholds(tx_threshold, rx_threshold)
        self._request(
            UartCommand.FIFO_CONFIG,
            encode_fifo_config(
                enabled,
                tx_threshold,
                rx_threshold,
                validate_dma_mode(dma_mode),
            ),
        )

    # 读取 status get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def status_get(self) -> UartStatus:

        body = self._request(
            UartCommand.STATUS_GET,
            response_size=UART_STATUS.size,
        )
        return decode_status(body)

    # 发送 irq config 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def irq_config(
        self,
        mask: UartIrqSource,
        enabled: bool,
        priority: int,
    ) -> None:

        if isinstance(mask, bool) or not isinstance(mask, (int, UartIrqSource)):
            raise ValueError("UART IRQ mask must be an integer mask")
        mask_value = uint(int(mask), 32, "IRQ mask")
        allowed_mask = int(
            UartIrqSource.RX_READY
            | UartIrqSource.TX_READY
            | UartIrqSource.LINE_ERROR
            | UartIrqSource.MODEM_STATUS
            | UartIrqSource.CHARACTER_TIMEOUT
            | UartIrqSource.BUSY
            | UartIrqSource.NINE_BIT_ADDRESS
        )
        if mask_value & ~allowed_mask:
            raise ValueError("UART IRQ mask contains an unknown source")
        priority_value = uint(priority, 8, "IRQ priority")
        self._request(
            UartCommand.IRQ_CONFIG,
            encode_irq_config(mask_value, enabled, priority_value),
        )

    # 在作用域进入时使能指定 UART 中断掩码，退出时关闭同一掩码；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def irq_mode(self, mask: UartIrqSource, priority: int) -> Iterator[None]:

        self.irq_config(mask, True, priority)
        with self._cleanup_mode(
            "UART IRQ mode",
            (("UART IRQ disable", lambda: self.irq_config(mask, False, priority)),),
        ):
            yield

    # 读取 irq state get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def irq_state_get(self, *, timeout_s: float | None = None) -> UartIrqState:

        body = self._request(
            UartCommand.IRQ_STATE_GET,
            response_size=UART_IRQ_STATE.size,
            timeout_s=timeout_s,
        )
        return decode_irq_state(body)

    # 在单一总Deadline内等待指定UART IRQ来源产生新事件，并返回首次匹配状态。
    def wait_irq_event(
        self,
        source: UartIrqSource,
        baseline_event_count: int,
        *,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> UartIrqState:

        source_value = enum_value(source, UartIrqSource, "IRQ source")
        if source_value == 0:
            raise ValueError("UART IRQ source must not be empty")
        baseline = uint(baseline_event_count, 32, "baseline event count")
        _, timeout, interval = validate_polling(
            max_polls=0xFFFFFFFF,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART IRQ event wait")
        while True:
            state = self.irq_state_get(timeout_s=deadline.remaining_s())
            observed_mask = state.pending_mask | state.active_mask
            if state.event_count > baseline and observed_mask & source_value:
                return state
            deadline.sleep(interval)

    # 发送 break set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def break_set(self, enabled: bool) -> None:

        self._request(
            UartCommand.BREAK_SET,
            encode_bool(enabled, "break enabled"),
        )

    # 保持进入时状态不变并在退出时释放 UART Break；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def break_release_on_exit(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART break-release-on-exit mode",
            (("UART break release", lambda: self.break_set(False)),),
        ):
            yield

    # 发送 halt set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def halt_set(self, halted: bool) -> None:

        self._request(
            UartCommand.HALT_SET,
            encode_bool(halted, "halted"),
        )

    # 在作用域进入时暂停 UART 发送，退出时恢复；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def halt_mode(self) -> Iterator[None]:

        self.halt_set(True)
        with self._cleanup_mode(
            "UART halt mode",
            (("UART halt release", lambda: self.halt_set(False)),),
        ):
            yield

    # 发送 dma mode set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def dma_mode_set(self, mode: UartDmaMode) -> None:

        self._request(
            UartCommand.DMA_MODE_SET,
            encode_bool(validate_dma_mode(mode), "DMA mode"),
        )

    # 发送 nine bit config 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def nine_bit_config(
        self,
        enabled: bool,
        address_match: bool = False,
        address: int = 0,
    ) -> None:

        self._request(
            UartCommand.NINE_BIT_CONFIG,
            encode_nine_bit_config(
                enabled,
                address_match,
                uint(address, 8, "9-bit address"),
            ),
        )

    # 在作用域进入时开启 UART 9-bit 模式，退出时关闭；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def nine_bit_mode(
        self,
        *,
        address_match: bool = False,
        address: int = 0,
    ) -> Iterator[None]:

        self.nine_bit_config(True, address_match, address)
        with self._cleanup_mode(
            "UART 9-bit mode",
            (("UART 9-bit disable", lambda: self.nine_bit_config(False)),),
        ):
            yield

    # 执行 write 9bit 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def write_9bit(
        self,
        values: Iterable[int],
        *,
        max_polls: int = 1_000_000,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> int:

        words = tuple(values)
        if not words or len(words) > MAX_NINE_BIT_WORDS:
            raise ValueError("UART 9-bit write length exceeds service capacity")
        checked = tuple(uint(value, 9, "9-bit value") for value in words)
        poll_cap, timeout, interval = validate_polling(
            max_polls=max_polls,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART 9-bit write")
        transferred = 0
        attempts = 0
        while transferred < len(checked) and attempts < poll_cap:
            remaining = checked[transferred:]
            body = self._request(
                UartCommand.WRITE_9BIT,
                encode_nine_bit_write(remaining, 1),
                response_size=TRANSFERRED.size,
                timeout_s=deadline.remaining_s(),
            )
            count = decode_transferred(
                body,
                len(remaining),
                "9-bit write",
            )
            transferred += count
            if transferred == len(checked):
                return transferred
            attempts += 1
            if count == 0:
                deadline.sleep(interval)
        raise TimeoutError(f"UART wrote {transferred}/{len(checked)} 9-bit words before poll cap")

    # 执行 read 9bit 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def read_9bit(
        self,
        length: int,
        *,
        max_polls: int = 1_000_000,
        timeout_s: float = DEFAULT_IO_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_IO_POLL_INTERVAL_S,
    ) -> tuple[int, ...]:

        uint(length, 16, "9-bit read length", nonzero=True)
        if length > MAX_NINE_BIT_WORDS:
            raise ValueError("UART 9-bit read length exceeds service capacity")
        poll_cap, timeout, interval = validate_polling(
            max_polls=max_polls,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        deadline = self._deadline(timeout, "UART 9-bit read")
        values: list[int] = []
        attempts = 0
        while len(values) < length and attempts < poll_cap:
            remaining = length - len(values)
            body = self._request(
                UartCommand.READ_9BIT,
                encode_read_request(remaining, 1),
                response_size=None,
                timeout_s=deadline.remaining_s(),
            )
            chunk = decode_nine_bit_read(body, remaining)
            values.extend(chunk)
            if len(values) == length:
                return tuple(values)
            attempts += 1
            if not chunk:
                deadline.sleep(interval)
        raise TimeoutError(f"UART read {len(values)}/{length} 9-bit words before poll cap")

    # 发送 flow control set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def flow_control_set(
        self,
        enabled: bool,
        rts_polarity: int = 0,
        cts_polarity: int = 0,
    ) -> None:

        self._request(
            UartCommand.FLOW_CONTROL_SET,
            encode_flow_control(
                enabled,
                uint(rts_polarity, 1, "RTS polarity"),
                uint(cts_polarity, 1, "CTS polarity"),
            ),
        )

    # 保持进入时状态不变并在退出时关闭 UART 自动流控；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def flow_control_disable_on_exit(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART flow-control-disable-on-exit mode",
            (("UART flow-control disable", lambda: self.flow_control_set(False)),),
        ):
            yield

    # 发送 modem control set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def modem_control_set(self, rts: bool, dtr: bool) -> None:

        self._request(
            UartCommand.MODEM_CONTROL_SET,
            encode_modem_control(rts, dtr),
        )

    # 保持进入时状态不变并在退出时释放 UART Modem 输出；清理命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def modem_outputs_release_on_exit(self) -> Iterator[None]:

        with self._cleanup_mode(
            "UART modem-outputs-release-on-exit mode",
            (("UART modem outputs release", lambda: self.modem_control_set(False, False)),),
        ):
            yield

    # 读取 modem status get 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def modem_status_get(self) -> UartModemStatus:

        body = self._request(
            UartCommand.MODEM_STATUS_GET,
            response_size=UART_MODEM_STATUS.size,
        )
        return decode_modem_status(body)

    # 发送 busy detect trigger 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def busy_detect_trigger(self) -> UartBusyDetectResult:

        try:
            body = self._request(
                UartCommand.BUSY_DETECT_TRIGGER,
                response_size=BUSY_DETECT_RESULT.size,
            )
        except TargetRejected as error:
            if error.status == int(Status.BUSY):
                raise OperationBusy("UART busy-detect condition was not formed in time") from error
            raise
        return decode_busy_detect(body)

    # 发送 shadow fifo config 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def shadow_fifo_config(
        self,
        enabled: bool,
        tx_threshold: int,
        rx_threshold: int,
    ) -> UartShadowFifoState:

        validate_fifo_thresholds(tx_threshold, rx_threshold)
        body = self._request(
            UartCommand.SHADOW_FIFO_CONFIG,
            encode_shadow_fifo(enabled, tx_threshold, rx_threshold),
            response_size=SHADOW_FIFO_CONFIG.size,
        )
        return decode_shadow_fifo(body)

    # 发送 test fifo access set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def test_fifo_access_set(self, enabled: bool) -> bool:

        body = self._request(
            UartCommand.FIFO_ACCESS_SET,
            encode_fifo_access(enabled),
            response_size=FIFO_ACCESS_CONFIG.size,
        )
        return decode_fifo_access(body)

    # 在作用域进入时开启 UART Direct FIFO 访问，退出时关闭；各命令只等待本次 Target 响应，拒绝、协议错误、超时或清理失败按平台异常上抛。
    @contextmanager
    def fifo_access_mode(self) -> Iterator[bool]:

        enabled = self.test_fifo_access_set(True)
        with self._cleanup_mode(
            "UART direct-FIFO-access mode",
            (("UART FIFO access disable", lambda: self.test_fifo_access_set(False)),),
        ):
            yield enabled

    # 发送 test fifo tx read 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def test_fifo_tx_read(self) -> int:

        body = self._request(
            UartCommand.FIFO_TX_READ,
            response_size=FIFO_TX_VALUE.size,
        )
        return decode_fifo_tx(body)

    # 执行 test fifo rx write 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def test_fifo_rx_write(
        self,
        value: int,
        parity_error: bool = False,
        framing_error: bool = False,
    ) -> None:

        self._request(
            UartCommand.FIFO_RX_WRITE,
            encode_fifo_rx(
                uint(value, 8, "FIFO RX value"),
                parity_error,
                framing_error,
            ),
        )

    # Preserve the primary failure while completing one-IP cleanup.
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

    def _write_with_deadline(
        self,
        payload: bytes,
        max_polls: int,
        poll_interval_s: float,
        deadline: OperationDeadline,
    ) -> int:
        transferred = 0
        attempts = 0
        while transferred < len(payload) and attempts < max_polls:
            chunk = payload[transferred : transferred + MAX_WRITE_CHUNK_BYTES]
            body = self._request(
                UartCommand.WRITE,
                encode_poll_budget(1) + chunk,
                response_size=TRANSFERRED.size,
                timeout_s=deadline.remaining_s(),
            )
            count = decode_transferred(body, len(chunk), "write")
            transferred += count
            if transferred == len(payload):
                return transferred
            attempts += 1
            if count == 0:
                deadline.sleep(poll_interval_s)
        raise TimeoutError(f"UART wrote {transferred}/{len(payload)} bytes before poll cap")

    def _read_with_deadline(
        self,
        length: int,
        max_polls: int,
        poll_interval_s: float,
        deadline: OperationDeadline,
    ) -> bytes:
        received = bytearray()
        attempts = 0
        while len(received) < length and attempts < max_polls:
            remaining = length - len(received)
            chunk_length = min(remaining, MAX_READ_CHUNK_BYTES)
            body = self._request(
                UartCommand.READ_EXACT,
                encode_read_request(chunk_length, 1),
                response_size=None,
                timeout_s=deadline.remaining_s(),
            )
            if len(body) > chunk_length:
                raise ProtocolError("UART read response exceeds request")
            received.extend(body)
            if len(received) == length:
                return bytes(received)
            attempts += 1
            if not body:
                deadline.sleep(poll_interval_s)
        raise TimeoutError(f"UART read {len(received)}/{length} bytes before poll cap")

    def _deadline(self, timeout_s: float, label: str) -> OperationDeadline:
        return OperationDeadline.start(
            timeout_s,
            clock=self._clock,
            sleep=self._sleep,
            label=label,
        )

    @staticmethod
    def _validate_capture_length(length: int) -> None:
        if not 0 < length <= MAX_CAPTURE_BYTES:
            raise ValueError(f"UART capture length must be between 1 and {MAX_CAPTURE_BYTES}")

    def _request(
        self,
        command: UartCommand,
        body: bytes = b"",
        *,
        response_size: int | None = 0,
        timeout_s: float | None = None,
    ) -> bytes:
        arguments: dict[str, object] = {
            "instance_id": self.instance_id,
            "body": body,
        }
        if timeout_s is not None:
            arguments["timeout_s"] = timeout_s
        try:
            message, _ = self._target.request(
                UART_SERVICE_ID,
                command,
                **arguments,
            )
        except TypeError as error:
            if timeout_s is None or "unexpected keyword argument 'timeout_s'" not in str(error):
                raise
            # Compatibility for pre-deadline Target doubles/adapters. The
            # production TargetClient accepts timeout_s and keeps the strict
            # total-deadline behavior; only legacy request signatures fall
            # back to their historical default request timeout.
            arguments.pop("timeout_s", None)
            message, _ = self._target.request(
                UART_SERVICE_ID,
                command,
                **arguments,
            )
        return require_response_size(
            message.body,
            response_size,
            command.name,
        )
