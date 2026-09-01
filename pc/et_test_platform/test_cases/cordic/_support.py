# CORDIC Formal Case 本地 Support。
#
# 职责：保存已经通过静态与运行时 Gate 的 CORDIC Driver 和只读能力事实。
# 边界：不修改硬件状态、不隐藏 Case 流程、不包含芯片 ID、物理地址或 IRQn。
# 依赖：仅依赖 CORDIC Driver、公共 Capability 查询和稳定错误类型。

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType
from typing import Any

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.cordic import (
    CordicCapabilities,
    CordicDriver,
    CordicFeature,
    CordicFunction,
    CordicIrqEvent,
)
from ...drivers.dma import DmaCapabilities, DmaDriver, DmaFeature
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SysctrlDriver
from ...profiles import chip_execution_mappings
from ...profiles.capabilities import ChipCapabilities


# 保存一个已通过静态与运行时 Gate 的 CORDIC 实例，不执行任何设备操作。
@dataclass(frozen=True, slots=True)
class CordicCaseSupport:
    instance_id: int
    instance_name: str
    cordic: CordicDriver
    runtime: CordicCapabilities


# 保存当前芯片已审核的 CORDIC 双向 DMA Request/Endpoint 执行事实。
#
# 该类型只描述 Case 所需的稳定路由字段，不包含芯片寄存器类型；当前芯片没有
# ``cordic_routes`` 扩展时，Resolver 会明确返回 UnsupportedCapability，Case 在
# 运行期失败关闭，而不是猜写历史 Request ID或把内部集成缺口记为SKIP。
@dataclass(frozen=True, slots=True)
class CordicDmaRoute:
    instance_id: int
    controller: int
    input_interface: int
    output_interface: int
    input_request_id: int
    output_request_id: int
    input_endpoint: int
    output_endpoint: int
    address_evidence: str
    request_evidence: str


# 保存 CORDIC DMA Case 所需的单 IP Driver 和跨 IP执行事实，不执行硬件动作。
@dataclass(frozen=True, slots=True)
class CordicDmaSupport:
    cordic_support: CordicCaseSupport
    dma: DmaDriver
    dma_capabilities: DmaCapabilities
    resource: ResourceDriver
    sysctrl: SysctrlDriver
    route: CordicDmaRoute


CordicSupportFactory = Callable[[int], CordicCaseSupport]


# 保存单个定点代表向量的芯片适配事实；Case仍使用独立PC数学Oracle判定。
@dataclass(frozen=True, slots=True)
class CordicFixedVector:
    arguments: tuple[float, ...]
    scale: int
    expected_primary: float
    expected_secondary: float | None
    primary_compensation: float
    secondary_compensation: float


# 保存公共CORDIC Case所需、但SVD无法完整表达的已审核数值执行语义。
@dataclass(frozen=True, slots=True)
class CordicExecutionSemantics:
    fixed_fraction_bits: Mapping[int, int]
    argument_storage_shift: Mapping[int, int]
    normalized_angle_divisor: float
    direct_angle_fraction_bits: Mapping[int, int]
    absolute_tolerance: float
    scale_maximum: int
    scale_affected_function: CordicFunction
    scale_argument: float
    scale_input_multiplier_base: float
    scale_output_multiplier_base: float
    scale_output_angle_unit: float
    precision_cycles: tuple[int, ...]
    argument_overflow_submit_count: int
    argument_overflow_result_read_count: int
    conversion_function: CordicFunction
    conversion_overflow_input: float
    conversion_underflow_input: float
    conversion_recovery_input: float
    fixed_vectors: Mapping[CordicFunction, CordicFixedVector]
    evidence: tuple[str, ...]


# 从目标芯片Execution Mapping读取CORDIC数值语义；缺失或不合法时在首次Mutation前失败关闭。
def resolve_cordic_execution_semantics(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> CordicExecutionSemantics:

    instance_name = f"cordic{instance_id}"
    if instance_name not in capabilities.instances("cordic"):
        raise UnsupportedCapability(f"capability profile has no CORDIC instance {instance_name!r}")

    module_name = f"{chip_execution_mappings.__package__}.{capabilities.chip_id}.cordic_semantics"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name in {
            f"{chip_execution_mappings.__package__}.{capabilities.chip_id}",
            module_name,
        }:
            raise UnsupportedCapability(
                f"chip {capabilities.chip_id!r} has no reviewed CORDIC numeric mapping"
            ) from error
        raise

    numeric = getattr(module, "CORDIC_NUMERIC_SEMANTICS", None)
    vectors = getattr(module, "CORDIC_FIXED_VECTORS", None)
    evidence = getattr(module, "CORDIC_SEMANTIC_EVIDENCE", None)
    if not isinstance(numeric, Mapping) or not isinstance(vectors, Mapping):
        raise UnsupportedCapability("CORDIC numeric mapping has an invalid structure")
    if (
        not isinstance(evidence, tuple)
        or not evidence
        or not all(isinstance(item, str) and item.strip() for item in evidence)
    ):
        raise UnsupportedCapability("CORDIC numeric mapping has no review evidence")

    function_by_name = {function.name.lower(): function for function in CordicFunction}
    fixed_vectors: dict[CordicFunction, CordicFixedVector] = {}
    for name, raw_vector in vectors.items():
        function = function_by_name.get(name)
        if function is None or not isinstance(raw_vector, tuple) or len(raw_vector) != 6:
            raise UnsupportedCapability("CORDIC fixed vector mapping is invalid")
        arguments, scale, expected_primary, expected_secondary, primary_factor, secondary_factor = (
            raw_vector
        )
        if (
            not isinstance(arguments, tuple)
            or not arguments
            or not all(isinstance(value, float) for value in arguments)
        ):
            raise UnsupportedCapability(f"CORDIC fixed vector {name!r} has invalid arguments")
        fixed_vectors[function] = CordicFixedVector(
            arguments=arguments,
            scale=_required_int(numeric_value=scale, label=f"{name}.scale", minimum=0),
            expected_primary=_required_float(expected_primary, f"{name}.expected_primary"),
            expected_secondary=(
                None
                if expected_secondary is None
                else _required_float(expected_secondary, f"{name}.expected_secondary")
            ),
            primary_compensation=_required_positive_float(
                primary_factor, f"{name}.primary_compensation"
            ),
            secondary_compensation=_required_positive_float(
                secondary_factor, f"{name}.secondary_compensation"
            ),
        )
    if set(fixed_vectors) != set(CordicFunction):
        raise UnsupportedCapability("CORDIC fixed vector mapping does not cover all functions")

    precision_minimum = _mapping_int(numeric, "precision_minimum_cycles", minimum=1)
    precision_maximum = _mapping_int(
        numeric,
        "precision_maximum_cycles",
        minimum=precision_minimum,
    )
    return CordicExecutionSemantics(
        fixed_fraction_bits=MappingProxyType(
            {
                16: _mapping_int(numeric, "fixed_fraction_bits_16", minimum=1),
                32: _mapping_int(numeric, "fixed_fraction_bits_32", minimum=1),
            }
        ),
        argument_storage_shift=MappingProxyType(
            {
                16: _mapping_int(numeric, "argument_storage_shift_16", minimum=0),
                32: _mapping_int(numeric, "argument_storage_shift_32", minimum=0),
            }
        ),
        normalized_angle_divisor=_mapping_positive_float(numeric, "normalized_angle_divisor"),
        direct_angle_fraction_bits=MappingProxyType(
            {
                16: _mapping_int(numeric, "direct_angle_fraction_bits_16", minimum=1),
                32: _mapping_int(numeric, "direct_angle_fraction_bits_32", minimum=1),
            }
        ),
        absolute_tolerance=_mapping_positive_float(numeric, "absolute_tolerance"),
        scale_maximum=_mapping_int(numeric, "scale_maximum", minimum=0),
        scale_affected_function=_mapping_function(
            numeric, "scale_affected_function", function_by_name
        ),
        scale_argument=_mapping_float(numeric, "scale_argument"),
        scale_input_multiplier_base=_mapping_positive_float(numeric, "scale_input_multiplier_base"),
        scale_output_multiplier_base=_mapping_positive_float(
            numeric, "scale_output_multiplier_base"
        ),
        scale_output_angle_unit=_mapping_positive_float(numeric, "scale_output_angle_unit"),
        precision_cycles=tuple(range(precision_minimum, precision_maximum + 1)),
        argument_overflow_submit_count=_mapping_int(
            numeric, "argument_overflow_submit_count", minimum=1
        ),
        argument_overflow_result_read_count=_mapping_int(
            numeric,
            "argument_overflow_result_read_count",
            minimum=1,
        ),
        conversion_function=_mapping_function(numeric, "conversion_function", function_by_name),
        conversion_overflow_input=_mapping_float(numeric, "conversion_overflow_input"),
        conversion_underflow_input=_mapping_float(numeric, "conversion_underflow_input"),
        conversion_recovery_input=_mapping_float(numeric, "conversion_recovery_input"),
        fixed_vectors=MappingProxyType(fixed_vectors),
        evidence=evidence,
    )


# 校验映射中的整数值，拒绝Bool借用整数语义。
def _required_int(*, numeric_value: object, label: str, minimum: int) -> int:

    if isinstance(numeric_value, bool) or not isinstance(numeric_value, int):
        raise UnsupportedCapability(f"CORDIC mapping {label!r} must be an integer")
    if numeric_value < minimum:
        raise UnsupportedCapability(f"CORDIC mapping {label!r} is below {minimum}")
    return numeric_value


# 读取并校验映射整数成员。
def _mapping_int(mapping: Mapping[str, object], name: str, *, minimum: int) -> int:

    return _required_int(numeric_value=mapping.get(name), label=name, minimum=minimum)


# 校验映射中的浮点值。
def _required_float(value: object, label: str) -> float:

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnsupportedCapability(f"CORDIC mapping {label!r} must be numeric")
    return float(value)


# 校验映射中的正浮点值。
def _required_positive_float(value: object, label: str) -> float:

    normalized = _required_float(value, label)
    if normalized <= 0.0:
        raise UnsupportedCapability(f"CORDIC mapping {label!r} must be positive")
    return normalized


# 读取映射浮点成员。
def _mapping_float(mapping: Mapping[str, object], name: str) -> float:

    return _required_float(mapping.get(name), name)


# 读取映射正浮点成员。
def _mapping_positive_float(mapping: Mapping[str, object], name: str) -> float:

    return _required_positive_float(mapping.get(name), name)


# 把芯片映射中的稳定函数名转换为公共枚举。
def _mapping_function(
    mapping: Mapping[str, object],
    name: str,
    function_by_name: Mapping[str, CordicFunction],
) -> CordicFunction:

    raw_name = mapping.get(name)
    if not isinstance(raw_name, str) or raw_name not in function_by_name:
        raise UnsupportedCapability(f"CORDIC mapping {name!r} has an invalid function")
    return function_by_name[raw_name]


# 核对 CORDIC 实例、IRQ Feature 与 Source 均由当前 Capability 明确声明。
def require_cordic_static_irq_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    event: CordicIrqEvent | None = None,
) -> str:

    instance = f"cordic{instance_id}"
    try:
        if instance not in capabilities.instances("cordic"):
            raise UnsupportedCapability(f"CORDIC instance {instance!r} is unavailable")
        if not capabilities.has_feature("cordic", "interrupts", instance=instance):
            raise UnsupportedCapability(f"{instance} does not declare interrupts")
        if event is not None:
            source_name = {
                CordicIrqEvent.ARG_OVERFLOW: "arg_overflow",
                CordicIrqEvent.CALCULATION_COMPLETE: "calculation_complete",
                CordicIrqEvent.PM_ARG2_ERROR: "pm_arg2_error",
            }.get(event)
            if source_name is None or source_name not in capabilities.options(
                "cordic",
                "irq_sources",
                instance=instance,
            ):
                raise UnsupportedCapability(f"{instance} does not declare IRQ source {event!r}")
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as error:
        raise UnsupportedCapability(f"CORDIC static capability is unavailable: {error}") from error


# 核对运行中 Service 的 IRQ Feature 与 Source，拒绝静态能力冒充运行能力。
def require_cordic_runtime_irq_capability(
    runtime: CordicCapabilities,
    event: CordicIrqEvent,
) -> None:

    if event == 0 or event & ~runtime.irq_events:
        raise UnsupportedCapability(f"running CORDIC service does not support IRQ event {event!r}")


# 从当前芯片 Execution Mapping 读取 CORDIC 双向 DMA 路由；缺失时不创建替代事实。
def resolve_cordic_dma_route(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
) -> CordicDmaRoute:

    instance_name = f"cordic{instance_id}"
    if instance_name not in capabilities.instances("cordic"):
        raise UnsupportedCapability(f"capability profile has no CORDIC instance {instance_name!r}")

    chip_id = capabilities.chip_id
    module_name = f"{chip_execution_mappings.__package__}.{chip_id}.cordic_routes"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name in {
            f"{chip_execution_mappings.__package__}.{chip_id}",
            module_name,
        }:
            raise UnsupportedCapability(
                f"chip {chip_id!r} has no reviewed CORDIC DMA execution mapping"
            ) from error
        raise

    raw_mapping = getattr(module, "CORDIC_DMA_MAPPING", None)
    raw_route = _select_cordic_dma_mapping(raw_mapping, instance_id)
    route = _build_cordic_dma_route(raw_route, instance_id=instance_id)
    if route.controller not in _dma_controller_ids(capabilities):
        raise UnsupportedCapability(
            f"CORDIC DMA mapping controller {route.controller} is absent from capability"
        )
    return route


# 兼容按实例表和单实例对象两种只读 Mapping 导出方式，但不放宽字段契约。
def _select_cordic_dma_mapping(raw_mapping: Any, instance_id: int) -> Any:

    if raw_mapping is None:
        raise UnsupportedCapability("CORDIC DMA execution mapping is not declared")
    if isinstance(raw_mapping, Mapping):
        if all(
            key in raw_mapping
            for key in (
                "controller",
                "input_interface",
                "output_interface",
                "input_request_id",
                "output_request_id",
                "input_endpoint",
                "output_endpoint",
            )
        ):
            return raw_mapping
        selected = raw_mapping.get(instance_id, raw_mapping.get(str(instance_id)))
        if selected is None:
            raise UnsupportedCapability(f"CORDIC DMA mapping has no instance {instance_id} entry")
        return selected
    return raw_mapping


# 把 Mapping 对象或已构造的只读对象收敛成 Case 内稳定 Route。
def _build_cordic_dma_route(raw_route: Any, *, instance_id: int) -> CordicDmaRoute:

    def field(name: str) -> Any:
        if isinstance(raw_route, Mapping):
            return raw_route.get(name)
        return getattr(raw_route, name, None)

    values = {
        name: field(name)
        for name in (
            "controller",
            "input_interface",
            "output_interface",
            "input_request_id",
            "output_request_id",
            "input_endpoint",
            "output_endpoint",
            "address_evidence",
            "request_evidence",
        )
    }
    integer_fields = (
        "controller",
        "input_interface",
        "output_interface",
        "input_request_id",
        "output_request_id",
        "input_endpoint",
        "output_endpoint",
    )
    if any(
        isinstance(values[name], bool) or not isinstance(values[name], int) or values[name] < 0
        for name in integer_fields
    ):
        raise UnsupportedCapability("CORDIC DMA execution mapping has invalid numeric fields")
    if values["input_endpoint"] == 0 or values["output_endpoint"] == 0:
        raise UnsupportedCapability("CORDIC DMA execution mapping has a zero endpoint")
    if values["input_request_id"] == values["output_request_id"]:
        raise UnsupportedCapability("CORDIC DMA input/output Request IDs must be distinct")
    if values["input_interface"] == values["output_interface"]:
        raise UnsupportedCapability("CORDIC DMA input/output interfaces must be distinct")
    if not isinstance(values["address_evidence"], str) or not values["address_evidence"].strip():
        raise UnsupportedCapability("CORDIC DMA address evidence is missing")
    if not isinstance(values["request_evidence"], str) or not values["request_evidence"].strip():
        raise UnsupportedCapability("CORDIC DMA Request evidence is missing")
    return CordicDmaRoute(instance_id=instance_id, **values)


# 返回静态 Capability 中声明的 DMA Controller 编号集合。
def _dma_controller_ids(capabilities: ChipCapabilities) -> set[int]:

    return {
        int(name.removeprefix("dma"))
        for name in capabilities.instances("dma")
        if name.startswith("dma") and name.removeprefix("dma").isdecimal()
    }


# 核对 CORDIC Runtime 与 DMA Runtime 的稳定功能交集。
def require_cordic_dma_runtime_capability(
    cordic_runtime: CordicCapabilities,
    dma_capabilities: DmaCapabilities,
) -> None:

    if not cordic_runtime.features & CordicFeature.DMA:
        raise UnsupportedCapability("running CORDIC service does not support DMA work mode")
    required = DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY
    if dma_capabilities.features & required != required:
        raise UnsupportedCapability("running DMA service lacks bidirectional transfer features")
