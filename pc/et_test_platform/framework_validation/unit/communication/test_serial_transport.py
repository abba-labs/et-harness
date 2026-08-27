# Framework Validation测试模块。
#
# 职责：验证test_serial_transport 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import sys
from types import SimpleNamespace

from et_test_platform.communication.transports.serial import SerialTransport


class _FakeSerial:
    def __init__(self, **settings) -> None:
        self.settings = settings
        self.port = settings.get("port")
        self.dtr = True
        self.rts = True
        self.timeout = settings["timeout"]
        self.write_timeout = settings["write_timeout"]
        self.write_timeouts: list[float | None] = []
        self.opened_with: tuple[bool, bool] | None = None
        self.read_sizes: list[int] = []
        self.read_timeouts: list[float] = []
        self.in_waiting = 2

    def open(self) -> None:
        self.opened_with = (self.dtr, self.rts)

    def close(self) -> None:
        pass

    def write(self, data: bytes) -> int:
        self.write_timeouts.append(self.write_timeout)
        return len(data)

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        self.read_timeouts.append(self.timeout)
        if size == 1:
            return b"E"
        return b"T!"


def test_serial_control_lines_are_set_before_open(monkeypatch) -> None:
    created: list[_FakeSerial] = []

    def create_serial(**settings) -> _FakeSerial:
        serial_port = _FakeSerial(**settings)
        created.append(serial_port)
        return serial_port

    monkeypatch.setitem(
        sys.modules,
        "serial",
        SimpleNamespace(Serial=create_serial),
    )
    transport = SerialTransport(
        port="COM_TEST",
        baudrate=115200,
        dtr=False,
        rts=True,
    )

    transport.open()

    assert created[0].port == "COM_TEST"
    assert created[0].opened_with == (False, True)
    assert created[0].settings["port"] is None
    assert "do_not_open" not in created[0].settings


def test_serial_read_returns_after_first_byte_and_drains_available(
    monkeypatch,
) -> None:
    created: list[_FakeSerial] = []

    def create_serial(**settings) -> _FakeSerial:
        serial_port = _FakeSerial(**settings)
        created.append(serial_port)
        return serial_port

    monkeypatch.setitem(
        sys.modules,
        "serial",
        SimpleNamespace(Serial=create_serial),
    )
    transport = SerialTransport(port="COM_TEST", baudrate=115200)
    transport.open()

    assert transport.read(16, 0.5) == b"ET!"
    assert created[0].read_timeouts == [0.5, 0.5]
    assert created[0].timeout == 0.02
    assert created[0].read_sizes == [1, 2]


def test_serial_write_applies_operation_timeout_and_restores_default(
    monkeypatch,
) -> None:
    created: list[_FakeSerial] = []

    def create_serial(**settings) -> _FakeSerial:
        serial_port = _FakeSerial(**settings)
        created.append(serial_port)
        return serial_port

    monkeypatch.setitem(
        sys.modules,
        "serial",
        SimpleNamespace(Serial=create_serial),
    )
    transport = SerialTransport(port="COM_TEST", baudrate=115200)
    transport.open()

    transport.write(b"ET", timeout_s=0.125)

    assert created[0].write_timeouts == [0.125]
    assert created[0].write_timeout == 1.0
