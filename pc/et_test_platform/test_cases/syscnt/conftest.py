# SYSCNT Formal Case依赖入口。
# 职责：解析能力、绑定逻辑实例和构造Driver。
# 边界：无配置、启动、停止或复位；执行步骤留在Case。
# 依赖：平台Framework连接、Capability和本IP支持数据。

import pytest

from ...core.errors import ConfigurationError
from ...drivers.crg import CRG_SERVICE_ID, CrgDriver
from ...drivers.syscnt import SYSCNT_SERVICE_ID, SyscntDriver, SyscntFeature
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.bench import load_serial_target
from ...profiles.capabilities import load_packaged_chip_capabilities
from ._support import SyscntSupport, resolve_mapping


# 从目标执行映射选择可用时钟源；无Bench的静态收集只使用明确占位参数。
def pytest_generate_tests(metafunc):
    if "syscnt_clock_source" in metafunc.fixturenames:
        bench = metafunc.config.getoption("et_bench")
        if not bench:
            metafunc.parametrize("syscnt_clock_source", [None], ids=["capability_required"])
            return
        target = load_serial_target(bench, metafunc.config.getoption("et_target"))
        mapping = resolve_mapping(load_packaged_chip_capabilities(target.chip_id))
        sources = [source for source, _ in mapping[0]]
        metafunc.parametrize(
            "syscnt_clock_source", sources, ids=[f"source_{source}" for source in sources]
        )


# 只读Runtime与YAML互相核对，能力缺失属于内部配置错误。
@pytest.fixture
def syscnt_support(framework_communication, target_capabilities) -> SyscntSupport:
    services = {
        (item.service_id, item.instance_id) for item in framework_communication.runtime_services
    }
    instances = target_capabilities.instances("syscnt")
    shared = [
        name
        for name in instances
        if name.startswith("syscnt")
        and name[6:].isdecimal()
        and (SYSCNT_SERVICE_ID, int(name[6:])) in services
    ]
    if not shared or any(
        (service, 0) not in services for service in (CRG_SERVICE_ID, SYSCTRL_SERVICE_ID)
    ):
        raise ConfigurationError("SYSCNT/CRG/SYSCTRL registry intersection is empty")
    name = shared[0]
    counter = SyscntDriver(framework_communication.target_client, int(name[6:]))
    runtime = counter.capabilities_get()
    if runtime.features != SyscntFeature.ALL or runtime.view_mask != 3:
        raise ConfigurationError("SYSCNT runtime omits required atomic operations")
    widths = tuple(
        target_capabilities.limit("syscnt", key, instance=name)
        for key in ("counter_bits", "word_bits")
    )
    if widths != (runtime.counter_bits, runtime.word_bits):
        raise ConfigurationError("SYSCNT SVD/runtime widths disagree")
    for feature in ("counter", "debug_halt", "frequency_id"):
        if not target_capabilities.has_feature("syscnt", feature, instance=name):
            raise ConfigurationError(f"SYSCNT capability missing: {feature}")
    return SyscntSupport(
        counter,
        CrgDriver(framework_communication.target_client),
        SysctrlDriver(framework_communication.target_client),
        runtime,
        *resolve_mapping(target_capabilities),
    )
