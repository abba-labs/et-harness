# SYSCTRL计数器路由的PC协议测试。
# 职责：验证新增原子动作的编码、响应校验和非法参数拒绝。
# 边界：不访问硬件，不推断频率或Halt功能通过。
# 依赖：pytest、标准库及本IP Driver。

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from et_test_platform.drivers.sysctrl.codec import decode_syscnt_routing, encode_syscnt_routing
from et_test_platform.drivers.sysctrl.contract import (
    SYSCTRL_SERVICE_ID,
    SyscntClockSource,
    SysctrlCommand,
)
from et_test_platform.drivers.sysctrl.driver import SysctrlDriver


# 测试Feature：路由命令Golden和真实状态响应。
# 测试方法：1. 精确比较4-byte编码。2. 遍历非法长度、源、Boolean、保留位。
# 通过条件：有效数据无损解码，无效数据全部抛异常。
def test_syscnt_routing_codec() -> None:

    assert encode_syscnt_routing(2, 1) == b"\x02\x01\x00\x00"
    assert decode_syscnt_routing(b"\x01\x01\x00\x00") == (SyscntClockSource.EXTERNAL, True)
    for invalid in (b"", bytes(5), b"\x02\x00\x00\x00", b"\x00\x02\x00\x00", b"\x00\x00\x01\x00"):
        with pytest.raises(ValueError):
            decode_syscnt_routing(invalid)


# 测试Feature：只发送SYSCTRL原子动作，非法参数不会触发I/O。
# 测试方法：1. 核对SET与GET请求。2. 非法源和Boolean必须在发送前被拒绝。
# 通过条件：没有隐含计数器启动或复位；所有异常如实返回。
def test_syscnt_routing_driver() -> None:

    target = Mock()
    target.request.return_value = (SimpleNamespace(body=b""), None)
    driver = SysctrlDriver(target)
    driver.syscnt_source_set(0, SyscntClockSource.EXTERNAL)
    target.request.assert_called_once_with(
        SYSCTRL_SERVICE_ID, SysctrlCommand.SYSCNT_SOURCE_SET, body=b"\x00\x01\x00\x00"
    )
    target.reset_mock()
    driver.syscnt_halt_set(0, enabled=True)
    target.request.assert_called_once_with(
        SYSCTRL_SERVICE_ID, SysctrlCommand.SYSCNT_HALT_SET, body=b"\x00\x01\x00\x00"
    )
    target.reset_mock()
    for invalid in (-1, 2, True, 1.5):
        with pytest.raises(ValueError):
            driver.syscnt_source_set(0, invalid)
    with pytest.raises(ValueError):
        driver.syscnt_halt_set(0, enabled=1)
    target.request.assert_not_called()
    target.request.return_value = (SimpleNamespace(body=bytes(4)), None)
    assert driver.syscnt_routing_get(0) == (SyscntClockSource.INTERNAL, False)
    target.request.assert_called_once_with(
        SYSCTRL_SERVICE_ID, SysctrlCommand.SYSCNT_ROUTING_GET, body=bytes(4), retry_safe=True
    )
