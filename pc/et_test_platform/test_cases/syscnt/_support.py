# SYSCNT能力与执行事实解析。
# 职责：构造类型化对象，核对Registry/YAML/Runtime交集。
# 边界：不执行Feature配置、基线或断言，不将内部缺口改成SKIP。
# 依赖：本IP/支撑IP Driver、Capability和芯片Execution Mapping。

from dataclasses import dataclass
from importlib import import_module

from ...core.errors import ConfigurationError
from ...drivers.crg import CrgDriver
from ...drivers.syscnt import SyscntCapabilities, SyscntDriver, SyscntHaltPolicy
from ...drivers.sysctrl import SysctrlDriver
from ...profiles import chip_execution_mappings
from ...profiles.capabilities import ChipCapabilities
from ...programmers import HaltSampleSpec


@dataclass(frozen=True, slots=True)
class SyscntSupport:
    counter: SyscntDriver
    crg: CrgDriver
    sysctrl: SysctrlDriver
    runtime: SyscntCapabilities
    source_hz: tuple[tuple[int, int], ...]
    reference_hz: int
    clock_evidence: str
    halt_spec: HaltSampleSpec
    halt_mask: int


# 缺少或未核实的实际频率失败关闭；不使用CNTFID0反推被测时钟。
def resolve_mapping(capabilities: ChipCapabilities) -> tuple:
    name = f"{chip_execution_mappings.__package__}.{capabilities.chip_id}.syscnt_routes"
    try:
        module = import_module(name)
    except ModuleNotFoundError as error:
        if error.name in (name, name.rpartition(".")[0]):
            raise ConfigurationError("SYSCNT execution mapping is missing") from error
        raise
    clocks = tuple(
        (source, module.SYSCNT_CLOCK_HZ.get(source)) for source in module.SYSCNT_SOURCE_IDS
    )
    if not clocks or any(type(hz) is not int or hz <= 0 for _, hz in clocks):
        raise ConfigurationError(
            "SYSCNT input clock frequencies require independent confirmation (G02)"
        )
    return (
        clocks,
        module.SYSCNT_REFERENCE_HZ,
        module.SYSCNT_CLOCK_EVIDENCE,
        module.SYSCNT_HALT_SAMPLE,
        module.SYSCNT_HALT_MASK,
    )


# 仅列出直接恢复动作；既有聚合器保证某一步失败不阻止后续资源归还。
def cleanup_actions(support, resource, old_route):
    counter = support.counter
    return (
        ("counter stop", lambda: counter.enable_set(False)),
        ("counter run-free", lambda: counter.halt_policy_set(SyscntHaltPolicy.RUN_FREE)),
        ("reference release", lambda: counter.reference_enable_set(False)),
        (
            "source restore",
            lambda: support.sysctrl.syscnt_source_set(counter.instance_id, old_route[0]),
        ),
        (
            "halt route restore",
            lambda: support.sysctrl.syscnt_halt_set(counter.instance_id, enabled=old_route[1]),
        ),
        ("resource pool reset", resource.reset),
    )
