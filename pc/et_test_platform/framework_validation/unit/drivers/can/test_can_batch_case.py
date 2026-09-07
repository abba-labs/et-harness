# CAN连续批量Case的独立软件回归。
# 职责：20轮全量Wire链路、整批请求及首次错误清理验证。
# 边界：不模拟CAN总线；固定响应不作为FPGA吞吐证据。
# 依赖：真实Case/Driver、独立二进制向量和轻量Peer替身。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ConfigurationError
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import dependencies
from et_test_platform.instruments.can_boxes.models import CanFrame, CanReceivedFrame
from et_test_platform.test_cases.can import test_can_p3 as batch_case
from et_test_platform.test_cases.can._support import batch_fifo_ram


# 测试Feature：连续FIFO几何和容量边界。
# 测试方法：独立计算32项64-byte元素地址，再请求越界深度。
# 通过条件：TX/RX及保留区互不覆盖，超过公开容量失败。
def test_batch_layout_geometry():
    support, *_ = dependencies()
    layout = batch_fifo_ram(support, count=32, payload_bytes=64)
    assert (layout.tx_offset, layout.rx0_offset, layout.rx_buffer_offset) == (4, 2308, 4612)
    assert layout.tx_buffer_count == 0 and layout.tx_fifo_count == layout.rx0_count == 32
    assert layout.rx_buffer_offset + 64 * 72 == 9220
    for count in (0, 33):
        with pytest.raises(ConfigurationError):
            batch_fifo_ram(support, count=count, payload_bytes=64)


# 测试Feature：整批排队、20轮双向1280帧、负向残留及错误拒绝。
# 测试方法：独立Wire和Peer向量运行完整Case；污染首轮及最后一轮的决定性事实。
# 通过条件：正确场景20个全位图请求、640次实际反向发送；任何坏值均失败并清理。
@pytest.mark.parametrize(
    "fault",
    (None, "peer_tail", "dut_tail", "last_sequence", "lost", "pending", "protocol", "extra"),
)
def test_batch_case_full_vectors(fault, monkeypatch):
    support, resource, target, calls = dependencies()
    support.mapping.CAN_TDC_TIMING_PROFILES = {40_000_000: {5_000_000: ((1, 5, 2, 2), 6)}}
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 6
        + [
            pack("<8I", 2, 15, 4, 4, 1, 5, 2, 2),
            pack("<10I", 1, 1, 0, 0, 0, 1, 1, 6, 0, 0),
            b"",
            pack("<I", 0),
        ]
    )
    captures, expected_sends = [], []
    for round_index in range(20):
        target.responses += [pack("<7I", 0, 0, 0, 32, 0, 0, 0)] + [b""] * 33
        target.responses += [
            pack("<7I", 0, 0xFFFFFFFF, 0, 32, 0, 0, 0),
            pack("<5I", 32, 0, 0, 1, int(fault == "lost")),
        ]
        for index in range(32):
            seq = round_index * 64 + index
            forward = seq.to_bytes(4, "little") + bytes((49 + i * 17) % 256 for i in range(4, 64))
            if fault == "peer_tail" and index == 1:
                forward = forward[:-1] + bytes([forward[-1] ^ 1])
            captures.append(CanReceivedFrame(CanFrame(0x123, forward, fd=True, brs=True), 1))
            reverse = (seq + 32).to_bytes(4, "little") + bytes(
                ((49 + i * 17) % 256) ^ 255 for i in range(4, 64)
            )
            expected_sends.append(CanFrame(0x321, reverse, fd=True, brs=True))
            if fault == "dut_tail" and index == 1:
                reverse = reverse[:-1] + bytes([reverse[-1] ^ 1])
            if fault == "last_sequence" and round_index == 19 and index == 31:
                reverse = bytes(4) + reverse[4:]
            target.responses += [pack("<8I", 0x321, 12, 15, 0, 0, 0, 64, index) + reverse, b""]
        target.responses += [
            pack("<7I", int(fault == "pending"), 0xFFFFFFFF, 0, 32, 0, 0, 0),
            pack("<5I", 0, 0, 0, 0, 0),
            pack("<15I", int(fault == "protocol"), *([0] * 14)),
        ]
    captured = iter(captures)
    sent = []

    # Peer只返回预置捕获；末尾没有更多数据时产生固定超时，不根据DUT请求造帧。
    def receive(**kwargs):
        try:
            return next(captured)
        except StopIteration:
            assert kwargs["timeout_s"] == 0.1
            if fault == "extra":
                return captures[-1]
            raise TimeoutError("independent empty peer window") from None

    box = SimpleNamespace(
        identity="software-peer",
        open=lambda: "software peer",
        configure=lambda config: None,
        clear=lambda: None,
        close=lambda: calls.append(("peer_close",)),
        error_get=lambda: 0,
        send=lambda frame, **kwargs: sent.append((frame, kwargs)),
        receive=receive,
    )
    gpio = SimpleNamespace(configure_signal=lambda *args: None)
    clock = iter((0.0, 0.2))
    monkeypatch.setattr(batch_case, "monotonic", lambda: next(clock))
    properties = []
    args = (
        (support, gpio, ((2, 7), (3, 8)), box),
        resource,
        lambda k, v: properties.append((k, v)),
    )
    if fault:
        with pytest.raises(AssertionError):
            batch_case.test_can_p3_001_bounded_fifo_traffic(*args)
    else:
        batch_case.test_can_p3_001_bounded_fifo_traffic(*args)
        assert not target.responses and [frame for frame, _ in sent] == expected_sends
        assert all(kwargs == {"single_shot": True} for _, kwargs in sent)
        requests = target.requests
        triggers = [i for i, r in enumerate(requests) if r["command"] == 18]
        assert len(triggers) == 20
        for trigger in triggers:
            assert [r["command"] for r in requests[trigger - 32 : trigger]] == [17] * 32
            assert requests[trigger]["body"] == bytes.fromhex("00 ffffffff")
        assert dict(properties)["counts"][-1] == {
            "round": 20,
            "peer_received": 640,
            "dut_received": 640,
        }
    assert calls == [("can", 0), ("resource",), ("peer_close",), ("can", 0), ("resource",)]
