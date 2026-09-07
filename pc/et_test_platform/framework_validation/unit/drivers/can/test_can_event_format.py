# CAN事件格式和宽Marker的独立Wire回归。
# 职责：验证配置、有效性及旧读取接口兼容边界。
# 边界：不操作实际CAN或TSU，不用软件向量证明硬件编码。
# 依赖：pytest、真实CAN Driver/Codec及最小Target替身。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import CanDriver, CanEventFormat, codec
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub


# 测试Feature：宽Marker设置和实际格式读取的固定Wire。
# 测试方法：核对59/60命令及独立小端字节；不允许8-bit与TSU组合。
# 通过条件：写不可重试、读可重试，非法参数不下发，实际格式不来自缓存。
def test_event_format_golden():
    target = TargetStub([b"", pack("<2I", 16, 0)])
    can = CanDriver(target, 2)
    can.event_format_set(CanEventFormat(16, False), timeout_s=0.2)
    assert can.event_format_get() == CanEventFormat(16, False)
    assert [r["command"] for r in target.requests] == [59, 60]
    assert target.requests[0]["body"] == bytes.fromhex("02 10000000 00000000")
    assert [r["retry_safe"] for r in target.requests] == [False, True]
    assert target.requests[0]["timeout_s"] == 0.2
    for value in (CanEventFormat(8, True), CanEventFormat(7, False), CanEventFormat(16, 1)):
        with pytest.raises(ValueError):
            can.event_format_set(value)
    assert len(target.requests) == 2


# 测试Feature：基本、宽Marker及TSU捕获模式不会混报时间戳。
# 测试方法：用十word独立响应验证Optional字段与完整Marker。
# 通过条件：E1A保留16-bit时间戳，E1B为None，TSU只有捕获时返回指针。
@pytest.mark.parametrize(
    "words,stamp,pointer",
    (
        ((0x123, 0, 8, 0x3456, 1, 0xAB, 2, 1, 0, 0), 0x3456, None),
        ((0x123, 0, 8, 0, 1, 0xABCD, 2, 0, 0, 0), None, None),
        ((0x123, 0, 8, 0, 1, 0x1234, 2, 0, 1, 15), None, 15),
    ),
)
def test_extended_event_golden(words, stamp, pointer):
    target = TargetStub([pack("<10I", *words)])
    actual = CanDriver(target, 1).tx_event_details_read(timeout_s=0.3)
    assert actual.marker == words[5] and actual.identifier == 0x123 and actual.index == 2
    assert actual.timestamp == stamp and actual.tsu_pointer == pointer
    assert target.requests[0]["command"] == 61
    assert target.requests[0]["body"] == b"\x01" and target.requests[0]["retry_safe"] is True


# 测试Feature：无效时间戳、无效指针及超宽Marker不能形成合法观测。
# 测试方法：逐个污染不同有效性字段。
# 通过条件：解码失败关闭，不把保留值静默丢弃。
@pytest.mark.parametrize("field,value", ((3, 1), (5, 0x10000), (7, 2), (8, 2), (9, 1), (9, 16)))
def test_extended_event_invalid_metadata(field, value):
    words = [0x123, 0, 8, 0, 1, 0xABCD, 2, 0, 0, 0]
    words[field] = value
    with pytest.raises(ProtocolError):
        codec.decode_tx_event_details(tuple(words))


# 测试Feature：硬件配置非法组合及响应长度拒绝。
# 测试方法：注入TSU+8bit、非法宽度、非法Boolean或缺字段。
# 通过条件：所有向量均为协议失败，不能静默回退8bit。
@pytest.mark.parametrize("words", ((8, 1), (0, 0), (16, 2), (16,)))
def test_event_format_bad_readback(words):
    with pytest.raises(ProtocolError):
        codec.decode_event_format(words)
