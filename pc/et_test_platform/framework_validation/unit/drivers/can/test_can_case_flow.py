# CAN正式Case的软件调用链回归。
# 职责：用独立响应驱动真实CanDriver和Case，核对命令顺序、强断言与异常清理。
# 边界：响应是软件夹具，不执行硬件，也不形成CAN HIL结果。
# 依赖：pytest、真实CAN公共Case/Driver和本模块显式响应队列。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ConfigurationError
from et_test_platform.drivers.can import (
    CanDriver,
    CanFrameFlags,
    CanPhaseTiming,
    CanRamLimits,
    CanTiming,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub
from et_test_platform.test_cases.can._support import CanSupport, loopback_ram, phase_timing
from et_test_platform.test_cases.can.test_can_p0 import (
    test_can_p0_002_internal_loopback as run_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_001_frame_formats as run_format_case,
)


# 明确序列化两帧独立RX Golden；不从Case刚发送的请求取回数据制造一致性。
def responses(*, corrupt_second=False):
    phase = (4, 15, 4, 4, 1, 15, 4, 4)
    result = [
        b"",
        pack("<I", 1),
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        pack("<I", 0),
        pack("<I", 1),
        pack("<8I", *phase),
    ]
    for index, data in enumerate(
        (
            bytes.fromhex("31 42 53 64 75 86 97 A8"),
            bytes.fromhex("CE BD AC 9B 8A 79 68 57"),
        )
    ):
        if corrupt_second and index == 1:
            data = bytes.fromhex("00 BD AC 9B 8A 79 68 57")
        result.extend(
            [
                pack("<5I", 0, index, index, 0, 0),
                b"",
                b"",
                pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, index) + data + bytes(56),
                b"",
                pack("<5I", 0, index + 1, index + 1, 0, 0),
            ]
        )
    return result


# 只构造显式依赖；复位替身保存调用次序，实际CAN请求仍经过真实Driver/Codec。
def dependencies(corrupt_second=False):
    target = TargetStub(responses(corrupt_second=corrupt_second))
    calls = []
    crg = SimpleNamespace(
        reset=lambda peripheral, **kwargs: calls.append(("can", kwargs["instance"]))
    )
    resource = SimpleNamespace(reset=lambda: calls.append(("resource",)))
    mapping = SimpleNamespace(CAN_RAM_HEADER_BYTES=8, CAN_STD_FILTER_BYTES=4)
    support = CanSupport(
        "can0",
        CanDriver(target, 0),
        crg,
        None,
        (),
        CanRamLimits(16384, 128, 64, 32, 64, 32, 64),
        CanTiming(CanPhaseTiming(512, 256, 128, 128), CanPhaseTiming(32, 32, 16, 16)),
        mapping,
        40_000_000,
    )
    return support, resource, target, calls


# 正常软件序列必须消费所有响应，两个独立Pattern均比较，Evidence四个端点分别存在。
def test_loopback_case_request_sequence_and_evidence():
    support, resource, target, calls = dependencies()
    properties = []
    run_case(support, resource, lambda key, value: properties.append((key, value)))
    assert target.responses == []
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    assert [row["command"] for row in target.requests] == [
        1,
        2,
        4,
        6,
        10,
        25,
        14,
        12,
        1,
        2,
        15,
        5,
        20,
        17,
        18,
        19,
        20,
        21,
        22,
        20,
        20,
        17,
        18,
        19,
        20,
        21,
        22,
        20,
    ]
    observations = [
        value for _, value in properties if isinstance(value, dict) and "endpoint" in value
    ]
    assert {row["endpoint"] for row in observations} == {
        "RX.FRAME",
        "RX0.FILL",
        "RX0.LOST",
        "TX.COMPLETED",
    }
    assert len(observations) == 8


# 第二帧一个Byte错误必须使真实Case失败，同时两项清理均执行，不能只核对第一帧。
def test_loopback_case_rejects_bad_payload_and_resets():
    support, resource, target, calls = dependencies(corrupt_second=True)
    with pytest.raises(AssertionError):
        run_case(support, resource, lambda key, value: None)
    assert target.responses == []
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# 纯配置不得把不精确时钟取整，也不得把芯片RAM容量不足降级为SKIP。
def test_can_timing_and_ram_configuration_bounds():
    support, _, target, _ = dependencies()
    phase = phase_timing(40_000_000, 500_000, support.timing_limits.nominal)
    assert phase == CanPhaseTiming(4, 15, 4, 4)
    with pytest.raises(ConfigurationError):
        phase_timing(40_000_001, 500_000, support.timing_limits.nominal)
    layout = loopback_ram(support)
    assert (layout.std_offset, layout.tx_offset, layout.rx0_offset, layout.rx_buffer_offset) == (
        0,
        4,
        20,
        84,
    )
    assert layout.rx0_count == 4
    assert target.requests == []


# 构造独立协议Oracle响应：数值flags/DLC表不从Case或Driver编码实现导入。
# 最后64-byte节点可独立损坏最后Byte，验证Case不会只比较首Byte或前8-byte。
def format_responses(flags, identifier, *, corrupt_last=False):
    result = []
    lengths = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)
    golden = bytes.fromhex(
        "31 42 53 64 75 86 97 A8 B9 CA DB EC FD 0E 1F 30 "
        "41 52 63 74 85 96 A7 B8 C9 DA EB FC 0D 1E 2F 40 "
        "51 62 73 84 95 A6 B7 C8 D9 EA FB 0C 1D 2E 3F 50 "
        "61 72 83 94 A5 B6 C7 D8 E9 FA 0B 1C 2D 3E 4F 60"
    )
    for dlc, fd_length in enumerate(lengths):
        length = fd_length if flags & 4 else min(dlc, 8)
        result.extend(
            [b"", pack("<I", 1), b"", b"", b"", b"", b"", b"", b"", pack("<I", 0), pack("<I", 1)]
        )
        for inverse in (False, True):
            payload = bytes(byte ^ (255 if inverse else 0) for byte in golden[:length])
            if corrupt_last and dlc == 15 and inverse:
                payload = payload[:-1] + bytes([payload[-1] ^ 1])
            index = int(inverse)
            result.extend(
                [
                    b"",
                    b"",
                    pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                    pack("<5I", 1, index, index + 1, 0, 0),
                    pack("<8I", identifier, flags, dlc, 0, 0, 1, length, index)
                    + payload
                    + bytes(64 - length),
                    b"",
                    pack("<5I", 0, index + 1, index + 1, 0, 0),
                ]
            )
    return result


# 六种格式乘两个ID边界，必须遍历每个DLC的两组Expected且执行每节点复位。
@pytest.mark.parametrize("flags", (0, 1, 4, 5, 12, 13))
@pytest.mark.parametrize("upper", (False, True))
def test_format_case_complete_matrix(flags, upper):
    support, resource, target, calls = dependencies()
    identifier = (0x1FFFFFFF if flags & 1 else 0x7FF) if upper else 0
    target.responses = format_responses(flags, identifier)
    properties = []
    run_format_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        "format",
        CanFrameFlags(flags),
        "maximum" if upper else "minimum",
    )
    assert target.responses == []
    assert len(target.requests) == 16 * (11 + 2 * 7)
    assert calls == [("can", 0), ("resource",)] * 17
    assert ("completed_nodes", 32) in properties
    assert sum(key == "format_text" for key, _ in properties) == 32


# FD64的最后Byte损坏必须失败；全部合法软件响应完成不等于数据正确。
def test_format_case_checks_last_payload_byte():
    support, resource, target, calls = dependencies()
    target.responses = format_responses(12, 0x7FF, corrupt_last=True)
    with pytest.raises(AssertionError):
        run_format_case(
            support, resource, lambda key, value: None, "fd_brs_std", CanFrameFlags(12), "maximum"
        )
    assert target.responses == []
    assert calls == [("can", 0), ("resource",)] * 17
