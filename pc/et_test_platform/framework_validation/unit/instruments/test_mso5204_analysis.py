# RIGOL MSO5204 游标、LA、Math、Histogram 和 Mask 无硬件协议测试。
#
# 职责：验证本批分析能力原子 API 的 SCPI 映射、参数校验、响应解析和 API Inventory。
# 边界：只验证软件命令契约，不模拟真实数字探头、FFT、直方图、Mask 或游标硬件行为。
# 依赖：仅依赖 MSO5204 Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes.mso5204.driver import Mso5204Driver


# 提供分析能力测试所需的脚本化字节 Transport；不模拟真实示波器状态机。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:mso5204-analysis"

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


# 验证 Manual、Track 和 XY Cursor 的设置与物理量查询保持单命令映射。
def test_cursor_command_mapping() -> None:
    responses = {
        b":CURSor:MODE?\n": b"MAN\n",
        b":CURSor:MANual:CAX?\n": b"200\n",
        b":CURSor:MANual:AXValue?\n": b"1.250000E-6\n",
        b":CURSor:TRACk:BYValue?\n": b"3.300000E+0\n",
        b":CURSor:XY:BY?\n": b"300\n",
    }
    driver, transport = _driver(responses)

    driver.cursor.mode_set("MANual")
    assert driver.cursor.mode_get() == "MAN"
    driver.cursor.manual_cursor_a_x_set(200)
    assert driver.cursor.manual_cursor_a_x_get() == 200
    assert driver.cursor.manual_cursor_a_x_value_get() == pytest.approx(1.25e-6)
    assert driver.cursor.track_cursor_b_y_value_get() == pytest.approx(3.3)
    driver.cursor.xy_cursor_b_y_set(300)
    assert driver.cursor.xy_cursor_b_y_get() == 300

    assert transport.writes == [
        b":CURSor:MODE MANual\n",
        b":CURSor:MODE?\n",
        b":CURSor:MANual:CAX 200\n",
        b":CURSor:MANual:CAX?\n",
        b":CURSor:MANual:AXValue?\n",
        b":CURSor:TRACk:BYValue?\n",
        b":CURSor:XY:BY 300\n",
        b":CURSor:XY:BY?\n",
    ]


# 验证 Logic Analyzer 数字通道、POD 阈值和用户分组都映射为独立 SCPI 命令。
def test_logic_analyzer_command_mapping() -> None:
    responses = {
        b":LA:STATe?\n": b"1\n",
        b":LA:DIGital:DISPlay? D3\n": b"1\n",
        b":LA:POD1:THReshold?\n": b"1.400000E+0\n",
        b":LA:DIGital:LABel? D0\n": b"ACK\n",
    }
    driver, transport = _driver(responses)

    driver.logic_analyzer.state_set(True)
    assert driver.logic_analyzer.state_get() is True
    driver.logic_analyzer.digital_display_set(3, True)
    assert driver.logic_analyzer.digital_display_get("D3") is True
    driver.logic_analyzer.pod_threshold_set(1, 1.4)
    assert driver.logic_analyzer.pod_threshold_get(1) == pytest.approx(1.4)
    driver.logic_analyzer.digital_label_set(0, "ACK")
    assert driver.logic_analyzer.digital_label_get(0) == "ACK"
    driver.logic_analyzer.group_append("GROup2", (0, 1, 2))

    assert transport.writes == [
        b":LA:STATe ON\n",
        b":LA:STATe?\n",
        b":LA:DIGital:DISPlay D3,ON\n",
        b":LA:DIGital:DISPlay? D3\n",
        b":LA:POD1:THReshold 1.4\n",
        b":LA:POD1:THReshold?\n",
        b":LA:DIGital:LABel D0,ACK\n",
        b":LA:DIGital:LABel? D0\n",
        b":LA:GROup:APPend GROup2,D0,D1,D2\n",
    ]


# 验证 Math、FFT、Filter 和逻辑运算参数均由对应原子 API 单独控制。
def test_math_command_mapping() -> None:
    responses = {
        b":MATH1:OPERator?\n": b"FFT\n",
        b":MATH1:FFT:WINDow?\n": b"HANN\n",
        b":MATH1:FFT:SEARch:NUM?\n": b"5\n",
        b":MATH2:DISTance?\n": b"20\n",
        b":MATH2:THReshold3?\n": b"8.000000E-1\n",
    }
    driver, transport = _driver(responses)

    driver.math.operator_set(1, "FFT")
    assert driver.math.operator_get(1) == "FFT"
    driver.math.fft_window_set(1, "HANNing")
    assert driver.math.fft_window_get(1) == "HANN"
    driver.math.fft_search_count_set(1, 5)
    assert driver.math.fft_search_count_get(1) == 5
    driver.math.distance_set(2, 20)
    assert driver.math.distance_get(2) == 20
    driver.math.threshold_3_set(2, 0.8)
    assert driver.math.threshold_3_get(2) == pytest.approx(0.8)

    assert transport.writes == [
        b":MATH1:OPERator FFT\n",
        b":MATH1:OPERator?\n",
        b":MATH1:FFT:WINDow HANNing\n",
        b":MATH1:FFT:WINDow?\n",
        b":MATH1:FFT:SEARch:NUM 5\n",
        b":MATH1:FFT:SEARch:NUM?\n",
        b":MATH2:DISTance 20\n",
        b":MATH2:DISTance?\n",
        b":MATH2:THReshold3 0.8\n",
        b":MATH2:THReshold3?\n",
    ]


# 验证 Histogram 与 Mask 的边界、统计查询和运行控制彼此独立且不隐藏联动动作。
def test_histogram_and_mask_command_mapping() -> None:
    responses = {
        b":HISTogram:SIZE?\n": b"2\n",
        b":HISTogram:BLIMit?\n": b"-2.000000E+0\n",
        b":MASK:OPERate?\n": b"RUN\n",
        b":MASK:PASSed?\n": b"123\n",
        b":MASK:FAILed?\n": b"4\n",
        b":MASK:TOTal?\n": b"127\n",
    }
    driver, transport = _driver(responses)

    driver.histogram.size_set(2)
    assert driver.histogram.size_get() == 2
    driver.histogram.bottom_limit_set(-2.0)
    assert driver.histogram.bottom_limit_get() == pytest.approx(-2.0)
    driver.mask.operate_set("RUN")
    assert driver.mask.operate_get() == "RUN"
    assert driver.mask.passed_count_get() == 123
    assert driver.mask.failed_count_get() == 4
    assert driver.mask.total_count_get() == 127

    assert transport.writes == [
        b":HISTogram:SIZE 2\n",
        b":HISTogram:SIZE?\n",
        b":HISTogram:BLIMit -2\n",
        b":HISTogram:BLIMit?\n",
        b":MASK:OPERate RUN\n",
        b":MASK:OPERate?\n",
        b":MASK:PASSed?\n",
        b":MASK:FAILed?\n",
        b":MASK:TOTal?\n",
    ]


# 验证本批明确范围错误会在 Transport 写入前拒绝，避免明显非法命令进入真实仪器。
def test_analysis_validation_rejects_invalid_inputs() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.cursor.manual_cursor_a_x_set(1000)
    with pytest.raises(ValueError):
        driver.logic_analyzer.pod_threshold_set(1, 16.0)
    with pytest.raises(ValueError):
        driver.logic_analyzer.digital_display_set(16, True)
    with pytest.raises(ValueError):
        driver.histogram.size_set(5)
    with pytest.raises(ValueError):
        driver.mask.x_adjust_set(0.001)
    with pytest.raises(ValueError):
        driver.math.fft_search_count_set(1, 16)
    with pytest.raises(ValueError):
        driver.math.distance_set(1, 4)

    assert transport.writes == []


# 固化本批新增 180 个 Cursor/LA/Math/Histogram/Mask 原子 API，防止重构静默丢失能力。
def test_mso5204_analysis_api_inventory() -> None:
    driver, _ = _driver()

    expected = {
        "cursor": 56,
        "histogram": 19,
        "logic_analyzer": 23,
        "mask": 17,
        "math": 65,
    }
    actual = {group: len(_public_methods(getattr(driver, group))) for group in expected}

    assert actual == expected
    assert sum(actual.values()) == 180
