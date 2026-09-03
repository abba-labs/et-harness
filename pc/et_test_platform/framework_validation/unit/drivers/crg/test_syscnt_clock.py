# CRG系统计数器时钟Wire测试。
# 职责：验证新增命令编号、固定长度、保留位和Driver响应校验。
# 边界：仅软件替身，不访问硬件。
# 依赖：CRG Driver、pytest和标准库。

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from et_test_platform.drivers.crg import CrgDriver
from et_test_platform.drivers.crg.codec import decode_syscnt_clock, encode_syscnt_clock
from et_test_platform.drivers.crg.contract import CRG_SERVICE_ID, CrgCommand


# 测试Feature：固定四字节时钟请求与Boolean读回。
# 测试方法：分别编码SET/GET，解码开关值并验证非法响应。
# 通过条件：Golden完全相同，长度、保留位或Boolean错误均被拒绝。
def test_syscnt_clock_codec() -> None:

    assert encode_syscnt_clock(3, 1) == b"\x03\x01\x00\x00"
    assert encode_syscnt_clock(3) == b"\x03\x00\x00\x00"
    assert decode_syscnt_clock(b"\x01\x00\x00\x00") is True
    assert decode_syscnt_clock(bytes(4)) is False
    for invalid in (b"", bytes(3), bytes(5), b"\x02\x00\x00\x00", b"\x01\x00\x01\x00"):
        with pytest.raises(ValueError):
            decode_syscnt_clock(invalid)


# 测试Feature：PC只发送CRG请求，不隐含复位或频率配置。
# 测试方法：调用公开SET/GET并精确比较请求和只读重试标志。
# 通过条件：只出现两次预期请求，响应体不合法时抛错。
def test_syscnt_clock_driver_requests() -> None:

    target = Mock()
    target.request.return_value = (SimpleNamespace(body=b""), None)
    driver = CrgDriver(target)
    driver.syscnt_clock_set(2, enabled=True)
    target.request.assert_called_once_with(
        CRG_SERVICE_ID, CrgCommand.SYSCNT_CLOCK_SET, body=b"\x02\x01\x00\x00"
    )

    target.request.reset_mock()
    target.request.return_value = (SimpleNamespace(body=b"\x01\x00\x00\x00"), None)
    assert driver.syscnt_clock_get(2) is True
    target.request.assert_called_once_with(
        CRG_SERVICE_ID, CrgCommand.SYSCNT_CLOCK_GET, body=b"\x02\x00\x00\x00", retry_safe=True
    )

    with pytest.raises(ValueError):
        driver.syscnt_clock_set(2, enabled=True)
    with pytest.raises(ValueError):
        driver.syscnt_clock_get(-1)
