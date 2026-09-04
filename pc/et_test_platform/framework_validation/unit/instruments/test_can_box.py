# CAN盒子的无硬件契约回归。
# 职责：检查ABI布局、帧边界、初始化顺序、错误传播和关闭恢复。
# 边界：Fake只替代厂商函数，不作为CAN总线或DUT的PASS证据。
# 依赖：pytest和正式CAN盒子Adapter。

import ctypes as ct
from pathlib import Path

import pytest
import yaml

from et_test_platform.instruments.can_boxes import (
    CanBusConfig,
    CanFrame,
    ZlgCanBox,
    ZlgConnection,
)
from et_test_platform.instruments.can_boxes import _zlg_abi as abi
from et_test_platform.instruments.can_boxes.connection import (
    create_zlg_can_box,
    create_zlg_can_box_from_environment,
)
from tools.runner.can_box import main


# Fake只接受当前Adapter实际使用的调用参数；不提供万能getattr兜底。
class FakeZlg:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self.fail_start = False
        self.fail_reset = False
        self.fd_rx: abi.FdRx | None = None
        self.classic_rx: abi.ClassicRx | None = None
        self.tx: abi.ClassicTx | abi.FdTx | None = None

    def ZCAN_OpenDevice(self, kind, index, reserved):
        assert (kind, index, reserved) == (41, 0, 0)
        self.calls.append("open")
        return 0x123456789ABC

    def ZCAN_GetDeviceInf(self, device, output):
        assert device == 0x123456789ABC
        raw = ct.cast(output, ct.POINTER(abi.DeviceInfo)).contents
        raw.serial, raw.hardware, raw.can_num = b"BOX01", b"USBCANFD_200U", 2
        return 1

    def ZCAN_SetValue(self, device, path, value):
        assert device == 0x123456789ABC
        assert path.startswith(b"1/")
        self.calls.append((path, value))
        return 1

    def ZCAN_InitCAN(self, device, channel, config):
        assert device == 0x123456789ABC and channel == 1
        raw = ct.cast(config, ct.POINTER(abi.ChannelConfig)).contents
        assert raw.can_type == 1 and raw.canfd.acc_mask == 0xFFFFFFFF
        self.calls.append("init")
        return 0xABCDEF123456

    def ZCAN_StartCAN(self, channel):
        assert channel == 0xABCDEF123456
        self.calls.append("start")
        return 0 if self.fail_start else 1

    def ZCAN_ResetCAN(self, channel):
        assert channel == 0xABCDEF123456
        self.calls.append("reset")
        return 0 if self.fail_reset else 1

    def ZCAN_CloseDevice(self, device):
        assert device == 0x123456789ABC
        self.calls.append("close")
        return 1

    def ZCAN_TransmitFD(self, channel, output, count):
        assert channel == 0xABCDEF123456 and count == 1
        self.tx = abi.FdTx.from_buffer_copy(ct.string_at(output, ct.sizeof(abi.FdTx)))
        return 1

    def ZCAN_Transmit(self, channel, output, count):
        assert channel == 0xABCDEF123456 and count == 1
        self.tx = abi.ClassicTx.from_buffer_copy(ct.string_at(output, ct.sizeof(abi.ClassicTx)))
        return 1

    def ZCAN_ReceiveFD(self, channel, output, count, wait):
        assert channel == 0xABCDEF123456 and (count, wait) == (1, 0)
        if self.fd_rx is None:
            return 0
        ct.memmove(output, ct.byref(self.fd_rx), ct.sizeof(self.fd_rx))
        self.fd_rx = None
        return 1

    def ZCAN_Receive(self, channel, output, count, wait):
        assert channel == 0xABCDEF123456 and (count, wait) == (1, 0)
        if self.classic_rx is None:
            return 0
        ct.memmove(output, ct.byref(self.classic_rx), ct.sizeof(self.classic_rx))
        self.classic_rx = None
        return 1

    def ZCAN_ReadChannelErrInfo(self, channel, output):
        assert channel == 0xABCDEF123456
        ct.cast(output, ct.POINTER(abi.ChannelError)).contents.error_code = 0x20
        return 1

    def ZCAN_ClearBuffer(self, channel):
        assert channel == 0xABCDEF123456
        self.calls.append("clear")
        return 1


@pytest.fixture
def box(monkeypatch):
    fake = FakeZlg()
    monkeypatch.setattr(abi, "load_library", lambda path: fake)
    box = ZlgCanBox(ZlgConnection(Path("zlgcan.dll"), "USBCANFD_200U", 0, 1, True, "BOX01"))
    yield box, fake
    fake.fail_reset = False
    box.close()


def test_native_abi_layout():
    assert ct.sizeof(abi.ClassicFrame) == 16
    assert ct.sizeof(abi.ClassicTx) == 20
    assert ct.sizeof(abi.ClassicRx) == 24
    assert ct.sizeof(abi.FdFrame) == 72
    assert ct.sizeof(abi.FdTx) == 76
    assert ct.sizeof(abi.FdRx) == 80
    assert ct.sizeof(abi.ChannelConfig) == 32
    assert ct.sizeof(abi.DeviceInfo) == 80
    assert abi.FdRx.timestamp.offset == 72
    assert abi.DeviceInfo.serial.offset == 11


@pytest.mark.parametrize("length,dlc", [(0, 0), (8, 8), (12, 9), (64, 15)])
def test_fd_dlc_preserves_payload(length, dlc):
    frame = CanFrame(0x123, bytes(length), fd=True, brs=True)
    assert frame.dlc == dlc and len(frame.data) == length


@pytest.mark.parametrize(
    "kwargs",
    [
        {"identifier": 0x800},
        {"identifier": -1},
        {"identifier": 0x20000000, "extended": True},
        {"identifier": 1, "data": bytes(9)},
        {"identifier": 1, "data": bytes(9), "fd": True},
        {"identifier": 1, "brs": True},
        {"identifier": 1, "fd": True, "remote": True},
        {"identifier": 1, "data": b"a", "remote": True},
        {"identifier": 1, "dlc": 8},
    ],
)
def test_invalid_frames_rejected(kwargs):
    with pytest.raises(ValueError):
        CanFrame(**kwargs)


def test_open_configure_order_and_identity(box):
    device, fake = box
    info = device.open()
    assert info.serial == "BOX01" and info.channels == 2
    device.configure(CanBusConfig())
    assert fake.calls == [
        "open",
        (b"1/canfd_standard", b"0"),
        (b"1/canfd_abit_baud_rate", b"500000"),
        (b"1/canfd_dbit_baud_rate", b"2000000"),
        "init",
        (b"1/initenal_resistance", b"1"),
        "start",
    ]
    device.configure(CanBusConfig(listen_only=True))
    assert fake.calls[7] == "reset"
    with pytest.raises(ValueError, match="listen-only"):
        device.send(CanFrame(0x123))


def test_start_failure_stops_channel(box):
    device, fake = box
    device.open()
    fake.fail_start = True
    with pytest.raises(OSError, match="start failed"):
        device.configure(CanBusConfig())
    assert fake.calls[-1] == "reset"
    with pytest.raises(RuntimeError, match="configure"):
        device.send(CanFrame(1))


def test_close_attempts_device_even_when_reset_fails(box):
    device, fake = box
    device.open()
    device.configure(CanBusConfig())
    fake.fail_reset = True
    with pytest.raises(RuntimeError, match="close failed"):
        device.close()
    assert fake.calls[-2:] == ["reset", "close"]


def test_send_fd_brs_and_classic_remote(box):
    device, fake = box
    device.open()
    device.configure(CanBusConfig())
    device.send(CanFrame(0x1234567, bytes(range(64)), extended=True, fd=True, brs=True))
    assert fake.tx.frame.can_id == 0x81234567
    assert fake.tx.frame.flags == abi.CANFD_BRS and fake.tx.frame.length == 64
    assert bytes(fake.tx.frame.data) == bytes(range(64))
    assert fake.tx.transmit_type == abi.TRANSMIT_SINGLE
    device.send(CanFrame(0x123, remote=True, dlc=8))
    assert fake.tx.frame.can_id == 0x40000123 and fake.tx.frame.length == 8
    with pytest.raises(NotImplementedError, match="DLC"):
        device.send(CanFrame(0x123, bytes(8), dlc=15))


def test_receive_preserves_timestamp_esi_and_echo(box):
    device, fake = box
    device.open()
    device.configure(CanBusConfig())
    fake.fd_rx = abi.FdRx(timestamp=123456789)
    fake.fd_rx.frame.can_id = 0x81234567
    fake.fd_rx.frame.length = 12
    fake.fd_rx.frame.flags = abi.CANFD_BRS | abi.CANFD_ESI | abi.TX_ECHO_FLAG
    fake.fd_rx.frame.data[:12] = range(12)
    rx = device.receive()
    assert rx.frame == CanFrame(0x1234567, bytes(range(12)), extended=True, fd=True, brs=True)
    assert rx.timestamp_us == 123456789 and rx.error_state_indicator and rx.is_echo
    with pytest.raises(TimeoutError, match="0x00000020"):
        device.receive(timeout_s=0.001)


def test_connection_uses_explicit_channel_and_config_directory(tmp_path):
    settings = {
        "kind": "usb",
        "library": "vendor/zlgcan.dll",
        "device_type": "USBCANFD_200U",
        "device_index": 0,
        "channel": 1,
        "termination": True,
    }
    device = create_zlg_can_box(settings, base=tmp_path)
    assert device.connection.library == tmp_path / "vendor" / "zlgcan.dll"
    assert device.connection.channel == 1
    with pytest.raises(ValueError, match="invalid CAN box"):
        create_zlg_can_box({**settings, "port": 0}, base=tmp_path)
    with pytest.raises(ValueError, match="termination"):
        create_zlg_can_box({**settings, "termination": "false"}, base=tmp_path)
    environment = {"ET_INSTRUMENT_CAN_BOX_" + k.upper(): str(v) for k, v in settings.items()}
    environment["ET_INSTRUMENT_CAN_BOX_DRIVER"] = "zlg_can"
    from_env = create_zlg_can_box_from_environment(
        environment, device_name="can_box", base=tmp_path
    )
    assert from_env.connection == device.connection


def test_cli_check_does_not_open_hardware_and_info_requires_confirmation(
    tmp_path, monkeypatch, capsys
):
    library = tmp_path / "zlgcan.dll"
    library.touch()
    config = {
        "pipeline": {"confirm_hardware_actions": False},
        "instruments": {
            "can_box": {
                "enabled": True,
                "driver": "zlg_can",
                "connection": {
                    "kind": "usb",
                    "library": "zlgcan.dll",
                    "device_type": "USBCANFD_200U",
                    "device_index": 0,
                    "channel": 1,
                    "termination": True,
                },
            }
        },
    }
    path = tmp_path / "run_config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    fake = FakeZlg()
    monkeypatch.setattr(abi, "load_library", lambda path: fake)
    assert main(["--config", str(path)]) == 0
    assert fake.calls == []
    assert main(["--config", str(path), "--action", "info"]) == 1
    assert fake.calls == []
    config["pipeline"]["confirm_hardware_actions"] = True
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert main(["--config", str(path), "--action", "info"]) == 0
    assert fake.calls == ["open", "close"]
    assert "BOX01" in capsys.readouterr().out
