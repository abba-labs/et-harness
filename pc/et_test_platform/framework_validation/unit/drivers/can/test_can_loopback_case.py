# 回环引脚对照的独立软件Oracle。
# 职责：验证Normal正对照、只听切换、完整静默窗口和双端帧强断言。
# 边界：不连接仪器，不生成HIL通过结论。
# 依赖：真实Case/Driver、固定Wire响应及显式Peer替身。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import dependencies
from et_test_platform.instruments.can_boxes.models import CanFrame, CanReceivedFrame
from et_test_platform.test_cases.can import test_can_p2_loopback as case_module


# 测试 Feature：回环引脚对照不能被坏帧、假静默、设备错误或无正对照骗过。
# 测试方法：逐阶段独立构造Wire和Peer响应；虚拟时钟仅用于100ms窗口软件回归。
# 通过条件：正常响应全部消费；六种错误均触发失败，并保留关闭/复位链。
@pytest.mark.parametrize(
    "fault", (None, "baseline", "local", "external", "leak", "short", "peer_error")
)
def test_loopback_pin_case_validates_observer(fault, monkeypatch):
    support, resource, target, calls = dependencies()
    target.responses = []
    clock = [0.0]
    monkeypatch.setattr(case_module, "monotonic", lambda: clock[0])
    for mode, sequences in ((0, (0,)), (1, (1, 2)), (2, (3, 4))):
        target.responses.extend(
            [b"", pack("<I", 1)] + [b""] * 7 + [pack("<I", 0), pack("<I", mode)]
        )
        for sequence in sequences:
            target.responses.extend([b"", b"", pack("<7I", 0, 1, 0, 1, 0, 0, 0)])
            if mode:
                data = sequence.to_bytes(4, "little") + bytes.fromhex("75 86 97 A8")
                if fault == "local":
                    data = data[:-1] + b"\0"
                target.responses.extend(
                    [
                        pack("<5I", 1, 0, 1, 0, 0),
                        pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, 0) + data + bytes(56),
                        b"",
                    ]
                )
        target.responses.extend([pack("<5I", 0, 0, 0, 0, 0), bytes(60)])
    receive_count = [0]
    configs = []

    # 捕获响应独立于DUT发送请求；静默阶段只有完整有效时间窗允许超时。
    def receive(*, timeout_s):
        index = receive_count[0]
        receive_count[0] += 1
        if index == 1:
            clock[0] += 0.05 if fault == "short" else timeout_s
            if fault != "leak":
                raise TimeoutError("software no frames")
            sequence = 1
        else:
            sequence = {0: 0, 2: 3, 3: 4}[index]
        payload = sequence.to_bytes(4, "little") + bytes.fromhex("75 86 97 A8")
        if (index == 0 and fault == "baseline") or (index == 2 and fault == "external"):
            payload = bytes(8)
        return CanReceivedFrame(CanFrame(0x123, payload), index)

    box = SimpleNamespace(
        identity="software:CAN1",
        open=lambda: "software peer",
        configure=lambda config: configs.append(config),
        clear=lambda: None,
        receive=receive,
        error_get=lambda: 4 if fault == "peer_error" else 0,
        close=lambda: calls.append(("box_close",)),
    )
    gpio = SimpleNamespace(configure_signal=lambda *args: None)
    properties = []
    if fault:
        with pytest.raises(AssertionError):
            case_module.test_can_p2_005_loopback_pin_comparison(
                (support, gpio, ((2, 7), (3, 8)), box),
                resource,
                lambda k, v: properties.append((k, v)),
            )
    else:
        case_module.test_can_p2_005_loopback_pin_comparison(
            (support, gpio, ((2, 7), (3, 8)), box), resource, lambda k, v: properties.append((k, v))
        )
        assert not target.responses and receive_count[0] == 4
        # 契约要求三个阶段均以正常模式Peer捕获：外部回环忽略ACK与RX引脚，Peer是否ACK不改变判据。
        assert [c.listen_only for c in configs] == [False, False, False]
        assert dict(properties)["silent_window_elapsed_s"] >= 0.1
    assert calls[-3:] == [("box_close",), ("can", 0), ("resource",)]
