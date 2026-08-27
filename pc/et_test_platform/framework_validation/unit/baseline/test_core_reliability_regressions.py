# Framework Validation测试模块。
#
# 职责：验证test_core_reliability_regressions 对应的软件合同和回归行为。
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
from et_test_platform.communication.protocols.et_message import ServiceMessage, Status
from et_test_platform.communication.transport import ByteTransport
from et_test_platform.drivers.framework import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
    FrameworkDriver,
)


def _wire_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return bytes((len(encoded),)) + encoded


def _hello_body() -> bytes:
    return (
        struct.pack("<H", 1)
        + _wire_string("et6801")
        + _wire_string("phase0")
        + _wire_string("4b95f515")
    )


# Return valid framework responses and an optional burst of events.
class _ScriptedTransport(ByteTransport):
    def __init__(self) -> None:
        self._opened = False
        self._reads: deque[bytes] = deque()
        self.event_burst = 0

    @property
    def identity(self) -> str:
        return "fake:phase0"

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
        request = FrameCodec.decode(data)
        message = ServiceMessage.decode(request.payload)

        for index in range(self.event_burst):
            self._reads.append(
                FrameCodec.encode(
                    Frame(
                        message_type=MessageType.EVENT,
                        flags=0,
                        sequence=index,
                        session_id=request.session_id,
                        payload=f"event-{index}".encode("ascii"),
                    )
                )
            )

        body = b""
        if message.service_id == FRAMEWORK_SERVICE_ID:
            if message.command_id == FrameworkCommand.HELLO:
                body = _hello_body()
            elif message.command_id == FrameworkCommand.SERVICE_LIST:
                body = struct.pack(
                    "<HHH",
                    1,
                    FRAMEWORK_SERVICE_ID,
                    FRAMEWORK_INSTANCE_ID,
                )

        self._reads.append(
            FrameCodec.encode(
                Frame(
                    message_type=MessageType.RESPONSE,
                    flags=0,
                    sequence=request.sequence,
                    session_id=request.session_id,
                    payload=ServiceMessage(
                        service_id=message.service_id,
                        command_id=message.command_id,
                        instance_id=message.instance_id,
                        status=Status.OK,
                        body=body,
                    ).encode(),
                )
            )
        )

    def read(self, max_bytes: int, timeout_s: float) -> bytes:
        del timeout_s
        if not self._reads:
            return b""
        chunk = self._reads.popleft()
        if len(chunk) <= max_bytes:
            return chunk
        self._reads.appendleft(chunk[max_bytes:])
        return chunk[:max_bytes]


# A caller cannot create an unbounded or already-expired sub-request.
def test_request_rejects_zero_and_negative_per_call_timeout() -> None:

    with TargetClient(_ScriptedTransport()) as target:
        with pytest.raises(ValueError, match="timeout_s must be a positive finite number"):
            target.request(0x1234, 0x0001, timeout_s=0)
        with pytest.raises(ValueError, match="timeout_s must be a positive finite number"):
            target.request(0x1234, 0x0001, timeout_s=-0.1)


# A fixed event queue may drop old events only with an explicit counter.
def test_event_queue_overflow_is_observable_without_dynamic_growth() -> None:

    transport = _ScriptedTransport()
    transport.event_burst = 40
    with TargetClient(transport) as target:
        target.request(0x1234, 0x0001)
        events = []
        while (event := target.pop_event()) is not None:
            events.append(event)

        assert target.event_overflow_count == 8
        assert len(events) == 32
        assert events[0].payload == b"event-8"
        assert events[-1].payload == b"event-39"


# Runtime capabilities from one session must not leak into the next session.
def test_new_hello_invalidates_old_service_registry_cache() -> None:

    sessions = iter((1, 2))
    with TargetClient(_ScriptedTransport()) as target:
        framework = FrameworkDriver(
            target,
            session_id_factory=lambda: next(sessions),
        )
        framework.hello()
        assert framework.discover_services() == framework.runtime_services

        framework.hello()
        with pytest.raises(RuntimeError, match="discover_services"):
            _ = framework.runtime_services
