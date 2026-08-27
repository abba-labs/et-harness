#!/usr/bin/env python3

# 独立手动诊断串口日志采集工具。
#
# 本工具只保存固件可读输出，不解析 ET-Frame，也不修改正式测试结果。

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Protocol

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_END_MARKER = "[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS end"
DEFAULT_START_TRIGGER = b"R"
READ_CHUNK_SIZE = 256


class SerialReader(Protocol):
    # 采集循环依赖的最小串口接口，便于无硬件单元测试。
    def read(self, size: int = 1) -> bytes: ...


class SerialPort(SerialReader, Protocol):
    port: str
    dtr: bool
    rts: bool

    def open(self) -> None: ...

    def close(self) -> None: ...


class SerialModule(Protocol):
    def Serial(
        self,
        *,
        port: None,
        baudrate: int,
        timeout: float,
        write_timeout: float,
    ) -> SerialPort: ...


def open_serial_port(serial_module: SerialModule, port: str, baudrate: int) -> SerialPort:
    # 与正式自动化平台保持相同的打开顺序及握手线状态，避免 J28 的控制线干扰通信。
    port_handle = serial_module.Serial(
        port=None,
        baudrate=baudrate,
        timeout=0.1,
        write_timeout=1.0,
    )
    port_handle.port = port
    port_handle.dtr = False
    port_handle.rts = False
    port_handle.open()

    return port_handle


def default_output_path(code_root: Path, now: datetime | None = None) -> Path:
    # 使用稳定时间戳创建一次独立采集目录，避免覆盖历史证据。
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return (
        code_root
        / "artifacts"
        / "runs"
        / f"{timestamp}_manual_et6801_diagnostics"
        / "manual"
        / "diagnostics.log"
    )


def capture_stream(
    reader: SerialReader,
    output: BinaryIO,
    *,
    timeout_s: float,
    end_marker: bytes,
    clock=time.monotonic,
) -> tuple[bool, int]:
    # 在总超时内原样保存串口字节；检测到结束标记后立即正常收口。
    deadline = clock() + timeout_s
    observed = bytearray()
    total_bytes = 0

    while clock() < deadline:
        chunk = reader.read(READ_CHUNK_SIZE)

        if not chunk:
            continue

        output.write(chunk)
        output.flush()
        observed.extend(chunk)
        total_bytes += len(chunk)

        if end_marker in observed:
            return True, total_bytes

        if len(observed) > len(end_marker):
            del observed[: len(observed) - len(end_marker)]

    return False, total_bytes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture ET6801 manual diagnostic UART output")
    parser.add_argument("--port", required=True, help="Serial port, for example COM5")
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--output", type=Path, help="Explicit log file path")
    parser.add_argument("--end-marker", default=DEFAULT_END_MARKER)
    parser.add_argument(
        "--no-start-trigger",
        action="store_true",
        help="Do not send the one-byte manual-firmware start trigger after opening the port",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.baudrate <= 0 or args.timeout_s <= 0:
        raise SystemExit("baudrate and timeout-s must be positive")

    code_root = Path(__file__).resolve().parents[2]
    output_path = args.output or default_output_path(code_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is required: install the project PC dependencies") from exc

    started_at = datetime.now().astimezone()

    port_handle = open_serial_port(serial, args.port, args.baudrate)

    try:
        port_handle.reset_input_buffer()

        if not args.no_start_trigger:
            port_handle.write(DEFAULT_START_TRIGGER)
            port_handle.flush()

        with output_path.open("wb") as output:
            completed, byte_count = capture_stream(
                port_handle,
                output,
                timeout_s=args.timeout_s,
                end_marker=args.end_marker.encode("utf-8"),
            )
    finally:
        port_handle.close()

    manifest = {
        "schema_version": 1,
        "started_at": started_at.isoformat(timespec="seconds"),
        "port": args.port,
        "baudrate": args.baudrate,
        "timeout_s": args.timeout_s,
        "end_marker": args.end_marker,
        "end_marker_observed": completed,
        "byte_count": byte_count,
        "log": str(output_path.resolve()),
        "result": "PASS" if completed else "TIMEOUT",
    }
    manifest_path = output_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"MANUAL_SERIAL_CAPTURE_{manifest['result']}|log={output_path}|bytes={byte_count}")

    return 0 if completed else 2


if __name__ == "__main__":
    sys.exit(main())
