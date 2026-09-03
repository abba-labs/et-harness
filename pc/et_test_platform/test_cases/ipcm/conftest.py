# IPCM正式Case对象与参数入口。
# 职责：Capability/Registry交集、Driver构造和静态参数矩阵。
# 边界：不复位、不配置、不发送消息；内部映射缺口明确失败。
# 依赖：现有Framework连接、Capability/Bench Loader及IPCM公开Driver。

import pytest

from ...core.errors import ConfigurationError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.ipcm import IPCM_SERVICE_ID, IpcmDriver
from ...profiles.bench import load_serial_target
from ...profiles.capabilities import load_packaged_chip_capabilities
from ._support import IpcmSupport, resolve_routes


# 无硬件收集时只产生明确占位参数；HIL依据选定Bench的Capability展开全部Mailbox。
def pytest_generate_tests(metafunc):

    if "ipcm_mailbox" not in metafunc.fixturenames:
        return
    bench = metafunc.config.getoption("et_bench")
    if not bench:
        metafunc.parametrize("ipcm_mailbox", [None], ids=["capability_required"])
        return
    target = load_serial_target(bench, metafunc.config.getoption("et_target"))
    capabilities = load_packaged_chip_capabilities(target.chip_id)
    instance = capabilities.instances("ipcm")[0]
    count = capabilities.limit("ipcm", "mailbox_count", instance=instance)
    metafunc.parametrize(
        "ipcm_mailbox", range(count), ids=[f"mailbox_{index}" for index in range(count)]
    )


# 读取硬件容量并构造独立本核/Peer Driver；Peer身份在每次实际转发时检查。
@pytest.fixture
def ipcm_support(framework_communication, target_capabilities):

    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    instances = target_capabilities.instances("ipcm")
    shared = [
        name
        for name in instances
        if name.startswith("ipcm")
        and name[4:].isdecimal()
        and (IPCM_SERVICE_ID, int(name[4:])) in services
    ]
    if not shared or (CRG_SERVICE_ID, 0) not in services:
        raise ConfigurationError("IPCM/CRG service is missing from the firmware registry")
    name = shared[0]
    instance = int(name[4:])
    local = IpcmDriver(framework_communication.target_client, instance)
    runtime = local.capabilities_get()
    values = tuple(
        target_capabilities.limit("ipcm", key, instance=name)
        for key in (
            "mailbox_count",
            "channel_count",
            "data_word_count",
            "payload_bytes_per_mailbox",
        )
    )
    local_endpoint, peer_endpoint, second_endpoint, identity = resolve_routes(
        target_capabilities, values[1]
    )
    return IpcmSupport(
        local,
        IpcmDriver(framework_communication.target_client, instance, peer_identity=identity),
        CrgDriver(framework_communication.target_client),
        runtime,
        target_capabilities,
        name,
        local_endpoint,
        peer_endpoint,
        second_endpoint,
        identity,
        *values,
    )
