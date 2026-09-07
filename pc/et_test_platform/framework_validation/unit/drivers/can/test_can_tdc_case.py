# TDC Case的软件调用链验证。
# 职责：独立Wire响应验证真实Case/Driver的配置与双向强断言。
# 边界：全部响应是软件夹具，不形成FPGA或Silicon通过证据。
# 依赖：pytest、CAN Driver及已有只读依赖构造器。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.instruments.can_boxes.models import CanFrame, CanReceivedFrame
from et_test_platform.profiles.chip_execution_mappings.et6801.can_routes import (
    CAN_TDC_TIMING_PROFILES,
)
from et_test_platform.test_cases.can.test_can_p1_tdc import (
    test_can_p1_021_tdc_external_fd as run_tdc_case,
)


# 测试 Feature：TDC实际开启、完整FD/BRS数据、独立Peer及异常清理。
# 测试方法：独立构造两速率的Wire向量，损坏配置、末字节、BRS或制造回显。
# 通过条件：正常向量全部消费；任一错误必须失败且关闭Peer、复位资源。
@pytest.mark.parametrize("bitrate", (2_000_000, 5_000_000))
@pytest.mark.parametrize("fault", (None, "disabled", "peer_tail", "dut_tail", "echo", "brs"))
def test_tdc_case_independent_wire_and_peer(bitrate, fault, tmp_path):
    support, resource, target, calls = dependencies()
    support.mapping.CAN_TDC_TIMING_PROFILES = CAN_TDC_TIMING_PROFILES
    data_phase = (1, 15, 4, 4) if bitrate == 2_000_000 else (1, 5, 2, 2)
    offset = 16 if bitrate == 2_000_000 else 6
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 6
        + [
            pack("<10I", 1, 1, 1, 0, 0, 1, int(fault != "disabled"), offset, 0, 0),
            pack("<8I", 2, 15, 4, 4, *data_phase),
            b"",
            pack("<I", 0),
        ]
    )
    for _ in range(2):
        target.responses.extend([b"", b"", pack("<7I", 0, 1, 0, 1, 0, 0, 0), bytes(60)])
    # 独立字节公式和固定序号，不从Case待发请求生成响应。
    forward = [
        i.to_bytes(4, "little") + bytes((49 + 17 * j) % 256 for j in range(4, 64)) for i in (1, 2)
    ]
    reverse = [
        i.to_bytes(4, "little") + bytes(255 - (49 + 17 * j) % 256 for j in range(4, 64))
        for i in (3, 4)
    ]
    for index, payload in enumerate(reverse):
        actual = payload[:-1] + bytes([payload[-1] ^ 1]) if fault == "dut_tail" else payload
        target.responses.extend(
            [
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x321, 4 if fault == "brs" else 12, 15, 0, 0, 0, 64, index) + actual,
                b"",
            ]
        )
    target.responses.extend(
        [pack("<7I", 0, 1, 0, 1, 0, 0, 0), pack("<5I", 0, 2, 2, 0, 0), bytes(60)]
    )
    peer = iter(
        [
            CanReceivedFrame(
                CanFrame(
                    0x123,
                    p[:-1] + bytes([p[-1] ^ 1]) if fault == "peer_tail" else p,
                    fd=True,
                    brs=True,
                ),
                i,
                is_echo=fault == "echo",
            )
            for i, p in enumerate(forward)
        ]
    )
    sent = []
    box = SimpleNamespace(
        identity="software-peer:CAN1",
        open=lambda: "software peer",
        configure=lambda config: calls.append(("peer_config", config)),
        clear=lambda: None,
        receive=lambda **kwargs: next(peer),
        send=lambda frame, **kwargs: sent.append(frame),
        close=lambda: calls.append(("peer_close",)),
    )
    gpio = SimpleNamespace(configure_signal=lambda *args: None)
    properties = []
    if fault:
        with pytest.raises(AssertionError):
            run_tdc_case(
                (support, gpio, ((2, 7), (3, 8)), box),
                resource,
                lambda k, v: properties.append((k, v)),
                bitrate,
            )
    else:
        run_tdc_case(
            (support, gpio, ((2, 7), (3, 8)), box),
            resource,
            lambda k, v: properties.append((k, v)),
            bitrate,
        )
        assert not target.responses
        assert sent == [CanFrame(0x321, p, fd=True, brs=True) for p in reverse]
    assert_case_report(properties, "CAN_P1_021", "FAIL" if fault else "PASS", tmp_path)
    assert calls[-3:] == [("peer_close",), ("can", 0), ("resource",)]
