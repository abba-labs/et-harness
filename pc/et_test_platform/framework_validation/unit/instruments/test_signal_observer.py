# 公共逻辑信号观测器 Adapter 无硬件测试。
#
# 职责：验证 MSO5204 Adapter 正确映射公共捕获与测量语义。
# 边界：只使用脚本化 Transport，不连接真实示波器，也不证明测量精度。
# 依赖：公共 SignalObserver、MSO5204 Driver、ScpiSession 和 ByteTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes import SignalEdge, SignalObserver
from et_test_platform.instruments.oscilloscopes.mso5204 import (
    Mso5204Driver,
    Mso5204ObserverBinding,
    Mso5204SignalObserver,
)


# 提供本测试所需的确定性 SCPI 响应；不模拟真实示波器状态机。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes]) -> None:
        self.responses = responses
        self.writes: list[bytes] = []
        self.pending: deque[bytes] = deque()

    @property
    def identity(self) -> str:
        return "scripted:signal-observer"

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def write(self, data: bytes, *, timeout_s: float | None = None) -> None:
        del timeout_s
        self.writes.append(data)
        if data in self.responses:
            self.pending.append(self.responses[data])

    def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        del timeout_s
        if not self.pending:
            return b""
        response = self.pending.popleft()
        return response[:max_bytes]


# 验证公共 Observer 不泄漏型号 API，并把逻辑测量转换为统一 SI 结果。
def test_mso5204_signal_observer_maps_public_measurement_contract() -> None:
    responses = {
        b":MEASure:ITEM? FREQuency,CHANnel2\n": b"1000\n",
        b":MEASure:ITEM? PERiod,CHANnel2\n": b"0.001\n",
        b":MEASure:ITEM? PWIDth,CHANnel2\n": b"0.00025\n",
        b":MEASure:ITEM? PDUTy,CHANnel2\n": b"25\n",
        b":MEASure:ITEM? VPP,CHANnel2\n": b"3.3\n",
    }
    transport = ScriptedTransport(responses)
    driver = Mso5204Driver(ScpiSession(transport))
    observer = Mso5204SignalObserver(
        driver,
        Mso5204ObserverBinding(
            channel=2,
            vertical_scale_v=1.0,
            trigger_level_v=1.65,
            probe_ratio=10.0,
        ),
    )

    assert isinstance(observer, SignalObserver)

    observer.configure_edge_capture(time_scale_s=0.001, edge=SignalEdge.RISING)
    observer.arm_single()
    result = observer.measure()

    assert result.frequency_hz == pytest.approx(1000.0)
    assert result.period_s == pytest.approx(0.001)
    assert result.positive_width_s == pytest.approx(0.00025)
    assert result.duty_cycle_percent == pytest.approx(25.0)
    assert result.vpp_v == pytest.approx(3.3)
    assert b":TRIGger:EDGE:SOURce CHANnel2\n" in transport.writes
    assert b":SINGle\n" in transport.writes
