# Framework Validation测试模块。
#
# 职责：验证test_protocol_capacity 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_frame import MAX_PAYLOAD
from et_test_platform.communication.protocols.et_message import HEADER, MAX_BODY, ServiceMessage
from et_test_platform.drivers.uart import UartCommand, UartDriver
from et_test_platform.drivers.uart.contract import (
    MAX_PARTIAL_WRITE_BYTES,
    MAX_READ_CHUNK_BYTES,
    MAX_WRITE_CHUNK_BYTES,
)


class _CapacityTarget:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes]] = []
        self.read_offset = 0

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        timeout_s: float | None = None,
    ):
        del timeout_s
        self.calls.append((int(command_id), bytes(body)))
        response = b""
        if command_id == UartCommand.WRITE:
            response = (len(body) - 4).to_bytes(4, "little")
        elif command_id == UartCommand.WRITE_PARTIAL:
            response = len(body).to_bytes(4, "little")
        elif command_id == UartCommand.READ_EXACT:
            requested = int.from_bytes(body[:4], "little")
            response = bytes((self.read_offset + index) & 0xFF for index in range(requested))
            self.read_offset += requested
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


def test_service_body_capacity_is_derived_from_et_frame() -> None:
    assert MAX_PAYLOAD - HEADER.size == MAX_BODY
    assert MAX_WRITE_CHUNK_BYTES == MAX_BODY - 4
    assert MAX_READ_CHUNK_BYTES == MAX_BODY
    assert MAX_PARTIAL_WRITE_BYTES == MAX_BODY


def test_uart_write_chunks_requests_at_service_body_boundary() -> None:
    target = _CapacityTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]
    payload = bytes(index & 0xFF for index in range(MAX_WRITE_CHUNK_BYTES * 2 + 17))

    assert uart.write(payload, timeout_s=10.0) == len(payload)

    write_bodies = [body for command, body in target.calls if command == UartCommand.WRITE]
    assert len(write_bodies) == 3
    assert all(len(body) <= MAX_BODY for body in write_bodies)
    assert all(body[:4] == b"\x01\x00\x00\x00" for body in write_bodies)
    assert b"".join(body[4:] for body in write_bodies) == payload


def test_uart_read_exact_chunks_responses_at_service_body_boundary() -> None:
    target = _CapacityTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]
    length = MAX_READ_CHUNK_BYTES * 2 + 9

    data = uart.read_exact(length, timeout_s=10.0)

    read_bodies = [body for command, body in target.calls if command == UartCommand.READ_EXACT]
    requested = [int.from_bytes(body[:4], "little") for body in read_bodies]
    assert requested == [MAX_READ_CHUNK_BYTES, MAX_READ_CHUNK_BYTES, 9]
    assert all(body[4:] == b"\x01\x00\x00\x00" for body in read_bodies)
    assert len(data) == length
    assert data == bytes(index & 0xFF for index in range(length))


def test_uart_write_partial_rejects_body_larger_than_protocol_capacity() -> None:
    target = _CapacityTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="service body capacity"):
        uart.write_partial(bytes(MAX_PARTIAL_WRITE_BYTES + 1))

    assert target.calls == []
