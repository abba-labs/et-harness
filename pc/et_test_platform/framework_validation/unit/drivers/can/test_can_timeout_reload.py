# CAN连续Timeout重装Wire回归。
# 职责：固定命令、真实前后计数、精确长度和禁止重试验证。
# 边界：不模拟计数器、不把软件向量作为硬件到期证据。
# 依赖：真实CanDriver及固定响应替身。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import CanDriver
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub


# 测试Feature：单次重装返回的前后读值不是TOP配置回显。
# 测试方法：提供非整值独立Wire，核对实例、命令和重试属性。
# 通过条件：输出9/997，无隐式GET/INIT，写动作不重试。
def test_timeout_reload_golden():
    target = TargetStub([pack("<2I", 9, 997)])
    assert CanDriver(target, 2).timeout_reload(timeout_s=0.3) == (9, 997)
    assert len(target.requests) == 1
    request = target.requests[0]
    assert request["command"] == 62 and request["body"] == b"\x02"
    assert request["timeout_s"] == 0.3 and request["retry_safe"] is False


# 测试Feature：计数位宽和协议长度严格验证。
# 测试方法：响应分别超出16-bit或缺少/多出word。
# 通过条件：非法响应均失败关闭，不截断为合法计数。
@pytest.mark.parametrize("words", ((65536, 1), (1, 65536), (1,), (1, 2, 3)))
def test_timeout_reload_invalid_response(words):
    target = TargetStub([pack(f"<{len(words)}I", *words)])
    with pytest.raises(ProtocolError):
        CanDriver(target, 0).timeout_reload()
