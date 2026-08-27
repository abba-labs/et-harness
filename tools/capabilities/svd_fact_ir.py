# Immutable capability-relevant facts extracted from one CMSIS-SVD.
#
# The fact IR deliberately contains no feature inference.  It preserves the
# source facts required by the later semantic normalizer and evidence generator.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FACT_SCHEMA = "et-svd-facts/v1"


@dataclass(frozen=True)
class EnumValue:
    name: str
    value: int | None
    description: str
    is_default: bool


@dataclass(frozen=True)
class InlineValue:
    name: str
    value: int
    description: str


@dataclass(frozen=True)
class Field:
    name: str
    description: str
    bit_offset: int
    bit_width: int
    access: str
    enum_values: tuple[EnumValue, ...]
    inline_values_text: str
    inline_values: tuple[InlineValue, ...]


@dataclass(frozen=True)
class Register:
    path: str
    source_name: str
    dim_index: str | None
    description: str
    address_offset: int
    size: int
    access: str
    reset_value: int
    reset_mask: int
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Cluster:
    path: str
    source_name: str
    dim_index: str | None
    description: str
    address_offset: int
    size: int | None
    access: str | None
    reset_value: int | None
    reset_mask: int | None


@dataclass(frozen=True)
class Interrupt:
    name: str
    description: str
    value: int


@dataclass(frozen=True)
class Peripheral:
    svd_name: str
    derived_from: str | None
    description: str
    base_address: int
    clusters: tuple[Cluster, ...]
    registers: tuple[Register, ...]
    interrupts: tuple[Interrupt, ...]


@dataclass(frozen=True)
class Instance:
    instance_id: str
    peripheral: Peripheral


@dataclass(frozen=True)
class IpGroup:
    ip_id: str
    instances: tuple[Instance, ...]


@dataclass(frozen=True)
class SvdFactIR:
    source_file: str
    source_sha256: str
    device_name: str
    device_description: str
    groups: tuple[IpGroup, ...]


# Convert immutable facts to the canonical portable document model.
def to_document(
    facts: SvdFactIR,
    *,
    chip_id: str,
    generator_version: int,
) -> dict[str, Any]:

    ips: dict[str, Any] = {}
    for group in facts.groups:
        instances: dict[str, Any] = {}
        for instance in group.instances:
            peripheral = instance.peripheral
            clusters = [
                {
                    "path": f"{peripheral.svd_name}.{cluster.path}",
                    "source_name": cluster.source_name,
                    "dim_index": cluster.dim_index,
                    "description": cluster.description,
                    "address_offset": cluster.address_offset,
                    "absolute_address": (peripheral.base_address + cluster.address_offset),
                    "size": cluster.size,
                    "access": cluster.access,
                    "reset_value": cluster.reset_value,
                    "reset_mask": cluster.reset_mask,
                }
                for cluster in peripheral.clusters
            ]
            registers: list[dict[str, Any]] = []
            for register in peripheral.registers:
                register_path = f"{peripheral.svd_name}.{register.path}"
                fields: list[dict[str, Any]] = []
                for field in register.fields:
                    fields.append(
                        {
                            "path": f"{register_path}.{field.name}",
                            "name": field.name,
                            "description": field.description,
                            "bit_offset": field.bit_offset,
                            "bit_width": field.bit_width,
                            "access": field.access,
                            "enumerated_values": [
                                {
                                    "name": item.name,
                                    "value": item.value,
                                    "description": item.description,
                                    "is_default": item.is_default,
                                }
                                for item in field.enum_values
                            ],
                            "inline_values_text": field.inline_values_text,
                            "inline_values": [
                                {
                                    "name": item.name,
                                    "value": item.value,
                                    "description": item.description,
                                }
                                for item in field.inline_values
                            ],
                        }
                    )
                registers.append(
                    {
                        "path": register_path,
                        "source_name": register.source_name,
                        "dim_index": register.dim_index,
                        "description": register.description,
                        "address_offset": register.address_offset,
                        "absolute_address": (peripheral.base_address + register.address_offset),
                        "size": register.size,
                        "access": register.access,
                        "reset_value": register.reset_value,
                        "reset_mask": register.reset_mask,
                        "fields": fields,
                    }
                )
            interrupts = [
                {
                    "path": (f"{peripheral.svd_name}.interrupt.{item.name}"),
                    "name": item.name,
                    "description": item.description,
                    "irqn": item.value,
                }
                for item in peripheral.interrupts
            ]
            instances[instance.instance_id] = {
                "svd_name": peripheral.svd_name,
                "derived_from": peripheral.derived_from,
                "description": peripheral.description,
                "base_address": peripheral.base_address,
                "clusters": clusters,
                "registers": registers,
                "interrupts": interrupts,
            }
        ips[group.ip_id] = {"instances": instances}

    return {
        "schema": FACT_SCHEMA,
        "chip": chip_id,
        "source": {
            "file": facts.source_file,
            "sha256": facts.source_sha256,
            "generator_version": generator_version,
        },
        "device": {
            "svd_name": facts.device_name,
            "description": facts.device_description,
        },
        "ips": ips,
    }
