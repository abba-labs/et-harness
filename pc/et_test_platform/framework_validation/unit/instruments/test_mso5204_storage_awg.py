# RIGOL MSO5204 存储、搜索与 AWG 无硬件协议测试。
#
# 职责：验证 Record、Reference、Save/Load、Search、AWG 原子 API 的 SCPI 映射和数量。
# 边界：只验证软件命令契约，不模拟真实存储介质、搜索状态机、AWG 输出或示波器采集行为。
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
        return "scripted:mso5204-storage-awg"

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


def test_record_reference_and_storage_mapping() -> None:
    responses = {
        b":RECord:FRAMes?\n": b"300\n",
        b":REFerence:DISPlay? 2\n": b"1\n",
        b":SAVE:IMAGe:TYPE?\n": b"PNG\n",
    }
    driver, transport = _driver(responses)

    driver.record.enabled_set(True)
    driver.record.frames_set(300)
    assert driver.record.frames_get() == 300
    driver.reference.display_set(2, True)
    assert driver.reference.display_get(2) is True
    driver.reference.label_content_set(2, "REF2")
    driver.save_load.image_type_set("PNG")
    assert driver.save_load.image_type_get() == "PNG"
    driver.save_load.setup_save(r"D:\scope.stp")

    assert transport.writes == [
        b":RECord:ENABle ON\n",
        b":RECord:FRAMes 300\n",
        b":RECord:FRAMes?\n",
        b":REFerence:DISPlay 2,ON\n",
        b":REFerence:DISPlay? 2\n",
        b":REFerence:LABel:CONTent 2,REF2\n",
        b":SAVE:IMAGe:TYPE PNG\n",
        b":SAVE:IMAGe:TYPE?\n",
        b":SAVE:SETup D:\\scope.stp\n",
    ]


def test_search_mapping() -> None:
    responses = {
        b":SEARch:COUNt?\n": b"12\n",
        b":SEARch:EDGE:THReshold?\n": b"1.250000E+0\n",
        b":SEARch:RUNT:WUPPer?\n": b"2.000000E-6\n",
    }
    driver, transport = _driver(responses)

    driver.search.enabled_set(True)
    driver.search.mode_set("EDGE")
    driver.search.edge_threshold_set(1.25)
    assert driver.search.edge_threshold_get() == pytest.approx(1.25)
    driver.search.runt_upper_width_set(2e-6)
    assert driver.search.runt_upper_width_get() == pytest.approx(2e-6)
    assert driver.search.count_get() == 12

    assert transport.writes == [
        b":SEARch:STATe ON\n",
        b":SEARch:MODE EDGE\n",
        b":SEARch:EDGE:THReshold 1.25\n",
        b":SEARch:EDGE:THReshold?\n",
        b":SEARch:RUNT:WUPPer 2e-06\n",
        b":SEARch:RUNT:WUPPer?\n",
        b":SEARch:COUNt?\n",
    ]


def test_awg_mapping_and_apply() -> None:
    responses = {
        b":SOURce2:FREQuency?\n": b"1.000000E+6\n",
        b":SOURce2:OUTPut?\n": b"1\n",
        b":SOURce2:APPLy?\n": b"SIN,1000000,2,0,90\n",
    }
    driver, transport = _driver(responses)

    driver.source.function_set(2, "SINusoid")
    driver.source.frequency_set(2, 1e6)
    assert driver.source.frequency_get(2) == pytest.approx(1e6)
    driver.source.output_enabled_set(2, True)
    assert driver.source.output_enabled_get(2) is True
    driver.source.apply_sine(2, 1e6, 2.0, 0.0, 90.0)
    assert driver.source.apply_get(2).startswith("SIN")

    assert transport.writes == [
        b":SOURce2:FUNCtion SINusoid\n",
        b":SOURce2:FREQuency 1000000\n",
        b":SOURce2:FREQuency?\n",
        b":SOURce2:OUTPut ON\n",
        b":SOURce2:OUTPut?\n",
        b":SOURce2:APPLy:SINusoid 1000000,2,0,90\n",
        b":SOURce2:APPLy?\n",
    ]


def test_validation_rejects_bad_inputs() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.reference.display_set(11, True)
    with pytest.raises(ValueError):
        driver.record.frames_set(0)
    with pytest.raises(ValueError):
        driver.save_load.setup_load("")
    with pytest.raises(ValueError):
        driver.source.frequency_set(3, 1e3)
    with pytest.raises(ValueError):
        driver.source.apply_sine(1, None, 1.0)

    assert transport.writes == []


def test_batch3_api_inventory() -> None:
    driver, _ = _driver()
    expected = {
        "record": 10,
        "reference": 17,
        "save_load": 16,
        "search": 54,
        "source": 54,
    }
    actual = {name: len(_public_methods(getattr(driver, name))) for name in expected}
    assert actual == expected
    assert sum(actual.values()) == 151
