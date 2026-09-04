# SPI正式Case的只读依赖入口。
# 职责：连接文件选择实例/引脚，核对Capability与Runtime注册交集。
# 边界：不初始化、不复位、不发送SPI数据、不执行GPIO配置。
# 依赖：Framework连接、Capability、硬件连接文件和本IP数据模型。

import os

import pytest

from ...core.errors import ConfigurationError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver
from ...drivers.gpio import GPIO_SERVICE_ID, GpioDriver
from ...drivers.spi import SPI_SERVICE_ID, SpiDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.hardware_connections import load_hardware_connections
from ._support import SIGNALS, SpiEndpoint, SpiSupport, dma_mapping


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
        endpoints.append(
            SpiEndpoint(
                endpoint.handle, driver, driver.limits_get(), pins, driver.fifo_limits_get()
            )
        )

    if endpoints[0].spi.instance_id == endpoints[1].spi.instance_id:
        raise ConfigurationError("paired SPI requires distinct instances")
    return SpiSupport(*endpoints, gpio, CrgDriver(framework_communication.target_client))


# DMA依赖只读选择：四通道分别服务两端RX/TX，不在Fixture中启动或复位。
@pytest.fixture
def spi_dma_support(spi_support, framework_communication, target_capabilities):

    mapping = dma_mapping(target_capabilities.chip_id)
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    candidates = [
        index
        for index in mapping.SPI_DMA_CONTROLLERS
        if f"dma{index}" in target_capabilities.instances("dma")
        and (DMA_SERVICE_ID, index) in services
    ]
    if not candidates or (SYSCTRL_SERVICE_ID, 0) not in services:
        raise ConfigurationError("SPI DMA requires DMA/SYSCTRL registry intersection")
    dma = DmaDriver(framework_communication.target_client, candidates[0])
    if dma.capabilities_get().channel_count < 4 or len(mapping.SPI_DMA_INTERFACES) < 4:
        raise ConfigurationError("bidirectional SPI DMA requires four channels/interfaces")

    # 数据地址由SPI自身发布，必须与独立SDK执行映射相符，不猜测端口地址。
    for endpoint in (spi_support.dut, spi_support.ref):
        expected = mapping.SPI_DMA_ENDPOINTS[endpoint.spi.instance_id][0]
        if endpoint.spi.dma_endpoint_get() != expected:
            raise ConfigurationError("SPI DMA endpoint disagrees with chip mapping")
    return dma, SysctrlDriver(framework_communication.target_client), mapping


# 单实例PAD回接必须由连接文件明确声明loopback角色；双SPI对接不能冒充该接线。
@pytest.fixture
def spi_external_support(framework_communication, target_capabilities):

    connections = load_hardware_connections(
        capabilities=target_capabilities, expected_lane=os.environ.get("ET_TARGET_KIND")
    )
    if set(connections.ips.get("spi", {})) != {"loopback"}:
        pytest.skip("当前为双SPI四线对接，未声明单SPI MOSI→MISO短接；该独立接线Case不执行")
    endpoint = connections.select("spi")["spi"]["loopback"]
    instance = int(endpoint.handle.removeprefix("spi"))
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    if not {(SPI_SERVICE_ID, instance), (GPIO_SERVICE_ID, 0), (CRG_SERVICE_ID, 0)} <= services:
        raise ConfigurationError("external SPI loop requires SPI/GPIO/CRG services")
    if set(endpoint.gpio) != set(SIGNALS):
        raise ConfigurationError("external SPI loop requires four signal GPIOs")
    gpio_driver = GpioDriver(framework_communication.target_client)
    driver = SpiDriver(framework_communication.target_client, instance)
    pins = tuple((endpoint.gpio[name], function) for name, function in SIGNALS.items())

    # 只读核对GPIO映射，不在Fixture中开启Pinmux或SPI。
    for number, function in pins:
        gpio_driver.validate_signal(number, function, instance)
    selected = SpiEndpoint(
        endpoint.handle, driver, driver.limits_get(), pins, driver.fifo_limits_get()
    )
    return SpiSupport(
        selected, selected, gpio_driver, CrgDriver(framework_communication.target_client)
    )
