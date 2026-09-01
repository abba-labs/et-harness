# Framework Validation测试模块。
#
# 职责：验证test_resource_driver 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.resource import (
    RESOURCE_SERVICE_ID,
    RESOURCE_TRANSFER_CHUNK,
    ResourceCommand,
    ResourceDriver,
    ResourceRef,
)


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ):
        self.calls.append((service_id, command_id, instance_id, body))
        response = b""
        if command_id == ResourceCommand.READ:
            requested = int.from_bytes(body[8:12], "little")
            offset = int.from_bytes(body[4:8], "little")
            response = bytes((offset + index) & 0xFF for index in range(requested))
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


def test_resource_write_is_split_below_the_frame_limit() -> None:
    target = _Target()
    resource = ResourceRef(7, 5000, 0x20400000)
    data = bytes(index & 0xFF for index in range(5000))

    ResourceDriver(target).write(resource, data)  # type: ignore[arg-type]

    assert len(target.calls) == 3
    assert all(call[0] == RESOURCE_SERVICE_ID for call in target.calls)
    assert all(call[1] == ResourceCommand.WRITE for call in target.calls)
    assert [int.from_bytes(call[3][4:8], "little") for call in target.calls] == [
        0,
        RESOURCE_TRANSFER_CHUNK,
        RESOURCE_TRANSFER_CHUNK * 2,
    ]
    assert b"".join(call[3][8:] for call in target.calls) == data


def test_resource_read_reassembles_chunked_responses() -> None:
    target = _Target()
    resource = ResourceRef(9, 5000, 0x20402000)

    result = ResourceDriver(target).read(resource)  # type: ignore[arg-type]

    assert len(target.calls) == 3
    expected = bytes(index & 0xFF for index in range(5000))
    assert result == expected


def test_resource_read_and_write_reject_out_of_range_access() -> None:
    driver = ResourceDriver(_Target())  # type: ignore[arg-type]
    resource = ResourceRef(1, 16, 0x20400000)

    for operation in (
        lambda: driver.write(resource, b"ab", offset=15),
        lambda: driver.read(resource, size=2, offset=15),
    ):
        try:
            operation()
        except ValueError as exc:
            assert "outside" in str(exc)
        else:
            raise AssertionError("out-of-range resource access was accepted")
