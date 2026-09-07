# CAN FD格式Case的软件调用链回归。
# 职责：独立构造Wire和Peer向量，覆盖格式正反例与错误清理。
# 边界：软件夹具不模拟CAN编码或形成硬件验证结论。
# 依赖：真实Case、CAN Driver及已有最小依赖构造器。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.instruments.can_boxes.models import CanFrame, CanReceivedFrame
from et_test_platform.test_cases.can.test_can_p1_format import (
    test_can_p1_020_fd_format_matrix as run_format_case,
)


# 测试 Feature：格式四组合、16/64-byte和ISO恢复的强断言。
# 测试方法：使用固定Wire而非请求回填响应，分别污染配置、整帧及失配错误证据。
# 通过条件：8个正常节点全部消费；任一决定性坏值失败并清理全部资源。
@pytest.mark.parametrize("length", (16, 64))
@pytest.mark.parametrize(
    "dut,peer,fault",
    (
        (False, False, None),
        (True, True, None),
        (False, True, None),
        (True, False, None),
        (True, True, "format"),
        (False, False, "peer_tail"),
        (False, False, "dut_tail"),
        (False, True, "error_code"),
        (False, True, "negative_rx"),
        (True, False, "irq_clear"),
        (True, False, "recovery_tail"),
    ),
)
def test_format_case_independent_vectors(length, dut, peer, fault, tmp_path):
    support, resource, target, calls = dependencies()
    payload = bytes((49 + 17 * i) % 256 for i in range(length))
    dlc = 10 if length == 16 else 15
    target.responses = []
    captures, expected_sends = [], []
    for stage, actual_dut, actual_peer in (("primary", dut, peer), ("recovery", False, False)):
        mode = not actual_dut if fault == "format" else actual_dut
        target.responses.extend(
            [b"", pack("<I", 1)]
            + [b""] * 7
            + [
                pack("<I", mode),
                pack("<10I", 1, 1, 0, 0, 0, 0, 0, 0, 0, 0),
                b"",
                bytes(60),
                b"",
                pack("<I", 0),
            ]
        )
        if actual_dut != actual_peer:
            target.responses.extend(
                [
                    pack("<4I", 1 << 27, 0, 0, 0),
                    pack("<15I", 7 if fault == "error_code" else 1, *([0] * 14)),
                ]
            )
        else:
            target.responses.extend([b"", b"", pack("<7I", 0, 1, 0, 1, 0, 0, 0)])
            actual_payload = (
                payload[:-1] + bytes([payload[-1] ^ 1]) if fault == "dut_tail" else payload
            )
            target.responses.extend(
                [
                    pack("<5I", 1, 0, 1, 0, 0),
                    pack("<8I", 0x123, 12, dlc, 0, 0, 0, length, 0)
                    + actual_payload
                    + bytes(64 - length),
                    b"",
                    bytes(60),
                ]
            )
            captured_payload = payload
            if fault == "peer_tail" or (fault == "recovery_tail" and stage == "recovery"):
                captured_payload = payload[:-1] + bytes([payload[-1] ^ 1])
            captures.append(
                CanReceivedFrame(CanFrame(0x123, captured_payload, fd=True, brs=True), 1)
            )
        target.responses.extend(
            [
                pack("<5I", int(fault == "negative_rx" and stage == "primary"), 0, 0, 0, 0),
                b"",
                pack("<4I", (1 << 27) if fault == "irq_clear" else 0, 0, 0, 0),
            ]
        )
        expected_sends.append(CanFrame(0x123, payload, fd=True, brs=True))
    captured = iter(captures)
    sent = []
    box = SimpleNamespace(
        identity="software-peer:CAN1",
        open=lambda: "software peer",
        clear=lambda: None,
        configure=lambda config: calls.append(("peer_config", config)),
        send=lambda frame, **kwargs: sent.append((frame, kwargs)),
        receive=lambda **kwargs: next(captured),
        close=lambda: calls.append(("peer_close",)),
    )
    gpio = SimpleNamespace(configure_signal=lambda *args: None)
    properties = []
    arguments = (
        (support, gpio, ((2, 7), (3, 8)), box),
        resource,
        lambda k, v: properties.append((k, v)),
        length,
        dut,
        peer,
    )
    if fault:
        with pytest.raises(AssertionError):
            run_format_case(*arguments)
    else:
        run_format_case(*arguments)
        assert not target.responses
        assert sent == [(frame, {"single_shot": True}) for frame in expected_sends]
        assert [c[1].non_iso for c in calls if c[0] == "peer_config"] == [peer, False]
        assert any(key == "format_summary" for key, _ in properties)
        assert any(key == "result_summary" for key, _ in properties)
    assert calls[-3:] == [("peer_close",), ("can", 0), ("resource",)]
    assert_case_report(properties, "CAN_P1_020", "FAIL" if fault else "PASS", tmp_path)
