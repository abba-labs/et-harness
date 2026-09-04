# GPIO PC命令合同测试。
# 职责：校验请求字节、独立Service路由和错误参数无副作用。
# 边界：Target桩不模拟引脚电平，不计入硬件测试覆盖。
# 依赖：pytest及真实GPIO Driver。

from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.gpio import GpioDriver, GpioFunction


# 保存唯一一次请求，测试代码独立给定期望字节。
class Target:
    def __init__(self, response=b""):
        self.calls = []
        self.response = response

    def request(self, service_id, command_id, **kwargs):
        self.calls.append((service_id, command_id, kwargs))
        return SimpleNamespace(body=self.response), None


# 测试Feature：GPIO Service路由与三字段u16LE编码。
# 测试方法：分别调用查询和配置，固定给定高字节非零的GPIO/实例以及SPI信号。
# 通过条件：Service实例为0、外设实例在body内，只有查询允许安全重试。
@pytest.mark.parametrize("method,command", [("validate_signal", 1), ("configure_signal", 2)])
def test_gpio_wire_golden_vector(method, command):
    target = Target()
    getattr(GpioDriver(target), method)(0x1234, GpioFunction.SPI_CLK, 0x9ABC, timeout_s=0.5)
    assert target.calls == [
        (
            0x0014,
            command,
            {
                "instance_id": 0,
                "body": b"\x34\x12\x03\x00\xbc\x9a",
                "timeout_s": 0.5,
                "retry_safe": command == 1,
            },
        )
    ]


# 测试Feature：参数边界拒绝与无请求副作用。
# 测试方法：传入越界值、Boolean、字符串及未命名功能。
# 通过条件：发送前抛出ValueError，Target始终没有收到请求。
@pytest.mark.parametrize(
    "pin,function,instance",
    [
        (-1, GpioFunction.SPI_CLK, 0),
        (65536, GpioFunction.SPI_CLK, 0),
        (True, GpioFunction.SPI_CLK, 0),
        (1, 3, 0),
        (1, GpioFunction.SPI_CLK, -1),
        (1, GpioFunction.SPI_CLK, "0"),
    ],
)
def test_gpio_invalid_input_does_not_send(pin, function, instance):
    target = Target()
    with pytest.raises(ValueError):
        GpioDriver(target).configure_signal(pin, function, instance)
    assert target.calls == []


# 测试Feature：响应长度固定为空，不忽略旧固件或错误Service返回的额外数据。
# 测试方法：Target返回一个多余字节。
# 通过条件：ProtocolError，命令只发送一次。
def test_gpio_rejects_nonempty_response():
    target = Target(b"\x00")
    with pytest.raises(ProtocolError):
        GpioDriver(target).configure_signal(60, GpioFunction.SPI_CLK, 0)
    assert len(target.calls) == 1
