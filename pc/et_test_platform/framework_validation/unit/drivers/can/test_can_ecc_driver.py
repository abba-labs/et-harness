# CAN ECC公共Wire合同回归。
# 职责：独立字节向量、源隔离和真实ISR实例解码。
# 边界：不模拟RAM纠错或替代硬件中断验证。
# 依赖：pytest、真实CAN Driver与最小Target替身。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import CanDriver, CanEccSource, CanIrqSource
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub


# 固定Wire响应故意不同于输入，避免配置回显冒充读回；验证读写重试属性。
def test_ecc_golden_vectors() -> None:
    target = TargetStub(
        [
            b"",
            b"",
            b"",
            b"",
            pack("<4I", 3, 2, 2, 1),
            b"",
            b"",
            pack("<9I", 3, 2, 2, 7, 0, 0, 4, 0, 1),
            b"",
        ]
    )
    can = CanDriver(target, 2)
    can.ecc_enable_set(CanEccSource.CORRECTED, True, timeout_s=0.2)
    can.ecc_mask_set(CanEccSource.UNCORRECTED, False)
    can.ecc_force(CanEccSource.CORRECTED | CanEccSource.UNCORRECTED)
    can.ecc_clear(CanEccSource.CORRECTED)
    snapshot = can.ecc_snapshot_get()
    assert (snapshot.raw, snapshot.status, snapshot.enabled, snapshot.masked) == (3, 2, 2, 1)
    can.ecc_capture_start(CanEccSource.UNCORRECTED)
    can.ecc_capture_stop()
    event = can.ecc_event_get()
    assert event.instance_id == 1  # 实际回调实例，不用请求中的2替换。
    assert (event.event_count, event.generation, event.latched_events) == (7, 4, 2)
    can.ecc_event_reset()
    assert [item["command"] for item in target.requests] == list(range(70, 79))
    assert [item["body"] for item in target.requests] == [
        bytes.fromhex("02 01000000 01000000"),
        bytes.fromhex("02 02000000 00000000"),
        bytes.fromhex("02 03000000"),
        bytes.fromhex("02 01000000"),
        b"\x02",
        bytes.fromhex("02 02000000"),
        b"\x02",
        b"\x02",
        b"\x02",
    ]
    assert [item["retry_safe"] for item in target.requests] == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
    ]
    assert target.requests[0]["timeout_s"] == 0.2


# 控制器IRQ枚举即使位值相同也不能作为ECC源输入。
@pytest.mark.parametrize(
    "source", [0, 1, True, CanEccSource.NONE, CanEccSource(4), CanIrqSource.RX_FIFO0_NEW]
)
def test_ecc_bad_source_before_io(source) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).ecc_force(source)
    assert not target.requests


# 非Boolean配置不得在Driver中按真值窄化。
@pytest.mark.parametrize("method", ["ecc_enable_set", "ecc_mask_set"])
def test_ecc_bad_boolean_before_io(method) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        getattr(CanDriver(target, 0), method)(CanEccSource.CORRECTED, 2)
    assert not target.requests


# 保留源、错误长度、非法实例必须拒绝；不补造有效结果。
@pytest.mark.parametrize(
    "method,words",
    [
        ("ecc_snapshot_get", (4, 0, 0, 0)),
        ("ecc_snapshot_get", (0, 4, 0, 0)),
        ("ecc_snapshot_get", (0, 0, 4, 0)),
        ("ecc_snapshot_get", (0, 0, 0, 4)),
        ("ecc_snapshot_get", (0, 0, 0)),
        ("ecc_event_get", (4, 0, 0, 0, 0, 0, 0, 0, 0)),
        ("ecc_event_get", (0, 4, 0, 0, 0, 0, 0, 0, 0)),
        ("ecc_event_get", (0, 0, 4, 0, 0, 0, 0, 0, 0)),
        ("ecc_event_get", (0, 0, 0, 0, 0, 0, 0, 0, 256)),
        ("ecc_event_get", (0,)),
    ],
)
def test_ecc_bad_response(method, words) -> None:
    target = TargetStub([pack(f"<{len(words)}I", *words)])
    with pytest.raises(ProtocolError):
        getattr(CanDriver(target, 0), method)()
    assert len(target.requests) == 1


# 初始实例哨兵必须保持无归属，不把逻辑实例0当作已回调。
def test_ecc_no_callback_sentinel() -> None:
    target = TargetStub([pack("<9I", 0, 0, 0, 0, 0, 0, 1, 0, 0xFFFFFFFF)])
    assert CanDriver(target, 0).ecc_event_get().instance_id is None
