# 芯片Capability YAML的Schema校验、加载与打包资源定位。
#
# 职责：把V1/V2 Capability和Audit YAML确定性解析为稳定只读模型。
# 边界：不提供业务查询、不读取Bench、不访问Driver/Target，也不包含具体芯片事实。
# 依赖：仅依赖PyYAML、标准库、Capability模型和平台配置异常。

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..core.errors import ConfigurationError
from ._capability_models import (
    _CAPABILITY_ID,
    _SEMANTIC_NAME,
    _V2_CAPABILITY_KEYS,
    CapabilityAudit,
    CapabilityEvidence,
    CapabilityProfile,
    ChipCapabilities,
    InterruptCapability,
    UnclassifiedFact,
    _capability_kind,
)

_SCHEMA_V1 = "et-ip-capability/v1"
_SCHEMA_V2 = "et-ip-capability/v2"
_AUDIT_SCHEMA = "et-capability-audit/v1"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_ROOT_KEYS = {
    "schema",
    "chip",
    "ip",
    "source",
    "instances",
    "generated",
    "manual",
}
_SOURCE_KEYS = {"file", "sha256", "generator_version"}
_INSTANCE_KEYS = {"svd_name"}
_MANUAL_KEYS = {"set", "remove"}
_V2_ROOT_KEYS = {
    "schema",
    "chip",
    "ip",
    "source",
    "instances",
    "capabilities",
    "evidence",
}
_EVIDENCE_KEYS = {"instance", "kind", "path", "rule"}
_EVIDENCE_KINDS = {"peripheral", "register", "field", "interrupt"}
_AUDIT_ROOT_KEYS = {
    "schema",
    "chip",
    "ip",
    "source",
    "unclassified",
}
_AUDIT_ITEM_KEYS = {"instance", "kind", "path", "reason"}


# 查询或构造 load capability profile 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
def load_capability_profile(profile_path: str | Path) -> CapabilityProfile:

    try:
        import yaml
    except ImportError as exc:
        raise ConfigurationError("PyYAML is required to load capability profiles") from exc

    path = Path(profile_path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"cannot read capability profile {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in capability profile {path}: {exc}") from exc

    root = _require_mapping(raw, "capability profile root")
    if root.get("schema") == _SCHEMA_V2:
        return _load_v2_profile(root)

    _require_exact_keys(root, _ROOT_KEYS, "capability profile root")
    if root["schema"] != _SCHEMA_V1:
        raise ConfigurationError(f"unsupported capability schema {root['schema']!r}")

    chip_id = _require_identifier(root["chip"], "chip")
    ip_id = _require_identifier(root["ip"], "ip")
    source = _validate_source(root["source"])
    instances = _validate_instances(root["instances"])

    generated = _require_mapping(root["generated"], "generated")
    _require_exact_keys(generated, {"capabilities"}, "generated")
    generated_capabilities = _validate_capabilities(
        generated["capabilities"],
        ip_id=ip_id,
        instances=instances,
        section="generated.capabilities",
    )

    manual = _require_mapping(root["manual"], "manual")
    _require_exact_keys(manual, _MANUAL_KEYS, "manual")
    manual_set = _validate_capabilities(
        manual["set"],
        ip_id=ip_id,
        instances=instances,
        section="manual.set",
    )
    manual_remove = _validate_remove(
        manual["remove"],
        ip_id=ip_id,
        generated=generated_capabilities,
    )
    conflict = set(manual_set).intersection(manual_remove)
    if conflict:
        raise ConfigurationError(
            "manual.set and manual.remove overlap: " + ", ".join(sorted(conflict))
        )

    effective = dict(generated_capabilities)
    for capability_id in manual_remove:
        del effective[capability_id]
    effective.update(manual_set)

    return CapabilityProfile(
        chip_id=chip_id,
        ip_id=ip_id,
        schema=_SCHEMA_V1,
        source=_freeze_mapping(source),
        _instances=_freeze_mapping(instances),
        _capabilities=_freeze_mapping(effective),
        _evidence=MappingProxyType({}),
    )


# 查询或构造 load capability audit 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
def load_capability_audit(audit_path: str | Path) -> CapabilityAudit:

    try:
        import yaml
    except ImportError as exc:
        raise ConfigurationError("PyYAML is required to load capability audits") from exc

    path = Path(audit_path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"cannot read capability audit {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in capability audit {path}: {exc}") from exc

    root = _require_mapping(raw, "capability audit root")
    _require_exact_keys(root, _AUDIT_ROOT_KEYS, "capability audit root")
    if root["schema"] != _AUDIT_SCHEMA:
        raise ConfigurationError(f"unsupported capability audit schema {root['schema']!r}")
    chip_id = _require_identifier(root["chip"], "chip")
    ip_id = _require_identifier(root["ip"], "ip")
    source = _validate_source(root["source"])
    raw_items = root["unclassified"]
    if not isinstance(raw_items, list):
        raise ConfigurationError("unclassified must be a list")

    items: list[UnclassifiedFact] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw_item in enumerate(raw_items):
        item = _require_mapping(raw_item, f"unclassified[{index}]")
        _require_exact_keys(
            item,
            _AUDIT_ITEM_KEYS,
            f"unclassified[{index}]",
        )
        instance = _require_identifier(item["instance"], f"unclassified[{index}].instance")
        kind = _validate_evidence_kind(item["kind"], f"unclassified[{index}].kind")
        fact_path = _require_svd_path(item["path"], f"unclassified[{index}].path")
        reason = _require_identifier(item["reason"], f"unclassified[{index}].reason")
        key = (instance, kind, fact_path)
        if key in seen:
            raise ConfigurationError(f"unclassified repeats {instance}:{kind}:{fact_path}")
        seen.add(key)
        items.append(
            UnclassifiedFact(
                instance=instance,
                kind=kind,
                path=fact_path,
                reason=reason,
            )
        )

    return CapabilityAudit(
        chip_id=chip_id,
        ip_id=ip_id,
        source=_freeze_mapping(source),
        unclassified=tuple(items),
    )


def _load_v2_profile(root: Mapping[str, Any]) -> CapabilityProfile:
    _require_exact_keys(root, _V2_ROOT_KEYS, "capability profile root")
    chip_id = _require_identifier(root["chip"], "chip")
    ip_id = _require_identifier(root["ip"], "ip")
    source = _validate_source(root["source"])
    instances = _validate_instances(root["instances"])
    capabilities = _validate_v2_capabilities(
        root["capabilities"],
        ip_id=ip_id,
        instances=instances,
    )
    evidence = _validate_v2_evidence(
        root["evidence"],
        capabilities=capabilities,
        instances=instances,
    )
    return CapabilityProfile(
        chip_id=chip_id,
        ip_id=ip_id,
        schema=_SCHEMA_V2,
        source=_freeze_mapping(source),
        _instances=_freeze_mapping(instances),
        _capabilities=_freeze_mapping(capabilities),
        _evidence=MappingProxyType(evidence),
    )


def _validate_v2_capabilities(
    value: Any,
    *,
    ip_id: str,
    instances: Mapping[str, Any],
) -> dict[str, Any]:
    sections = _require_mapping(value, "capabilities")
    _require_exact_keys(sections, _V2_CAPABILITY_KEYS, "capabilities")
    capabilities: dict[str, Any] = {}
    validators = {
        "features": _validate_feature,
        "limits": _validate_numeric_values,
        "options": _validate_option_values,
        "parameters": _validate_parameter_values,
        "interrupts": _validate_interrupt_values,
        "identities": _validate_identity_values,
    }
    singular = {
        "features": "feature",
        "limits": "limit",
        "options": "option",
        "parameters": "parameter",
        "interrupts": "interrupt",
        "identities": "identity",
    }
    for section_name in (
        "features",
        "limits",
        "options",
        "parameters",
        "interrupts",
        "identities",
    ):
        entries = _require_mapping(sections[section_name], f"capabilities.{section_name}")
        for raw_name, raw_value in entries.items():
            name = _require_semantic_name(raw_name, f"capabilities.{section_name} name")
            capability_id = f"{ip_id}.{singular[section_name]}.{name}"
            if capability_id in capabilities:
                raise ConfigurationError(f"duplicate capability {capability_id!r}")
            capabilities[capability_id] = validators[section_name](
                raw_value,
                instances,
                capability_id,
            )
    if not capabilities:
        raise ConfigurationError("capabilities must not be empty")
    return capabilities


def _validate_numeric_values(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> dict[str, int | float]:
    def validate(raw: Any, _instance: str) -> int | float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConfigurationError(f"{capability_id!r} values must be numeric")
        return raw

    return _validate_typed_instance_values(
        value,
        instances=instances,
        capability_id=capability_id,
        validator=validate,
    )


def _validate_option_values(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> dict[str, tuple[Any, ...]]:
    return _validate_typed_instance_values(
        value,
        instances=instances,
        capability_id=capability_id,
        validator=lambda raw, instance: _validate_options(raw, capability_id, instance),
    )


def _validate_interrupt_values(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> dict[str, InterruptCapability]:
    def validate(raw: Any, instance: str) -> InterruptCapability:
        item = _require_mapping(raw, f"{capability_id}.{instance}")
        _require_exact_keys(
            item,
            {"svd_name", "irqn"},
            f"{capability_id}.{instance}",
        )
        svd_name = _require_non_empty_string(
            item["svd_name"], f"{capability_id}.{instance}.svd_name"
        )
        irqn = item["irqn"]
        if isinstance(irqn, bool) or not isinstance(irqn, int) or irqn < 0:
            raise ConfigurationError(
                f"{capability_id}.{instance}.irqn must be a non-negative integer"
            )
        return InterruptCapability(svd_name=svd_name, irqn=irqn)

    return _validate_typed_instance_values(
        value,
        instances=instances,
        capability_id=capability_id,
        validator=validate,
    )


def _validate_identity_values(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> dict[str, str | int]:
    def validate(raw: Any, _instance: str) -> str | int:
        if isinstance(raw, bool) or not isinstance(raw, (str, int)):
            raise ConfigurationError(f"{capability_id!r} values must be strings or integers")
        return raw

    return _validate_typed_instance_values(
        value,
        instances=instances,
        capability_id=capability_id,
        validator=validate,
    )


def _validate_parameter_values(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> dict[str, dict[str, str | int | float | bool]]:
    def validate(
        raw: Any,
        instance: str,
    ) -> dict[str, str | int | float | bool]:
        members = _require_mapping(raw, f"{capability_id}.{instance}")
        if not members:
            raise ConfigurationError(f"{capability_id}.{instance} must define at least one member")
        result: dict[str, str | int | float | bool] = {}
        for raw_member, raw_value in members.items():
            member = _require_semantic_name(
                raw_member,
                f"{capability_id}.{instance} member",
            )
            if raw_value is None or isinstance(raw_value, (dict, list)):
                raise ConfigurationError(f"{capability_id}.{instance}.{member} must be scalar")
            if not isinstance(raw_value, (str, int, float, bool)):
                raise ConfigurationError(
                    f"{capability_id}.{instance}.{member} has unsupported value type"
                )
            result[member] = raw_value
        return result

    return _validate_typed_instance_values(
        value,
        instances=instances,
        capability_id=capability_id,
        validator=validate,
    )


def _validate_typed_instance_values(
    value: Any,
    *,
    instances: Mapping[str, Any],
    capability_id: str,
    validator: Callable[[Any, str], Any],
) -> dict[str, Any]:
    raw_values = _require_mapping(value, capability_id)
    if not raw_values:
        raise ConfigurationError(f"{capability_id!r} must define at least one instance value")
    values: dict[str, Any] = {}
    for instance, raw_value in raw_values.items():
        if not isinstance(instance, str) or instance not in instances:
            raise ConfigurationError(f"{capability_id!r} references unknown instance {instance!r}")
        values[instance] = validator(raw_value, instance)
    return values


def _validate_v2_evidence(
    value: Any,
    *,
    capabilities: Mapping[str, Any],
    instances: Mapping[str, Any],
) -> dict[str, tuple[CapabilityEvidence, ...]]:
    raw_evidence = _require_mapping(value, "evidence")
    _require_matching_evidence_capabilities(raw_evidence, capabilities)
    return {
        capability_id: _validate_capability_evidence(
            capability_id,
            raw_items,
            capabilities=capabilities,
            instances=instances,
        )
        for capability_id, raw_items in raw_evidence.items()
    }


def _require_matching_evidence_capabilities(
    raw_evidence: Mapping[str, Any],
    capabilities: Mapping[str, Any],
) -> None:
    unknown = set(raw_evidence) - set(capabilities)
    missing = set(capabilities) - set(raw_evidence)
    if unknown or missing:
        raise ConfigurationError(
            "evidence: "
            + _format_set_difference(
                missing,
                unknown,
                missing_label="missing",
                extra_label="unknown",
            )
        )


def _validate_capability_evidence(
    capability_id: str,
    raw_items: Any,
    *,
    capabilities: Mapping[str, Any],
    instances: Mapping[str, Any],
) -> tuple[CapabilityEvidence, ...]:
    if not isinstance(raw_items, list) or not raw_items:
        raise ConfigurationError(f"evidence for {capability_id!r} must be a non-empty list")
    capability_kind = _capability_kind(capability_id)
    items: list[CapabilityEvidence] = []
    seen: set[tuple[str, str, str, str, str | None]] = set()
    for index, raw_item in enumerate(raw_items):
        item = _parse_capability_evidence_item(
            capability_id,
            capability_kind,
            index,
            raw_item,
            instances=instances,
        )
        key = (
            item.instance,
            item.kind,
            item.path,
            item.rule,
            item.member,
        )
        if key in seen:
            raise ConfigurationError(
                f"evidence for {capability_id!r} repeats {item.instance}:{item.kind}:{item.path}"
            )
        seen.add(key)
        items.append(item)
    _require_matching_evidence_instances(
        capability_id,
        items,
        capabilities=capabilities,
    )
    if capability_kind == "parameter":
        _require_matching_parameter_members(
            capability_id,
            items,
            capabilities=capabilities,
        )
    return tuple(items)


def _parse_capability_evidence_item(
    capability_id: str,
    capability_kind: str,
    index: int,
    raw_item: Any,
    *,
    instances: Mapping[str, Any],
) -> CapabilityEvidence:
    context = f"evidence.{capability_id}[{index}]"
    item = _require_mapping(raw_item, context)
    expected_keys = set(_EVIDENCE_KEYS)
    if capability_kind == "parameter":
        expected_keys.add("member")
    _require_exact_keys(item, expected_keys, context)
    instance = item["instance"]
    if not isinstance(instance, str) or instance not in instances:
        raise ConfigurationError(
            f"evidence for {capability_id!r} references unknown instance {instance!r}"
        )
    member = (
        _require_semantic_name(item["member"], f"{context}.member")
        if capability_kind == "parameter"
        else None
    )
    return CapabilityEvidence(
        instance=instance,
        kind=_validate_evidence_kind(item["kind"], f"{context}.kind"),
        path=_require_svd_path(item["path"], f"{context}.path"),
        rule=_require_identifier(item["rule"], f"{context}.rule"),
        member=member,
    )


def _require_matching_evidence_instances(
    capability_id: str,
    items: list[CapabilityEvidence],
    *,
    capabilities: Mapping[str, Any],
) -> None:
    expected = set(capabilities[capability_id])
    actual = {item.instance for item in items}
    if actual != expected:
        raise ConfigurationError(
            f"evidence for {capability_id!r}: "
            + _format_set_difference(
                expected - actual,
                actual - expected,
                missing_label="missing instances",
                extra_label="extra instances",
            )
        )


def _require_matching_parameter_members(
    capability_id: str,
    items: list[CapabilityEvidence],
    *,
    capabilities: Mapping[str, Any],
) -> None:
    expected = {
        (instance, member)
        for instance, members in capabilities[capability_id].items()
        for member in members
    }
    actual = {(item.instance, item.member) for item in items}
    if actual != expected:
        raise ConfigurationError(
            f"evidence for {capability_id!r}: "
            + _format_set_difference(
                expected - actual,
                actual - expected,
                missing_label="missing members",
                extra_label="extra members",
                formatter=lambda item: f"{item[0]}.{item[1]}",
            )
        )


def _format_set_difference(
    missing: set[Any],
    extra: set[Any],
    *,
    missing_label: str,
    extra_label: str,
    formatter: Callable[[Any], str] = str,
) -> str:
    details: list[str] = []
    if missing:
        details.append(missing_label + " " + ", ".join(formatter(item) for item in sorted(missing)))
    if extra:
        details.append(extra_label + " " + ", ".join(formatter(item) for item in sorted(extra)))
    return "; ".join(details)


# 查询或构造 load chip capabilities 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
def load_chip_capabilities(profile_dir: str | Path) -> ChipCapabilities:

    directory = Path(profile_dir)
    if not directory.is_dir():
        raise ConfigurationError(f"capability profile directory does not exist: {directory}")
    files = sorted(directory.glob("*.yaml"), key=lambda item: item.name)
    if not files:
        raise ConfigurationError(
            f"capability profile directory contains no YAML files: {directory}"
        )

    profiles: dict[str, CapabilityProfile] = {}
    chip_id: str | None = None
    schema: str | None = None
    for path in files:
        profile = load_capability_profile(path)
        if path.stem != profile.ip_id:
            raise ConfigurationError(
                f"capability file {path.name!r} must be named {profile.ip_id}.yaml"
            )
        if chip_id is None:
            chip_id = profile.chip_id
        elif profile.chip_id != chip_id:
            raise ConfigurationError(
                f"capability directory mixes chips {chip_id!r} and {profile.chip_id!r}"
            )
        if schema is None:
            schema = profile.schema
        elif profile.schema != schema:
            raise ConfigurationError(
                f"capability directory mixes schemas {schema!r} and {profile.schema!r}"
            )
        if profile.ip_id in profiles:
            raise ConfigurationError(f"duplicate capability profile for IP {profile.ip_id!r}")
        profiles[profile.ip_id] = profile

    if chip_id is None or schema is None:
        raise ConfigurationError("capability profile directory produced no effective profiles")
    return ChipCapabilities(
        chip_id=chip_id,
        schema=schema,
        _profiles=MappingProxyType(profiles),
    )


# 查询或构造 load packaged chip capabilities 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
@cache
def load_packaged_chip_capabilities(chip_id: str) -> ChipCapabilities:

    normalized_chip = _require_identifier(chip_id, "chip_id")
    profile_dir = Path(__file__).resolve().parent / "chip_capabilities" / normalized_chip / "ip"
    capabilities = load_chip_capabilities(profile_dir)
    if capabilities.chip_id != normalized_chip:
        raise ConfigurationError(
            f"packaged profile {normalized_chip!r} contains chip {capabilities.chip_id!r}"
        )
    return capabilities


def _validate_source(value: Any) -> dict[str, Any]:
    source = _require_mapping(value, "source")
    _require_exact_keys(source, _SOURCE_KEYS, "source")
    file_name = source["file"]
    sha256 = source["sha256"]
    version = source["generator_version"]
    if not isinstance(file_name, str) or not file_name.strip():
        raise ConfigurationError("source.file must be a non-empty string")
    if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
        raise ConfigurationError("source.sha256 must contain 64 hex digits")
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise ConfigurationError("source.generator_version must be a positive integer")
    return {
        "file": file_name,
        "sha256": sha256.upper(),
        "generator_version": version,
    }


def _validate_instances(value: Any) -> dict[str, dict[str, str]]:
    raw_instances = _require_mapping(value, "instances")
    if not raw_instances:
        raise ConfigurationError("instances must not be empty")
    instances: dict[str, dict[str, str]] = {}
    for instance_id, raw_metadata in raw_instances.items():
        normalized = _require_identifier(instance_id, "instance ID")
        metadata = _require_mapping(raw_metadata, f"instances.{normalized}")
        _require_exact_keys(metadata, _INSTANCE_KEYS, f"instances.{normalized}")
        svd_name = metadata["svd_name"]
        if not isinstance(svd_name, str) or not svd_name.strip():
            raise ConfigurationError(f"instances.{normalized}.svd_name must be non-empty")
        instances[normalized] = {"svd_name": svd_name}
    return instances


def _validate_capabilities(
    value: Any,
    *,
    ip_id: str,
    instances: Mapping[str, Any],
    section: str,
) -> dict[str, Any]:
    raw_capabilities = _require_mapping(value, section)
    capabilities: dict[str, Any] = {}
    for capability_id, raw_value in raw_capabilities.items():
        if not isinstance(capability_id, str) or not _CAPABILITY_ID.fullmatch(capability_id):
            raise ConfigurationError(f"{section} contains invalid capability ID {capability_id!r}")
        if not capability_id.startswith(f"{ip_id}."):
            raise ConfigurationError(f"{capability_id!r} does not belong to IP {ip_id!r}")
        kind = _capability_kind(capability_id)
        if kind == "feature":
            capabilities[capability_id] = _validate_feature(raw_value, instances, capability_id)
        else:
            capabilities[capability_id] = _validate_values_by_instance(
                raw_value,
                instances=instances,
                capability_id=capability_id,
                kind=kind,
            )
    return capabilities


def _validate_feature(
    value: Any,
    instances: Mapping[str, Any],
    capability_id: str,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{capability_id!r} must contain a non-empty instance list")
    result: list[str] = []
    for instance in value:
        if not isinstance(instance, str) or instance not in instances:
            raise ConfigurationError(f"{capability_id!r} references unknown instance {instance!r}")
        if instance in result:
            raise ConfigurationError(f"{capability_id!r} repeats instance {instance!r}")
        result.append(instance)
    return tuple(result)


def _validate_values_by_instance(
    value: Any,
    *,
    instances: Mapping[str, Any],
    capability_id: str,
    kind: str,
) -> dict[str, Any]:
    raw_values = _require_mapping(value, capability_id)
    if not raw_values:
        raise ConfigurationError(f"{capability_id!r} must define at least one instance value")
    values: dict[str, Any] = {}
    for instance, raw_value in raw_values.items():
        if not isinstance(instance, str) or instance not in instances:
            raise ConfigurationError(f"{capability_id!r} references unknown instance {instance!r}")
        if kind == "limit":
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ConfigurationError(
                    f"{capability_id!r} limit for {instance!r} must be numeric"
                )
            values[instance] = raw_value
        elif kind == "option":
            values[instance] = _validate_options(raw_value, capability_id, instance)
        elif kind == "identity":
            if isinstance(raw_value, bool) or not isinstance(raw_value, (str, int)):
                raise ConfigurationError(
                    f"{capability_id!r} identity for {instance!r} must be a string or integer"
                )
            values[instance] = raw_value
        else:
            raise ConfigurationError(f"unsupported capability kind {kind!r}")
    return values


def _validate_options(
    value: Any,
    capability_id: str,
    instance: str,
) -> tuple[Any, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{capability_id!r} options for {instance!r} must be non-empty")
    result: list[Any] = []
    for option in value:
        if option is None or isinstance(option, (dict, list)):
            raise ConfigurationError(f"{capability_id!r} contains a non-scalar option")
        if option in result:
            raise ConfigurationError(f"{capability_id!r} repeats option {option!r}")
        result.append(option)
    return tuple(result)


def _validate_remove(
    value: Any,
    *,
    ip_id: str,
    generated: Mapping[str, Any],
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigurationError("manual.remove must be a list")
    result: list[str] = []
    for capability_id in value:
        if not isinstance(capability_id, str):
            raise ConfigurationError("manual.remove entries must be capability IDs")
        if not _CAPABILITY_ID.fullmatch(capability_id):
            raise ConfigurationError(
                f"manual.remove contains invalid capability ID {capability_id!r}"
            )
        if not capability_id.startswith(f"{ip_id}."):
            raise ConfigurationError(f"{capability_id!r} does not belong to IP {ip_id!r}")
        if capability_id not in generated:
            raise ConfigurationError(
                f"manual.remove references non-generated capability {capability_id!r}"
            )
        if capability_id in result:
            raise ConfigurationError(f"manual.remove repeats {capability_id!r}")
        result.append(capability_id)
    return tuple(result)


def _require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ConfigurationError(f"{label} must match {_IDENTIFIER.pattern!r}")
    return value


def _require_semantic_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SEMANTIC_NAME.fullmatch(value):
        raise ConfigurationError(f"{label} must match {_SEMANTIC_NAME.pattern!r}")
    return value


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty string")
    return value


def _require_svd_path(value: Any, label: str) -> str:
    path = _require_non_empty_string(value, label)
    if "/" in path or "\\" in path or ":" in path:
        raise ConfigurationError(f"{label} must be an SVD logical path, not a filesystem path")
    return path


def _validate_evidence_kind(value: Any, label: str) -> str:
    if not isinstance(value, str) or value not in _EVIDENCE_KINDS:
        raise ConfigurationError(f"{label} must be one of {', '.join(sorted(_EVIDENCE_KINDS))}")
    return value


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be a mapping")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if extra:
            details.append("unknown " + ", ".join(sorted(extra)))
        raise ConfigurationError(f"{label}: {'; '.join(details)}")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            frozen[key] = _freeze_mapping(item)
        elif isinstance(item, list):
            frozen[key] = tuple(item)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)
