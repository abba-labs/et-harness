# 外部仪器 Connection 工厂无硬件单元测试。
#
# 职责：验证 DM3068 LAN 与 9130B USBTMC 工厂的 VISA 资源约束、构造结果和零 I/O 行为。
# 边界：不打开真实 VISA 资源、不依赖 PyVISA backend，也不证明真实仪器通信成功。
# 依赖：仅依赖两个型号包的公共 Connection API 和 pytest。

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from et_test_platform.communication.transports.visa import VisaTransport
from et_test_platform.core.errors import TransportError
from et_test_platform.instruments.dmms.dm3068 import create_dm3068_lan_driver
from et_test_platform.instruments.power_supplies.bk9130b import create_bk9130b_usb_driver


class _FakeVisaResource:
    def __init__(self) -> None:
        self.timeout = 111
        self.writes: list[bytes] = []
        self.reads = [b"abcdef"]
        self.closed = False

    def write_raw(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def read_raw(self) -> bytes:
        return self.reads.pop(0)

    def close(self) -> None:
        self.closed = True


class _FakeVisaManager:
    def __init__(self, resource: _FakeVisaResource) -> None:
        self.resource = resource
        self.open_calls: list[tuple[str, int]] = []
        self.closed = False

    def open_resource(self, name: str, *, open_timeout: int) -> _FakeVisaResource:
        self.open_calls.append((name, open_timeout))
        return self.resource

    def close(self) -> None:
        self.closed = True


# 验证 DM3068 LAN 工厂接受 TCPIP VISA 资源，并在构造阶段只建立本地 Driver 对象。
def test_dm3068_lan_factory_builds_tcpip_visa_driver_without_io() -> None:
    driver = create_dm3068_lan_driver(" TCPIP0::192.168.10.22::INSTR ")

    assert driver.identity == "visa:TCPIP0::192.168.10.22::INSTR"
    assert driver.operations is not None


# 验证 DM3068 LAN 工厂在创建 Transport 前拒绝空资源和非 TCPIP VISA 资源。
def test_dm3068_lan_factory_rejects_non_lan_resources() -> None:
    with pytest.raises(ValueError):
        create_dm3068_lan_driver("")
    with pytest.raises(ValueError):
        create_dm3068_lan_driver("USB0::0x1AB1::0x1234::SN::INSTR")


# 验证 9130B USB 工厂接受 USBTMC VISA 资源，并在构造阶段不要求安装或打开 PyVISA backend。
def test_bk9130b_usb_factory_builds_usbtmc_visa_driver_without_io() -> None:
    driver = create_bk9130b_usb_driver(" USB0::0xFFFF::0x1234::BK9130B0001::INSTR ")

    assert driver.identity == "visa:USB0::0xFFFF::0x1234::BK9130B0001::INSTR"
    assert driver.operations is not None


# 验证 9130B USB 工厂只接受 USB VISA 资源，避免把 GPIB/TCPIP 误当成项目默认 USB 通道。
def test_bk9130b_usb_factory_rejects_non_usb_resources() -> None:
    with pytest.raises(ValueError):
        create_bk9130b_usb_driver("")
    with pytest.raises(ValueError):
        create_bk9130b_usb_driver("GPIB0::5::INSTR")


# 验证公共 VISA Transport 延迟创建 backend，并保持原始字节、调用超时和分块读取语义。
def test_visa_transport_maps_raw_io_and_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    resource = _FakeVisaResource()
    manager = _FakeVisaManager(resource)
    fake_pyvisa = SimpleNamespace(
        ResourceManager=lambda: manager,
        constants=SimpleNamespace(StatusCode=SimpleNamespace(error_timeout=-1)),
    )
    monkeypatch.setitem(sys.modules, "pyvisa", fake_pyvisa)
    transport = VisaTransport(resource_name=" TCPIP0::192.168.10.22::INSTR ")

    assert transport.identity == "visa:TCPIP0::192.168.10.22::INSTR"
    transport.open()
    transport.write(b"*IDN?\n", timeout_s=0.25)
    first = transport.read(4, timeout_s=0.5)
    second = transport.read(4, timeout_s=0.5)
    transport.close()

    assert manager.open_calls == [("TCPIP0::192.168.10.22::INSTR", 5000)]
    assert resource.writes == [b"*IDN?\n"]
    assert first == b"abcd"
    assert second == b"ef"
    assert resource.timeout == 111
    assert resource.closed is True
    assert manager.closed is True


# 验证 VISA Transport 在未打开时失败关闭，不把程序错误伪装成空读取。
def test_visa_transport_rejects_io_before_open() -> None:
    transport = VisaTransport(resource_name="USB0::1::2::SN::INSTR")

    with pytest.raises(TransportError, match="not open"):
        transport.write(b"*IDN?\n")
    with pytest.raises(TransportError, match="not open"):
        transport.read(1)
