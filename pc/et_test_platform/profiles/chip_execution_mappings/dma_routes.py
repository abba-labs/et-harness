# 芯片无关的 DMA 外设执行映射模型与加载入口。
#
# 职责：定义公共 DMA 路由事实类型，并按运行时 chip_id 加载对应芯片的只读执行映射。
# 边界：不导入具体芯片模块、不访问 TargetClient、不发送硬件命令，也不执行 Test Case 判断。
# 依赖：仅依赖标准库和平台公共异常；具体芯片只需新增同名映射模块。

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from functools import cache
from importlib import import_module

from ...core.errors import ConfigurationError, UnsupportedCapability

_CHIP_ID = re.compile(r"^[a-z][a-z0-9_]*$")


# 表示 DMA 外设方向的稳定公共语义，不包含任何芯片私有值。
class DmaPeripheralDirection(str, Enum):
    TX = "tx"
    RX = "rx"


# 表示单个芯片已审核的 DMA 外设映射事实，不执行任何硬件动作。
@dataclass(frozen=True, slots=True)
class DmaPeripheralMapping:
    peripheral: str
    instance_id: int
    direction: DmaPeripheralDirection
    peripheral_address: int
    request_id: int
    allowed_controllers: tuple[int, ...]
    allowed_interfaces: tuple[int, ...]
    address_evidence: str
    request_evidence: str


# 表示无外接 Bench 的单向 DMA 输入端点映射事实。
@dataclass(frozen=True, slots=True)
class DmaInputMapping:
    peripheral: str
    instance_id: int
    peripheral_address: int
    request_id: int
    allowed_controllers: tuple[int, ...]
    allowed_interfaces: tuple[int, ...]
    address_evidence: str
    request_evidence: str


# 表示一个双向 AES DMA 数据路径的芯片事实，不选择具体 Controller/Interface。
@dataclass(frozen=True, slots=True)
class AesDmaMapping:
    instance_id: int
    input_fifo_address: int
    output_fifo_address: int
    input_register_address: int
    output_register_address: int
    input_request_id: int
    output_request_id: int
    allowed_controllers: tuple[int, ...]
    allowed_interfaces: tuple[int, ...]
    address_evidence: str
    request_evidence: str


# 按 chip_id 加载 UART DMA 映射；缺少芯片扩展时明确报告不支持而不修改公共 Resolver。
@cache
def load_uart_dma_mappings(
    chip_id: str,
) -> Mapping[tuple[int, DmaPeripheralDirection], DmaPeripheralMapping]:

    normalized_chip = _require_chip_id(chip_id)
    package = __package__ or ""
    chip_package = f"{package}.{normalized_chip}"
    module_name = f"{chip_package}.dma_routes"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name in {chip_package, module_name}:
            raise UnsupportedCapability(
                f"UART DMA execution mapping is unavailable for chip {normalized_chip!r}"
            ) from exc
        raise

    mappings = getattr(module, "UART_DMA_MAPPINGS", None)
    if not isinstance(mappings, Mapping) or not mappings:
        raise ConfigurationError(
            f"chip {normalized_chip!r} UART DMA mapping module must export non-empty "
            "UART_DMA_MAPPINGS"
        )
    for key, mapping in mappings.items():
        _validate_uart_dma_mapping(normalized_chip, key, mapping)
    return mappings


# 按 chip_id 加载 CRC DMA 输入映射；缺少扩展时明确报告不支持。
@cache
def load_crc_dma_mapping(chip_id: str) -> DmaInputMapping:

    mappings = load_dma_input_mappings(chip_id, "crc")
    mapping = mappings.get(0)
    if mapping is None:
        raise UnsupportedCapability(f"chip {chip_id!r} has no reviewed CRC DMA input mapping")
    return mapping


# 按 chip_id 加载某一公共外设的单向 DMA 输入映射集合。
#
# 芯片扩展模块只需导出 `<PERIPHERAL>_DMA_INPUT_MAPPINGS`；公共 Case/Driver
# 不读取芯片文件，也不感知芯片 Request ID 或寄存器地址。
@cache
def load_dma_input_mappings(
    chip_id: str,
    peripheral: str,
) -> Mapping[int, DmaInputMapping]:

    normalized_chip = _require_chip_id(chip_id)
    normalized_peripheral = _require_peripheral(peripheral)
    package = __package__ or ""
    chip_package = f"{package}.{normalized_chip}"
    peripheral_module_name = f"{chip_package}.{normalized_peripheral}_routes"
    legacy_module_name = f"{chip_package}.dma_routes"
    try:
        module = import_module(peripheral_module_name)
    except ModuleNotFoundError as exc:
        if exc.name not in {chip_package, peripheral_module_name}:
            raise
        try:
            module = import_module(legacy_module_name)
        except ModuleNotFoundError as legacy_exc:
            if legacy_exc.name in {chip_package, legacy_module_name}:
                raise UnsupportedCapability(
                    f"{normalized_peripheral.upper()} DMA execution mapping is unavailable for "
                    f"chip {normalized_chip!r}"
                ) from legacy_exc
            raise

    export_name = f"{normalized_peripheral.upper()}_DMA_INPUT_MAPPINGS"
    mappings = getattr(module, export_name, None)
    if not isinstance(mappings, Mapping) or not mappings:
        raise ConfigurationError(
            f"chip {normalized_chip!r} DMA mapping module must export non-empty {export_name}"
        )

    for instance_id, mapping in mappings.items():
        if (
            isinstance(instance_id, bool)
            or not isinstance(instance_id, int)
            or instance_id < 0
            or not isinstance(mapping, DmaInputMapping)
            or mapping.peripheral != normalized_peripheral
            or mapping.instance_id != instance_id
            or mapping.peripheral_address <= 0
            or mapping.request_id < 0
            or not mapping.allowed_controllers
            or not mapping.allowed_interfaces
            or not mapping.address_evidence
            or not mapping.request_evidence
        ):
            raise ConfigurationError(
                f"chip {normalized_chip!r} {normalized_peripheral} DMA input mapping "
                f"{instance_id!r} is incomplete"
            )
    return mappings


def _require_peripheral(peripheral: str) -> str:
    if not isinstance(peripheral, str) or not _CHIP_ID.fullmatch(peripheral):
        raise ConfigurationError(f"invalid peripheral {peripheral!r}")
    return peripheral


# 按 chip_id 加载 AES DMA 双向映射；具体芯片事实只存在于芯片扩展模块。
@cache
def load_aes_dma_mapping(chip_id: str) -> AesDmaMapping:

    normalized_chip = _require_chip_id(chip_id)
    package = __package__ or ""
    chip_package = f"{package}.{normalized_chip}"
    module_name = f"{chip_package}.dma_routes"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name in {chip_package, module_name}:
            raise UnsupportedCapability(
                f"AES DMA execution mapping is unavailable for chip {normalized_chip!r}"
            ) from exc
        raise
    mapping = getattr(module, "AES_DMA_MAPPING", None)
    if not isinstance(mapping, AesDmaMapping):
        raise ConfigurationError(
            f"chip {normalized_chip!r} DMA mapping module must export AES_DMA_MAPPING"
        )
    addresses = (
        mapping.input_fifo_address,
        mapping.output_fifo_address,
        mapping.input_register_address,
        mapping.output_register_address,
    )
    request_ids = (mapping.input_request_id, mapping.output_request_id)
    if (
        mapping.instance_id < 0
        or any(address <= 0 for address in addresses)
        or any(request_id < 0 for request_id in request_ids)
        or not mapping.allowed_controllers
        or len(mapping.allowed_interfaces) < 2
        or not mapping.address_evidence
        or not mapping.request_evidence
    ):
        raise ConfigurationError(f"chip {normalized_chip!r} AES DMA mapping is incomplete")
    return mapping


def _require_chip_id(chip_id: str) -> str:
    if not isinstance(chip_id, str) or not _CHIP_ID.fullmatch(chip_id):
        raise ConfigurationError(f"invalid chip_id {chip_id!r}")
    return chip_id


def _validate_uart_dma_mapping(
    chip_id: str,
    key: object,
    mapping: object,
) -> None:
    if (
        not isinstance(key, tuple)
        or len(key) != 2
        or isinstance(key[0], bool)
        or not isinstance(key[0], int)
        or key[0] < 0
        or not isinstance(key[1], DmaPeripheralDirection)
    ):
        raise ConfigurationError(f"chip {chip_id!r} has an invalid UART DMA mapping key {key!r}")
    if not isinstance(mapping, DmaPeripheralMapping):
        raise ConfigurationError(
            f"chip {chip_id!r} UART DMA mapping {key!r} must be DmaPeripheralMapping"
        )
    if mapping.instance_id != key[0] or mapping.direction is not key[1]:
        raise ConfigurationError(
            f"chip {chip_id!r} UART DMA mapping {key!r} disagrees with its mapping payload"
        )
    if (
        mapping.peripheral != "uart"
        or mapping.peripheral_address < 0
        or mapping.request_id < 0
        or not mapping.allowed_controllers
        or not mapping.allowed_interfaces
        or not mapping.address_evidence
        or not mapping.request_evidence
    ):
        raise ConfigurationError(f"chip {chip_id!r} UART DMA mapping {key!r} is incomplete")
