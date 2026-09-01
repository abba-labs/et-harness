# DP711 无硬件协议单元测试。
#
# 职责：验证关键原子 API 的 SCPI 映射、二进制块解析、组合操作和 108 项公共 API 规模。
# 边界：只验证软件命令契约，不模拟或证明真实 DP711 硬件行为。
# 依赖：仅依赖 DP711 Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.power_supplies.dp711.driver import Dp711Driver
from et_test_platform.instruments.power_supplies.dp711.models import (
    Dp711FileType,
    Dp711OutputMode,
    Dp711Parity,
    Dp711TimerEndState,
    Dp711TimerTriggerMode,
)
from et_test_platform.instruments.power_supplies.dp711.operations import Dp711Operations


# 提供测试内可脚本化字节 Transport；不模拟真实仪器时序。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:dp711"

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
) -> tuple[Dp711Driver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Dp711Driver(ScpiSession(transport)), transport


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


# 验证文本响应和 definite-length block 都由公共 SCPI 会话完整读取。
def test_scpi_session_and_basic_mapping() -> None:
    responses = {
        b"*IDN?\n": b"RIGOL TECHNOLOGIES,DP711,SN1,00.01.02\n",
        b":BIN?\n": b"#211hello world\n",
        b":APPLy? CH1\n": b"5.00,1.00\n",
        b"*OPT?\n": b"DP7-TRIGGER,DP7-TIMER,0\n",
    }
    driver, transport = _driver(responses)

    assert driver.basic.identity_get().model == "DP711"
    assert driver._session.query_bytes(":BIN?") == b"hello world"
    driver.basic.apply_set(5.0, 1.0)
    assert driver.basic.apply_get().voltage_v == pytest.approx(5.0)
    assert driver.basic.options_get().timer is True

    assert transport.writes == [
        b"*IDN?\n",
        b":BIN?\n",
        b":APPLy CH1,5,1\n",
        b":APPLy? CH1\n",
        b"*OPT?\n",
    ]


# 验证测量、Memory、OUTPut 和 SOURce 的关键命令映射保持原子语义。
def test_measurement_memory_output_and_source_mapping() -> None:
    responses = {
        b":MEASure:ALL? CH1\n": b"5.001,0.500,2.5005\n",
        b":MEMory:LOCK? RSF,2\n": b"YES\n",
        b":OUTPut:MODE? CH1\n": b"CV\n",
        b":SOURce1:VOLTage?\n": b"12.0\n",
        b":SOURce1:CURRent?\n": b"1.5\n",
    }
    driver, transport = _driver(responses)

    measurement = driver.measurement.all_get()
    assert measurement.power_w == pytest.approx(2.5005)
    driver.memory.store(Dp711FileType.STATE, 2)
    assert driver.memory.locked_get(Dp711FileType.STATE, 2) is True
    assert driver.output.mode_get() is Dp711OutputMode.CONSTANT_VOLTAGE
    driver.source.voltage_set(12.0)
    driver.source.current_set(1.5)
    assert driver.source.voltage_get() == pytest.approx(12.0)
    assert driver.source.current_get() == pytest.approx(1.5)

    assert transport.writes == [
        b":MEASure:ALL? CH1\n",
        b":MEMory:STORe RSF,2\n",
        b":MEMory:LOCK? RSF,2\n",
        b":OUTPut:MODE? CH1\n",
        b":SOURce1:VOLTage 12\n",
        b":SOURce1:CURRent 1.5\n",
        b":SOURce1:VOLTage?\n",
        b":SOURce1:CURRent?\n",
    ]


# 验证 System 的串口设置与错误查询不会隐藏重连或其他仪器动作。
def test_system_mapping() -> None:
    responses = {
        b":SYSTem:COMMunicate:RS232:BAUD?\n": b"9600\n",
        b":SYSTem:COMMunicate:RS232:PARItybit?\n": b"NONE\n",
        b":SYSTem:ERRor?\n": b'-113,"Undefined header"\n',
    }
    driver, transport = _driver(responses)

    assert driver.system.rs232_baudrate_get() == 9600
    assert driver.system.rs232_parity_get() is Dp711Parity.NONE
    assert driver.system.error_get().code == -113
    driver.system.rs232_baudrate_set(115200)

    assert transport.writes[-1] == b":SYSTem:COMMunicate:RS232:BAUD 115200\n"


# 验证 Timer 参数、二进制块查询和触发模式按手册命令独立执行。
def test_timer_mapping() -> None:
    responses = {
        b":TIMEr:CYCLEs?\n": b"N,2\n",
        b":TIMEr:ENDState?\n": b"LAST\n",
        b":TIMEr:PARAmeter? 1,2\n": b"#90000000361,20.00,2.00,5.00;2,18.00,1.80,3.00;\n",
        b":TIMEr:TRIGger?\n": b"SINGLE\n",
    }
    driver, transport = _driver(responses)

    driver.timer.cycles_set(2)
    assert driver.timer.cycles_get() == 2
    driver.timer.end_state_set(Dp711TimerEndState.LAST)
    assert driver.timer.end_state_get() is Dp711TimerEndState.LAST
    driver.timer.parameter_set(1, 20.0, 2.0, 5.0)
    assert [step.group for step in driver.timer.parameter_get(1, 2)] == [1, 2]
    driver.timer.trigger_mode_set(Dp711TimerTriggerMode.SINGLE)
    assert driver.timer.trigger_mode_get() is Dp711TimerTriggerMode.SINGLE

    assert b":TIMEr:PARAmeter 1,20,2,5\n" in transport.writes


# 验证常用组合只复用公开原子 API，并保持清晰可见的动作顺序。
def test_operations_compose_atomic_driver_calls() -> None:
    driver, transport = _driver()
    operations = Dp711Operations(driver)

    operations.configure_and_enable(5.0, 1.0)
    operations.safe_output_off(clear_protection=True)

    assert transport.writes == [
        b":SOURce1:VOLTage 5\n",
        b":SOURce1:CURRent 1\n",
        b":OUTPut:STATe CH1,ON\n",
        b":OUTPut:STATe CH1,OFF\n",
        b":OUTPut:OCP:CLEAR CH1\n",
        b":OUTPut:OVP:CLEAR CH1\n",
    ]


# 固化 Programming Guide 的 108 个规范化原子 API 数量，并检查各能力组关键入口存在。
def test_dp711_public_api_inventory_matches_manual() -> None:
    driver, _ = _driver()
    expected_counts = {
        "basic": 15,
        "measurement": 4,
        "memory": 6,
        "output": 18,
        "source": 16,
        "system": 37,
        "timer": 12,
    }
    actual = {group: len(_public_methods(getattr(driver, group))) for group in expected_counts}
    assert actual == expected_counts
    assert sum(actual.values()) == 108
    assert {"identity_get", "apply_set", "options_get"} <= _public_methods(driver.basic)
    assert {"enabled_set", "ovp_clear", "ocp_clear"} <= _public_methods(driver.output)
    assert {"voltage_set", "current_set"} <= _public_methods(driver.source)
