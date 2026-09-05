# CAN正式Case只读依赖入口。
# 职责：从唯一连接文件获取handle，核对Capability与Firmware注册交集。
# 边界：不复位、不配置Pinmux、不启动CAN；盒子基础连接另行按明确设备配置管理。
# 依赖：当前Framework连接、Capability、CAN/CRG Driver和本IP Support。

import os

import pytest

from ...core.errors import ConfigurationError
from ...drivers.can import CAN_SERVICE_ID, CanDriver
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
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
