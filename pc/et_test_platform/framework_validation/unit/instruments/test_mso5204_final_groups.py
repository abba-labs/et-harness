# RIGOL MSO5204 最终命令组无硬件协议测试。
#
# 职责：验证 Bode、LAN、Power、Quick、Trace 原子 API 的 SCPI 映射、参数校验和数量。
# 边界：只验证软件命令契约，不模拟真实示波器、网络、AWG、Bode 或 Power Analysis 行为。
# 依赖：仅依赖 MSO5204 Driver、公共 ScpiSession、ByteTransport 和 pytest。
from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes.mso5204.driver import Mso5204Driver


class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:mso5204-final-groups"

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def write(self, data: bytes, *, timeout_s: float | None = None) -> None:
        self.writes.append(data)
        response = self.responses.get(data)
        if response is not None:
            self._pending.append(response)

    def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        if not self._pending:
            return b""
        data = self._pending.popleft()
        if len(data) <= max_bytes:
            return data
        self._pending.appendleft(data[max_bytes:])
        return data[:max_bytes]


def _driver(
    responses: dict[bytes, bytes] | None = None,
) -> tuple[Mso5204Driver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Mso5204Driver(ScpiSession(transport)), transport


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


def test_bodeplot_mapping() -> None:
    responses = {
        b":BODeplot:POINT?\n": b"30\n",
        b":BODeplot:VOLTage? F1MHZ\n": b"1.000000E+0\n",
        b":BODeplot:GMARgin?\n": b"1.250000E+1\n",
    }
    driver, transport = _driver(responses)

    driver.bodeplot.enabled_set(True)
    driver.bodeplot.start_frequency_set(10.0)
    driver.bodeplot.stop_frequency_set(1e6)
    driver.bodeplot.points_per_decade_set(30)
    assert driver.bodeplot.points_per_decade_get() == 30
    driver.bodeplot.voltage_set(1.0, "F1MHZ")
    assert driver.bodeplot.voltage_get("F1MHZ") == pytest.approx(1.0)
    assert driver.bodeplot.gain_margin_get() == pytest.approx(12.5)

    assert transport.writes == [
        b":BODeplot:ENABle ON\n",
        b":BODeplot:STARt 10\n",
        b":BODeplot:STOP 1000000\n",
        b":BODeplot:POINT 30\n",
        b":BODeplot:POINT?\n",
        b":BODeplot:VOLTage 1,F1MHZ\n",
        b":BODeplot:VOLTage? F1MHZ\n",
        b":BODeplot:GMARgin?\n",
    ]


def test_lan_power_and_quick_mapping() -> None:
    responses = {
        b":LAN:IPADdress?\n": b"192.168.1.10\n",
        b":POWer:TYPE?\n": b"QUAL\n",
        b":QUICk:OPERation?\n": b"SWAV\n",
    }
    driver, transport = _driver(responses)

    driver.lan.manual_ip_set(True)
    driver.lan.ip_address_set("192.168.1.10")
    assert driver.lan.ip_address_get() == "192.168.1.10"
    driver.lan.apply()
    driver.power.analysis_type_set("QUALity")
    assert driver.power.analysis_type_get() == "QUAL"
    driver.quick.operation_set("SWAVe")
    assert driver.quick.operation_get() == "SWAV"

    assert transport.writes == [
        b":LAN:MANual ON\n",
        b":LAN:IPADdress 192.168.1.10\n",
        b":LAN:IPADdress?\n",
        b":LAN:APPLy\n",
        b":POWer:TYPE QUALity\n",
        b":POWer:TYPE?\n",
        b":QUICk:OPERation SWAVe\n",
        b":QUICk:OPERation?\n",
    ]


def test_trace_dac16_binary_block_mapping() -> None:
    driver, transport = _driver()

    driver.trace.dac16_data_set(2, b"\x00\x00\xff?\x01\x00\x02\x00")

    assert transport.writes == [
        b":TRACe2:DATA:DAC16 volatile,END,#18\x00\x00\xff?\x01\x00\x02\x00\n"
    ]


def test_final_group_validation_rejects_bad_inputs() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.bodeplot.points_per_decade_set(9)
    with pytest.raises(ValueError):
        driver.trace.dac16_data_set(3, b"\x00\x00\x00\x00")
    with pytest.raises(ValueError):
        driver.trace.dac16_data_set(1, b"\x00\x00\x00")

    assert transport.writes == []


def test_final_group_api_inventory() -> None:
    driver, _ = _driver()
    expected = {
        "bodeplot": 28,
        "lan": 25,
        "power": 16,
        "quick": 2,
        "trace": 1,
    }
    actual = {name: len(_public_methods(getattr(driver, name))) for name in expected}
    assert actual == expected
    assert sum(actual.values()) == 72
