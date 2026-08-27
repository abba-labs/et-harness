# RIGOL DM3068 无硬件协议单元测试。
#
# 职责：验证关键原子 API 的 SCPI 映射、响应解析、Operations、参数校验和 183 项公共 API 规模。
# 边界：只验证软件命令契约，不模拟或证明真实 DM3068 仪器行为。
# 依赖：仅依赖 DM3068 Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.dmms.dm3068.driver import Dm3068Driver
from et_test_platform.instruments.dmms.dm3068.models import (
    Dm3068CommandSet,
    Dm3068Parity,
    Dm3068RangeKeyword,
    Dm3068Rate,
    Dm3068TriggerSource,
    Dm3068VmcPolarity,
)
from et_test_platform.instruments.dmms.dm3068.operations import (
    configure_dc_voltage,
    configure_external_trigger,
)


# 提供测试内可脚本化字节 Transport；不模拟真实仪器时序、量程切换或触发行为。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:dm3068"

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


def _driver(
    responses: dict[bytes, bytes] | None = None,
) -> tuple[Dm3068Driver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Dm3068Driver(ScpiSession(transport, terminator=b"\r\n")), transport


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


# 验证 Common/System 命令映射、CRLF 结束符以及关键结构化响应解析。
def test_common_and_system_mapping() -> None:
    responses = {
        b"CMDSet?\r\n": b"RIGOL\r\n",
        b"*IDN?\r\n": b"RIGOL TECHNOLOGIES,DM3068,DM3A123456789,01.01.00\r\n",
        b":SYSTem:ERRor?\r\n": b'-113,"Undefined header"\r\n',
        b":SYSTem:BEEPer:STATe?\r\n": b"1\r\n",
    }
    driver, transport = _driver(responses)

    driver.common.command_set_set(Dm3068CommandSet.RIGOL)
    assert driver.common.command_set_get() == "RIGOL"
    assert driver.common.identity_get().model == "DM3068"
    assert driver.system.error_get().code == -113
    driver.system.beeper_state_set(True)
    assert driver.system.beeper_state_get() is True

    assert transport.writes == [
        b"CMDSet RIGOL\r\n",
        b"CMDSet?\r\n",
        b"*IDN?\r\n",
        b":SYSTem:ERRor?\r\n",
        b":SYSTem:BEEPer:STATe ON\r\n",
        b":SYSTem:BEEPer:STATe?\r\n",
    ]


# 验证基础功能、量程、速率和测量查询保持彼此独立的一条命令语义。
def test_measurement_function_and_rate_mapping() -> None:
    responses = {
        b":MEASure:VOLTage:DC?\r\n": b"3.299812E+00\r\n",
        b":MEASure:VOLTage:DC:RANGe?\r\n": b"2\r\n",
        b":RATE:VOLTage:DC?\r\n": b"M\r\n",
    }
    driver, transport = _driver(responses)

    driver.function.voltage_dc_select()
    driver.measurement.voltage_dc_range_set(Dm3068RangeKeyword.DEFAULT)
    driver.rate.voltage_dc_set(Dm3068Rate.MEDIUM)
    assert driver.measurement.voltage_dc_get() == pytest.approx(3.299812)
    assert driver.measurement.voltage_dc_range_get() == 2
    assert driver.rate.voltage_dc_get() == "M"

    assert transport.writes == [
        b":FUNCtion:VOLTage:DC\r\n",
        b":MEASure:VOLTage:DC DEF\r\n",
        b":RATE:VOLTage:DC M\r\n",
        b":MEASure:VOLTage:DC?\r\n",
        b":MEASure:VOLTage:DC:RANGe?\r\n",
        b":RATE:VOLTage:DC?\r\n",
    ]


# 验证数学、触发和接口参数均由各自 Control 直接发送，不隐藏额外配置动作。
def test_calculate_trigger_and_interface_mapping() -> None:
    responses = {
        b":CALCulate:REL:OFFSet?\r\n": b"1.25\r\n",
        b":TRIGger:SOURce?\r\n": b"EXT\r\n",
        b":TRIGger:VMComplete:PULSewidth?\r\n": b"10\r\n",
        b":UTILity:INTErface:RS232:BAUD?\r\n": b"115200\r\n",
    }
    driver, transport = _driver(responses)

    driver.calculate.relative_offset_set(1.25)
    assert driver.calculate.relative_offset_get() == pytest.approx(1.25)
    driver.trigger.source_set(Dm3068TriggerSource.EXTERNAL)
    assert driver.trigger.source_get() == "EXT"
    driver.trigger.vmc_polarity_set(Dm3068VmcPolarity.POSITIVE)
    driver.trigger.vmc_pulse_width_set(10)
    assert driver.trigger.vmc_pulse_width_get() == 10
    driver.interface.rs232_baudrate_set(115200)
    assert driver.interface.rs232_baudrate_get() == 115200
    driver.interface.rs232_parity_set(Dm3068Parity.EVEN)

    assert transport.writes == [
        b":CALCulate:REL:OFFSet 1.25\r\n",
        b":CALCulate:REL:OFFSet?\r\n",
        b":TRIGger:SOURce EXT\r\n",
        b":TRIGger:SOURce?\r\n",
        b":TRIGger:VMComplete:POLAr POS\r\n",
        b":TRIGger:VMComplete:PULSewidth 10\r\n",
        b":TRIGger:VMComplete:PULSewidth?\r\n",
        b":UTILity:INTErface:RS232:BAUD 115200\r\n",
        b":UTILity:INTErface:RS232:BAUD?\r\n",
        b":UTILity:INTErface:RS232:PARIty EVEN\r\n",
    ]


# 验证双显示原生接口使用 DM3068 原生 FUNCtion2 命令，不扩展兼容命令集。
def test_secondary_display_mapping() -> None:
    responses = {
        b":FUNCtion2?\r\n": b"FREQ\r\n",
        b":FUNCtion2:ON?\r\n": b"1\r\n",
        b":FUNCtion2:VALUe1?\r\n": b"1000.0\r\n",
        b":FUNCtion2:VALUe2?\r\n": b"3.3\r\n",
    }
    driver, transport = _driver(responses)

    driver.secondary_display.frequency_select()
    assert driver.secondary_display.function_get() == "FREQ"
    assert driver.secondary_display.enabled_get() is True
    assert driver.secondary_display.value1_get() == pytest.approx(1000.0)
    assert driver.secondary_display.value2_get() == pytest.approx(3.3)
    driver.secondary_display.clear()

    assert transport.writes == [
        b":FUNCtion2:FREQuency\r\n",
        b":FUNCtion2?\r\n",
        b":FUNCtion2:ON?\r\n",
        b":FUNCtion2:VALUe1?\r\n",
        b":FUNCtion2:VALUe2?\r\n",
        b":FUNCtion2:CLEar\r\n",
    ]


# 验证 Operations 只按可见顺序复用原子 API，并且不会产生额外隐藏 SCPI。
def test_operations_compose_atomic_calls() -> None:
    driver, transport = _driver()

    configure_dc_voltage(driver)
    configure_external_trigger(driver, "RISE")

    assert transport.writes == [
        b":FUNCtion:VOLTage:DC\r\n",
        b":MEASure:VOLTage:DC DEF\r\n",
        b":RATE:VOLTage:DC M\r\n",
        b":TRIGger:SOURce EXT\r\n",
        b":TRIGger:EXT RISE\r\n",
    ]


# 验证手册明确范围约束和字符串安全检查会在任何写入发生前拒绝非法输入。
def test_validation_rejects_invalid_atomic_parameters_before_write() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.interface.rs232_baudrate_set(7200)
    with pytest.raises(ValueError):
        driver.measurement.voltage_dc_range_set(-1)
    with pytest.raises(ValueError):
        driver.measurement.mode_set("BAD\nCOMMAND")

    assert transport.writes == []


# 固化 Common + RIGOL 原生命令体系 183 个稳定原子 API 的能力组规模和关键公共入口。
def test_dm3068_public_api_inventory_matches_native_manual_scope() -> None:
    driver, _ = _driver()
    expected_counts = {
        "common": 18,
        "status": 9,
        "calculate": 29,
        "function": 12,
        "secondary_display": 6,
        "measurement": 34,
        "rate": 14,
        "system": 24,
        "trigger": 17,
        "interface": 20,
    }
    actual = {group: len(_public_methods(getattr(driver, group))) for group in expected_counts}
    assert actual == expected_counts
    assert sum(actual.values()) == 183
    assert {"identity_get", "reset", "self_test_get"} <= _public_methods(driver.common)
    assert {"voltage_dc_get", "frequency_get", "capacitance_get"} <= _public_methods(
        driver.measurement
    )
    assert {"source_set", "single_trigger", "external_mode_set"} <= _public_methods(driver.trigger)
