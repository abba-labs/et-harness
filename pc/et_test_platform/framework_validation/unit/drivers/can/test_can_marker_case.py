# CAN Marker正式Case的独立软件向量。
# 职责：验证两种位宽、事件/RX完整性和失败清理。
# 边界：固定Wire替身不模拟CAN硬件或证明物理时序。
# 依赖：真实Case、CanDriver及已有最小依赖构造器。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can import test_can_p1_marker as marker_case


# 测试Feature：Marker位宽及每项决定性硬件事实均由独立Expected约束。
# 测试方法：两种位宽注入格式、Marker高位、RX末字节、事件类型和残留错误。
# 通过条件：正确向量完全消费；所有坏值失败且执行同样清理，不放宽断言。
@pytest.mark.parametrize("bits", (8, 16))
@pytest.mark.parametrize(
    "fault", (None, "format", "marker", "rx_tail", "event_type", "stamp", "extra", "lost")
)
def test_marker_case_vectors(bits, fault, monkeypatch, tmp_path):
    support, resource, target, calls = dependencies()
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 7
        + [
            pack("<2I", (16 if bits == 8 else 8) if fault == "format" else bits, 0),
            b"",
            pack("<I", 0),
        ]
    )
    for index in range(2):
        payload = bytes(((49 + 17 * i) % 256) ^ (255 if index else 0) for i in range(8))
        if fault == "rx_tail" and index == 1:
            payload = payload[:-1] + bytes([payload[-1] ^ 1])
        target.responses.extend(
            [
                b"",
                b"",
                pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, index) + payload + bytes(56),
                b"",
                pack("<5I", index + 1, 0, index + 1, 0, 0),
            ]
        )
    expected_markers = (0x12, 0xAB) if bits == 8 else (0x1234, 0xABCD)
    for index, marker in enumerate(expected_markers):
        if fault == "marker" and index == 1:
            marker = (marker & 255) if bits == 16 else marker ^ 1
        valid = int(bits == 8)
        if fault == "stamp":
            valid = 1 - valid
        target.responses.extend(
            [
                pack(
                    "<10I",
                    0x123,
                    0,
                    8,
                    0x5678 if valid else 0,
                    1 if fault == "event_type" else 2,
                    marker,
                    index,
                    valid,
                    0,
                    0,
                ),
                b"",
            ]
        )
    target.responses.extend(
        [
            pack("<5I", int(fault == "extra"), 2, 2, 0, int(fault == "lost")),
            pack("<5I", 0, 2, 2, 0, 0),
        ]
    )
    clock = iter((0.0, 0.2))
    monkeypatch.setattr(marker_case, "monotonic", lambda: next(clock))
    properties = []
    args = (support, resource, lambda key, value: properties.append((key, value)), bits)
    if fault:
        expected_error = ProtocolError if fault == "stamp" and bits == 16 else AssertionError
        with pytest.raises(expected_error):
            marker_case.test_can_p1_010_message_marker_width(*args)
    else:
        marker_case.test_can_p1_010_message_marker_width(*args)
        assert not target.responses
        writes = [r for r in target.requests if r["command"] == 17]
        assert len(writes) == 2 and all(not r["retry_safe"] for r in writes)
        assert [entry["marker"] for entry in dict(properties)["event_summary"]] == list(
            expected_markers
        )
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    assert_case_report(properties, "CAN_P1_010", "FAIL" if fault else "PASS", tmp_path)
    if fault not in (None, "extra", "lost"):
        assert dict(properties)["empty_window"] == "NOT_OBSERVED"
