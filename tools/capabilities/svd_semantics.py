# Conservative, chip-independent semantics derived from :mod:`svd_fact_ir`.
#
# Every emitted value has direct fact evidence.  Facts that cannot be mapped by
# the small universal rules in this module are returned in the audit document.

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from svd_fact_ir import Field, Peripheral, Register, SvdFactIR

PROFILE_SCHEMA = "et-ip-capability/v2"
AUDIT_SCHEMA = "et-capability-audit/v1"
SEMANTIC_GENERATOR_VERSION = 11
RESERVED_PREFIXES = ("rsvd", "reserved")
ACCEPTED_SHORT_TOKENS = {"et", "id", "io"}
CONFIGURABLE_OPTION_ACCESS = {"read-write", "read-writeonce"}

TOKEN_ALIASES = {
    "blk": "block",
    "cfg": "config",
    "cnt": "count",
    "ctl": "control",
    "dis": "disable",
    "dst": "destination",
    "dms": "destination_master_select",
    "en": "enable",
    "err": "error",
    "gat": "gather",
    "int": "interrupt",
    "irq": "interrupt",
    "llp": "linked_list",
    "lms": "linked_list_master_select",
    "num": "count",
    "rept": "repeat",
    "rpt": "repeat",
    "rx": "receive",
    "sca": "scatter",
    "src": "source",
    "sms": "source_master_select",
    "stat": "status",
    "sts": "status",
    "tfr": "transfer",
    "tran": "transaction",
    "tx": "transmit",
    "upd": "update",
    "wb": "writeback",
}

INTERRUPT_ALIASES = {
    "combint": "combined",
    "dsttran": "destination_transaction",
    "err": "error",
    "srctran": "source_transaction",
    "tfr": "transfer_done",
}

_PART = re.compile(r"[A-Za-z]+\d*|\d+")
_CHANNEL = re.compile(r"(?:ch|channel)\d+$")
_CORTEX_M_TOKEN = re.compile(r"m\d+$")
_DESCRIPTION_BREAK = re.compile(r"\bvalues\s*:|[.;\r\n。；]", re.I)
_DESCRIPTION_TITLE = re.compile(r"^[A-Za-z][A-Za-z0-9 _/-]*$")
_ENUM_SUBJECT = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9 _/-]{1,80}?)\s+is\b",
    re.I,
)
_LEADING_ACTION_WORDS = {
    "a",
    "an",
    "contains",
    "controls",
    "defines",
    "determines",
    "enables",
    "if",
    "indicates",
    "select",
    "selects",
    "specifies",
    "the",
    "this",
    "used",
    "when",
}
_TRAILING_STRUCTURE_WORDS = {"bit", "register"}


@dataclass(frozen=True)
class SemanticArtifacts:
    profiles: Mapping[str, Mapping[str, Any]]
    audits: Mapping[str, Mapping[str, Any]]


# One SVD-explicit semantic shape that still needs a stable name.
@dataclass(frozen=True)
class ExplicitSemanticMarker:
    kind: str
    rule: str
    values: tuple[Any, ...] = ()


# One SVD-fixed, member-scoped component parameter value.
@dataclass(frozen=True)
class ComponentParameter:
    name: str
    member: str
    value: str | int | float | bool


def normalize(facts: SvdFactIR, *, chip_id: str) -> SemanticArtifacts:
    profiles: dict[str, Mapping[str, Any]] = {}
    audits: dict[str, Mapping[str, Any]] = {}

    for group in facts.groups:
        instance_order = tuple(item.instance_id for item in group.instances)
        features: dict[str, set[str]] = {}
        limits: dict[str, dict[str, int | float]] = {}
        options: dict[str, dict[str, tuple[Any, ...]]] = {}
        parameters: dict[
            str,
            dict[str, dict[str, str | int | float | bool]],
        ] = {}
        interrupts: dict[str, dict[str, dict[str, Any]]] = {}
        identities: dict[str, dict[str, str | int]] = {"base_address": {}}
        evidence: dict[str, list[dict[str, str]]] = {}
        audit: dict[tuple[str, str, str], dict[str, str]] = {}

        for instance in group.instances:
            instance_id = instance.instance_id
            peripheral = instance.peripheral
            identities["base_address"][instance_id] = f"0x{peripheral.base_address:08X}"
            _add_evidence(
                evidence,
                f"{group.ip_id}.identity.base_address",
                instance=instance_id,
                kind="peripheral",
                path=f"{peripheral.svd_name}.baseAddress",
                rule="direct",
            )

            consumed_fields: set[str] = set()
            _promote_timestamp_counter_semantics(
                peripheral=peripheral,
                capability_prefix=group.ip_id,
                instance_id=instance_id,
                features=features,
                limits=limits,
                evidence=evidence,
                consumed_fields=consumed_fields,
            )
            _promote_mailbox_engine_semantics(
                peripheral=peripheral,
                capability_prefix=group.ip_id,
                instance_id=instance_id,
                features=features,
                limits=limits,
                options=options,
                evidence=evidence,
                consumed_fields=consumed_fields,
            )
            _promote_crc_engine_semantics(
                peripheral=peripheral,
                capability_prefix=group.ip_id,
                instance_id=instance_id,
                features=features,
                limits=limits,
                options=options,
                parameters=parameters,
                evidence=evidence,
                consumed_fields=consumed_fields,
            )
            _promote_aes_engine_semantics(
                peripheral=peripheral,
                capability_prefix=group.ip_id,
                instance_id=instance_id,
                features=features,
                limits=limits,
                options=options,
                evidence=evidence,
                consumed_fields=consumed_fields,
            )
            _promote_cordic_engine_semantics(
                peripheral=peripheral,
                capability_prefix=group.ip_id,
                instance_id=instance_id,
                features=features,
                limits=limits,
                options=options,
                evidence=evidence,
                consumed_fields=consumed_fields,
            )
            option_candidates: dict[str, list[tuple[tuple[Any, ...], str, str]]] = {}
            parameter_candidates: dict[
                str,
                dict[
                    str,
                    list[tuple[str | int | float | bool, str]],
                ],
            ] = {}
            identity_candidates: dict[str, list[tuple[int, str]]] = {}

            for register in peripheral.registers:
                register_path = f"{peripheral.svd_name}.{register.path}"
                if not register.fields:
                    _audit(
                        audit,
                        instance=instance_id,
                        kind="register",
                        path=register_path,
                        reason="no_fields",
                    )
                for field in register.fields:
                    field_path = f"{register_path}.{field.name}"
                    if _is_reserved(field.name):
                        continue
                    if field_path in consumed_fields:
                        continue

                    parameter, parameter_error = _component_parameter(
                        field,
                        register,
                        peripheral_name=peripheral.svd_name,
                    )
                    if parameter is not None:
                        parameter_candidates.setdefault(parameter.name, {}).setdefault(
                            parameter.member, []
                        ).append((parameter.value, field_path))
                    elif parameter_error is not None:
                        _audit(
                            audit,
                            instance=instance_id,
                            kind="field",
                            path=field_path,
                            reason=parameter_error,
                        )

                    if _is_boolean_feature(field) and _feature_is_present(field, register):
                        name = _field_semantic_name(
                            field.name,
                            peripheral_name=peripheral.svd_name,
                            remove_enable=True,
                            allow_generic_enable_description=True,
                            description=field.description,
                            enum_descriptions=_enum_descriptions(field),
                        )
                        if name not in {
                            "enable",
                            group.ip_id,
                            "interrupt",
                        } and not has_dominant_short_tokens(name):
                            features.setdefault(name, set()).add(instance_id)
                            _add_evidence(
                                evidence,
                                f"{group.ip_id}.feature.{name}",
                                instance=instance_id,
                                kind="field",
                                path=field_path,
                                rule="boolean_enable_field",
                            )
                            consumed_fields.add(field_path)
                    elif (
                        parameter is None
                        and parameter_error is None
                        and _is_boolean_feature(field)
                        and field.access
                        in {
                            "read",
                            "read-only",
                        }
                    ):
                        _audit(
                            audit,
                            instance=instance_id,
                            kind="field",
                            path=field_path,
                            reason="disabled_component_parameter",
                        )

                    # An explicit value domain is a configurable Option only
                    # when software can both write the selection and read the
                    # resulting state.  Read-only fields describe status or
                    # implementation parameters; write-only fields commonly
                    # encode commands.  Both stay in Audit until a separate
                    # Identity/Status/Command rule can prove their meaning.
                    option = (
                        _explicit_options(field)
                        if field.access in CONFIGURABLE_OPTION_ACCESS
                        else None
                    )
                    # A one-bit enable field already proves a Feature.  Its
                    # disabled/enabled enum is the control value for that same
                    # fact, not a second independent Option capability.
                    if option and field_path not in consumed_fields:
                        name = _field_semantic_name(
                            field.name,
                            peripheral_name=peripheral.svd_name,
                            description=field.description,
                            enum_descriptions=_enum_descriptions(field),
                        )
                        if name in {"enable", "enabled", group.ip_id} or (
                            has_dominant_short_tokens(name)
                        ):
                            continue
                        option_candidates.setdefault(name, []).append(
                            (option[0], field_path, option[1])
                        )

                    identity_name = _identity_name(field, register)
                    if identity_name is not None:
                        mask = (1 << field.bit_width) - 1
                        value = (register.reset_value >> field.bit_offset) & mask
                        identity_candidates.setdefault(identity_name, []).append(
                            (value, field_path)
                        )

            for name, member_candidates in parameter_candidates.items():
                for member, candidates in member_candidates.items():
                    values = {item[0] for item in candidates}
                    if len(values) != 1:
                        for _, path in candidates:
                            if path not in consumed_fields:
                                _audit(
                                    audit,
                                    instance=instance_id,
                                    kind="field",
                                    path=path,
                                    reason="ambiguous_semantics",
                                )
                        continue
                    parameters.setdefault(name, {}).setdefault(instance_id, {})[member] = next(
                        iter(values)
                    )
                    for _, path in candidates:
                        _add_evidence(
                            evidence,
                            f"{group.ip_id}.parameter.{name}",
                            instance=instance_id,
                            member=member,
                            kind="field",
                            path=path,
                            rule="readonly_component_parameter",
                        )
                        consumed_fields.add(path)

            for name, candidates in option_candidates.items():
                values = {item[0] for item in candidates}
                if len(values) != 1:
                    for _, path, _ in candidates:
                        if path not in consumed_fields:
                            _audit(
                                audit,
                                instance=instance_id,
                                kind="field",
                                path=path,
                                reason="ambiguous_semantics",
                            )
                    continue
                value = next(iter(values))
                options.setdefault(name, {})[instance_id] = value
                for _, path, rule in candidates:
                    _add_evidence(
                        evidence,
                        f"{group.ip_id}.option.{name}",
                        instance=instance_id,
                        kind="field",
                        path=path,
                        rule=rule,
                    )
                    consumed_fields.add(path)
                if all(
                    isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
                ):
                    limit_name = f"max_{name}"
                    limits.setdefault(limit_name, {})[instance_id] = max(value)
                    for _, path, _ in candidates:
                        _add_evidence(
                            evidence,
                            f"{group.ip_id}.limit.{limit_name}",
                            instance=instance_id,
                            kind="field",
                            path=path,
                            rule="explicit_numeric_options_max",
                        )

            for name, candidates in identity_candidates.items():
                values = {item[0] for item in candidates}
                if len(values) != 1:
                    for _, path in candidates:
                        if path not in consumed_fields:
                            _audit(
                                audit,
                                instance=instance_id,
                                kind="field",
                                path=path,
                                reason="ambiguous_semantics",
                            )
                    continue
                identities.setdefault(name, {})[instance_id] = next(iter(values))
                for _, path in candidates:
                    _add_evidence(
                        evidence,
                        f"{group.ip_id}.identity.{name}",
                        instance=instance_id,
                        kind="field",
                        path=path,
                        rule="readonly_reset_identity",
                    )
                    consumed_fields.add(path)

            interrupt_candidates: dict[str, list[tuple[str, int, str]]] = {}
            for interrupt in peripheral.interrupts:
                path = f"{peripheral.svd_name}.interrupt.{interrupt.name}"
                if interrupt.value < 0:
                    _audit(
                        audit,
                        instance=instance_id,
                        kind="interrupt",
                        path=path,
                        reason="unsupported_encoding",
                    )
                    continue
                event = _interrupt_name(
                    interrupt.name,
                    peripheral_name=peripheral.svd_name,
                    instance_id=instance_id,
                    ip_id=group.ip_id,
                )
                interrupt_candidates.setdefault(event, []).append(
                    (interrupt.name, interrupt.value, path)
                )

            for event, candidates in interrupt_candidates.items():
                identities_for_event = {(name, irqn) for name, irqn, _ in candidates}
                if len(identities_for_event) != 1:
                    for _, _, path in candidates:
                        _audit(
                            audit,
                            instance=instance_id,
                            kind="interrupt",
                            path=path,
                            reason="ambiguous_semantics",
                        )
                    continue
                svd_name, irqn = next(iter(identities_for_event))
                interrupts.setdefault(event, {})[instance_id] = {
                    "svd_name": svd_name,
                    "irqn": irqn,
                }
                for _, _, path in candidates:
                    _add_evidence(
                        evidence,
                        f"{group.ip_id}.interrupt.{event}",
                        instance=instance_id,
                        kind="interrupt",
                        path=path,
                        rule="direct",
                    )

            for register in peripheral.registers:
                register_path = f"{peripheral.svd_name}.{register.path}"
                for field in register.fields:
                    if _is_reserved(field.name):
                        continue
                    path = f"{register_path}.{field.name}"
                    if (
                        path not in consumed_fields
                        and (
                            instance_id,
                            "field",
                            path,
                        )
                        not in audit
                    ):
                        _audit(
                            audit,
                            instance=instance_id,
                            kind="field",
                            path=path,
                            reason="no_semantic_mapping",
                        )

        source = {
            "file": facts.source_file,
            "sha256": facts.source_sha256,
            "generator_version": SEMANTIC_GENERATOR_VERSION,
        }
        profile = {
            "schema": PROFILE_SCHEMA,
            "chip": chip_id,
            "ip": group.ip_id,
            "source": dict(source),
            "instances": {
                item.instance_id: {"svd_name": item.peripheral.svd_name} for item in group.instances
            },
            "capabilities": {
                "features": {
                    name: [item for item in instance_order if item in values]
                    for name, values in sorted(features.items())
                },
                "limits": {
                    name: _ordered_instance_values(values, instance_order)
                    for name, values in sorted(limits.items())
                },
                "options": {
                    name: _ordered_instance_values(values, instance_order)
                    for name, values in sorted(options.items())
                },
                "parameters": {
                    name: _ordered_parameter_values(values, instance_order)
                    for name, values in sorted(parameters.items())
                },
                "interrupts": {
                    name: _ordered_instance_values(values, instance_order)
                    for name, values in sorted(interrupts.items())
                },
                "identities": {
                    name: _ordered_instance_values(values, instance_order)
                    for name, values in sorted(identities.items())
                    if values
                },
            },
            "evidence": {
                capability_id: sorted(
                    items,
                    key=lambda item: (
                        item["instance"],
                        item.get("member", ""),
                        item["kind"],
                        item["path"],
                        item["rule"],
                    ),
                )
                for capability_id, items in sorted(evidence.items())
            },
        }
        audit_document = {
            "schema": AUDIT_SCHEMA,
            "chip": chip_id,
            "ip": group.ip_id,
            "source": dict(source),
            "unclassified": sorted(
                audit.values(),
                key=lambda item: (
                    item["instance"],
                    item["kind"],
                    item["path"],
                    item["reason"],
                ),
            ),
        }
        profiles[group.ip_id] = profile
        audits[group.ip_id] = audit_document

    return SemanticArtifacts(profiles=profiles, audits=audits)


def explain(
    artifacts: SemanticArtifacts,
    capability_id: str,
) -> dict[str, Any]:
    parts = capability_id.split(".", 2)
    if len(parts) != 3:
        raise KeyError(capability_id)
    ip_id, kind, name = parts
    profile = artifacts.profiles.get(ip_id)
    if profile is None:
        raise KeyError(capability_id)
    sections = {
        "feature": "features",
        "limit": "limits",
        "option": "options",
        "parameter": "parameters",
        "interrupt": "interrupts",
        "identity": "identities",
    }
    section = sections.get(kind)
    if section is None or name not in profile["capabilities"][section]:
        raise KeyError(capability_id)
    return {
        "capability": capability_id,
        "value": profile["capabilities"][section][name],
        "evidence": profile["evidence"][capability_id],
    }


def _promote_crc_engine_semantics(
    *,
    peripheral: Peripheral,
    capability_prefix: str,
    instance_id: str,
    features: dict[str, set[str]],
    limits: dict[str, dict[str, int | float]],
    options: dict[str, dict[str, tuple[Any, ...]]],
    parameters: dict[str, dict[str, dict[str, str | int | float | bool]]],
    evidence: dict[str, list[dict[str, str]]],
    consumed_fields: set[str],
) -> bool:
    # Promote one SVD-proven CRC engine shape without chip/IP branches.

    registers = {
        "_".join(_tokens(register.source_name)): register for register in peripheral.registers
    }
    control = registers.get("ctrl")
    if control is None:
        return False

    control_fields = {"_".join(_tokens(field.name)): field for field in control.fields}
    selector = next(
        (field for name, field in control_fields.items() if name.endswith("kernel_sel")),
        None,
    )
    if selector is None:
        return False
    mode_labels = {
        item.lower() for item in re.findall(r"\bCRC(?:8|16|32)\b", selector.description, re.I)
    }
    if mode_labels != {"crc8", "crc16", "crc32"}:
        return False

    register_feature_roles = {
        "module_en": "module_enable",
        "poly": "polynomial",
        "ini": "initial_seed",
        "length": "length",
        "res": "result",
        "fifo_trhd": "fifo_threshold",
        "fifo_ovf": "fifo_overflow",
        "int_en": "irq_enable",
        "int_mask": "irq_mask",
        "int_force_ind": "irq_force",
        "int_clr": "irq_clear",
        "int_raw_rpt": "irq_raw_status",
        "int_status_rpt": "irq_status",
    }
    control_feature_suffixes = {
        "refin_en": "refin",
        "refout_en": "refout",
        "xorsel": "xor_out",
        "alr_en": "alr",
        "byteswap_en": "byteswap",
        "check_en": "check",
    }

    required_registers = set(register_feature_roles)
    if not required_registers.issubset(registers):
        return False
    selected_control_fields: dict[str, Field] = {}
    for suffix, role in control_feature_suffixes.items():
        field = next(
            (item for name, item in control_fields.items() if name.endswith(suffix)),
            None,
        )
        if field is None:
            return False
        selected_control_fields[role] = field

    def field_path(register: Register, field: Field) -> str:
        return f"{peripheral.svd_name}.{register.path}.{field.name}"

    selector_path = field_path(control, selector)
    options.setdefault("modes", {})[instance_id] = (
        "crc8",
        "crc16",
        "crc32",
    )
    _add_evidence(
        evidence,
        f"{capability_prefix}.option.modes",
        instance=instance_id,
        kind="field",
        path=selector_path,
        rule="crc_kernel_labels",
    )
    consumed_fields.add(selector_path)

    for role, field in selected_control_fields.items():
        path = field_path(control, field)
        features.setdefault(role, set()).add(instance_id)
        _add_evidence(
            evidence,
            f"{capability_prefix}.feature.{role}",
            instance=instance_id,
            kind="field",
            path=path,
            rule="crc_control_field",
        )
        consumed_fields.add(path)

    byte_swap = selected_control_fields["byteswap"]
    byte_swap_path = field_path(control, byte_swap)
    byte_swap_modes = tuple(
        mode for mode in ("crc8", "crc16", "crc32") if mode.upper() in byte_swap.description.upper()
    )
    if byte_swap_modes:
        options.setdefault("byte_swap_modes", {})[instance_id] = byte_swap_modes
        _add_evidence(
            evidence,
            f"{capability_prefix}.option.byte_swap_modes",
            instance=instance_id,
            kind="field",
            path=byte_swap_path,
            rule="description_mode_scope",
        )

    role_fields: dict[str, Field] = {}
    for register_name, role in register_feature_roles.items():
        register = registers[register_name]
        fields_in_register = [field for field in register.fields if not _is_reserved(field.name)]
        if not fields_in_register:
            return False
        role_fields[role] = fields_in_register[0]
        feature_kind = (
            "register"
            if all(field.access in {"read", "read-only"} for field in fields_in_register)
            else "field"
        )
        for field in fields_in_register:
            path = field_path(register, field)
            features.setdefault(role, set()).add(instance_id)
            _add_evidence(
                evidence,
                f"{capability_prefix}.feature.{role}",
                instance=instance_id,
                kind=feature_kind,
                path=(
                    f"{peripheral.svd_name}.{register.path}" if feature_kind == "register" else path
                ),
                rule="crc_register_role",
            )
            consumed_fields.add(path)

    length_field = role_fields["length"]
    length_path = field_path(registers["length"], length_field)
    limits.setdefault("length_field_max", {})[instance_id] = (1 << length_field.bit_width) - 1
    _add_evidence(
        evidence,
        f"{capability_prefix}.limit.length_field_max",
        instance=instance_id,
        kind="field",
        path=length_path,
        rule="field_encoding_max",
    )

    threshold_field = role_fields["fifo_threshold"]
    threshold_register = registers["fifo_trhd"]
    threshold_path = field_path(threshold_register, threshold_field)
    threshold_mask = (1 << threshold_field.bit_width) - 1
    threshold_reset = (
        threshold_register.reset_value >> threshold_field.bit_offset
    ) & threshold_mask
    if "最大" in threshold_field.description or "maximum" in threshold_field.description.lower():
        limits.setdefault("fifo_threshold_max", {})[instance_id] = threshold_reset
        _add_evidence(
            evidence,
            f"{capability_prefix}.limit.fifo_threshold_max",
            instance=instance_id,
            kind="field",
            path=threshold_path,
            rule="description_declares_reset_maximum",
        )

    result_path = f"{peripheral.svd_name}.{registers['res'].path}"
    parameters.setdefault("result_width_bits", {})[instance_id] = {
        "crc8": 8,
        "crc16": 16,
        "crc32": 32,
    }
    for mode in ("crc8", "crc16", "crc32"):
        _add_evidence(
            evidence,
            f"{capability_prefix}.parameter.result_width_bits",
            instance=instance_id,
            member=mode,
            kind="register",
            path=result_path,
            rule="mode_label_width",
        )

    irq_fields = [field for field in registers["int_en"].fields if not _is_reserved(field.name)]
    source_by_description = {
        "bus_error": ("总线错误", "bus error"),
        "length_error": ("长度错误", "length error"),
        "check_error": ("匹配错误", "check error", "match error"),
    }
    irq_sources: list[str] = []
    irq_paths: list[str] = []
    for source_name, markers in source_by_description.items():
        field = next(
            (
                item
                for item in irq_fields
                if any(marker in item.description.lower() for marker in markers)
            ),
            None,
        )
        if field is None:
            return False
        irq_sources.append(source_name)
        irq_paths.append(field_path(registers["int_en"], field))
    options.setdefault("irq_sources", {})[instance_id] = tuple(irq_sources)
    for path in irq_paths:
        _add_evidence(
            evidence,
            f"{capability_prefix}.option.irq_sources",
            instance=instance_id,
            kind="field",
            path=path,
            rule="interrupt_source_description",
        )
    return True


# 从时间戳计数器的高/低字及控制字段提取语义，不依赖外设名、地址或芯片。
def _promote_timestamp_counter_semantics(
    *,
    peripheral: Peripheral,
    capability_prefix: str,
    instance_id: str,
    features: dict[str, set[str]],
    limits: dict[str, dict[str, int | float]],
    evidence: dict[str, list[dict[str, str]]],
    consumed_fields: set[str],
) -> None:

    registers = {register.path: register for register in peripheral.registers}
    halves: list[tuple[Register, Field]] = []
    for name, word in (("CNTCVL", "lower"), ("CNTCVU", "upper")):
        register = registers.get(name)
        if register is None or len(register.fields) != 1:
            return
        field = register.fields[0]
        description = field.description.lower()
        if (
            field.bit_offset != 0
            or field.bit_width != register.size
            or "timestamp counter" not in description
            or word not in description
        ):
            return
        halves.append((register, field))
    if halves[0][1].bit_width != halves[1][1].bit_width:
        return

    # 位宽来自明确描述为同一时间戳的上下字；不把位宽当成实例数或时钟频率。
    word_bits = halves[0][1].bit_width
    for name, value in (("counter_bits", word_bits * 2), ("word_bits", word_bits)):
        limits.setdefault(name, {})[instance_id] = value
        for register, field in halves:
            path = f"{peripheral.svd_name}.{register.path}.{field.name}"
            _add_evidence(
                evidence,
                f"{capability_prefix}.limit.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule="timestamp_counter_word_pair",
            )
            consumed_fields.add(path)

    # 控制窗口才有启停、暂停和频率登记；读取窗口不继承控制能力。
    control = registers.get("CNTCR")
    if control is None:
        return
    candidates = {
        "counter": (control, "EN", "counter is enabled"),
        "debug_halt": (control, "HDBG", "halt on debug"),
        "frequency_id": (registers.get("CNTFID0"), "FREQ", "ticks per second"),
    }
    for name, (register, field_name, phrase) in candidates.items():
        if register is None:
            continue
        matching = [field for field in register.fields if field.name == field_name]
        if len(matching) != 1:
            continue
        field = matching[0]
        if field.access != "read-write" or phrase not in field.description.lower():
            continue
        if name != "frequency_id" and field.bit_width != 1:
            continue
        features.setdefault(name, set()).add(instance_id)
        path = f"{peripheral.svd_name}.{register.path}.{field.name}"
        _add_evidence(
            evidence,
            f"{capability_prefix}.feature.{name}",
            instance=instance_id,
            kind="field",
            path=path,
            rule="timestamp_counter_control",
        )
        consumed_fields.add(path)


# 从完整Mailbox寄存器形状提取能力；数量来自只读配置值并与数组结构交叉核对。
# 不按芯片、IP名称或地址匹配；不把运行时Peer、Driver实现程度写成硬件Feature。
def _promote_mailbox_engine_semantics(
    *,
    peripheral: Peripheral,
    capability_prefix: str,
    instance_id: str,
    features: dict[str, set[str]],
    limits: dict[str, dict[str, int | float]],
    options: dict[str, dict[str, tuple[Any, ...]]],
    evidence: dict[str, list[dict[str, str]]],
    consumed_fields: set[str],
) -> None:

    # 配置：必须存在唯一的只读容量寄存器，不能用字段位宽猜测实例数量。
    capacity_names = {"MAILBOXES", "INTERRUPTS", "DATAWORDS"}
    configs = [
        register
        for register in peripheral.registers
        if register.access == "read-only"
        and capacity_names.issubset({field.name.upper() for field in register.fields})
    ]
    if len(configs) != 1:
        return
    config = configs[0]
    capacities = {
        field.name.upper(): (config.reset_value >> field.bit_offset) & ((1 << field.bit_width) - 1)
        for field in config.fields
        if field.name.upper() in capacity_names and field.access == "read-only"
    }
    if set(capacities) != capacity_names or not all(capacities.values()):
        return
    if any(
        config.reset_mask & (((1 << field.bit_width) - 1) << field.bit_offset)
        != ((1 << field.bit_width) - 1) << field.bit_offset
        for field in config.fields
        if field.name.upper() in capacity_names
    ):
        return

    # 结构：按展开后的Cluster归组；每个Mailbox必须具备同样的原子路由与数据字段。
    groups: dict[str, dict[str, tuple[Register, Field]]] = {}
    for register in peripheral.registers:
        parent = register.path.rpartition(".")[0]
        if parent:
            for field in register.fields:
                groups.setdefault(parent, {})[field.name.upper()] = (register, field)
    boxes = [fields for fields in groups.values() if "AUTOACKNOWLEDGE" in fields]
    pending = [fields for fields in groups.values() if "RAWINTSTAT" in fields]
    required = {
        "SOURCE",
        "DESTINATIONSET",
        "DESTINATIONCLEAR",
        "DESTINATIONSTATUS",
        "AUTOACKNOWLEDGE",
        "AUTOLINK",
        "MASKSET",
        "MASKCLEAR",
        "MASKSTATUS",
        "SEND",
    }
    if len(boxes) != capacities["MAILBOXES"] or len(pending) != capacities["INTERRUPTS"]:
        return
    for fields in boxes:
        if not required.issubset(fields):
            return
        for name in ("AUTOACKNOWLEDGE", "AUTOLINK"):
            field = fields[name][1]
            if (
                field.bit_width != 1
                or field.access != "read-write"
                or "enable" not in field.description.lower()
            ):
                return
        send = fields["SEND"][1]
        if send.bit_width != 2 or send.access != "read-write":
            return
        text = " ".join(send.description.lower().split())
        if not all(
            value in text
            for value in (
                "00 = inactive",
                "01 = send message to destination",
                "10 = send message to source",
                "11 = invalid",
            )
        ):
            return
        data = {name: item for name, item in fields.items() if re.fullmatch(r"DATA\d+", name)}
        if set(data) != {f"DATA{index}" for index in range(capacities["DATAWORDS"])}:
            return
        if any(field.bit_width != 32 or field.access != "read-write" for _, field in data.values()):
            return
        if any(
            fields[name][1].bit_width < capacities["INTERRUPTS"]
            for name in (
                "SOURCE",
                "DESTINATIONSET",
                "DESTINATIONCLEAR",
                "DESTINATIONSTATUS",
                "MASKSET",
                "MASKCLEAR",
                "MASKSTATUS",
            )
        ):
            return
        if "polling" not in fields["MASKSTATUS"][1].description.lower():
            return
        if any(
            fields[name][1].access not in {"read-write", "write-only"}
            for name in ("SOURCE", "DESTINATIONSET", "DESTINATIONCLEAR", "MASKSET", "MASKCLEAR")
        ):
            return
        if any(
            fields[name][1].access != "read-only" for name in ("DESTINATIONSTATUS", "MASKSTATUS")
        ):
            return
        auto_ack_register, auto_ack = fields["AUTOACKNOWLEDGE"]
        auto_link_register, auto_link = fields["AUTOLINK"]
        if (
            auto_ack_register.path != auto_link_register.path
            or auto_ack.bit_offset == auto_link.bit_offset
        ):
            return
    if any(
        not {"MASKINTSTAT", "RAWINTSTAT"}.issubset(fields)
        or any(
            fields[name][1].access != "read-only"
            or fields[name][1].bit_width < capacities["MAILBOXES"]
            for name in ("MASKINTSTAT", "RAWINTSTAT")
        )
        for fields in pending
    ):
        return

    # 证据：每个语义都绑定原始字段路径；相同寄存器阵列不能同时留在未分类Audit。
    def emit(kind: str, name: str, selected: list[tuple[Register, Field]]) -> None:
        for register, field in selected:
            path = f"{peripheral.svd_name}.{register.path}.{field.name}"
            _add_evidence(
                evidence,
                f"{capability_prefix}.{kind}.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule="mailbox_field_contract",
            )
            consumed_fields.add(path)

    feature_fields = {
        "manual_ack": ("SEND",),
        "ack_payload_update": ("SEND", "DATA0"),
        "auto_ack": ("AUTOACKNOWLEDGE", "DESTINATIONCLEAR"),
        "explicit_ack_in_auto": ("AUTOACKNOWLEDGE", "SEND"),
        "auto_link": ("AUTOLINK",),
        "auto_ack_link": ("AUTOLINK", "AUTOACKNOWLEDGE"),
        "irq_delivery": ("MASKSET", "MASKCLEAR"),
        "polling": ("MASKCLEAR",),
        "multi_destination": ("DESTINATIONSET", "DESTINATIONCLEAR"),
    }
    for name, fields in feature_fields.items():
        features.setdefault(name, set()).add(instance_id)
        emit("feature", name, [box[field] for box in boxes for field in fields])
    for name, values, field in (
        ("ack_modes", ("manual", "auto"), "AUTOACKNOWLEDGE"),
        ("link_modes", ("single", "linked"), "AUTOLINK"),
    ):
        options.setdefault(name, {})[instance_id] = values
        emit("option", name, [box[field] for box in boxes])
    for name, value in {
        "mailbox_count": capacities["MAILBOXES"],
        "channel_count": capacities["INTERRUPTS"],
        "data_word_count": capacities["DATAWORDS"],
        "payload_bytes_per_mailbox": capacities["DATAWORDS"] * 4,
        "linked_payload_max_bytes": capacities["MAILBOXES"] * capacities["DATAWORDS"] * 4,
    }.items():
        limits.setdefault(name, {})[instance_id] = value
        # 容量由完整只读配置寄存器联合解码，不把它错误标成可配置字段的取值上限。
        _add_evidence(
            evidence,
            f"{capability_prefix}.limit.{name}",
            instance=instance_id,
            kind="register",
            path=f"{peripheral.svd_name}.{config.path}",
            rule="mailbox_configuration_capacity",
        )


def _promote_aes_engine_semantics(
    *,
    peripheral: Peripheral,
    capability_prefix: str,
    instance_id: str,
    features: dict[str, set[str]],
    limits: dict[str, dict[str, int | float]],
    options: dict[str, dict[str, tuple[Any, ...]]],
    evidence: dict[str, list[dict[str, str]]],
    consumed_fields: set[str],
) -> bool:
    # 只按完整寄存器形状提升 AES 兼容引擎，不按 chip_id 或 ip_id 分支。
    registers = {
        "_".join(_tokens(register.source_name)): register for register in peripheral.registers
    }
    required_registers = {
        "work",
        "crtl",
        "work_mode",
        "block_cnt",
        "data_size0",
        "data_size1",
        "dma",
        "data",
        "result",
        "rpt_aes_work",
        "rpt_aes_sts",
        "int_en",
        "int_mask",
        "int_force_ind",
        "int_clr",
        "rpt_aes_int_status",
        "rpt_aes_int_raw",
        *(f"work_key{index}" for index in range(8)),
        *(f"work_iv{index}" for index in range(4)),
        *(f"din{index}" for index in range(4)),
        *(f"result_dout{index}" for index in range(4)),
    }
    if not required_registers.issubset(registers):
        return False

    def fields_of(register_name: str) -> dict[str, Field]:
        return {
            "_".join(_tokens(field.name)): field
            for field in registers[register_name].fields
            if not _is_reserved(field.name)
        }

    required_fields = {
        "work": {"en": (0, 1)},
        "crtl": {
            "padding": (0, 2),
            "direction": (2, 1),
            "key_size": (3, 1),
            "dma_mode": (4, 1),
            "endian_sel": (5, 1),
        },
        "work_mode": {"mode": (0, 2)},
        "data_size0": {"size0": (0, 32)},
        "data_size1": {"size1": (0, 4)},
        "dma": {"en": (0, 2)},
        "rpt_aes_work": {"busy": (0, 1)},
        "rpt_aes_sts": {
            "finish": (0, 1),
            "din_flg": (1, 1),
            "dout_flg": (2, 1),
        },
    }
    selected_fields: dict[str, dict[str, Field]] = {}
    for register_name, expected_fields in required_fields.items():
        actual = fields_of(register_name)
        for field_name, (bit_offset, bit_width) in expected_fields.items():
            field = actual.get(field_name)
            if field is None or (field.bit_offset, field.bit_width) != (
                bit_offset,
                bit_width,
            ):
                return False
        selected_fields[register_name] = actual

    # 数据、密钥、IV 和中断路径的位宽也必须完整，避免同名寄存器误识别。
    for register_name in (
        *(f"work_key{index}" for index in range(8)),
        *(f"work_iv{index}" for index in range(4)),
        *(f"din{index}" for index in range(4)),
        *(f"result_dout{index}" for index in range(4)),
        "data",
        "result",
        "block_cnt",
    ):
        fields = fields_of(register_name)
        if len(fields) != 1:
            return False
        field = next(iter(fields.values()))
        if field.bit_offset != 0 or field.bit_width != 32:
            return False

    interrupt_registers = (
        "int_en",
        "int_mask",
        "int_force_ind",
        "int_clr",
        "rpt_aes_int_status",
        "rpt_aes_int_raw",
    )
    for register_name in interrupt_registers:
        fields = fields_of(register_name)
        if len(fields) != 1:
            return False
        field = next(iter(fields.values()))
        if field.bit_offset != 0 or field.bit_width != 7:
            return False

    def field_path(register_name: str, field: Field) -> str:
        register = registers[register_name]
        return f"{peripheral.svd_name}.{register.path}.{field.name}"

    def add_feature(name: str, paths: tuple[str, ...], rule: str) -> None:
        features.setdefault(name, set()).add(instance_id)
        for path in paths:
            _add_evidence(
                evidence,
                f"{capability_prefix}.feature.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule=rule,
            )

    def add_option(name: str, values: tuple[Any, ...], paths: tuple[str, ...]) -> None:
        options.setdefault(name, {})[instance_id] = values
        for path in paths:
            _add_evidence(
                evidence,
                f"{capability_prefix}.option.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule="aes_field_encoding",
            )

    crtl = selected_fields["crtl"]
    mode = selected_fields["work_mode"]["mode"]
    work_en = selected_fields["work"]["en"]
    dma_en = selected_fields["dma"]["en"]
    status_fields = selected_fields["rpt_aes_sts"]
    add_feature("module_enable", (field_path("work", work_en),), "aes_control_path")
    add_feature("encryption", (field_path("crtl", crtl["direction"]),), "aes_direction")
    add_feature("decryption", (field_path("crtl", crtl["direction"]),), "aes_direction")
    add_feature(
        "key",
        tuple(
            field_path(f"work_key{index}", next(iter(fields_of(f"work_key{index}").values())))
            for index in range(8)
        ),
        "aes_key_path",
    )
    add_feature(
        "iv",
        tuple(
            field_path(f"work_iv{index}", next(iter(fields_of(f"work_iv{index}").values())))
            for index in range(4)
        ),
        "aes_iv_path",
    )
    add_feature(
        "ctr_counter",
        (field_path("block_cnt", next(iter(fields_of("block_cnt").values()))),),
        "aes_counter_path",
    )
    add_feature("padding", (field_path("crtl", crtl["padding"]),), "aes_padding")
    add_feature(
        "status",
        (*(field_path("rpt_aes_sts", item) for item in status_fields.values()),),
        "aes_status_path",
    )
    add_feature(
        "cpu_register_path",
        tuple(
            field_path(f"din{index}", next(iter(fields_of(f"din{index}").values())))
            for index in range(4)
        ),
        "aes_register_data_path",
    )
    add_feature(
        "dma_fifo_path",
        (field_path("data", next(iter(fields_of("data").values()))),),
        "aes_fifo_data_path",
    )
    add_feature("dma", (field_path("dma", dma_en),), "aes_dma_gate")

    interrupt_paths = tuple(
        field_path(register_name, next(iter(fields_of(register_name).values())))
        for register_name in interrupt_registers[:4]
    )
    add_feature("interrupts", interrupt_paths, "aes_interrupt_path")

    add_option("directions", ("encrypt", "decrypt"), (field_path("crtl", crtl["direction"]),))
    add_option("key_sizes", (128, 256), (field_path("crtl", crtl["key_size"]),))
    add_option("modes", ("ecb", "cbc", "ctr"), (field_path("work_mode", mode),))
    add_option("padding_modes", ("none", "zero", "pkcs7"), (field_path("crtl", crtl["padding"]),))
    add_option("endian_modes", ("little", "big"), (field_path("crtl", crtl["endian_sel"]),))
    add_option("dma_modes", ("fifo", "register"), (field_path("crtl", crtl["dma_mode"]),))
    add_option(
        "irq_sources",
        (
            "output_conflict",
            "key_missing",
            "iv_missing",
            "complete",
            "incomplete_disable",
            "data_in_request",
            "data_out_request",
        ),
        (field_path("int_en", next(iter(fields_of("int_en").values()))),),
    )

    size0 = selected_fields["data_size0"]["size0"]
    size1 = selected_fields["data_size1"]["size1"]
    size_paths = (field_path("data_size0", size0), field_path("data_size1", size1))
    limits.setdefault("block_size_bytes", {})[instance_id] = 16
    limits.setdefault("data_length_bits", {})[instance_id] = 36
    limits.setdefault("data_length_max", {})[instance_id] = (1 << 36) - 1
    for name, rule, paths in (
        (
            "block_size_bytes",
            "four_word_block_path",
            tuple(
                field_path(f"din{index}", next(iter(fields_of(f"din{index}").values())))
                for index in range(4)
            ),
        ),
        ("data_length_bits", "concatenated_field_width", size_paths),
        ("data_length_max", "concatenated_field_encoding_max", size_paths),
    ):
        for path in paths:
            _add_evidence(
                evidence,
                f"{capability_prefix}.limit.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule=rule,
            )

    # 已被上述稳定语义完整分类的字段不再落入 no_semantic_mapping 审计。
    consumed_registers = required_registers
    for register_name in consumed_registers:
        for field in fields_of(register_name).values():
            consumed_fields.add(field_path(register_name, field))
    return True


def _promote_cordic_engine_semantics(
    *,
    peripheral: Peripheral,
    capability_prefix: str,
    instance_id: str,
    features: dict[str, set[str]],
    limits: dict[str, dict[str, int | float]],
    options: dict[str, dict[str, tuple[Any, ...]]],
    evidence: dict[str, list[dict[str, str]]],
    consumed_fields: set[str],
) -> bool:
    # 只按完整寄存器形状提升 CORDIC 兼容引擎，不按 chip_id 或 ip_id 分支。
    registers = {
        "_".join(_tokens(register.source_name)): register for register in peripheral.registers
    }
    function_registers = (
        "sincos_cal",
        "pm_cal",
        "arctan_cal",
        "hsincos_cal",
        "harctan_cal",
        "ex_cal",
        "ln_cal",
        "sqrt_cal",
        "tan_cal",
    )
    interrupt_registers = (
        "int_en",
        "int_mask",
        "int_force_ind",
        "int_clr",
        "int_raw_rpt",
        "int_status_rpt",
    )
    required_registers = {
        "ctrl0",
        "status_rpt",
        "wr_nargs_cnt_rpt",
        "rpt_cordic_float2_fixed",
        "res1_rpt",
        "res2_rpt",
        *function_registers,
        *interrupt_registers,
    }
    if not required_registers.issubset(registers):
        return False

    def fields_of(register_name: str) -> dict[str, Field]:
        return {
            "_".join(_tokens(field.name)): field
            for field in registers[register_name].fields
            if not _is_reserved(field.name)
        }

    required_fields = {
        "ctrl0": {
            "cordic_noi": (0, 5),
            "cordic_scale": (5, 3),
            "cordic_argsize": (8, 1),
            "cordic_ressize": (9, 1),
            "cordic_work_mode": (10, 2),
            "cordic_fmode": (12, 1),
            "cordic_dmode": (13, 1),
            "cordic_sincos_nres": (16, 1),
            "cordic_pm_nres": (20, 1),
            "cordic_hsincos_nres": (24, 1),
        },
        "status_rpt": {
            "wr_nargs_ovf_rpt": (0, 1),
            "rrdy_flg_rpt": (4, 1),
            "wr_arg2_error_rpt": (8, 1),
        },
        "rpt_cordic_float2_fixed": {
            "udf": (0, 1),
            "ovf": (1, 1),
        },
    }
    selected_fields: dict[str, dict[str, Field]] = {}
    for register_name, expected_fields in required_fields.items():
        actual = fields_of(register_name)
        for field_name, (bit_offset, bit_width) in expected_fields.items():
            field = actual.get(field_name)
            if field is None or (field.bit_offset, field.bit_width) != (
                bit_offset,
                bit_width,
            ):
                return False
        selected_fields[register_name] = actual

    # 函数输入、结果、参数计数和中断寄存器必须具备完整位宽，避免误识别。
    for register_name in (*function_registers, "res1_rpt", "res2_rpt"):
        register_fields = fields_of(register_name)
        if len(register_fields) != 1:
            return False
        field = next(iter(register_fields.values()))
        if field.bit_offset != 0 or field.bit_width != 32:
            return False

    argument_count_fields = fields_of("wr_nargs_cnt_rpt")
    if len(argument_count_fields) != 1:
        return False
    argument_count_field = next(iter(argument_count_fields.values()))
    if argument_count_field.bit_offset != 0 or argument_count_field.bit_width != 2:
        return False

    for register_name in interrupt_registers:
        register_fields = fields_of(register_name)
        if len(register_fields) != 1:
            return False
        field = next(iter(register_fields.values()))
        if field.bit_offset != 0 or field.bit_width != 3:
            return False

    def field_path(register_name: str, field: Field) -> str:
        register = registers[register_name]
        return f"{peripheral.svd_name}.{register.path}.{field.name}"

    def add_feature(name: str, paths: tuple[str, ...], rule: str) -> None:
        features.setdefault(name, set()).add(instance_id)
        for path in paths:
            _add_evidence(
                evidence,
                f"{capability_prefix}.feature.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule=rule,
            )

    def add_option(name: str, values: tuple[Any, ...], paths: tuple[str, ...]) -> None:
        options.setdefault(name, {})[instance_id] = values
        for path in paths:
            _add_evidence(
                evidence,
                f"{capability_prefix}.option.{name}",
                instance=instance_id,
                kind="field",
                path=path,
                rule="cordic_field_encoding",
            )

    ctrl = selected_fields["ctrl0"]
    status = selected_fields["status_rpt"]
    conversion = selected_fields["rpt_cordic_float2_fixed"]
    function_paths = tuple(
        field_path(name, next(iter(fields_of(name).values()))) for name in function_registers
    )
    interrupt_paths = tuple(
        field_path(name, next(iter(fields_of(name).values()))) for name in interrupt_registers
    )

    add_feature("calculation_engine", function_paths, "cordic_function_input_path")
    add_feature(
        "argument_width",
        (field_path("ctrl0", ctrl["cordic_argsize"]),),
        "cordic_argument_width",
    )
    add_feature(
        "result_width",
        (field_path("ctrl0", ctrl["cordic_ressize"]),),
        "cordic_result_width",
    )
    add_feature(
        "input_range",
        (field_path("ctrl0", ctrl["cordic_dmode"]),),
        "cordic_input_range",
    )
    add_feature(
        "scale",
        (field_path("ctrl0", ctrl["cordic_scale"]),),
        "cordic_scale_field",
    )
    add_feature(
        "precision_cycles",
        (field_path("ctrl0", ctrl["cordic_noi"]),),
        "cordic_iteration_field",
    )
    add_feature(
        "result_count",
        tuple(
            field_path("ctrl0", ctrl[name])
            for name in (
                "cordic_sincos_nres",
                "cordic_pm_nres",
                "cordic_hsincos_nres",
            )
        ),
        "cordic_result_count",
    )
    add_feature(
        "work_mode",
        (field_path("ctrl0", ctrl["cordic_work_mode"]),),
        "cordic_work_mode",
    )
    add_feature(
        "complete_status",
        (field_path("status_rpt", status["rrdy_flg_rpt"]),),
        "cordic_status_path",
    )
    add_feature(
        "arg_overflow_status",
        (field_path("status_rpt", status["wr_nargs_ovf_rpt"]),),
        "cordic_status_path",
    )
    add_feature(
        "pm_arg2_error_status",
        (field_path("status_rpt", status["wr_arg2_error_rpt"]),),
        "cordic_status_path",
    )
    add_feature(
        "float_conversion_status",
        tuple(field_path("rpt_cordic_float2_fixed", item) for item in conversion.values()),
        "cordic_conversion_status_path",
    )
    add_feature("interrupts", interrupt_paths[:4], "cordic_interrupt_path")

    add_option(
        "math_functions",
        (
            "sincos",
            "phase_modulus",
            "arctan",
            "hsincos",
            "atanh",
            "exp",
            "ln",
            "sqrt",
            "tan",
        ),
        function_paths,
    )
    add_option(
        "numeric_modes",
        ("fixed", "float32"),
        (field_path("ctrl0", ctrl["cordic_fmode"]),),
    )
    add_option(
        "argument_widths",
        (16, 32),
        (field_path("ctrl0", ctrl["cordic_argsize"]),),
    )
    add_option(
        "result_widths",
        (16, 32),
        (field_path("ctrl0", ctrl["cordic_ressize"]),),
    )
    add_option(
        "input_ranges",
        ("normalized", "direct_angle"),
        (field_path("ctrl0", ctrl["cordic_dmode"]),),
    )
    add_option(
        "result_counts",
        (1, 2),
        tuple(
            field_path("ctrl0", ctrl[name])
            for name in (
                "cordic_sincos_nres",
                "cordic_pm_nres",
                "cordic_hsincos_nres",
            )
        ),
    )
    add_option(
        "work_modes",
        ("interrupt", "polling", "zero_overhead", "dma"),
        (field_path("ctrl0", ctrl["cordic_work_mode"]),),
    )
    add_option(
        "irq_sources",
        ("arg_overflow", "calculation_complete", "pm_arg2_error"),
        (field_path("int_en", next(iter(fields_of("int_en").values()))),),
    )

    # 已被上述稳定语义完整分类的字段不再落入 no_semantic_mapping 审计。
    for register_name in required_registers:
        for field in fields_of(register_name).values():
            consumed_fields.add(field_path(register_name, field))
    return True


def _field_semantic_name(
    raw_name: str,
    *,
    peripheral_name: str,
    remove_enable: bool = False,
    allow_generic_enable_description: bool = False,
    description: str = "",
    enum_descriptions: Iterable[str] = (),
) -> str:
    tokens = _tokens(raw_name)
    peripheral_tokens = _tokens(peripheral_name)
    if tokens[: len(peripheral_tokens)] == peripheral_tokens:
        tokens = tokens[len(peripheral_tokens) :]
    while tokens and _CHANNEL.fullmatch(tokens[0]):
        tokens.pop(0)
    expanded = [TOKEN_ALIASES.get(token, token) for token in tokens]
    if (
        remove_enable
        and len(expanded) > 1
        and expanded[-1]
        in {
            "enable",
            "enabled",
        }
    ):
        expanded.pop()
    if not expanded:
        expanded = ["enable"]
    raw_semantic = _semantic_identifier(expanded)
    generic_enable = raw_semantic in {"enable", "enabled"}
    if not has_dominant_short_tokens(raw_semantic) and not generic_enable:
        return raw_semantic
    if generic_enable and not allow_generic_enable_description:
        return raw_semantic
    description_name = _description_semantic_name(
        description,
        raw_semantic=raw_semantic,
        remove_enable=remove_enable,
    )
    if description_name is not None:
        return description_name
    enum_name = _common_enum_subject_name(
        enum_descriptions,
        raw_semantic=raw_semantic,
        remove_enable=remove_enable,
    )
    return enum_name or raw_semantic


# Return unstable short tokens used by semantic quality checks.
def opaque_short_tokens(name: str) -> tuple[str, ...]:

    tokens = [token for part in name.split(".") for token in part.split("_")]
    return tuple(
        token
        for token in tokens
        if len(token) <= 2
        and not token.isdigit()
        and token not in ACCEPTED_SHORT_TOKENS
        and _CORTEX_M_TOKEN.fullmatch(token) is None
    )


# Return whether abbreviations dominate one natural lookup phrase.
def has_dominant_short_tokens(name: str) -> bool:

    tokens = [token for part in name.split(".") for token in part.split("_")]
    short = opaque_short_tokens(name)
    return bool(short) and len(short) * 2 >= len(tokens)


def _description_semantic_name(
    description: str,
    *,
    raw_semantic: str,
    remove_enable: bool,
) -> str | None:
    if raw_semantic in {"enable", "enabled"}:
        boolean_subject = re.fullmatch(
            r"\s*1\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 _/-]{0,60}?)"
            r"\s+is\s+enabled\b.*?,\s*0\s+(?:the\s+)?\1"
            r"\s+is\s+disabled\b.*",
            description,
            re.I,
        )
        if boolean_subject is not None:
            return _validated_expansion(
                _tokens(boolean_subject.group(1)),
                raw_semantic=raw_semantic,
                remove_enable=remove_enable,
            )
    phrase = _DESCRIPTION_BREAK.split(description.strip(), maxsplit=1)[0].strip()
    if not phrase or not _DESCRIPTION_TITLE.fullmatch(phrase):
        return None
    action = re.fullmatch(
        r"enables?\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 _/-]{0,80})",
        phrase,
        re.I,
    )
    if action is not None:
        phrase = action.group(1)
    return _validated_expansion(
        _tokens(phrase),
        raw_semantic=raw_semantic,
        remove_enable=remove_enable,
    )


def _common_enum_subject_name(
    descriptions: Iterable[str],
    *,
    raw_semantic: str,
    remove_enable: bool,
) -> str | None:
    subjects = []
    for description in descriptions:
        match = _ENUM_SUBJECT.match(description)
        if match is None:
            return None
        subjects.append(tuple(_tokens(match.group(1))))
    if not subjects or len(set(subjects)) != 1:
        return None
    return _validated_expansion(
        subjects[0],
        raw_semantic=raw_semantic,
        remove_enable=remove_enable,
    )


def _validated_expansion(
    source_tokens: Iterable[str],
    *,
    raw_semantic: str,
    remove_enable: bool,
) -> str | None:
    tokens = [TOKEN_ALIASES.get(token, token) for token in source_tokens]
    minimum = 1 if raw_semantic in {"enable", "enabled"} else 2
    if not minimum <= len(tokens) <= 8 or tokens[0] in _LEADING_ACTION_WORDS:
        return None
    while len(tokens) > 1 and tokens[-1] in _TRAILING_STRUCTURE_WORDS:
        tokens.pop()
    if remove_enable:
        if len(tokens) > 1 and tokens[-2:] == ["enable", "status"]:
            del tokens[-2:]
        elif len(tokens) > 1 and tokens[-1] in {"enable", "enabled"}:
            tokens.pop()
    if not tokens:
        return None
    candidate = _semantic_identifier(tokens)
    if has_dominant_short_tokens(candidate):
        return None
    raw_meaningful = {
        token
        for token in raw_semantic.split("_")
        if len(token) > 2 and token not in {"enable", "enabled"}
    }
    if not raw_meaningful.issubset(set(tokens)):
        return None
    return candidate


def _enum_descriptions(field: Field) -> tuple[str, ...]:
    standard = tuple(
        item.description
        for item in field.enum_values
        if item.value is not None and item.description
    )
    if standard:
        return standard
    return tuple(item.description for item in field.inline_values if item.description)


def _interrupt_name(
    raw_name: str,
    *,
    peripheral_name: str,
    instance_id: str,
    ip_id: str,
) -> str:
    normalized = "_".join(_tokens(raw_name))
    prefixes = {
        "_".join(_tokens(peripheral_name)),
        "_".join(_tokens(instance_id)),
        "_".join(_tokens(ip_id)),
    }
    if normalized in prefixes:
        return "irq"
    for prefix in sorted(prefixes, key=len, reverse=True):
        if normalized.startswith(prefix + "_"):
            normalized = normalized[len(prefix) + 1 :]
            break
    if normalized.isdigit():
        return f"line_{normalized}"
    normalized = re.sub(r"_(?:irq|interrupt|int)$", "", normalized)
    value = INTERRUPT_ALIASES.get(
        normalized,
        "_".join(TOKEN_ALIASES.get(item, item) for item in normalized.split("_")),
    )
    return _semantic_identifier(value.split("_"))


def _is_boolean_feature(field: Field) -> bool:
    if field.bit_width != 1:
        return False
    tokens = _tokens(field.name)
    return bool(tokens) and tokens[-1] in {"en", "enable", "enabled"}


# Return one explicit channel parameter or a stable audit reason.
def _component_parameter(
    field: Field,
    register: Register,
    *,
    peripheral_name: str,
) -> tuple[ComponentParameter | None, str | None]:

    if field.access not in {"read", "read-only"}:
        return None, None
    marker_tokens = _tokens(f"{register.source_name} {register.description}")
    if not any(
        left in {"comp", "component"} and right in {"param", "params", "parameter", "parameters"}
        for left, right in zip(marker_tokens, marker_tokens[1:])
    ):
        return None, None
    field_tokens = _tokens(field.name)
    if not field_tokens:
        return None, "ambiguous_semantics"
    member_match = re.fullmatch(r"(?:ch|channel)(\d+)", field_tokens[0])
    if member_match is None:
        # V5 deliberately introduces only the proven channel-scoped shape.
        # Instance-wide component parameters remain in Audit until the same
        # contract has been reviewed on more than one SVD family.
        return None, None
    member = f"channel_{int(member_match.group(1))}"
    name = _field_semantic_name(
        field.name,
        peripheral_name=peripheral_name,
        description=field.description,
        enum_descriptions=_enum_descriptions(field),
        remove_enable=_is_boolean_feature(field),
    )
    if name in {"enable", "enabled", "value"} or has_dominant_short_tokens(name):
        return None, "ambiguous_semantics"

    encoded = [item for item in field.enum_values if item.value is not None]
    if not encoded:
        encoded = list(field.inline_values)
    if not encoded:
        return None, None
    mask = (1 << field.bit_width) - 1
    selected = (register.reset_value >> field.bit_offset) & mask
    matches = [item for item in encoded if item.value == selected]
    if len(matches) != 1:
        return None, "ambiguous_semantics"
    item = matches[0]
    value = _component_parameter_value(name, item.name, item.description)
    if isinstance(value, str):
        if value.startswith("reserved") or has_dominant_short_tokens(value):
            return None, "unsupported_encoding"
        if value == "true":
            value = True
        elif value == "false":
            value = False
    return ComponentParameter(name=name, member=member, value=value), None


# Decode a selected implementation value without channel prose leakage.
def _component_parameter_value(
    parameter_name: str,
    encoded_name: str,
    description: str,
) -> Any:

    parameter_tokens = parameter_name.split("_")
    encoded_tokens = [TOKEN_ALIASES.get(item, item) for item in _tokens(encoded_name)]
    if encoded_tokens[: len(parameter_tokens)] == parameter_tokens:
        suffix = encoded_tokens[len(parameter_tokens) :]
        if len(suffix) == 1 and suffix[0].isdigit():
            return int(suffix[0])
    return _enum_label(parameter_name, encoded_name, description)


def _feature_is_present(field: Field, register: Register) -> bool:
    if field.access not in {"read", "read-only"}:
        return True
    mask = (1 << field.bit_width) - 1
    return ((register.reset_value >> field.bit_offset) & mask) == 1


def _explicit_options(field: Field) -> tuple[tuple[Any, ...], str] | None:
    if field.enum_values:
        values = [item for item in field.enum_values if item.value is not None]
        if values:
            labels = tuple(_enum_label(field.name, item.name, item.description) for item in values)
            if len(set(labels)) == len(labels):
                return labels, "enumerated_values"
    if field.inline_values:
        labels = tuple(
            _enum_label(field.name, item.name, item.description) for item in field.inline_values
        )
        if len(set(labels)) == len(labels):
            return labels, "inline_values"
    return None


# Return review markers without promoting them to capabilities.
#
# This deliberately reuses the exact generic predicates used by
# :func:`normalize`.  A marker means that the SVD explicitly describes a
# semantic shape, but it does not prove that a stable cross-chip capability
# name can be emitted.
def explicit_field_markers(field: Field) -> tuple[ExplicitSemanticMarker, ...]:

    markers: list[ExplicitSemanticMarker] = []
    if _is_boolean_feature(field):
        markers.append(
            ExplicitSemanticMarker(
                kind="feature",
                rule="boolean_enable_field",
            )
        )
    option = _explicit_options(field)
    if option is not None:
        values, rule = option
        markers.append(
            ExplicitSemanticMarker(
                kind="option",
                rule=rule,
                values=values,
            )
        )
        if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in values):
            markers.append(
                ExplicitSemanticMarker(
                    kind="limit",
                    rule="explicit_numeric_options_max",
                    values=values,
                )
            )
    return tuple(markers)


def _enum_label(
    field_name: str,
    enum_name: str,
    description: str,
) -> Any:
    field_tokens = _tokens(field_name)
    enum_tokens = _tokens(enum_name)
    candidate = enum_tokens
    if enum_tokens[: len(field_tokens)] == field_tokens:
        suffix = enum_tokens[len(field_tokens) :]
        if suffix and any(len(item) > 1 and item.isalpha() for item in suffix):
            candidate = suffix
        elif (description_value := _description_value(description)) is not None:
            return description_value
    return "_".join(TOKEN_ALIASES.get(item, item) for item in candidate)


def _description_value(description: str) -> Any | None:
    match = re.search(
        r"\bis\s+(.+?)(?=\s+and\s+(?:flow|controller)\b|[.;]|$)",
        description,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    phrase = match.group(1).strip()
    numeric = re.fullmatch(r"(\d+)(?:\s+(?:bits?|bytes?|items?))?", phrase, re.I)
    if numeric is not None:
        return int(numeric.group(1))
    tokens = _tokens(phrase)
    if not tokens or len(tokens) > 6:
        return None
    return "_".join(TOKEN_ALIASES.get(item, item) for item in tokens)


def _identity_name(field: Field, register: Register) -> str | None:
    name = "_".join(_tokens(field.name))
    if name not in {"id", "type", "version", "head"} and not name.endswith(
        ("_id", "_type", "_version", "_head")
    ):
        return None
    if field.bit_width < 8:
        return None
    # Field access is already resolved against the containing register while
    # building Fact IR.  Unknown or writable identity-looking fields are not
    # safe identity evidence.
    if field.access not in {"read", "read-only"}:
        return None
    return _field_semantic_name(field.name, peripheral_name="")


def _tokens(value: str) -> list[str]:
    return [item.lower() for item in _PART.findall(value)]


def _semantic_identifier(tokens: Iterable[str]) -> str:
    value = "_".join(item for item in tokens if item)
    if not value:
        return "value"
    if value[0].isdigit():
        return "value_" + value
    return value


def _is_reserved(value: str) -> bool:
    normalized = "_".join(_tokens(value))
    return normalized.startswith(RESERVED_PREFIXES)


def _ordered_instance_values(
    values: Mapping[str, Any], instance_order: Iterable[str]
) -> dict[str, Any]:
    return {instance: values[instance] for instance in instance_order if instance in values}


def _ordered_parameter_values(
    values: Mapping[str, Mapping[str, Any]],
    instance_order: Iterable[str],
) -> dict[str, dict[str, Any]]:
    return {
        instance: dict(sorted(values[instance].items()))
        for instance in instance_order
        if instance in values
    }


def _add_evidence(
    evidence: dict[str, list[dict[str, str]]],
    capability_id: str,
    *,
    instance: str,
    member: str | None = None,
    kind: str,
    path: str,
    rule: str,
) -> None:
    item = {
        "instance": instance,
        "kind": kind,
        "path": path,
        "rule": rule,
    }
    if member is not None:
        item["member"] = member
    values = evidence.setdefault(capability_id, [])
    if item not in values:
        values.append(item)


def _audit(
    audit: dict[tuple[str, str, str], dict[str, str]],
    *,
    instance: str,
    kind: str,
    path: str,
    reason: str,
) -> None:
    key = (instance, kind, path)
    existing = audit.get(key)
    if existing is not None and existing["reason"] != reason:
        existing["reason"] = "ambiguous_semantics"
        return
    audit[key] = {
        "instance": instance,
        "kind": kind,
        "path": path,
        "reason": reason,
    }
