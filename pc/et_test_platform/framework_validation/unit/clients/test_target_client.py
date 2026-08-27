# Framework Validation测试模块。
#
# 职责：验证test_target_client 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import struct
from collections import deque

import pytest

from et_test_platform.clients.target import TargetClient
from et_test_platform.communication.protocols.et_frame import (
    Frame,
    FrameCodec,
    MessageType,
)
from et_test_platform.communication.protocols.et_message import (
    ServiceMessage,
    Status,
)
from et_test_platform.communication.transport import ByteTransport
from et_test_platform.core.errors import ProtocolError, RequestTimeout, TargetRejected
from et_test_platform.drivers.framework import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
    FrameworkDriver,
)


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return bytes((len(encoded),)) + encoded


def _hello_body(registry_hash: str = "4b95f515") -> bytes:
    return struct.pack("<H", 1) + _string("et6801") + _string("unit-test") + _string(registry_hash)


class FakeTargetTransport(ByteTransport):
    def __init__(self) -> None:
        self._opened = False
        self._reads: deque[bytes] = deque()
        self.reject_command: int | None = None
        self.drop_response_writes = 0
        self.emit_event = False
        self.registry_hash = "4b95f515"
        self.writes: list[bytes] = []

    @property
    def identity(self) -> str:
        return "fake:target"

    def open(self) -> None:
        self._opened = True

    def close(self) -> None:
        self._opened = False

    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        assert self._opened
        self.writes.append(data)
        request = FrameCodec.decode(data)
        message = ServiceMessage.decode(request.payload)
        status = Status.INVALID_PARAM if message.command_id == self.reject_command else Status.OK
        body = b""
        if status is Status.OK:
            if message.command_id == FrameworkCommand.HELLO:
                body = _hello_body(self.registry_hash)
            elif message.command_id == FrameworkCommand.ECHO:
                body = message.body
            elif message.command_id == FrameworkCommand.VERSION_GET:
                body = struct.pack("<H", 1) + _string("unit-test")
            elif message.command_id == FrameworkCommand.SERVICE_LIST:
                body = struct.pack(
                    "<HHH",
                    1,
                    FRAMEWORK_SERVICE_ID,
                    FRAMEWORK_INSTANCE_ID,
                )
            elif message.command_id == FrameworkCommand.STATISTICS_GET:
                body = struct.pack("<IIII", 10, 9, 1, 2)
            elif message.command_id == FrameworkCommand.RESET_REASON_GET:
                status = Status.NOT_SUPPORTED
        response = FrameCodec.encode(
            Frame(
                message_type=MessageType.RESPONSE,
                flags=0,
                sequence=request.sequence,
                session_id=request.session_id,
                payload=ServiceMessage(
                    service_id=message.service_id,
                    command_id=message.command_id,
                    instance_id=message.instance_id,
                    status=status,
                    body=(body if status is Status.OK else b"invalid-test-parameter"),
                ).encode(),
            )
        )
        if self.drop_response_writes > 0:
            self.drop_response_writes -= 1
            return
        if self.emit_event:
            self._reads.append(
                FrameCodec.encode(
                    Frame(
                        message_type=MessageType.EVENT,
                        flags=0,
                        sequence=0x12345678,
                        session_id=request.session_id,
                        payload=b"event-before-response",
                    )
                )
            )
        midpoint = len(response) // 2
        self._reads.extend((response[:midpoint], response[midpoint:]))

    def read(self, max_bytes: int, timeout_s: float) -> bytes:
        del timeout_s
        if not self._reads:
            return b""
        chunk = self._reads.popleft()
        if len(chunk) <= max_bytes:
            return chunk
        self._reads.appendleft(chunk[max_bytes:])
        return chunk[:max_bytes]


def test_framework_driver_hello_version_services_and_statistics() -> None:
    with TargetClient(FakeTargetTransport()) as target:
        framework = FrameworkDriver(target)
        hello = framework.hello()
        version = framework.version_get()
        services = framework.service_list()
        statistics = framework.statistics_get()

    assert hello.chip_id == "et6801"
    assert version.firmware_build_id == "unit-test"
    assert framework.registry_hash == "4b95f515"
    assert [(item.service_id, item.instance_id) for item in services] == [(0, 0)]
    assert statistics.rx_frames == 10
    assert statistics.duplicate_requests == 2


# Catch SERVICE_LIST content drifting away from the HELLO hash.
def test_framework_driver_discovers_and_validates_registry() -> None:

    with TargetClient(FakeTargetTransport()) as target:
        framework = FrameworkDriver(target)
        framework.hello()
        services = framework.discover_services()

    assert services == framework.runtime_services
    assert [(item.service_id, item.instance_id) for item in services] == [(0, 0)]


# Catch a stale or corrupted HELLO registry fingerprint at startup.
def test_framework_driver_rejects_registry_hash_mismatch() -> None:

    transport = FakeTargetTransport()
    transport.registry_hash = "00000000"
    with TargetClient(transport) as target:
        framework = FrameworkDriver(target)
        framework.hello()
        with pytest.raises(ProtocolError, match="registry hash"):
            framework.discover_services()


# A failed refresh must not leave the previous Runtime Registry readable.
def test_framework_failed_rediscovery_invalidates_previous_registry(monkeypatch) -> None:

    with TargetClient(FakeTargetTransport()) as target:
        framework = FrameworkDriver(target)
        framework.hello()
        framework.discover_services()
        monkeypatch.setattr(
            framework,
            "service_list",
            lambda: (_ for _ in ()).throw(RuntimeError("refresh failed")),
        )

        with pytest.raises(RuntimeError, match="refresh failed"):
            framework.discover_services()
        with pytest.raises(RuntimeError, match="discover_services"):
            _ = framework.runtime_services


def test_target_rejection_is_not_reported_as_success() -> None:
    transport = FakeTargetTransport()
    transport.reject_command = FrameworkCommand.ECHO

    with TargetClient(transport) as target:
        framework = FrameworkDriver(target)
        framework.hello()
        with pytest.raises(TargetRejected) as error:
            framework.echo(b"bad")
        assert error.value.status == int(Status.INVALID_PARAM)
        assert error.value.service_id == FRAMEWORK_SERVICE_ID
        assert error.value.command_id == FrameworkCommand.ECHO
        assert error.value.instance_id == FRAMEWORK_INSTANCE_ID
        assert error.value.body == b"invalid-test-parameter"


def test_timeout_retries_exact_request_once() -> None:
    transport = FakeTargetTransport()
    transport.drop_response_writes = 1

    with TargetClient(transport, request_timeout_s=0.02) as target:
        hello = FrameworkDriver(target).hello()

    assert hello.chip_id == "et6801"
    assert target.retry_count == 1
    assert len(transport.writes) == 2
    assert transport.writes[0] == transport.writes[1]


def test_timeout_stops_after_two_attempts() -> None:
    transport = FakeTargetTransport()
    transport.drop_response_writes = 2

    with (
        TargetClient(transport, request_timeout_s=0.02) as target,
        pytest.raises(RequestTimeout, match="2 attempts"),
    ):
        FrameworkDriver(target).hello()

    assert target.retry_count == 1
    assert len(transport.writes) == 2


# A mutating request must not be repeated after an ambiguous timeout.
def test_non_idempotent_timeout_is_not_retried_by_default() -> None:

    transport = FakeTargetTransport()
    transport.drop_response_writes = 1

    with (
        TargetClient(transport, request_timeout_s=0.02) as target,
        pytest.raises(RequestTimeout, match="1 attempts"),
    ):
        target.request(0x1234, 0x0001)

    assert target.retry_count == 0
    assert len(transport.writes) == 1


# An explicitly retry-safe request reuses its sequence and encoded frame.
def test_retry_safe_request_reuses_the_exact_frame_once() -> None:

    transport = FakeTargetTransport()
    transport.drop_response_writes = 1

    with TargetClient(transport, request_timeout_s=0.02) as target:
        message, _ = target.request(0x1234, 0x0007, retry_safe=True)

    assert message.body == b""
    assert target.retry_count == 1
    assert len(transport.writes) == 2
    assert transport.writes[0] == transport.writes[1]


def test_retry_safe_request_stops_after_two_attempts() -> None:
    transport = FakeTargetTransport()
    transport.drop_response_writes = 2

    with (
        TargetClient(transport, request_timeout_s=0.02) as target,
        pytest.raises(RequestTimeout, match="2 attempts"),
    ):
        target.request(0x1234, 0x0007, retry_safe=True)

    assert target.retry_count == 1
    assert len(transport.writes) == 2


def test_framework_echo_preserves_binary_payload() -> None:
    payload = bytes(range(256)) * 4

    with TargetClient(FakeTargetTransport()) as target:
        framework = FrameworkDriver(target)
        framework.hello()
        assert framework.echo(payload).response == payload


def test_unsolicited_event_is_queued_without_hiding_response() -> None:
    transport = FakeTargetTransport()
    transport.emit_event = True

    with TargetClient(transport) as target:
        response = FrameworkDriver(target).echo(b"request")
        event = target.pop_event()

    assert response.response == b"request"
    assert event is not None
    assert event.message_type is MessageType.EVENT
    assert event.payload == b"event-before-response"


class _WriteDeadlineTransport(FakeTargetTransport):
    def __init__(self) -> None:
        super().__init__()
        self.write_timeouts: list[float | None] = []

    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        self.write_timeouts.append(timeout_s)
        super().write(data, timeout_s=timeout_s)


class _TrailingEventTransport(FakeTargetTransport):
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        super().write(data, timeout_s=timeout_s)
        request = FrameCodec.decode(data)
        response = b"".join(self._reads)
        self._reads.clear()
        event = FrameCodec.encode(
            Frame(
                message_type=MessageType.EVENT,
                flags=0,
                sequence=0x87654321,
                session_id=request.session_id,
                payload=b"event-after-response",
            )
        )
        self._reads.append(response + event)


class _DuplicateResponseTransport(FakeTargetTransport):
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        super().write(data, timeout_s=timeout_s)
        response = b"".join(self._reads)
        self._reads.clear()
        self._reads.append(response + response)


class _NonzeroResponseFlagsTransport(FakeTargetTransport):
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        super().write(data, timeout_s=timeout_s)
        response = FrameCodec.decode(b"".join(self._reads))
        self._reads.clear()
        self._reads.append(
            FrameCodec.encode(
                Frame(
                    message_type=response.message_type,
                    flags=1,
                    sequence=response.sequence,
                    session_id=response.session_id,
                    payload=response.payload,
                )
            )
        )


def test_target_write_receives_remaining_total_deadline() -> None:
    transport = _WriteDeadlineTransport()

    with TargetClient(transport, request_timeout_s=0.25) as target:
        FrameworkDriver(target).hello()

    assert len(transport.write_timeouts) == 1
    assert transport.write_timeouts[0] is not None
    assert 0 < transport.write_timeouts[0] <= 0.25


def test_event_after_matching_response_in_same_read_batch_is_queued() -> None:
    transport = _TrailingEventTransport()

    with TargetClient(transport) as target:
        response = FrameworkDriver(target).echo(b"request")
        event = target.pop_event()

    assert response.response == b"request"
    assert event is not None
    assert event.message_type is MessageType.EVENT
    assert event.payload == b"event-after-response"


def test_multiple_matching_responses_in_one_batch_fail_closed() -> None:
    transport = _DuplicateResponseTransport()

    with (
        TargetClient(transport) as target,
        pytest.raises(
            ProtocolError,
            match="multiple responses",
        ),
    ):
        FrameworkDriver(target).echo(b"request")


# ET-Frame v1响应的保留flags必须为零，不能把未知扩展当作合法响应继续执行。
def test_nonzero_response_flags_fail_closed() -> None:

    with (
        TargetClient(_NonzeroResponseFlagsTransport()) as target,
        pytest.raises(ProtocolError, match="response flags must be zero"),
    ):
        FrameworkDriver(target).hello()
