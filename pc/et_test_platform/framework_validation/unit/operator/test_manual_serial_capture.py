# 手动诊断串口捕获工具的无硬件单元测试。
# 职责：验证日志捕获、时间推进和输出边界。
# 边界：不访问真实串口或目标硬件。
# 依赖：仅依赖标准库和手动串口捕获工具模块。
from __future__ import annotations

import importlib.util
import io
from datetime import datetime
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[5]
MODULE_PATH = CODE_ROOT / "tools" / "manual_test" / "capture_serial_log.py"
SPEC = importlib.util.spec_from_file_location("capture_serial_log", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
capture_serial_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture_serial_log)


class FakeSerial:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)

    def read(self, size: int = 1) -> bytes:
        del size
        return next(self._chunks, b"")


class StepClock:
    def __init__(self) -> None:
        self._value = 0.0

    def __call__(self) -> float:
        self._value += 0.1
        return self._value


class FakePort:
    def __init__(self) -> None:
        self.port = ""
        self.dtr = True
        self.rts = True
        self.opened = False

    def read(self, size: int = 1) -> bytes:
        del size
        return b""

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False


class FakeSerialModule:
    def __init__(self) -> None:
        self.port_handle = FakePort()
        self.arguments: dict[str, object] = {}

    def Serial(self, **kwargs: object) -> FakePort:
        self.arguments = kwargs
        return self.port_handle


def test_capture_stream_stops_after_marker_and_preserves_raw_bytes() -> None:
    output = io.BytesIO()
    reader = FakeSerial(
        [b"[MANUAL] start\r\n", b"[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS end\r\n"]
    )

    completed, byte_count = capture_serial_log.capture_stream(
        reader,
        output,
        timeout_s=2.0,
        end_marker=b"[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS end",
        clock=StepClock(),
    )

    assert completed is True
    assert byte_count == len(output.getvalue())
    assert output.getvalue().endswith(b"end\r\n")


def test_capture_stream_reports_timeout_without_marker() -> None:
    output = io.BytesIO()

    completed, byte_count = capture_serial_log.capture_stream(
        FakeSerial([b"partial\r\n"]),
        output,
        timeout_s=0.5,
        end_marker=b"end-marker",
        clock=StepClock(),
    )

    assert completed is False
    assert byte_count == len(b"partial\r\n")


def test_default_output_path_uses_artifacts_run_layout() -> None:
    code_root = Path("D:/workspace/code")
    output = capture_serial_log.default_output_path(
        code_root,
        datetime(2026, 8, 24, 12, 34, 56, 123456),
    )

    assert output == (
        code_root
        / "artifacts"
        / "runs"
        / "20260824_123456_123456_manual_et6801_diagnostics"
        / "manual"
        / "diagnostics.log"
    )


def test_open_serial_port_matches_formal_transport_control_lines() -> None:
    serial_module = FakeSerialModule()

    port_handle = capture_serial_log.open_serial_port(serial_module, "COM12", 115200)

    assert serial_module.arguments == {
        "port": None,
        "baudrate": 115200,
        "timeout": 0.1,
        "write_timeout": 1.0,
    }
    assert port_handle.port == "COM12"
    assert port_handle.dtr is False
    assert port_handle.rts is False
    assert port_handle.opened is True
