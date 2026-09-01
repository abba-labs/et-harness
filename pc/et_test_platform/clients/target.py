# 芯片无关的同步 TargetClient 请求通道。
#
# 职责：负责 ET-Frame 请求/响应、Session、Sequence、有界重试和异步 Event 队列。
# 边界：不解释任何 IP Command 业务语义，不读取 Capability/Bench，也不做 Test Case 判断。
# 依赖：仅依赖通用 ET-Frame/ServiceMessage、ByteTransport、Deadline 与平台异常。

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable, Iterable
from types import TracebackType

from ..communication.protocols.et_frame import (
    Frame,
    FrameCodec,
    FrameDecoder,
    MessageType,
)
from ..communication.protocols.et_message import ServiceMessage, Status
from ..communication.transport import ByteTransport
from ..core.deadline import require_positive_seconds
from ..core.errors import ProtocolError, RequestTimeout, TargetRejected


# 封装 TargetClient 的稳定操作边界；只负责当前层业务动作，不承担跨 IP Test Case 编排或最终断言。
class TargetClient:
    _MAX_REQUEST_ATTEMPTS = 2
    _EVENT_QUEUE_CAPACITY = 32

    def __init__(
        self,
        transport: ByteTransport,
        *,
        request_timeout_s: float = 1.0,
        read_chunk_size: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._request_timeout_s = require_positive_seconds(
            request_timeout_s,
            "request_timeout_s",
        )
        if read_chunk_size <= 0:
            raise ValueError("read_chunk_size must be positive")
        self._transport = transport
        self._read_chunk_size = read_chunk_size
        self._clock = clock
        self._decoder = FrameDecoder()
        self._sequence = 0
        self._session_id = 0
        self._retry_count = 0
        self._events: deque[Frame] = deque(maxlen=self._EVENT_QUEUE_CAPACITY)
        self._event_overflow_count = 0
        self._opened = False

    # 返回当前底层 Transport 的稳定连接标识；只读访问，不触发设备 I/O 或新的协议请求。
    @property
    def identity(self) -> str:

        return self._transport.identity

    # 返回 Framework HELLO 已绑定的当前 Session ID；只读访问，不发送请求或改变会话状态。
    @property
    def session_id(self) -> int:

        return self._session_id

    # 返回当前进程累计执行的安全重试次数；只读访问，不触发新的重试或设备 I/O。
    @property
    def retry_count(self) -> int:

        return self._retry_count

    # 返回固定 Event 队列累计丢弃最老事件的次数；只读访问，用于暴露观测证据是否完整。
    @property
    def event_overflow_count(self) -> int:

        return self._event_overflow_count

    # 打开底层 Transport 并重置 Decoder/Session/Event 本地状态；不等待任何 Service 响应，Transport 失败以平台异常上抛。
    def open(self) -> None:

        if self._opened:
            return
        self._transport.open()
        self._decoder.reset()
        self._session_id = 0
        self._events.clear()
        self._event_overflow_count = 0
        self._opened = True

    # 关闭底层 Transport 并清除本地 Session/Event 状态；不发送 Firmware 命令，关闭失败由 Transport 异常直接上抛。
    def close(self) -> None:

        if not self._opened:
            return
        self._transport.close()
        self._opened = False
        self._session_id = 0
        self._events.clear()
        self._decoder.reset()

    # 绑定 Framework HELLO 返回的非零 Session ID；不发送设备请求，非法 ID 或会话冲突以协议异常失败。
    def bind_session(self, session_id: int) -> None:

        if not 0 < session_id <= 0xFFFFFFFF:
            raise ProtocolError("target session id must be a nonzero uint32")
        if session_id != self._session_id:
            self._events.clear()
            self._event_overflow_count = 0
        self._session_id = session_id

    # 在一个总 Deadline 内发送一次 ET-Frame Request 并等待匹配 Response；仅 retry_safe 命令允许复用同一帧重试，超时、协议错误或 Target 拒绝均以平台异常上抛。
    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        timeout_s: float | None = None,
        session_id: int | None = None,
        retry_safe: bool = False,
    ) -> tuple[ServiceMessage, Frame]:

        self._require_open()
        request_timeout = require_positive_seconds(
            self._request_timeout_s if timeout_s is None else timeout_s,
            "timeout_s",
        )
        request_session_id = self._resolve_session_id(session_id)
        sequence, encoded_request = self._encode_request(
            service_id,
            command_id,
            instance_id,
            request_session_id,
            body,
        )
        attempts = self._MAX_REQUEST_ATTEMPTS if retry_safe else 1
        total_deadline = self._clock() + request_timeout
        attempts_made = 0

        for attempt in range(attempts):
            attempt_deadline = self._allocate_attempt_deadline(
                total_deadline,
                attempts - attempt,
            )
            if attempt_deadline is None:
                break
            attempts_made += 1
            write_timeout = attempt_deadline - self._clock()
            if write_timeout <= 0:
                break
            self._transport.write(
                encoded_request,
                timeout_s=write_timeout,
            )
            response = self._read_attempt_response(
                attempt_deadline,
                sequence=sequence,
                session_id=request_session_id,
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
            )
            if response is not None:
                return response
            self._prepare_retry(attempt, attempts, total_deadline)

        raise RequestTimeout(
            f"service=0x{service_id:04x} command=0x{command_id:04x} "
            f"timed out after {attempts_made} attempts on "
            f"{self._transport.identity}"
        )

    # 返回队列中最早的异步 Event；只消费已观测事实，不等待设备，也不发送新的协议请求。
    def pop_event(self) -> Frame | None:

        return self._events.popleft() if self._events else None

    def _require_open(self) -> None:
        if not self._opened:
            raise RuntimeError("TargetClient is not open")

    def _resolve_session_id(self, session_id: int | None) -> int:
        resolved = self._session_id if session_id is None else session_id
        if not 0 <= resolved <= 0xFFFFFFFF:
            raise ValueError("session_id must fit uint32")
        return resolved

    def _encode_request(
        self,
        service_id: int,
        command_id: int,
        instance_id: int,
        session_id: int,
        body: bytes,
    ) -> tuple[int, bytes]:
        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        payload = ServiceMessage(
            service_id=service_id,
            command_id=command_id,
            instance_id=instance_id,
            status=Status.OK,
            body=body,
        ).encode()
        frame = Frame(
            message_type=MessageType.REQUEST,
            flags=0,
            sequence=self._sequence,
            session_id=session_id,
            payload=payload,
        )
        return self._sequence, FrameCodec.encode(frame)

    def _allocate_attempt_deadline(
        self,
        total_deadline: float,
        attempts_left: int,
    ) -> float | None:
        remaining_total = total_deadline - self._clock()
        if remaining_total <= 0:
            return None
        return self._clock() + remaining_total / attempts_left

    def _read_attempt_response(
        self,
        attempt_deadline: float,
        *,
        sequence: int,
        session_id: int,
        service_id: int,
        command_id: int,
        instance_id: int,
    ) -> tuple[ServiceMessage, Frame] | None:
        while True:
            remaining = attempt_deadline - self._clock()
            if remaining <= 0:
                return None
            chunk = self._transport.read(self._read_chunk_size, remaining)
            if not chunk:
                continue
            response = self._select_matching_response(
                self._decoder.feed(chunk),
                sequence=sequence,
                session_id=session_id,
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
            )
            if response is not None:
                return response

    # Consume the complete decoder batch before returning a response.
    #
    # Events before and after a matching response are observations from the
    # same byte batch and must all be queued.  A second matching response is
    # rejected instead of applying an implicit first/last-wins policy.
    def _select_matching_response(
        self,
        frames: Iterable[Frame],
        *,
        sequence: int,
        session_id: int,
        service_id: int,
        command_id: int,
        instance_id: int,
    ) -> tuple[ServiceMessage, Frame] | None:

        selected: tuple[ServiceMessage, Frame] | None = None
        duplicate_response = False
        for frame in frames:
            if frame.message_type is MessageType.EVENT:
                if frame.session_id != session_id:
                    raise ProtocolError("event session does not match the active request")
                self._queue_event(frame)
                continue
            if not self._frame_matches_request(frame, sequence, session_id):
                continue
            if frame.flags != 0:
                raise ProtocolError("ET-Frame v1 response flags must be zero")
            if selected is not None:
                duplicate_response = True
                continue
            message = ServiceMessage.decode(frame.payload)
            self._validate_response_identity(
                message,
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
            )
            selected = (message, frame)

        if duplicate_response:
            raise ProtocolError(f"multiple responses for ET-Frame sequence {sequence}")
        if selected is None:
            return None
        self._raise_if_rejected(selected[0])
        return selected

    @staticmethod
    def _frame_matches_request(
        frame: Frame,
        sequence: int,
        session_id: int,
    ) -> bool:
        return (
            frame.message_type is MessageType.RESPONSE
            and frame.sequence == sequence
            and frame.session_id == session_id
        )

    @staticmethod
    def _validate_response_identity(
        message: ServiceMessage,
        *,
        service_id: int,
        command_id: int,
        instance_id: int,
    ) -> None:
        if (
            message.service_id != service_id
            or message.command_id != command_id
            or message.instance_id != instance_id
        ):
            raise ProtocolError("response service, command or instance does not match the request")

    @staticmethod
    def _raise_if_rejected(message: ServiceMessage) -> None:
        if message.status is Status.OK:
            return
        raise TargetRejected(
            service_id=message.service_id,
            command_id=message.command_id,
            instance_id=message.instance_id,
            status=int(message.status),
            body=message.body,
            status_name=message.status.name,
        )

    def _prepare_retry(
        self,
        attempt: int,
        attempts: int,
        total_deadline: float,
    ) -> None:
        if attempt + 1 >= attempts or self._clock() >= total_deadline:
            return
        self._retry_count += 1
        self._decoder.reset()

    def _queue_event(self, frame: Frame) -> None:
        if len(self._events) == self._EVENT_QUEUE_CAPACITY:
            self._event_overflow_count += 1
        self._events.append(frame)

    def __enter__(self) -> TargetClient:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback
        self.close()
