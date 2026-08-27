# DP711、B&K 9130B、DM3068 参数契约与 Typed Operations 无硬件测试。
#
# 职责：验证三台仪器的组合配置在首条写入前校验参数，并检查 driver.operations 的可见命令顺序。
# 边界：只证明软件命令契约，不模拟真实电源输出、DMM 测量精度、保护动作或 HIL 行为。
# 依赖：仅依赖三台仪器公共 API、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.dmms.dm3068 import (
    Dm3068BasicMeasurementFunction,
    Dm3068Driver,
    Dm3068MeasurementConfig,
    Dm3068MeasurementMode,
    Dm3068Rate,
)
from et_test_platform.instruments.power_supplies.bk9130b import (
    Bk9130bChannel,
    Bk9130bChannelConfig,
    Bk9130bDriver,
)
from et_test_platform.instruments.power_supplies.dp711 import (
    Dp711Driver,
    Dp711OutputConfig,
)


# 提供三台仪器测试共用的脚本化字节 Transport；不模拟真实仪器状态机。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:instrument-hardening"

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
        current = self._pending.popleft()
        if len(current) <= max_bytes:
            return current
        self._pending.appendleft(current[max_bytes:])
        return current[:max_bytes]


def test_dp711_typed_output_config_validates_before_write_and_is_visible() -> None:
    transport = ScriptedTransport()
    driver = Dp711Driver(ScpiSession(transport))

    with pytest.raises(ValueError):
        driver.operations.configure_output(Dp711OutputConfig(voltage_v=31.0, current_a=1.0))
    assert transport.writes == []

    driver.operations.configure_output(
        Dp711OutputConfig(
            voltage_v=5.0,
            current_a=1.0,
            ocp_limit_a=1.5,
            ovp_limit_v=6.0,
        )
    )
    assert transport.writes == [
        b":OUTPut:STATe CH1,OFF\n",
        b":SOURce1:CURRent:PROTection 1.5\n",
        b":SOURce1:CURRent:PROTection:STATe ON\n",
        b":SOURce1:VOLTage:PROTection 6\n",
        b":SOURce1:VOLTage:PROTection:STATe ON\n",
        b":SOURce1:VOLTage 5\n",
        b":SOURce1:CURRent 1\n",
        b":OUTPut:STATe CH1,ON\n",
    ]


def test_bk9130b_typed_channel_config_enforces_ch3_limit_before_write() -> None:
    transport = ScriptedTransport()
    driver = Bk9130bDriver(ScpiSession(transport))

    with pytest.raises(ValueError):
        driver.operations.configure_channel(
            Bk9130bChannelConfig(channel=Bk9130bChannel.CH3, voltage_v=5.1, current_a=1.0)
        )
    assert transport.writes == []

    driver.operations.configure_channel(
        Bk9130bChannelConfig(
            channel=Bk9130bChannel.CH3,
            voltage_v=5.0,
            current_a=1.0,
            ovp_limit_v=5.0,
            ovp_enabled=True,
        )
    )
    assert transport.writes == [
        b"INSTrument:SELect CH3\n",
        b"CHANnel:OUTPut:STATe OFF\n",
        b"VOLTage:LEVel 5\n",
        b"CURRent:LEVel 1\n",
        b"VOLTage:PROTection:LEVel 5\n",
        b"VOLTage:PROTection:STATe ON\n",
        b"CHANnel:OUTPut:STATe ON\n",
    ]


def test_bk9130b_typed_measurement_snapshots() -> None:
    responses = {
        b"MEASure:SCALar:VOLTage:ALL:DC?\n": b"5.0,12.0,3.3\n",
        b"MEASure:SCALar:CURRent:ALL:DC?\n": b"1.0,0.5,0.2\n",
    }
    transport = ScriptedTransport(responses)
    driver = Bk9130bDriver(ScpiSession(transport))

    result = driver.operations.read_all_outputs()

    assert result.voltages_v == pytest.approx((5.0, 12.0, 3.3))
    assert result.currents_a == pytest.approx((1.0, 0.5, 0.2))


def test_dm3068_typed_measurement_config_and_reading() -> None:
    responses = {b":MEASure:VOLTage:DC?\r\n": b"3.3000\r\n"}
    transport = ScriptedTransport(responses)
    driver = Dm3068Driver(ScpiSession(transport, terminator=b"\r\n"))

    with pytest.raises(ValueError):
        driver.operations.configure_measurement(
            Dm3068MeasurementConfig(
                function=Dm3068BasicMeasurementFunction.VOLTAGE_DC,
                range_value=-1,
            )
        )
    assert transport.writes == []

    config = Dm3068MeasurementConfig(
        function=Dm3068BasicMeasurementFunction.VOLTAGE_DC,
        range_value=2,
        rate=Dm3068Rate.SLOW,
    )
    result = driver.operations.configure_and_read(config)

    assert result.function is Dm3068BasicMeasurementFunction.VOLTAGE_DC
    assert result.value == pytest.approx(3.3)
    assert transport.writes == [
        b":FUNCtion:VOLTage:DC\r\n",
        b":MEASure:VOLTage:DC 2\r\n",
        b":RATE:VOLTage:DC S\r\n",
        b":MEASure:VOLTage:DC?\r\n",
    ]


def test_dm3068_measurement_mode_contract_rejects_unknown_mode_before_write() -> None:
    transport = ScriptedTransport()
    driver = Dm3068Driver(ScpiSession(transport, terminator=b"\r\n"))

    driver.measurement.mode_set(Dm3068MeasurementMode.AUTO)
    with pytest.raises(ValueError):
        driver.measurement.mode_set("BAD")

    assert transport.writes == [b":MEASure AUTO\r\n"]


def test_all_three_drivers_expose_operations_without_constructor_io() -> None:
    for driver_type, terminator in (
        (Dp711Driver, b"\n"),
        (Bk9130bDriver, b"\n"),
        (Dm3068Driver, b"\r\n"),
    ):
        transport = ScriptedTransport()
        driver = driver_type(ScpiSession(transport, terminator=terminator))
        assert driver.operations is not None
        assert transport.writes == []
