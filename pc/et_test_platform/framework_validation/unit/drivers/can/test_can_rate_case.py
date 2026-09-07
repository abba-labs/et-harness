# CAN速率矩阵独立Wire回归。
# 职责：独立九组时序Golden与双向完整帧、错误路径和清理验证。
# 边界：不依赖Case计算响应，不模拟总线时序，不代表FPGA PASS。
# 依赖：真实Case/Driver及软件Target/Peer。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import dependencies
from et_test_platform.instruments.can_boxes.models import CanFrame, CanReceivedFrame
from et_test_platform.test_cases.can.test_can_p1_rates import (
    test_can_p1_012_bitrate_matrix as run_case,
)

# 独立40MHz时序表，覆盖800k的25TQ和5M的8TQ；不导入被测Case的节点表。
NOMINAL = {
    125_000: (16, 15, 4, 4),
    250_000: (8, 15, 4, 4),
    500_000: (4, 15, 4, 4),
    800_000: (2, 19, 5, 4),
    1_000_000: (2, 15, 4, 4),
}
NODES = [(rate, None) for rate in NOMINAL] + [
    (nominal, data) for nominal in (500_000, 1_000_000) for data in (2_000_000, 5_000_000)
]


# 测试Feature：完整九组速率，真实时序读回与双向数据不可弱化。
# 测试方法：独立Golden注入错误BRP、FD配置、末字节、回显及Bus Off。
# 通过条件：正常全部消费，错误首错失败；不进行CRG时钟配置，退出复位资源。
@pytest.mark.parametrize("nominal,data", NODES)
@pytest.mark.parametrize(
    "fault", (None, "timing", "options", "peer_tail", "dut_tail", "echo", "bus_off")
)
def test_rate_matrix_vectors(nominal, data, fault):
    support, resource, target, calls = dependencies()
    fd = data is not None
    size, dlc, flags = (64, 15, 12) if fd else (8, 8, 0)
    nominal_phase = NOMINAL[nominal]
    if fault == "timing":
        nominal_phase = (nominal_phase[0] + 1, *nominal_phase[1:])
    data_phase = (1, 5, 2, 2) if data == 5_000_000 else (1, 15, 4, 4)
    offset = (6 if data == 5_000_000 else 16) if fd else 0
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 6
        + [
            pack("<8I", *nominal_phase, *data_phase),
            pack(
                "<10I",
                int(not fd) if fault == "options" else int(fd),
                int(fd),
                1,
                0,
                0,
                1,
                int(fd),
                offset,
                0,
                0,
            ),
            b"",
            pack("<I", 0),
        ]
    )
    for _ in range(2):
        target.responses += [b"", b"", pack("<7I", 0, 1, 0, 1, 0, 0, 0)]
    forward = [
        i.to_bytes(4, "little") + bytes((49 + 17 * j) % 256 for j in range(4, size)) for i in (1, 2)
    ]
    reverse = [
        i.to_bytes(4, "little") + bytes(255 - (49 + 17 * j) % 256 for j in range(4, size))
        for i in (3, 4)
    ]
    for index, payload in enumerate(reverse):
        actual = payload[:-1] + bytes([payload[-1] ^ 1]) if fault == "dut_tail" else payload
        target.responses += [
            pack("<5I", 1, index, index + 1, 0, 0),
            pack("<8I", 0x321, flags, dlc, 0, 0, 0, size, index) + actual + bytes(64 - size),
            b"",
        ]
    target.responses += [
        pack("<7I", 0, 1, 0, 1, 0, 0, 0),
        pack("<5I", 0, 2, 2, 0, 0),
        pack("<15I", 0, 0, 0, 0, int(fault == "bus_off"), *([0] * 10)),
    ]
    peer = iter(
        [
            CanReceivedFrame(
                CanFrame(
                    0x123, p[:-1] + bytes([p[-1] ^ 1]) if fault == "peer_tail" else p, fd=fd, brs=fd
                ),
                i,
                is_echo=fault == "echo",
            )
            for i, p in enumerate(forward)
        ]
    )
    sent, configured, properties = [], [], []
    box = SimpleNamespace(
        identity="software-peer",
        open=lambda: "software",
        configure=configured.append,
        clear=lambda: None,
        receive=lambda **kwargs: next(peer),
        send=lambda frame, **kwargs: sent.append(frame),
        close=lambda: calls.append(("peer_close",)),
    )
    gpio = SimpleNamespace(configure_signal=lambda *args: None)
    args = (
        (support, gpio, ((2, 7), (3, 8)), box),
        resource,
        lambda k, v: properties.append((k, v)),
        nominal,
        data,
    )
    if fault:
        with pytest.raises(AssertionError):
            run_case(*args)
    else:
        run_case(*args)
        assert not target.responses
        assert sent == [CanFrame(0x321, p, fd=fd, brs=fd) for p in reverse]
        assert configured[0].nominal_bitrate == nominal
        assert configured[0].data_bitrate == (data or 2_000_000)
        assert dict(properties)["expected"]["clock_source"] == "chip_profile"
        assert dict(properties)["timing"][0]["sample_point"] == 0.8
    assert calls == [("can", 0), ("resource",), ("peer_close",), ("can", 0), ("resource",)]
