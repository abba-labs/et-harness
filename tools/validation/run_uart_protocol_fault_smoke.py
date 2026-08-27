# ET-Frame hardware fault-recovery smoke over a serial bench profile.

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE_ROOT / "pc"))

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
from et_test_platform.clients.target import TargetClient
from et_test_platform.communication.transport import ByteTransport
from et_test_platform.communication.transports.serial import SerialTransport
from et_test_platform.drivers.framework import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
    FrameworkDriver,
)
from et_test_platform.profiles.bench import load_serial_target


def _make_transport(config) -> SerialTransport:
    return SerialTransport(
        port=config.port,
        baudrate=config.baudrate,
        bytesize=config.bytesize,
        parity=config.parity,
        stopbits=config.stopbits,
        dtr=config.dtr,
        rts=config.rts,
    )


def _echo_frame(sequence: int, session_id: int, body: bytes) -> bytes:
    return FrameCodec.encode(
        Frame(
            message_type=MessageType.REQUEST,
            flags=0,
            sequence=sequence,
            session_id=session_id,
            payload=ServiceMessage(
                service_id=FRAMEWORK_SERVICE_ID,
                command_id=FrameworkCommand.ECHO,
                instance_id=FRAMEWORK_INSTANCE_ID,
                status=Status.OK,
                body=body,
            ).encode(),
        )
    )


def _read_response(
    transport: ByteTransport,
    decoder: FrameDecoder,
    *,
    sequence: int,
    timeout_s: float,
) -> Frame | None:
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        for frame in decoder.feed(transport.read(4096, remaining)):
            if frame.message_type is MessageType.RESPONSE and frame.sequence == sequence:
                return frame


def _verify_echo(frame: Frame, expected: bytes) -> None:
    message = ServiceMessage.decode(frame.payload)
    if (
        message.service_id != FRAMEWORK_SERVICE_ID
        or message.command_id != FrameworkCommand.ECHO
        or message.instance_id != FRAMEWORK_INSTANCE_ID
        or message.status is not Status.OK
        or message.body != expected
    ):
        raise RuntimeError("Framework ECHO response does not match the request")


class _DropFirstResponseTransport(ByteTransport):
    def __init__(self, inner: ByteTransport) -> None:
        self._inner = inner
        self._writes = 0

    @property
    def identity(self) -> str:
        return f"drop-first:{self._inner.identity}"

    def open(self) -> None:
        self._inner.open()

    def close(self) -> None:
        self._inner.close()

    def write(self, data: bytes) -> None:
        self._writes += 1
        self._inner.write(data)

    def read(self, max_bytes: int, timeout_s: float) -> bytes:
        data = self._inner.read(max_bytes, timeout_s)
        return b"" if self._writes == 1 else data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", required=True)
    parser.add_argument("--target", default="dut")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    config = load_serial_target(args.bench, args.target)
    with TargetClient(
        _make_transport(config),
        request_timeout_s=config.request_timeout_s,
    ) as target:
        FrameworkDriver(target).hello()
        protocol_session_id = target.session_id

    results: dict[str, object] = {
        "schemaVersion": 1,
        "transport": f"serial:{config.port}@{config.baudrate}",
        "sessionId": protocol_session_id,
    }
    transport = _make_transport(config)
    decoder = FrameDecoder()
    transport.open()
    try:
        bad_crc_body = bytes(range(32))
        bad_crc = bytearray(_echo_frame(100, protocol_session_id, bad_crc_body))
        bad_crc[-1] ^= 0x80
        transport.write(bytes(bad_crc))
        if (
            _read_response(
                transport,
                decoder,
                sequence=100,
                timeout_s=0.25,
            )
            is not None
        ):
            raise RuntimeError("bad-CRC request unexpectedly received a response")
        decoder.reset()
        valid = _echo_frame(100, protocol_session_id, bad_crc_body)
        transport.write(valid)
        response = _read_response(
            transport,
            decoder,
            sequence=100,
            timeout_s=config.request_timeout_s,
        )
        if response is None:
            raise RuntimeError("valid request after bad CRC timed out")
        _verify_echo(response, bad_crc_body)
        results["badCrcRecovery"] = "PASS"

        noise_body = bytes((index * 17) & 0xFF for index in range(96))
        transport.write(
            b"\x00\xffnoise-before-frame" + _echo_frame(101, protocol_session_id, noise_body)
        )
        response = _read_response(
            transport,
            decoder,
            sequence=101,
            timeout_s=config.request_timeout_s,
        )
        if response is None:
            raise RuntimeError("valid request after noise timed out")
        _verify_echo(response, noise_body)
        results["noiseResync"] = "PASS"

        partial_body = bytes((index * 29) & 0xFF for index in range(64))
        partial = _echo_frame(102, protocol_session_id, partial_body)
        transport.write(partial[:20])
        time.sleep(0.2)
        transport.write(partial)
        response = _read_response(
            transport,
            decoder,
            sequence=102,
            timeout_s=config.request_timeout_s,
        )
        if response is None:
            raise RuntimeError("valid request after partial-frame idle timed out")
        _verify_echo(response, partial_body)
        results["partialFrameIdleRecovery"] = "PASS"
    finally:
        transport.close()

    drop_transport = _DropFirstResponseTransport(_make_transport(config))
    with TargetClient(
        drop_transport,
        request_timeout_s=0.25,
    ) as target:
        hello = FrameworkDriver(target).hello()
        if hello.protocol_version != 1 or target.retry_count != 1:
            raise RuntimeError("timeout retry did not recover exactly once")
        results["timeoutRetry"] = "PASS"
        results["retryCount"] = target.retry_count

    results["status"] = "PASS"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
