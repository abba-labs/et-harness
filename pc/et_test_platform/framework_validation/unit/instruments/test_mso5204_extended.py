# RIGOL MSO5204 高级触发与总线解码无硬件协议测试。
#
# 职责：验证 Advanced Trigger、Protocol Trigger 和 BUS 全量命令注册表的 SCPI 映射与 API 数量。
# 边界：只验证软件命令契约，不模拟真实触发、协议解码、选件授权或模拟输入行为。
# 依赖：仅依赖 MSO5204 Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes.mso5204.driver import Mso5204Driver


# 提供高级触发和 BUS 测试所需的脚本化字节 Transport，不模拟真实示波器状态机。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:mso5204-extended"

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
) -> tuple[Mso5204Driver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Mso5204Driver(ScpiSession(transport)), transport


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


# 验证 PULSE、PATTERN、DURATION 和 Nth EDGE 高级触发仍保持一项设置对应一条 SCPI。
def test_advanced_trigger_mapping() -> None:
    responses = {
        b":TRIGger:PULSe:UWIDth?\n": b"3.000000E-6\n",
        b":TRIGger:PATTern:PATTern?\n": b"H,R,L,X,X,X,X,X,X,X,X,X,X,X,X,X,X,X,X,X\n",
        b":TRIGger:DURation:LEVel? CHANnel2\n": b"1.600000E-1\n",
        b":TRIGger:NEDGe:EDGE?\n": b"20\n",
    }
    driver, transport = _driver(responses)

    driver.trigger_advanced.pulse_condition_set("LESS")
    driver.trigger_advanced.pulse_upper_width_set(3e-6)
    assert driver.trigger_advanced.pulse_upper_width_get() == pytest.approx(3e-6)
    driver.trigger_advanced.pattern_values_set(("H", "R", "L", "X"))
    assert driver.trigger_advanced.pattern_values_get()[:4] == ("H", "R", "L", "X")
    driver.trigger_advanced.duration_level_set("CHANnel2", 0.16)
    assert driver.trigger_advanced.duration_level_get("CHANnel2") == pytest.approx(0.16)
    driver.trigger_advanced.nth_edge_count_set(20)
    assert driver.trigger_advanced.nth_edge_count_get() == 20

    assert transport.writes == [
        b":TRIGger:PULSe:WHEN LESS\n",
        b":TRIGger:PULSe:UWIDth 3e-06\n",
        b":TRIGger:PULSe:UWIDth?\n",
        b":TRIGger:PATTern:PATTern H,R,L,X\n",
        b":TRIGger:PATTern:PATTern?\n",
        b":TRIGger:DURation:LEVel CHANnel2,0.16\n",
        b":TRIGger:DURation:LEVel? CHANnel2\n",
        b":TRIGger:NEDGe:EDGE 20\n",
        b":TRIGger:NEDGe:EDGE?\n",
    ]


# 验证 CAN、I2C、SPI、LIN 和 1553 协议触发 API 直接映射手册协议触发命令。
def test_protocol_trigger_mapping() -> None:
    responses = {
        b":TRIGger:CAN:BAUD?\n": b"500000\n",
        b":TRIGger:IIC:ADDRess?\n": b"80\n",
        b":TRIGger:SPI:MODE?\n": b"CS\n",
        b":TRIGger:LIN:ID?\n": b"18\n",
        b":TRIGger:M1553:POLarity?\n": b"POS\n",
    }
    driver, transport = _driver(responses)

    driver.trigger_protocol.can_baud_set(500000)
    assert driver.trigger_protocol.can_baud_get() == 500000
    driver.trigger_protocol.iic_address_set(80)
    assert driver.trigger_protocol.iic_address_get() == 80
    driver.trigger_protocol.spi_mode_set("CS")
    assert driver.trigger_protocol.spi_mode_get() == "CS"
    driver.trigger_protocol.lin_id_set(18)
    assert driver.trigger_protocol.lin_id_get() == 18
    driver.trigger_protocol.m1553_polarity_set("POSitive")
    assert driver.trigger_protocol.m1553_polarity_get() == "POS"

    assert transport.writes == [
        b":TRIGger:CAN:BAUD 500000\n",
        b":TRIGger:CAN:BAUD?\n",
        b":TRIGger:IIC:ADDRess 80\n",
        b":TRIGger:IIC:ADDRess?\n",
        b":TRIGger:SPI:MODE CS\n",
        b":TRIGger:SPI:MODE?\n",
        b":TRIGger:LIN:ID 18\n",
        b":TRIGger:LIN:ID?\n",
        b":TRIGger:M1553:POLarity POSitive\n",
        b":TRIGger:M1553:POLarity?\n",
    ]


# 验证 BUS1..BUS4 公共设置、协议字段、门限和事件表二进制数据均使用独立原子命令。
def test_bus_decode_mapping_and_event_data() -> None:
    responses = {
        b":BUS1:MODE?\n": b"CAN\n",
        b":BUS1:DISPlay?\n": b"1\n",
        b":BUS1:THReshold? CAN\n": b"1.500000E+0\n",
        b":BUS1:CAN:BAUD?\n": b"500000\n",
        b":BUS1:DATA?\n": b"#210CAN,1,2,3\n",
    }
    driver, transport = _driver(responses)

    driver.bus.mode_set(1, "CAN")
    assert driver.bus.mode_get(1) == "CAN"
    driver.bus.display_set(1, True)
    assert driver.bus.display_get(1) is True
    driver.bus.threshold_set(1, "CAN", 1.5)
    assert driver.bus.threshold_get(1, "CAN") == pytest.approx(1.5)
    driver.bus.can_baud_set(1, 500000)
    assert driver.bus.can_baud_get(1) == 500000
    assert driver.bus.event_data_get(1) == b"CAN,1,2,3\n"

    assert transport.writes == [
        b":BUS1:MODE CAN\n",
        b":BUS1:MODE?\n",
        b":BUS1:DISPlay ON\n",
        b":BUS1:DISPlay?\n",
        b":BUS1:THReshold 1.5,CAN\n",
        b":BUS1:THReshold? CAN\n",
        b":BUS1:CAN:BAUD 500000\n",
        b":BUS1:CAN:BAUD?\n",
        b":BUS1:DATA?\n",
    ]


# 验证 BUS 编号与 Pattern Trigger 结构错误会在 Transport 写入前被拒绝。
def test_extended_validation_rejects_invalid_inputs() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.bus.mode_set(5, "CAN")
    with pytest.raises(ValueError):
        driver.trigger_advanced.pattern_values_set(("R", "F"))
    with pytest.raises(ValueError):
        driver.trigger_advanced.duration_pattern_set(("H", "BAD"))

    assert transport.writes == []


# 固化本批次新增的 380 个高级触发和 BUS 原子 API，防止后续重构静默丢失控制能力。
def test_mso5204_extended_api_inventory() -> None:
    driver, _ = _driver()

    assert len(_public_methods(driver.trigger_advanced)) == 134
    assert len(_public_methods(driver.trigger_protocol)) == 120
    assert len(_public_methods(driver.bus)) == 126
    assert 134 + 120 + 126 == 380
