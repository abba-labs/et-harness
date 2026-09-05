# CAN正式Case只读依赖入口。
# 职责：从唯一连接文件获取handle，核对Capability与Firmware注册交集。
# 边界：不复位、不配置Pinmux、不启动CAN；盒子基础连接另行按明确设备配置管理。
# 依赖：当前Framework连接、Capability、CAN/CRG Driver和本IP Support。

import os
from dataclasses import replace
from pathlib import Path

import pytest

from ...core.errors import ConfigurationError
from ...drivers.can import CAN_SERVICE_ID, CanDriver
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.gpio import GPIO_SERVICE_ID, GpioDriver, GpioFunction
from ...instruments.can_boxes.connection import create_zlg_can_box_from_environment
from ...profiles.hardware_connections import load_hardware_connections
from ._support import CanSupport, chip_mapping


# 选择唯一dut角色并做只读一致性核对；不将缺失命令或时钟映射降级为SKIP。
@pytest.fixture
def can_support(framework_communication, target_capabilities):

    connections = load_hardware_connections(
        capabilities=target_capabilities, expected_lane=os.environ.get("ET_TARGET_KIND")
    )
    # 内部回环只消费实例选择，不占用或校验外部引脚；外部Case另行select并验证GPIO。
    selected = connections.ips.get("can", {})
    if set(selected) != {"dut"}:
        raise ConfigurationError(
            "CAN requires one explicit dut role; box is an external instrument"
        )
    endpoint = selected["dut"]
    suffix = endpoint.handle.removeprefix("can")
    if not suffix.isdecimal():
        raise ConfigurationError("CAN connection requires a logical CAN handle")
    instance = int(suffix)
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    if not {(CAN_SERVICE_ID, instance), (CRG_SERVICE_ID, 0)} <= services:
        raise ConfigurationError("CAN/CRG services do not match the local capability/connection")
    target_capabilities.interrupt("can", "int0", instance=endpoint.handle)
    mapping = chip_mapping(target_capabilities.chip_id)
    if connections.lane not in mapping.CAN_CLOCK_HZ:
        raise ConfigurationError("CAN input clock is not yet confirmed for this target lane")

    # 仅获取本次内部测试用到的限制，不提前创建外部GPIO依赖。
    target = framework_communication.target_client
    driver = CanDriver(target, instance)
    return CanSupport(
        endpoint.handle,
        driver,
        CrgDriver(target),
        driver.ram_limits_get(),
        driver.timing_limits_get(),
        mapping,
        mapping.CAN_CLOCK_HZ[connections.lane],
    )


# 全实例只读入口：核对Capability与Runtime交集，不配置硬件或截取代表实例。
@pytest.fixture
def can_instance_supports(can_support, framework_communication, target_capabilities):

    # 全实例是本Case的Feature，不沿用普通Case的代表实例选择。
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    supports = []

    # 只查询限制并构造Driver；任何复位和配置均留在Case主体。
    for handle in target_capabilities.instances("can"):
        suffix = handle.removeprefix("can")
        if not suffix.isdecimal() or (CAN_SERVICE_ID, int(suffix)) not in services:
            raise ConfigurationError(f"CAN instance has no matching runtime service: {handle}")
        driver = CanDriver(framework_communication.target_client, int(suffix))
        supports.append(
            replace(
                can_support,
                handle=handle,
                can=driver,
                ram_limits=driver.ram_limits_get(),
                timing_limits=driver.timing_limits_get(),
            )
        )

    if len(supports) < 2:
        raise ConfigurationError("CAN isolation requires at least two declared instances")
    return tuple(supports)


# 外部依赖只读选择：GPIO独立验证、盒子仅构造对象；不在Fixture中打开或配置设备。
@pytest.fixture
def can_external_support(can_support, framework_communication, target_capabilities):

    connections = load_hardware_connections(
        capabilities=target_capabilities, expected_lane=os.environ.get("ET_TARGET_KIND")
    ).select("can")["can"]
    endpoint = connections["dut"]
    if endpoint.handle != can_support.handle or set(endpoint.gpio) != {"rx", "tx"}:
        raise ConfigurationError("CAN external connection requires the selected handle and RX/TX")
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    if (GPIO_SERVICE_ID, 0) not in services:
        raise ConfigurationError("CAN external case requires independent GPIO Service")

    # 仅核对本Case的两根引脚，不全局禁止其他串行Case复用这些GPIO。
    gpio = GpioDriver(framework_communication.target_client)
    pins = ((endpoint.gpio["rx"], GpioFunction.CAN_RX), (endpoint.gpio["tx"], GpioFunction.CAN_TX))
    for number, function in pins:
        gpio.validate_signal(number, function, can_support.can.instance_id)
    box = create_zlg_can_box_from_environment(os.environ, device_name="can_box", base=Path.cwd())
    return can_support, gpio, pins, box


# 只为外部IRQ参数节点解析盒子和引脚；内部节点不要求GPIO Service或外部设备。
@pytest.fixture
def can_irq_peer(request, mode):

    if mode == "internal":
        return None

    return request.getfixturevalue("can_external_support")
