# SPI正式Case的只读依赖入口。
# 职责：连接文件选择实例/引脚，核对Capability与Runtime注册交集。
# 边界：不初始化、不复位、不发送SPI数据、不执行GPIO配置。
# 依赖：Framework连接、Capability、硬件连接文件和本IP数据模型。

import os

import pytest

from ...core.errors import ConfigurationError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.gpio import GPIO_SERVICE_ID, GpioDriver
from ...drivers.spi import SPI_SERVICE_ID, SpiDriver
from ...profiles.hardware_connections import load_hardware_connections
from ._support import SIGNALS, SpiEndpoint, SpiSupport


# 只读验证逻辑GPIO映射，防止已经配置一端后才发现另一端引脚不合法。
@pytest.fixture
def spi_support(framework_communication, target_capabilities):

    connections = load_hardware_connections(
        capabilities=target_capabilities, expected_lane=os.environ.get("ET_TARGET_KIND")
    ).select("spi")["spi"]
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    if set(connections) != {"dut", "ref"}:
        raise ConfigurationError("SPI requires dut/ref connections")
    if not {(GPIO_SERVICE_ID, 0), (CRG_SERVICE_ID, 0)} <= services:
        raise ConfigurationError("SPI requires independent GPIO and CRG services")
    gpio = GpioDriver(framework_communication.target_client)
    endpoints = []

    # 只消费当前active区域；固件核对GPIO/逻辑信号/实例组合，不写Pinmux。
    for role in ("dut", "ref"):
        endpoint = connections[role]
        suffix = endpoint.handle.removeprefix("spi")
        if not suffix.isdecimal() or set(endpoint.gpio) != set(SIGNALS):
            raise ConfigurationError("invalid SPI handle or signal names")
        instance = int(suffix)
        if (SPI_SERVICE_ID, instance) not in services:
            raise ConfigurationError(f"SPI service absent: {endpoint.handle}")
        target_capabilities.interrupt("spi", "irq", instance=endpoint.handle)
        driver = SpiDriver(framework_communication.target_client, instance)
        pins = tuple((endpoint.gpio[name], function) for name, function in SIGNALS.items())
        for number, function in pins:
            gpio.validate_signal(number, function, instance)
        endpoints.append(SpiEndpoint(endpoint.handle, driver, driver.limits_get(), pins))

    if endpoints[0].spi.instance_id == endpoints[1].spi.instance_id:
        raise ConfigurationError("paired SPI requires distinct instances")
    return SpiSupport(*endpoints, gpio, CrgDriver(framework_communication.target_client))
