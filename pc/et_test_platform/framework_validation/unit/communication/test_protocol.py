# Framework Validation测试模块。
#
# 职责：验证test_protocol 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import json
from pathlib import Path

import pytest

from et_test_platform.communication.protocols.et_frame import (
    Frame,
    FrameCodec,
    FrameDecoder,
    MessageType,
)
from et_test_platform.communication.protocols.et_message import (
    ServiceMessage,
    Status,
)
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.framework import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
)


def test_frame_round_trip_and_fragmented_decode() -> None:
    frame = Frame(
        message_type=MessageType.REQUEST,
        flags=0,
        sequence=0x10203040,
        session_id=0x55667788,
        payload=ServiceMessage(
            service_id=FRAMEWORK_SERVICE_ID,
            command_id=FrameworkCommand.HELLO,
            instance_id=FRAMEWORK_INSTANCE_ID,
        ).encode(),
    )
    encoded = FrameCodec.encode(frame)

    assert FrameCodec.decode(encoded) == frame

    decoder = FrameDecoder()
    decoded = []
    for byte in encoded:
        decoded.extend(decoder.feed(bytes((byte,))))
    assert decoded == [frame]


def test_decoder_resynchronizes_after_noise_and_bad_crc() -> None:
    valid = FrameCodec.encode(
        Frame(
            message_type=MessageType.RESPONSE,
            flags=0,
            sequence=7,
            session_id=9,
            payload=ServiceMessage(
                service_id=FRAMEWORK_SERVICE_ID,
                command_id=FrameworkCommand.ECHO,
                instance_id=FRAMEWORK_INSTANCE_ID,
                body=b"ok",
            ).encode(),
        )
    )
    corrupted = bytearray(valid)
    corrupted[-1] ^= 0xFF

    decoder = FrameDecoder()
    frames = decoder.feed(b"\x00noise" + bytes(corrupted) + valid)

    assert len(frames) == 1
    assert frames[0].sequence == 7


def test_frame_crc_failure_is_not_accepted() -> None:
    encoded = bytearray(
        FrameCodec.encode(
            Frame(
                message_type=MessageType.EVENT,
                flags=0,
                sequence=1,
                session_id=2,
                payload=b"payload",
            )
        )
    )
    encoded[-1] ^= 1

    with pytest.raises(ProtocolError, match="CRC"):
        FrameCodec.decode(bytes(encoded))


def test_service_message_round_trip_and_validation() -> None:
    message = ServiceMessage(
        service_id=0x1234,
        command_id=0x5678,
        instance_id=3,
        status=Status.BUSY,
        body=b"\x00\xff",
    )
    assert ServiceMessage.decode(message.encode()) == message

    with pytest.raises(ProtocolError, match="shorter"):
        ServiceMessage.decode(b"\x00" * 7)
    with pytest.raises(ProtocolError, match="unknown status"):
        ServiceMessage.decode(b"\x00\x00\x00\x00\x00\x00\xff\xff")


def test_et_frame_v1_golden_vectors_are_stable() -> None:
    fixture = Path(__file__).parents[2] / "test_data" / "protocol" / "et_frame_v1_golden.json"
    vectors = {
        item["name"]: item["hex"]
        for item in json.loads(fixture.read_text(encoding="utf-8"))["vectors"]
    }

    hello_request = FrameCodec.encode(
        Frame(
            message_type=MessageType.REQUEST,
            flags=0,
            sequence=1,
            session_id=0xA1B2C3D4,
            payload=ServiceMessage(
                service_id=FRAMEWORK_SERVICE_ID,
                command_id=FrameworkCommand.HELLO,
                instance_id=FRAMEWORK_INSTANCE_ID,
            ).encode(),
        )
    )
    echo_response = FrameCodec.encode(
        Frame(
            message_type=MessageType.RESPONSE,
            flags=0,
            sequence=2,
            session_id=0x10203040,
            payload=ServiceMessage(
                service_id=FRAMEWORK_SERVICE_ID,
                command_id=FrameworkCommand.ECHO,
                instance_id=FRAMEWORK_INSTANCE_ID,
                body=b"ET",
            ).encode(),
        )
    )

    assert hello_request.hex() == vectors["framework_hello_request"]
    assert echo_response.hex() == vectors["framework_echo_response"]
