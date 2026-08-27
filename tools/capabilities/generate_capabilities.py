#!/usr/bin/env python3
# Generate deterministic per-IP capability YAML files from one CMSIS-SVD.
#
# This is intentionally one generic generator.  It contains no chip/IP-specific
# register names, feature tables, instance counts, base addresses, or IRQ values.

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from svd_fact_ir import (
    Cluster,
    EnumValue,
    Field,
    InlineValue,
    Instance,
    Interrupt,
    IpGroup,
    Peripheral,
    Register,
    SvdFactIR,
    to_document,
)
from svd_semantics import (
    SemanticArtifacts,
    explain as explain_semantic,
    normalize as normalize_semantics,
)
from capability_quality import analyze as analyze_quality
from capability_requirements import (
    load_capability_requirements,
    merge_capability_requirements,
)


SCHEMA = "et-ip-capability/v1"
GENERATOR_VERSION = 1
FACT_GENERATOR_VERSION = 1
BUS_PREFIXES = ("AHB", "APB", "AXI")
RESERVED_PREFIXES = ("RSVD", "RESERVED")
YAML_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
BIT_RANGE = re.compile(r"^\[\s*(\d+)\s*:\s*(\d+)\s*\]$")
NATURAL_PART = re.compile(r"(\d+)")
INLINE_VALUE = re.compile(
    r"(?P<value>0[xX][0-9A-Fa-f]+|\d+)\s*"
    r"\((?P<name>[^()]+)\)\s*:\s*"
)


# Raised when SVD facts cannot be converted without guessing.
class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RegisterDefaults:
    size: int | None = None
    access: str | None = None
    reset_value: int | None = None
    reset_mask: int | None = None

    def overlay(self, element: ET.Element) -> "RegisterDefaults":
        return RegisterDefaults(
            size=_optional_int(element, "size", self.size),
            access=_normalize_access(_optional_text(element, "access", self.access)),
            reset_value=_optional_int(element, "resetValue", self.reset_value),
            reset_mask=_optional_int(element, "resetMask", self.reset_mask),
        )


# Parse one SVD into immutable, capability-relevant source facts.
def parse_svd_facts(path: Path) -> SvdFactIR:

    raw = path.read_bytes()
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise GenerationError("DTD and ENTITY declarations are not allowed")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise GenerationError(f"invalid XML: {exc}") from exc
    _strip_namespaces(root)
    if root.tag != "device":
        raise GenerationError(f"expected <device>, got <{root.tag}>")

    device_name = _required_text(root, "name")
    device_description = _description(root)
    source_hash = hashlib.sha256(raw).hexdigest().upper()
    peripherals_node = root.find("peripherals")
    if peripherals_node is None:
        raise GenerationError("SVD contains no <peripherals>")

    elements: dict[str, ET.Element] = {}
    order: list[str] = []
    for element in peripherals_node.findall("peripheral"):
        name = _required_text(element, "name")
        if name in elements:
            raise GenerationError(f"duplicate peripheral {name!r}")
        elements[name] = element
        order.append(name)
    if not elements:
        raise GenerationError("SVD contains no peripheral")

    for element in root.iter():
        if element.get("derivedFrom") and element.tag != "peripheral":
            raise GenerationError(
                f"unsupported derivedFrom on <{element.tag}>; "
                "generation stopped instead of ignoring it"
            )

    device_defaults = RegisterDefaults().overlay(root)
    resolved: dict[str, Peripheral] = {}
    resolving: set[str] = set()

    def resolve(name: str) -> Peripheral:
        cached = resolved.get(name)
        if cached is not None:
            return cached
        if name in resolving:
            raise GenerationError(f"peripheral derivedFrom cycle at {name}")
        element = elements.get(name)
        if element is None:
            raise GenerationError(f"unknown peripheral {name!r}")

        resolving.add(name)
        parent_name = element.get("derivedFrom")
        parent = resolve(parent_name) if parent_name else None
        base_address = _optional_int(
            element,
            "baseAddress",
            parent.base_address if parent is not None else None,
        )
        if base_address is None:
            raise GenerationError(f"{name} has no baseAddress")

        defaults = device_defaults.overlay(element)
        local_registers = element.find("registers")
        if local_registers is None:
            registers = copy.deepcopy(parent.registers) if parent is not None else ()
            clusters = copy.deepcopy(parent.clusters) if parent is not None else ()
        else:
            parsed, parsed_clusters = _parse_registers(local_registers, defaults)
            if parent is None:
                registers = parsed
                clusters = parsed_clusters
            else:
                merged = {register.path: register for register in parent.registers}
                for register in parsed:
                    merged[register.path] = register
                registers = tuple(
                    sorted(
                        merged.values(),
                        key=lambda item: (
                            item.address_offset,
                            _natural_key(item.path),
                        ),
                    )
                )
                merged_clusters = {cluster.path: cluster for cluster in parent.clusters}
                for cluster in parsed_clusters:
                    merged_clusters[cluster.path] = cluster
                clusters = tuple(
                    sorted(
                        merged_clusters.values(),
                        key=lambda item: (
                            item.address_offset,
                            _natural_key(item.path),
                        ),
                    )
                )

        local_interrupts = element.findall("interrupt")
        if local_interrupts:
            interrupts = tuple(
                sorted(
                    (
                        Interrupt(
                            name=_required_text(node, "name"),
                            description=_description(node),
                            value=_required_int(node, "value"),
                        )
                        for node in local_interrupts
                    ),
                    key=lambda item: (item.value, _natural_key(item.name)),
                )
            )
        elif parent is not None:
            interrupts = copy.deepcopy(parent.interrupts)
        else:
            interrupts = ()

        peripheral = Peripheral(
            svd_name=name,
            derived_from=parent_name,
            description=_description(
                element,
                parent.description if parent is not None else "",
            ),
            base_address=base_address,
            clusters=clusters,
            registers=registers,
            interrupts=interrupts,
        )
        _validate_peripheral_paths(peripheral)
        resolving.remove(name)
        resolved[name] = peripheral
        return peripheral

    for peripheral_name in order:
        resolve(peripheral_name)

    groups_by_root: dict[str, list[str]] = {}
    for name in order:
        root_name = _root_peripheral_name(name, elements)
        groups_by_root.setdefault(root_name, []).append(name)

    instances_by_ip: dict[str, list[Instance]] = {}
    for root_name, member_names in groups_by_root.items():
        stem = _common_instance_stem(member_names)
        ip_id = _normalize_ip_id(stem)
        instances = instances_by_ip.setdefault(ip_id, [])
        used_instances = {item.instance_id for item in instances}
        for ordinal, member_name in enumerate(sorted(member_names, key=_natural_key)):
            suffix = member_name[len(stem) :]
            suffix_id = _normalize_suffix(suffix) if suffix else str(ordinal)
            instance_id = f"{ip_id}{suffix_id}"
            if instance_id in used_instances:
                raise GenerationError(f"duplicate instance ID {instance_id!r} in {ip_id}")
            used_instances.add(instance_id)
            instances.append(
                Instance(
                    instance_id=instance_id,
                    peripheral=resolved[member_name],
                )
            )
    groups = [
        IpGroup(
            ip_id=ip_id,
            instances=tuple(sorted(instances, key=lambda item: _natural_key(item.instance_id))),
        )
        for ip_id, instances in instances_by_ip.items()
    ]
    groups.sort(key=lambda item: _natural_key(item.ip_id))
    return SvdFactIR(
        source_file=path.name,
        source_sha256=source_hash,
        device_name=device_name,
        device_description=device_description,
        groups=tuple(groups),
    )


# Compatibility view used by the transitional v1 renderer.
def parse_svd(path: Path) -> tuple[str, str, tuple[IpGroup, ...]]:

    facts = parse_svd_facts(path)
    return facts.device_name, facts.source_sha256, facts.groups


# Build canonical YAML text for every IP in one SVD.
def build_profiles(
    *,
    svd_path: Path,
    chip_id: str | None = None,
    output_dir: Path | None = None,
    facts: SvdFactIR | None = None,
) -> dict[str, str]:

    facts = facts or parse_svd_facts(svd_path)
    device_name = facts.device_name
    source_hash = facts.source_sha256
    groups = facts.groups
    normalized_chip = (
        _normalize_identifier(chip_id)
        if chip_id is not None
        else _normalize_identifier(device_name)
    )
    profiles: dict[str, str] = {}
    for group in groups:
        existing_path = output_dir / f"{group.ip_id}.yaml" if output_dir is not None else None
        manual = _load_manual(existing_path)
        capabilities = _extract_capabilities(group)
        text = _render_profile(
            chip_id=normalized_chip,
            group=group,
            source_file=svd_path.name,
            source_hash=source_hash,
            capabilities=capabilities,
            manual=manual,
        )
        _validate_profile_text(text)
        profiles[group.ip_id] = text
    return profiles


# Build canonical JSON for the lossless capability fact IR.
def build_fact_document(
    *,
    svd_path: Path,
    chip_id: str | None = None,
    facts: SvdFactIR | None = None,
) -> str:

    facts = facts or parse_svd_facts(svd_path)
    normalized_chip = (
        _normalize_identifier(chip_id)
        if chip_id is not None
        else _normalize_identifier(facts.device_name)
    )
    document = to_document(
        facts,
        chip_id=normalized_chip,
        generator_version=FACT_GENERATOR_VERSION,
    )
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


# Atomically write, or byte-check, one canonical fact document.
def write_or_check_fact_document(
    text: str,
    output_path: Path,
    *,
    check: bool,
) -> dict[str, Any]:

    encoded = text.encode("utf-8")
    current = output_path.read_bytes() if output_path.is_file() else None
    changed = current != encoded
    if check and changed:
        raise GenerationError(f"SVD fact output is stale or missing: {output_path.name}")
    if not check and changed:
        _atomic_write(output_path, text)
    return {
        "file": output_path.name,
        "changed": changed,
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


# Build validated v2 profiles and audit YAML from the fact IR.
def build_semantic_documents(
    *,
    svd_path: Path,
    chip_id: str | None = None,
    facts: SvdFactIR | None = None,
) -> tuple[SemanticArtifacts, dict[str, str], dict[str, str]]:

    facts = facts or parse_svd_facts(svd_path)
    normalized_chip = (
        _normalize_identifier(chip_id)
        if chip_id is not None
        else _normalize_identifier(facts.device_name)
    )
    artifacts = normalize_semantics(facts, chip_id=normalized_chip)
    profiles: dict[str, str] = {}
    audits: dict[str, str] = {}
    for ip_id, document in artifacts.profiles.items():
        text = _render_yaml_document(document)
        _validate_profile_text(text)
        profiles[ip_id] = text
    for ip_id, document in artifacts.audits.items():
        text = _render_yaml_document(document)
        _validate_audit_text(text)
        audits[ip_id] = text
    return artifacts, profiles, audits


# Build one canonical quality report from semantic artifacts.
def build_quality_document(
    artifacts: SemanticArtifacts,
    *,
    facts: SvdFactIR | None = None,
    required_capabilities: Sequence[str] = (),
) -> tuple[dict[str, Any], str]:

    report = analyze_quality(
        artifacts,
        facts=facts,
        required_capabilities=required_capabilities,
    )
    text = (
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return report, text


# Atomically write, or byte-check, one quality report.
def write_or_check_quality_document(
    text: str,
    output_path: Path,
    *,
    check: bool,
) -> dict[str, Any]:

    encoded = text.encode("utf-8")
    current = output_path.read_bytes() if output_path.is_file() else None
    changed = current != encoded
    if check and changed:
        raise GenerationError(f"capability quality output is stale or missing: {output_path.name}")
    if not check and changed:
        _atomic_write(output_path, text)
    return {
        "file": output_path.name,
        "changed": changed,
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


# Write profiles atomically, or check the directory byte-for-byte.
def write_or_check_profiles(
    profiles: Mapping[str, str],
    output_dir: Path,
    *,
    check: bool,
) -> dict[str, Any]:

    expected_names = {f"{ip_id}.yaml" for ip_id in profiles}
    existing_names = (
        {path.name for path in output_dir.glob("*.yaml")} if output_dir.is_dir() else set()
    )
    changed: list[str] = []

    for ip_id, text in profiles.items():
        target = output_dir / f"{ip_id}.yaml"
        current = target.read_bytes() if target.is_file() else None
        if current != text.encode("utf-8"):
            changed.append(target.name)

    extra = sorted(existing_names - expected_names, key=_natural_key)
    if check:
        if changed or extra:
            details = []
            if changed:
                details.append("changed/missing=" + ",".join(changed))
            if extra:
                details.append("extra=" + ",".join(extra))
            raise GenerationError("capability output is stale: " + "; ".join(details))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        for ip_id, text in profiles.items():
            target = output_dir / f"{ip_id}.yaml"
            _atomic_write(target, text)

    return {
        "profile_count": len(profiles),
        "changed": sorted(changed, key=_natural_key),
        "extra": extra,
        "files": {
            f"{ip_id}.yaml": hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
            for ip_id, text in sorted(profiles.items(), key=lambda item: _natural_key(item[0]))
        },
    }


def _parse_registers(
    registers_node: ET.Element,
    defaults: RegisterDefaults,
) -> tuple[tuple[Register, ...], tuple[Cluster, ...]]:
    registers: list[Register] = []
    clusters: list[Cluster] = []
    for child in list(registers_node):
        if child.tag == "register":
            registers.extend(_expand_register(child, base_offset=0, prefix="", defaults=defaults))
        elif child.tag == "cluster":
            registers.extend(
                _expand_cluster(
                    child,
                    base_offset=0,
                    prefix="",
                    defaults=defaults,
                    clusters=clusters,
                )
            )
        else:
            raise GenerationError(f"unsupported <registers> child <{child.tag}>")
    ordered_registers = tuple(
        sorted(
            registers,
            key=lambda item: (item.address_offset, _natural_key(item.path)),
        )
    )
    ordered_registers = _disambiguate_register_paths(ordered_registers)
    ordered_clusters = tuple(
        sorted(
            clusters,
            key=lambda item: (item.address_offset, _natural_key(item.path)),
        )
    )
    _require_unique_paths(
        (register.path for register in ordered_registers),
        "register",
    )
    _require_unique_paths(
        (cluster.path for cluster in ordered_clusters),
        "cluster",
    )
    return ordered_registers, ordered_clusters


def _disambiguate_register_paths(
    registers: tuple[Register, ...],
) -> tuple[Register, ...]:
    by_path: dict[str, list[Register]] = {}
    for register in registers:
        by_path.setdefault(register.path, []).append(register)

    result: list[Register] = []
    for register in registers:
        collisions = by_path[register.path]
        if len(collisions) == 1:
            result.append(register)
            continue
        offsets = {item.address_offset for item in collisions}
        if len(offsets) != len(collisions):
            raise GenerationError(
                f"duplicate register logical path {register.path!r} "
                f"at offset 0x{register.address_offset:08X}"
            )
        result.append(
            replace(
                register,
                path=f"{register.path}@0x{register.address_offset:08X}",
            )
        )
    return tuple(result)


def _expand_cluster(
    element: ET.Element,
    *,
    base_offset: int,
    prefix: str,
    defaults: RegisterDefaults,
    clusters: list[Cluster],
) -> list[Register]:
    name = _required_text(element, "name")
    offset = _required_int(element, "addressOffset")
    local_defaults = defaults.overlay(element)
    result: list[Register] = []
    for actual_name, delta, dim_index in _expanded_names(element, name):
        full_name = f"{prefix}.{actual_name}" if prefix else actual_name
        cluster_base = base_offset + offset + delta
        clusters.append(
            Cluster(
                path=full_name,
                source_name=name,
                dim_index=dim_index,
                description=_description(element),
                address_offset=cluster_base,
                size=local_defaults.size,
                access=local_defaults.access,
                reset_value=local_defaults.reset_value,
                reset_mask=local_defaults.reset_mask,
            )
        )
        for child in list(element):
            if child.tag == "register":
                result.extend(
                    _expand_register(
                        child,
                        base_offset=cluster_base,
                        prefix=full_name,
                        defaults=local_defaults,
                    )
                )
            elif child.tag == "cluster":
                result.extend(
                    _expand_cluster(
                        child,
                        base_offset=cluster_base,
                        prefix=full_name,
                        defaults=local_defaults,
                    )
                )
            elif child.tag not in {
                "name",
                "description",
                "addressOffset",
                "dim",
                "dimIncrement",
                "dimIndex",
                "size",
                "access",
                "resetValue",
                "resetMask",
            }:
                raise GenerationError(f"unsupported <cluster> child <{child.tag}>")
    return result


def _expand_register(
    element: ET.Element,
    *,
    base_offset: int,
    prefix: str,
    defaults: RegisterDefaults,
) -> list[Register]:
    name = _required_text(element, "name")
    offset = _required_int(element, "addressOffset")
    local_defaults = defaults.overlay(element)
    if local_defaults.size is None:
        raise GenerationError(f"register {name} has no size")
    size = local_defaults.size
    if size <= 0:
        raise GenerationError(f"register {name} has invalid size {size}")
    access = local_defaults.access or "unspecified"
    description = _description(element)
    reset_value = local_defaults.reset_value or 0
    reset_mask = (
        local_defaults.reset_mask if local_defaults.reset_mask is not None else (1 << size) - 1
    )

    fields_node = element.find("fields")
    fields = (
        tuple(
            sorted(
                (
                    _parse_field(field_node, register_access=access)
                    for field_node in fields_node.findall("field")
                ),
                key=lambda item: (item.bit_offset, _natural_key(item.name)),
            )
        )
        if fields_node is not None
        else ()
    )
    _require_unique_paths((field.name for field in fields), f"field in {name}")
    for field in fields:
        if field.bit_offset + field.bit_width > size:
            raise GenerationError(f"field {name}.{field.name} exceeds {size}-bit register")

    result: list[Register] = []
    for actual_name, delta, dim_index in _expanded_names(element, name):
        full_name = f"{prefix}.{actual_name}" if prefix else actual_name
        result.append(
            Register(
                path=full_name,
                source_name=name,
                dim_index=dim_index,
                description=description,
                address_offset=base_offset + offset + delta,
                size=size,
                access=access,
                reset_value=reset_value,
                reset_mask=reset_mask,
                fields=fields,
            )
        )
    return result


def _parse_field(element: ET.Element, *, register_access: str) -> Field:
    name = _required_text(element, "name")
    description = _description(element)
    positions: list[tuple[int, int]] = []
    bit_offset = element.find("bitOffset")
    bit_width = element.find("bitWidth")
    if (bit_offset is None) != (bit_width is None):
        raise GenerationError(f"field {name} must define bitOffset and bitWidth together")
    if bit_offset is not None and bit_width is not None:
        positions.append((_parse_int(bit_offset.text), _parse_int(bit_width.text)))

    lsb = element.find("lsb")
    msb = element.find("msb")
    if (lsb is None) != (msb is None):
        raise GenerationError(f"field {name} must define lsb and msb together")
    if lsb is not None and msb is not None:
        lo = _parse_int(lsb.text)
        hi = _parse_int(msb.text)
        positions.append((lo, hi - lo + 1))

    bit_range = element.findtext("bitRange")
    if bit_range is not None:
        match = BIT_RANGE.fullmatch(bit_range.strip())
        if match is None:
            raise GenerationError(f"field {name} has invalid bitRange")
        hi, lo = (int(match.group(1)), int(match.group(2)))
        positions.append((lo, hi - lo + 1))

    if not positions:
        raise GenerationError(f"field {name} has no bit position")
    if len(set(positions)) != 1:
        raise GenerationError(f"field {name} has conflicting bit positions")
    offset, width = positions[0]
    if offset < 0 or width <= 0:
        raise GenerationError(f"field {name} has invalid bit position")

    enum_values: list[EnumValue] = []
    for enum_set in element.findall("enumeratedValues"):
        if enum_set.get("derivedFrom"):
            raise GenerationError(f"unsupported enumeratedValues derivedFrom in field {name}")
        for enum in enum_set.findall("enumeratedValue"):
            value_node = enum.find("value")
            is_default = (enum.findtext("isDefault") or "").strip().lower() == "true"
            if value_node is None and not is_default:
                raise GenerationError(f"enumeratedValue in field {name} has no value")
            enum_values.append(
                EnumValue(
                    name=_required_text(enum, "name"),
                    value=(_parse_int(value_node.text) if value_node is not None else None),
                    description=_description(enum),
                    is_default=is_default,
                )
            )
    enum_values.sort(
        key=lambda item: (
            item.value is None,
            item.value if item.value is not None else 0,
            _natural_key(item.name),
        )
    )
    _require_unique_paths(
        (item.name for item in enum_values),
        f"enumerated value in {name}",
    )
    inline_values_text, inline_values = _parse_inline_values(description)

    access = _normalize_access(_optional_text(element, "access", register_access))
    return Field(
        name=name,
        description=description,
        bit_offset=offset,
        bit_width=width,
        access=access or "unspecified",
        enum_values=tuple(enum_values),
        inline_values_text=inline_values_text,
        inline_values=inline_values,
    )


def _extract_capabilities(group: IpGroup) -> dict[str, Any]:
    features: dict[str, list[str]] = {}
    limits: dict[str, dict[str, Any]] = {}
    options: dict[str, dict[str, Any]] = {}
    identities: dict[str, dict[str, Any]] = {}
    instance_ids = [instance.instance_id for instance in group.instances]

    for instance in group.instances:
        instance_id = instance.instance_id
        peripheral = instance.peripheral
        field_occurrences: dict[str, list[tuple[Register, Field]]] = {}
        for register in peripheral.registers:
            for field in register.fields:
                if _is_reserved(field.name):
                    continue
                field_id = _normalize_identifier(field.name)
                field_occurrences.setdefault(field_id, []).append((register, field))
                _add_feature(
                    features,
                    f"{group.ip_id}.feature.field.{field_id}",
                    instance_id,
                )

        interrupt_events = [
            _interrupt_event_name(
                interrupt.name,
                ip_id=group.ip_id,
                instance_id=instance_id,
            )
            for interrupt in peripheral.interrupts
        ]
        for event in interrupt_events:
            _add_feature(
                features,
                f"{group.ip_id}.feature.interrupt.{event}",
                instance_id,
            )

        _put_value(
            limits,
            f"{group.ip_id}.limit.instance_count",
            instance_id,
            len(group.instances),
        )
        _put_value(
            limits,
            f"{group.ip_id}.limit.register_count",
            instance_id,
            len(peripheral.registers),
        )
        _put_value(
            limits,
            f"{group.ip_id}.limit.field_count",
            instance_id,
            sum(len(register.fields) for register in peripheral.registers),
        )
        _put_value(
            limits,
            f"{group.ip_id}.limit.interrupt_count",
            instance_id,
            len(peripheral.interrupts),
        )
        address_span = max(
            (
                register.address_offset + ((register.size + 7) // 8)
                for register in peripheral.registers
            ),
            default=0,
        )
        _put_value(
            limits,
            f"{group.ip_id}.limit.register_span_bytes",
            instance_id,
            address_span,
        )

        widths = sorted({register.size for register in peripheral.registers})
        if widths:
            _put_value(
                options,
                f"{group.ip_id}.option.register_width_bits",
                instance_id,
                widths,
            )
        accesses = sorted(
            {register.access for register in peripheral.registers},
            key=_natural_key,
        )
        if accesses:
            _put_value(
                options,
                f"{group.ip_id}.option.register_access",
                instance_id,
                accesses,
            )
        if interrupt_events:
            _put_value(
                options,
                f"{group.ip_id}.option.interrupt_events",
                instance_id,
                sorted(set(interrupt_events), key=_natural_key),
            )

        for field_id, occurrences in field_occurrences.items():
            field_widths = sorted({field.bit_width for _, field in occurrences})
            if len(field_widths) == 1:
                _put_value(
                    limits,
                    f"{group.ip_id}.limit.field.{field_id}.bit_width",
                    instance_id,
                    field_widths[0],
                )
            else:
                _put_value(
                    options,
                    f"{group.ip_id}.option.field.{field_id}.bit_width_bits",
                    instance_id,
                    field_widths,
                )

            enum_values = sorted(
                {
                    enum.value
                    for _, field in occurrences
                    for enum in field.enum_values
                    if enum.value is not None
                }
            )
            if enum_values:
                _put_value(
                    options,
                    f"{group.ip_id}.option.field.{field_id}.encoded_values",
                    instance_id,
                    enum_values,
                )

            identity_values: set[int] = set()
            for register, field in occurrences:
                if not _is_identity_field(field_id, field, register):
                    continue
                mask = (1 << field.bit_width) - 1
                identity_values.add((register.reset_value >> field.bit_offset) & mask)
            if len(identity_values) == 1:
                value = next(iter(identity_values))
                digits = max(2, (max(field_widths) + 3) // 4)
                _put_value(
                    identities,
                    f"{group.ip_id}.identity.{field_id}",
                    instance_id,
                    f"0x{value:0{digits}X}",
                )

        _put_value(
            identities,
            f"{group.ip_id}.identity.base_address",
            instance_id,
            f"0x{peripheral.base_address:08X}",
        )

    ordered: dict[str, Any] = {}
    for section in (features, limits, options, identities):
        for capability_id in sorted(section, key=_capability_sort_key):
            value = section[capability_id]
            if capability_id.startswith(f"{group.ip_id}.feature."):
                ordered[capability_id] = [item for item in instance_ids if item in value]
            else:
                ordered[capability_id] = {
                    item: value[item] for item in instance_ids if item in value
                }
    return ordered


def _render_profile(
    *,
    chip_id: str,
    group: IpGroup,
    source_file: str,
    source_hash: str,
    capabilities: Mapping[str, Any],
    manual: Mapping[str, Any],
) -> str:
    lines = [
        f"schema: {SCHEMA}",
        f"chip: {chip_id}",
        f"ip: {group.ip_id}",
        "",
        "source:",
        f"  file: {_yaml_scalar(source_file)}",
        f"  sha256: {source_hash}",
        f"  generator_version: {GENERATOR_VERSION}",
        "",
        "instances:",
    ]
    for instance in group.instances:
        lines.append(f"  {instance.instance_id}:")
        lines.append(f"    svd_name: {_yaml_scalar(instance.peripheral.svd_name)}")
    lines.extend(["", "generated:"])
    if capabilities:
        lines.append("  capabilities:")
        for capability_id, value in capabilities.items():
            if capability_id.startswith(f"{group.ip_id}.feature."):
                rendered = ", ".join(_yaml_scalar(item) for item in value)
                lines.append(f"    {capability_id}: [{rendered}]")
            else:
                lines.append(f"    {capability_id}:")
                for instance_id, item in value.items():
                    lines.append(f"      {instance_id}: {_yaml_inline_value(item)}")
    else:
        lines.append("  capabilities: {}")

    manual_set = manual.get("set", {})
    manual_remove = manual.get("remove", [])
    lines.extend(["", "manual:"])
    if manual_set:
        lines.append("  set:")
        for capability_id in sorted(manual_set, key=_capability_sort_key):
            value = manual_set[capability_id]
            if isinstance(value, Mapping):
                lines.append(f"    {capability_id}:")
                for key in sorted(value, key=_natural_key):
                    lines.append(
                        f"      {key}: {_yaml_inline_value(_canonical_manual_value(value[key]))}"
                    )
            else:
                lines.append(
                    f"    {capability_id}: {_yaml_inline_value(_canonical_manual_value(value))}"
                )
    else:
        lines.append("  set: {}")
    if manual_remove:
        lines.append("  remove:")
        for item in sorted(manual_remove, key=_capability_sort_key):
            lines.append(f"    - {_yaml_scalar(item)}")
    else:
        lines.append("  remove: []")
    return "\n".join(lines) + "\n"


def _load_manual(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"set": {}, "remove": []}
    try:
        import yaml
    except ImportError as exc:
        raise GenerationError("PyYAML is required to preserve existing manual overrides") from exc
    try:
        root = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GenerationError(f"cannot load existing {path}: {exc}") from exc
    if not isinstance(root, Mapping):
        raise GenerationError(f"existing {path} is not a YAML mapping")
    manual = root.get("manual", {"set": {}, "remove": []})
    if not isinstance(manual, Mapping):
        raise GenerationError(f"manual in {path} is not a mapping")
    manual_set = manual.get("set", {})
    manual_remove = manual.get("remove", [])
    if not isinstance(manual_set, Mapping) or not isinstance(manual_remove, list):
        raise GenerationError(f"manual in {path} has invalid set/remove")
    return {"set": dict(manual_set), "remove": list(manual_remove)}


def _validate_profile_text(text: str) -> None:
    code_root = Path(__file__).resolve().parents[2]
    pc_root = code_root / "pc"
    inserted = False
    if str(pc_root) not in sys.path:
        sys.path.insert(0, str(pc_root))
        inserted = True
    try:
        from et_test_platform.profiles.capabilities import (
            load_capability_profile,
        )

        with tempfile.TemporaryDirectory(prefix="et-capability-validate-") as raw_directory:
            path = Path(raw_directory) / "profile.yaml"
            path.write_text(text, encoding="utf-8", newline="\n")
            load_capability_profile(path)
    except Exception as exc:
        raise GenerationError(f"generated profile failed platform validation: {exc}") from exc
    finally:
        if inserted:
            sys.path.remove(str(pc_root))


def _validate_audit_text(text: str) -> None:
    code_root = Path(__file__).resolve().parents[2]
    pc_root = code_root / "pc"
    inserted = False
    if str(pc_root) not in sys.path:
        sys.path.insert(0, str(pc_root))
        inserted = True
    try:
        from et_test_platform.profiles.capabilities import (
            load_capability_audit,
        )

        with tempfile.TemporaryDirectory(prefix="et-capability-audit-validate-") as raw_directory:
            path = Path(raw_directory) / "audit.yaml"
            path.write_text(text, encoding="utf-8", newline="\n")
            load_capability_audit(path)
    except Exception as exc:
        raise GenerationError(f"generated audit failed platform validation: {exc}") from exc
    finally:
        if inserted:
            sys.path.remove(str(pc_root))


def _render_yaml_document(document: Mapping[str, Any]) -> str:
    try:
        import yaml
    except ImportError as exc:
        raise GenerationError("PyYAML is required to render semantic capability documents") from exc
    return yaml.safe_dump(
        dict(document),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )


def _canonical_manual_value(value: Any) -> Any:
    if isinstance(value, list):
        return sorted(
            value,
            key=lambda item: (type(item).__name__, _natural_key(str(item))),
        )
    return value


def _expanded_names(element: ET.Element, template: str) -> list[tuple[str, int, str | None]]:
    dim_text = element.findtext("dim")
    if dim_text is None:
        return [(template, 0, None)]
    count = _parse_int(dim_text)
    increment = _required_int(element, "dimIncrement")
    if count <= 0 or increment < 0:
        raise GenerationError(f"invalid dim on {template}")
    indices = _dim_indices(element.findtext("dimIndex"), count)
    result = []
    for position, index in enumerate(indices):
        if "%s" in template:
            actual = template.replace("%s", index)
        else:
            actual = f"{template}{index}"
        result.append((actual, position * increment, index))
    return result


def _dim_indices(text: str | None, count: int) -> list[str]:
    if text is None or not text.strip():
        return [str(index) for index in range(count)]
    value = text.strip()
    if "," in value:
        indices = [item.strip() for item in value.split(",")]
    elif "-" in value:
        start, end = (item.strip() for item in value.split("-", 1))
        if start.isdigit() and end.isdigit():
            indices = [str(item) for item in range(int(start), int(end) + 1)]
        elif len(start) == 1 and len(end) == 1 and ord(start) <= ord(end):
            indices = [chr(item) for item in range(ord(start), ord(end) + 1)]
        else:
            raise GenerationError(f"unsupported dimIndex range {value!r}")
    else:
        indices = [value]
    if len(indices) != count or len(set(indices)) != count:
        raise GenerationError(f"dimIndex {value!r} does not define {count} unique indices")
    return indices


def _description(element: ET.Element, default: str = "") -> str:
    node = element.find("description")
    if node is None:
        return default
    return "".join(node.itertext()).strip()


def _require_unique_paths(paths: Iterable[str], kind: str) -> None:
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            raise GenerationError(f"duplicate {kind} logical path {path!r}")
        seen.add(path)


def _validate_peripheral_paths(peripheral: Peripheral) -> None:
    _require_unique_paths(
        (
            *(cluster.path for cluster in peripheral.clusters),
            *(register.path for register in peripheral.registers),
        ),
        f"container in {peripheral.svd_name}",
    )
    _require_unique_paths(
        (interrupt.name for interrupt in peripheral.interrupts),
        f"interrupt in {peripheral.svd_name}",
    )


def _parse_inline_values(
    description: str,
) -> tuple[str, tuple[InlineValue, ...]]:
    marker = re.search(r"\bValues\s*:\s*", description, flags=re.IGNORECASE)
    if marker is None:
        return "", ()
    raw = description[marker.end() :].strip()
    matches = list(INLINE_VALUE.finditer(raw))
    values: list[InlineValue] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        values.append(
            InlineValue(
                name=match.group("name").strip(),
                value=_parse_int(match.group("value")),
                description=raw[match.end() : end].strip(),
            )
        )
    return raw, tuple(values)


def _root_peripheral_name(name: str, elements: Mapping[str, ET.Element]) -> str:
    seen: set[str] = set()
    current = name
    while True:
        if current in seen:
            raise GenerationError(f"peripheral derivedFrom cycle at {current}")
        seen.add(current)
        element = elements.get(current)
        if element is None:
            raise GenerationError(f"unknown peripheral {current!r}")
        parent = element.get("derivedFrom")
        if not parent:
            return current
        current = parent


def _common_instance_stem(names: Sequence[str]) -> str:
    if len(names) == 1:
        name = names[0]
        match = re.fullmatch(r"(.+?)(\d+)", name)
        return match.group(1) if match else name
    stem = os.path.commonprefix(names).rstrip("_-")
    if not stem:
        raise GenerationError("cannot derive a common instance stem for " + ", ".join(names))
    return stem


def _normalize_ip_id(stem: str) -> str:
    value = stem
    upper = value.upper()
    for prefix in BUS_PREFIXES:
        if upper.startswith(prefix) and len(value) - len(prefix) >= 3:
            value = value[len(prefix) :]
            break
    return _normalize_identifier(value)


def _normalize_identifier(value: str | None) -> str:
    if value is None:
        raise GenerationError("cannot normalize a missing identifier")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    if not normalized:
        raise GenerationError(f"cannot normalize identifier {value!r}")
    if normalized[0].isdigit():
        normalized = "value_" + normalized
    return normalized


def _normalize_suffix(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    if not normalized:
        raise GenerationError(f"cannot normalize instance suffix {value!r}")
    return normalized


def _interrupt_event_name(name: str, *, ip_id: str, instance_id: str) -> str:
    normalized = _normalize_identifier(name)
    tokens = normalized.split("_")
    if len(tokens) > 1 and re.search(r"\d", tokens[0]):
        normalized = "_".join(tokens[1:])
    else:
        instance_base = re.sub(r"\d+$", "", instance_id)
        normalized_base = re.sub(r"\d+$", "", normalized)
        if normalized_base in {ip_id, instance_base}:
            normalized = "irq"
    if normalized.isdigit():
        normalized = f"line_{normalized}"
    aliases = {
        "combint": "combined",
        "tfr": "transfer",
        "err": "error",
        "srctran": "source_transaction",
        "dsttran": "destination_transaction",
    }
    return aliases.get(normalized, normalized)


def _is_reserved(name: str) -> bool:
    upper = name.upper()
    return upper.startswith(RESERVED_PREFIXES)


def _is_identity_field(field_id: str, field: Field, register: Register) -> bool:
    if field.bit_width < 8:
        return False
    if register.access not in {"read-only", "read", "unspecified"} and (
        field.access not in {"read-only", "read"}
    ):
        return False
    return field_id in {"id", "type", "version", "head"} or field_id.endswith(
        ("_id", "_type", "_version", "_head")
    )


def _add_feature(target: dict[str, list[str]], capability_id: str, instance_id: str) -> None:
    values = target.setdefault(capability_id, [])
    if instance_id not in values:
        values.append(instance_id)


def _put_value(
    target: dict[str, dict[str, Any]],
    capability_id: str,
    instance_id: str,
    value: Any,
) -> None:
    target.setdefault(capability_id, {})[instance_id] = value


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise GenerationError(f"unsupported YAML scalar {value!r}")
    lowered = value.lower()
    if (
        YAML_KEY.fullmatch(value)
        and lowered not in {"true", "false", "null", "yes", "no", "on", "off"}
        and not value.startswith(("0x", "0X"))
    ):
        return value
    return json.dumps(value, ensure_ascii=False)


def _yaml_inline_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_yaml_scalar(item) for item in value) + "]"
    return _yaml_scalar(value)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _strip_namespaces(root: ET.Element) -> None:
    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]


def _parse_int(text: str | None) -> int:
    if text is None:
        raise GenerationError("missing integer")
    value = text.strip().replace("_", "")
    if not value:
        raise GenerationError("empty integer")
    if value.startswith("#"):
        bits = value[1:]
        if not bits or any(bit not in "01" for bit in bits):
            raise GenerationError(f"unsupported binary integer {text!r}")
        return int(bits, 2)
    try:
        return int(value, 0)
    except ValueError as exc:
        raise GenerationError(f"invalid integer {text!r}") from exc


def _required_text(element: ET.Element, name: str) -> str:
    value = element.findtext(name)
    if value is None or not value.strip():
        raise GenerationError(f"<{element.tag}> has no {name}")
    return value.strip()


def _optional_text(element: ET.Element, name: str, default: str | None) -> str | None:
    value = element.findtext(name)
    return value.strip() if value is not None and value.strip() else default


def _required_int(element: ET.Element, name: str) -> int:
    return _parse_int(_required_text(element, name))


def _optional_int(element: ET.Element, name: str, default: int | None) -> int | None:
    value = element.findtext(name)
    return _parse_int(value) if value is not None and value.strip() else default


def _normalize_access(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", "-", value.strip().lower())
    normalized = normalized.strip("*-")
    aliases = {
        "readonly": "read-only",
        "writeonly": "write-only",
        "readwrite": "read-write",
        "read-writeonce": "read-writeonce",
    }
    return aliases.get(normalized, normalized or None)


def _natural_key(value: str) -> tuple[Any, ...]:
    return tuple(
        int(part) if part.isdigit() else part.lower() for part in NATURAL_PART.split(value)
    )


def _capability_sort_key(capability_id: str) -> tuple[Any, ...]:
    parts = capability_id.split(".")
    kinds = {"feature": 0, "limit": 1, "option": 2, "identity": 3}
    rank = kinds.get(parts[1] if len(parts) > 1 else "", 9)
    return (rank, *_natural_key(capability_id))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic Fact IR, Capability profiles, audit, "
            "and quality reports from one CMSIS-SVD without chip/IP-specific "
            "branches."
        )
    )
    parser.add_argument("--svd", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="directory for transitional et-ip-capability/v1 YAML files",
    )
    parser.add_argument(
        "--facts-output",
        type=Path,
        help="canonical et-svd-facts/v1 JSON output file",
    )
    parser.add_argument(
        "--facts-only",
        action="store_true",
        help="emit/check only the fact IR; requires --facts-output",
    )
    parser.add_argument(
        "--semantic-output-dir",
        type=Path,
        help="directory for et-ip-capability/v2 YAML files",
    )
    parser.add_argument(
        "--audit-output-dir",
        type=Path,
        help="directory for et-capability-audit/v1 YAML files",
    )
    parser.add_argument(
        "--explain",
        action="append",
        default=[],
        metavar="IP.KIND.NAME",
        help="include one generated capability and its evidence in summary",
    )
    parser.add_argument(
        "--quality-output",
        type=Path,
        help="canonical et-capability-quality/v1 JSON output file",
    )
    parser.add_argument(
        "--require-capability",
        action="append",
        default=[],
        metavar="IP.KIND.NAME",
        help="fail quality gate when a required evidenced capability is absent",
    )
    parser.add_argument(
        "--requirements-file",
        action="append",
        default=[],
        type=Path,
        metavar="YAML",
        help=("load a strict test-suite capability requirement manifest; may be repeated"),
    )
    parser.add_argument(
        "--chip-id",
        help="optional assertion/override; defaults to the SVD device name",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if output files are missing, stale, or extra",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        requirement_manifests = [
            load_capability_requirements(path.resolve(strict=True))
            for path in args.requirements_file
        ]
        required_capabilities = merge_capability_requirements(
            requirement_manifests,
            args.require_capability,
        )
        if args.facts_only and args.facts_output is None:
            raise GenerationError("--facts-only requires --facts-output")
        if args.facts_only and any(
            (
                args.output_dir,
                args.semantic_output_dir,
                args.audit_output_dir,
                args.explain,
                args.quality_output,
                args.require_capability,
                args.requirements_file,
            )
        ):
            raise GenerationError("--facts-only cannot be combined with semantic or quality output")
        if (args.semantic_output_dir is None) != (args.audit_output_dir is None):
            raise GenerationError(
                "--semantic-output-dir and --audit-output-dir are required together"
            )
        if not any(
            (
                args.output_dir,
                args.facts_output,
                args.semantic_output_dir,
                args.explain,
                args.quality_output,
                args.require_capability,
                args.requirements_file,
            )
        ):
            raise GenerationError("no output mode selected")
        svd_path = args.svd.resolve(strict=True)
        facts = parse_svd_facts(svd_path)
        summary: dict[str, Any] = {}
        if args.output_dir is not None:
            output_dir = args.output_dir.resolve()
            profiles = build_profiles(
                svd_path=svd_path,
                chip_id=args.chip_id,
                output_dir=output_dir,
                facts=facts,
            )
            profile_summary = write_or_check_profiles(
                profiles,
                output_dir,
                check=args.check,
            )
            summary.update(profile_summary)
            summary["output_dir"] = str(output_dir)
        if args.facts_output is not None:
            facts_output = args.facts_output.resolve()
            fact_text = build_fact_document(
                svd_path=svd_path,
                chip_id=args.chip_id,
                facts=facts,
            )
            summary["facts"] = write_or_check_fact_document(
                fact_text,
                facts_output,
                check=args.check,
            )
            summary["facts_output"] = str(facts_output)
        if (
            args.semantic_output_dir is not None
            or args.explain
            or args.quality_output is not None
            or required_capabilities
        ):
            artifacts, semantic_profiles, semantic_audits = build_semantic_documents(
                svd_path=svd_path,
                chip_id=args.chip_id,
                facts=facts,
            )
            if args.semantic_output_dir is not None:
                semantic_output_dir = args.semantic_output_dir.resolve()
                audit_output_dir = args.audit_output_dir.resolve()
                summary["semantic"] = write_or_check_profiles(
                    semantic_profiles,
                    semantic_output_dir,
                    check=args.check,
                )
                summary["audit"] = write_or_check_profiles(
                    semantic_audits,
                    audit_output_dir,
                    check=args.check,
                )
                summary["semantic_output_dir"] = str(semantic_output_dir)
                summary["audit_output_dir"] = str(audit_output_dir)
            if args.explain:
                explanations: dict[str, Any] = {}
                for capability_id in args.explain:
                    try:
                        explanations[capability_id] = explain_semantic(
                            artifacts,
                            capability_id,
                        )
                    except KeyError as exc:
                        raise GenerationError(
                            f"unknown semantic capability {capability_id!r}"
                        ) from exc
                summary["explain"] = explanations
            if args.quality_output is not None or required_capabilities:
                quality, quality_text = build_quality_document(
                    artifacts,
                    facts=facts,
                    required_capabilities=required_capabilities,
                )
                if args.quality_output is not None:
                    quality_output = args.quality_output.resolve()
                    summary["quality"] = write_or_check_quality_document(
                        quality_text,
                        quality_output,
                        check=args.check,
                    )
                    summary["quality_output"] = str(quality_output)
                summary["quality_status"] = quality["status"]
                summary["quality_summary"] = quality["summary"]
                if quality["status"] != "pass":
                    raise GenerationError(
                        f"capability quality gate failed: {quality['summary']['errors']} error(s)"
                    )
        if requirement_manifests:
            summary["requirement_suites"] = sorted(
                manifest.suite for manifest in requirement_manifests
            )
        summary.update(
            {
                "status": "checked" if args.check else "generated",
                "svd": svd_path.name,
            }
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except (GenerationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
